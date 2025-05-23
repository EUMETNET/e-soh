package postgresql

import (
	"database/sql"
	"datastore/common"
	"datastore/datastore"
	"fmt"
	"reflect"
	"strings"

	"github.com/lib/pq"
	"google.golang.org/grpc/codes"
	"google.golang.org/protobuf/types/known/timestamppb"
)

// getTSColVals gets the time series metadata column values from tsMdata.
//
// Returns (all column values, column values of constraint unique_main, nil) upon success,
// otherwise (..., ..., error).
func getTSColVals(tsMdata *datastore.TSMetadata) ([]interface{}, []interface{}, error) {

	colVals := []interface{}{}
	colName2Val := map[string]interface{}{}

	// --- BEGIN non-reflectable metadata ---------------------------

	getLinkVals := func(key string) ([]string, error) {
		linkVals := []string{}
		for _, link := range tsMdata.GetLinks() {
			var val string
			switch key {
			case "link_href":
				val = link.GetHref()
			case "link_rel":
				val = link.GetRel()
			case "link_type":
				val = link.GetType()
			case "link_hreflang":
				val = link.GetHreflang()
			case "link_title":
				val = link.GetTitle()
			default:
				return nil, fmt.Errorf("unsupported link key: >%s<", key)
			}
			linkVals = append(linkVals, val)
		}
		return linkVals, nil
	}

	for _, key := range []string{
		"link_href", "link_rel", "link_type", "link_hreflang", "link_title"} {
		if linkVals, err := getLinkVals(key); err != nil {
			return nil, nil, fmt.Errorf("getLinkVals() failed: %v", err)
		} else {
			vals := pq.StringArray(linkVals)
			colVals = append(colVals, vals)
			colName2Val[common.ToSnakeCase(key)] = vals
		}
	}

	// --- END non-reflectable metadata ---------------------------

	rv := reflect.ValueOf(tsMdata)

	// --- BEGIN reflectable metadata of type int64 ---------------------------
	for _, field := range tsInt64StructFields {
		methodName := fmt.Sprintf("Get%s", field.Name)
		method := rv.MethodByName(methodName)
		if method.IsValid() {
			val, ok := method.Call([]reflect.Value{})[0].Interface().(int64)
			if !ok {
				return nil, nil, fmt.Errorf(
					"method.Call() failed for method %s; failed to return int64", methodName)
			}
			colVals = append(colVals, val)
			colName2Val[common.ToSnakeCase(field.Name)] = val
		}
	}
	// --- END reflectable metadata of type int64 ---------------------------

	// --- BEGIN reflectable metadata of type string ---------------------------
	for _, field := range tsStringStructFields {
		methodName := fmt.Sprintf("Get%s", field.Name)
		method := rv.MethodByName(methodName)
		if method.IsValid() {
			val, ok := method.Call([]reflect.Value{})[0].Interface().(string)
			if !ok {
				return nil, nil, fmt.Errorf(
					"method.Call() failed for method %s; failed to return string", methodName)
			}
			colVals = append(colVals, val)
			colName2Val[common.ToSnakeCase(field.Name)] = val
		}
	}
	// --- END reflectable metadata of type string ---------------------------

	// derive colValsUnique from colName2Val
	colValsUnique, err := getTSColValsUnique(colName2Val)
	if err != nil {
		return nil, nil, fmt.Errorf("getTSColValsUnique() failed: %v", err)
	}

	return colVals, colValsUnique, nil
}

// getTSColValsUnique gets the subset of colName2Val that correspond to the fields defined by
// constraint unique_main.
//
// The order in the returned array is consistent with the array returned by getTSColNamesUnique().
//
// Returns (column values, nil) upon success, otherwise (..., error).
func getTSColValsUnique(colName2Val map[string]interface{}) ([]interface{}, error) {

	result := []interface{}{}

	for _, col := range getTSColNamesUnique() {
		colVal, found := colName2Val[col]
		if !found {
			return []interface{}{},
				fmt.Errorf("column '%s' not found in colName2Val: %v", col, colName2Val)
		}
		result = append(result, colVal)
	}

	return result, nil
}

// upsertTS retrieves the ID of the row in table time_series that matches tsMdata wrt.
// the fields - U - defined by constraint unique_main, inserting a new row if necessary.
//
// If the row already existed, the function ensures that the row is updated with the tsMdata
// fields - UC - that are not in U (i.e. the complement of U).
//
// The ID is first looked up in a cache (where the key consists of all fields (U + UC)) in order to
// save unnecessary database access. In other words, a cache hit means that the row for
// time series not only existed, but was also already fully updated according to tsMdata.
// And vice versa: a cache miss means the row either didn't exist at all or wasn't fully updated
// according to tsMdata.
//
// Returns (ID, nil) upon success, otherwise (..., error).
func upsertTS(
	db *sql.DB, tsMdata *datastore.TSMetadata, cache map[string]int64) (int64, error) {

	colVals, colValsUnique, err := getTSColVals(tsMdata)
	if err != nil {
		return -1, fmt.Errorf("getTSColVals() failed: %v", err)
	}

	// first try a cache lookup
	cacheKey := fmt.Sprintf("%v", colVals)
	if id, found := cache[cacheKey]; found {
		return id, nil
	}

	// then access database ...

	// start transaction
	tx, err := db.Begin()
	if err != nil {
		return -1, fmt.Errorf("db.Begin() failed: %v", err)
	}
	defer tx.Rollback()

	// STEP 1: upsert row

	_, err = tx.Exec(upsertTSInsertCmd, colVals...)
	if err != nil {
		return -1, fmt.Errorf("tx.Exec() failed: %v", err)
	}

	// STEP 2: retrieve ID of upserted row

	var id int64

	err = tx.QueryRow(upsertTSSelectCmd, colValsUnique...).Scan(&id)
	if err != nil {
		return -1, fmt.Errorf("tx.QueryRow() failed: %v", err)
	}

	// commit transaction
	if err = tx.Commit(); err != nil {
		return -1, fmt.Errorf("tx.Commit() failed: %v", err)
	}

	// cache ID
	cache[cacheKey] = id

	return id, nil
}

// getObsTime extracts the obs time from obsMdata.
// Returns (obs time, nil) upon success, otherwise (..., error).
func getObsTime(obsMdata *datastore.ObsMetadata) (*timestamppb.Timestamp, error) {
	if obsTime := obsMdata.GetObstimeInstant(); obsTime != nil {
		return obsTime, nil
	}
	return nil, fmt.Errorf("obsMdata.GetObstimeInstant()is nil")
}

// --- BEGIN a variant of getObsTime that also supports intervals ---------------------------------
// getObsTime extracts the obs time from obsMdata as either an instant time or the end of
// an interval.
// Returns (obs time, nil) upon success, otherwise (..., error).
/*
func getObsTime(obsMdata *datastore.ObsMetadata) (*timestamppb.Timestamp, error) {
	if obsTime := obsMdata.GetInstant(); obsTime != nil {
		return obsTime, nil
	}
	if obsTime := obsMdata.GetInterval().GetEnd(); obsTime != nil {
		return obsTime, nil
	}
	return nil, fmt.Errorf("obsMdata.GetInstant() and obsMdata.GetInterval().GetEnd() are both nil")
}
*/
// --- END a variant of getObsTime that also supports intervals ---------------------------------

// getGeoPointID retrieves the ID of the row in table geo_point that matches point,
// inserting a new row if necessary. The ID is first looked up in a cache in order to save
// unnecessary database access.
// Returns (ID, nil) upon success, otherwise (..., error).
func getGeoPointID(db *sql.DB, point *datastore.Point, cache map[string]int64) (int64, error) {

	var id int64 = -1

	// first try a cache lookup
	cacheKey := fmt.Sprintf("%v %v", point.GetLon(), point.GetLat())
	if id, found := cache[cacheKey]; found {
		return id, nil
	}

	// Get a Tx for making transaction requests.
	tx, err := db.Begin()
	if err != nil {
		return -1, fmt.Errorf("db.Begin() failed: %v", err)
	}
	// Defer a rollback in case anything fails.
	defer tx.Rollback()

	// NOTE: the 'WHERE false' is a feature that ensures that another transaction cannot
	// delete the row
	insertCmd := `
		INSERT INTO geo_point (point) VALUES (ST_MakePoint($1, $2)::geography)
		ON CONFLICT (point) DO UPDATE SET point = EXCLUDED.point WHERE false
	`

	_, err = tx.Exec(insertCmd, point.GetLon(), point.GetLat())
	if err != nil {
		return -1, fmt.Errorf("tx.Exec() failed: %v", err)
	}

	selectCmd := "SELECT id FROM geo_point WHERE point = ST_MakePoint($1, $2)::geography"

	err = tx.QueryRow(selectCmd, point.GetLon(), point.GetLat()).Scan(&id)
	if err != nil {
		return -1, fmt.Errorf("tx.QueryRow() failed: %v", err)
	}

	// Commit the transaction.
	if err = tx.Commit(); err != nil {
		return -1, fmt.Errorf("tx.Commit() failed: %v", err)
	}

	// cache ID
	cache[cacheKey] = id

	return id, nil
}

// createInsertVals generates from (tsID, obsTimes, gpIDs, and omds) two arrays:
//   - in valsExpr: the list of arguments to the VALUES clause in the SQL INSERT
//     statement, and
//   - in phVals: the total, flat list of all placeholder values.
func createInsertVals(
	tsID int64, obsTimes *[]*timestamppb.Timestamp, gpIDs *[]int64,
	omds *[]*datastore.ObsMetadata, valsExpr *[]string, phVals *[]interface{}) {
	// assert(len(*obsTimes) > 0)
	// assert(len(*obsTimes) == len(*gpIDs) == len(*omds))

	index := 0
	for i := 0; i < len(*obsTimes); i++ {
		valsExpr0 := fmt.Sprintf(`(
			$%d,
			to_timestamp($%d),
			$%d,
			$%d,
			to_timestamp($%d),
			$%d,
			$%d,
			$%d,
			$%d,
			$%d,
			$%d
			)`,
			index+1,
			index+2,
			index+3,
			index+4,
			index+5,
			index+6,
			index+7,
			index+8,
			index+9,
			index+10,
			index+11,
		)

		phVals0 := []interface{}{
			tsID,
			common.Tstamp2float64Secs((*obsTimes)[i]),
			(*omds)[i].GetId(),
			(*gpIDs)[i],
			common.Tstamp2float64Secs((*omds)[i].GetPubtime()),
			(*omds)[i].GetDataId(),
			(*omds)[i].GetHistory(),
			(*omds)[i].GetProcessingLevel(),
			(*omds)[i].GetQualityCode(),
			(*omds)[i].GetCamsl(),
			(*omds)[i].GetValue(),
		}

		*valsExpr = append(*valsExpr, valsExpr0)
		*phVals = append(*phVals, phVals0...)
		index += len(phVals0)
	}
}

// upsertObs inserts new observations and/or updates existing ones.
//
// Returns nil upon success, otherwise error.
func upsertObs(
	db *sql.DB, tsID int64, obsTimes *[]*timestamppb.Timestamp, gpIDs *[]int64,
	omds *[]*datastore.ObsMetadata) error {

	// assert(obsTimes != nil)
	if obsTimes == nil {
		return fmt.Errorf("precondition failed: obsTimes == nil")
	}

	// assert(len(*obsTimes) > 0)
	if len(*obsTimes) == 0 {
		return fmt.Errorf("precondition failed: len(*obsTimes) == 0")
	}

	// assert(len(*obsTimes) == len(*gpIDs) == len(*omds))
	// for now don't check explicitly for this precondition

	valsExpr := []string{}
	phVals := []interface{}{}
	createInsertVals(tsID, obsTimes, gpIDs, omds, &valsExpr, &phVals)

	cmd := fmt.Sprintf(`
		INSERT INTO observation (
			ts_id,
			obstime_instant,
			id,
			geo_point_id,
			pubtime,
			data_id,
			history,
			processing_level,
			quality_code,
			camsl,
			value)
		VALUES %s
		ON CONFLICT ON CONSTRAINT observation_pkey DO UPDATE SET
	    	id = EXCLUDED.id,
	 		geo_point_id = EXCLUDED.geo_point_id,
	 		pubtime = EXCLUDED.pubtime,
	 		data_id = EXCLUDED.data_id,
	 		history = EXCLUDED.history,
	 		processing_level = EXCLUDED.processing_level,
			quality_code = EXCLUDED.quality_code,
			camsl = EXCLUDED.camsl,
	 		value = EXCLUDED.value
	`, strings.Join(valsExpr, ","))

	_, err := db.Exec(cmd, phVals...)
	if err != nil {
		return fmt.Errorf("db.Exec() failed: %v", err)
	}

	return nil
}

// PutObservations ... (see documentation in StorageBackend interface)
func (sbe *PostgreSQL) PutObservations(request *datastore.PutObsRequest) (codes.Code, string) {

	type tsInfo struct {
		obsTimes *[]*timestamppb.Timestamp
		gpIDs    *[]int64 // geo point IDs
		omds     *[]*datastore.ObsMetadata
	}

	tsInfos := map[int64]tsInfo{}

	tsIDCache := map[string]int64{}
	gpIDCache := map[string]int64{}

	loTime, hiTime := common.GetValidTimeRange()

	// reject call if # of observations exceeds limit
	if len(request.Observations) > putObsLimit {
		return codes.OutOfRange, fmt.Sprintf(
			"too many observations in a single call: %d > %d",
			len(request.Observations), putObsLimit)
	}

	// populate tsInfos
	for _, obs := range request.Observations {

		obsTime, err := getObsTime(obs.GetObsMdata())
		if err != nil {
			return codes.Internal, fmt.Sprintf("getObsTime() failed: %v", err)
		}

		if obsTime.AsTime().Before(loTime) {
			return codes.OutOfRange, fmt.Sprintf(
				"obs time too old: %v < %v (hiTime: %v; settings: %s)",
				obsTime.AsTime(), loTime, hiTime, common.GetValidTimeRangeSettings())
		}

		if obsTime.AsTime().After(hiTime) {
			return codes.OutOfRange, fmt.Sprintf(
				"obs time too new: %v > %v (loTime: %v; settings: %s)",
				obsTime.AsTime(), hiTime, loTime, common.GetValidTimeRangeSettings())
		}

		tsID, err := upsertTS(sbe.Db, obs.GetTsMdata(), tsIDCache)
		if err != nil {
			return codes.Internal, fmt.Sprintf("upsertTS() failed: %v", err)
		}

		gpID, err := getGeoPointID(sbe.Db, obs.GetObsMdata().GetGeoPoint(), gpIDCache)
		if err != nil {
			return codes.Internal, fmt.Sprintf("getGeoPointID() failed: %v", err)
		}

		var obsTimes []*timestamppb.Timestamp
		var gpIDs []int64
		var omds []*datastore.ObsMetadata
		var tsInfo0 tsInfo
		var found bool
		if tsInfo0, found = tsInfos[tsID]; !found {
			obsTimes = []*timestamppb.Timestamp{}
			gpIDs = []int64{}
			omds = []*datastore.ObsMetadata{}
			tsInfos[tsID] = tsInfo{
				obsTimes: &obsTimes,
				gpIDs:    &gpIDs,
				omds:     &omds,
			}
			tsInfo0, found = tsInfos[tsID]
			// assert(found)
			_ = found
		}
		*tsInfo0.obsTimes = append(*tsInfo0.obsTimes, obsTime)
		*tsInfo0.gpIDs = append(*tsInfo0.gpIDs, gpID)
		*tsInfo0.omds = append(*tsInfo0.omds, obs.GetObsMdata())
	}

	// insert/update observations for each time series
	for tsID, tsInfo := range tsInfos {
		if err := upsertObs(
			sbe.Db, tsID, tsInfo.obsTimes, tsInfo.gpIDs, tsInfo.omds); err != nil {
			return codes.Internal, fmt.Sprintf("upsertObs() failed: %v", err)
		}
	}

	return codes.OK, ""
}
