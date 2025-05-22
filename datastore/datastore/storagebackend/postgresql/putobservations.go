package postgresql

import (
	"database/sql"
	"datastore/common"
	"datastore/datastore"
	"fmt"
	"log"
	"reflect"
	"slices"
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

func getUpsertStatement(nRows int) string {

	cols := getTSColNames()
	colsUnique := getTSColNamesUnique()

	valuesColumns := []string{}
	for _, col := range getTSColNames() {
		valuesColumns = append(valuesColumns, fmt.Sprintf("(NULL::time_series).%s", col))
	}

	formats := make([]string, nRows)
	index := 1
	for i := 0; i < nRows; i++ {
		oneRow := make([]string, len(cols))
		for j := 0; j < len(cols); j++ {
			oneRow[j] = fmt.Sprintf("$%d", index)
			index += 1
		}
		formats[i] = "(" + strings.Join(oneRow, ",") + ")"
	}

	updateExpr := []string{}
	for _, col := range getTSColNamesUniqueCompl() {
		updateExpr = append(updateExpr, fmt.Sprintf("%s = EXCLUDED.%s", col, col))
	}

	updateWhereExpr := []string{}
	for _, col := range getTSColNamesUniqueCompl() {
		updateWhereExpr = append(updateWhereExpr, fmt.Sprintf("time_series.%s IS DISTINCT FROM EXCLUDED.%s", col, col))
	}

	// This uses https://stackoverflow.com/a/42217872 under "Without concurrent write load",
	// with the following modifications:
	// 1. Using ON CONFLICT UPDATE (instead of NOTHING), but only doing an update if at least one of the values
	//    actually changed (to avoid table trashing).
	// 2. Use approach 5 of https://stackoverflow.com/a/12427434 to avoid having to provide types for the input VALUES
	// 3. Deal with "Concurrency issue 1" by retrying the whole query is returned number of rows is wrong.
	// 4. Deal with deadlocks by ordering the data
	// TODO?: Look at "Concurrency issue 2"
	insertCmd := fmt.Sprintf(`
		WITH input_rows AS (
			SELECT * FROM (
				SELECT * FROM (
					VALUES
						(%s), -- header column to get correct column types
						%s    -- actual values
				) t (%s) OFFSET 1
			) t ORDER BY %s   -- ORDER BY for consistent order to avoid deadlocks
		)
		, ins AS (
			INSERT INTO time_series (%s)
				SELECT * FROM input_rows
				ON CONFLICT ON CONSTRAINT unique_main
					DO UPDATE SET %s  -- do update of fields not in unique constraint
						WHERE %s      -- only if at least one value is actually different, to avoid table trashing
				RETURNING id, %s  -- RETURNING only gives back rows that were actually inserterd or modified
		)
		SELECT id, %s  -- magic to get the id's for all rows'
		FROM   ins
		UNION
		SELECT ts.id, %s
		FROM   input_rows
		JOIN   time_series ts USING (%s);
		`,
		strings.Join(valuesColumns, ","),
		strings.Join(formats, ","),
		strings.Join(cols, ","),
		strings.Join(colsUnique, ","),
		strings.Join(cols, ","),
		strings.Join(updateExpr, ","),
		strings.Join(updateWhereExpr, " OR "),
		strings.Join(colsUnique, ","),
		strings.Join(colsUnique, ","),
		strings.Join(colsUnique, ","),
		strings.Join(colsUnique, ","),
	)
	//log.Printf("%v", insertCmd)
	return insertCmd
}

// upsertTSs returns a map that can be used up to look up the timeseries ID for a timeseries.
// The key is based on the values of the columns in the unique constraint of the table.
//
// UpsertTSs inserts a new row if necessary.
// If the row already existed, the function ensures that the row is updated with the tsMdata.
//
// Returns (map, nil) upon success, otherwise (..., error).
func upsertTSs(
	db *sql.DB, observations []*datastore.Metadata1) (map[string]int64, error) {

	mapTScolVals := map[string][]interface{}{}
	mapTScolValsConstraint := map[string][]interface{}{}

	// Collect all unique timeseries values by constraint.
	// If there are observations that have the same unique constraint value, last one wins.
	// This looks like premature optimisation... but it is not. Postgres will throw error on duplicates in the INSERT
	for _, obs := range observations {
		tsMdata := obs.GetTsMdata()
		colVals, colValsUnique, err := getTSColVals(tsMdata)
		if err != nil {
			return nil, fmt.Errorf("getTSColVals() failed: %v", err)
		}

		cacheKey := fmt.Sprintf("%v", colValsUnique)
		//log.Printf("cachkeKey: %v", cacheKey)
		mapTScolVals[cacheKey] = colVals
		mapTScolValsConstraint[cacheKey] = colValsUnique
	}

	phVals := []interface{}{}
	phValsConstraint := []interface{}{}

	for _, colVals := range mapTScolVals {
		phVals = append(phVals, colVals...)

	}
	for _, colValsUnique := range mapTScolValsConstraint {
		phValsConstraint = append(phValsConstraint, colValsUnique...)
	}

	insertCmd := getUpsertStatement(len(mapTScolVals))

	//log.Printf("Before row insert")
	for range 3 { // try at most 3 times
		rows, err := db.Query(insertCmd, phVals...)
		if err != nil {
			// TODO: Put this in a helper function... but we still need to see the line number of the calling function!
			log.Printf("db.Query() failed: %v", err)
			if e, ok := err.(*pq.Error); ok {
				if len(e.Detail) > 0 {
					log.Printf("db.Query() failed: DETAIL: %v", e.Detail)
				}
				if len(e.Hint) > 0 {
					log.Printf("db.Query() failed: HINT: %v", e.Hint)
				}
			}
			return nil, fmt.Errorf("tx.Query() failed: %v", err)
		}

		//log.Printf("After select query")

		defer rows.Close()
		colNamesUnique := getTSColNamesUnique()
		var tsID int64
		colValsStrings := make([]interface{}, len(colNamesUnique))
		colValPtrs := []interface{}{&tsID}
		for i := range colNamesUnique {
			colValPtrs = append(colValPtrs, &colValsStrings[i])
		}

		tsIDmap := map[string]int64{}
		for rows.Next() {
			rows.Scan(colValPtrs...)
			tsIDmap[fmt.Sprintf("%v", colValsStrings)] = tsID
		}
		//log.Printf("After getting data from rows query")

		// Under concurrent load, if another process is adding the same entry, in which case this transaction
		// waited for it to complete. Once completed, this transaction would not change it (because of the WHERE),
		// and therefore not return the row. The SELECT would also not return it, because it see the snapshot
		// at the start of this transaction.
		// A simple solution is to just rerun the query.
		// See under "Concurrency issue 1" for a similar case here: https://stackoverflow.com/a/42217872
		if len(tsIDmap) == len(mapTScolVals) {
			return tsIDmap, nil
		}
		log.Printf("In upsertTSs(): concurrency issue detected: 'len(tsIDmap)=%v', 'len(mapTScolVals)=%v', "+
			"retrying db query...", len(tsIDmap), len(mapTScolVals))
	}
	return nil, fmt.Errorf("upsertTSs() failed: still concurrency issues afer 3 retries")
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

// TODO: Update comments
// getGeoPointID retrieves the ID of the row in table geo_point that matches point,
// inserting a new row if necessary. The ID is first looked up in a cache in order to save
// unnecessary database access.
// Returns (ID, nil) upon success, otherwise (..., error).
func getGeoPointIDs(db *sql.DB, observations []*datastore.Metadata1) (map[string]int64, error) {

	valsExpr := []string{}
	phVals := []interface{}{}

	// TODO: Clean up point handling in maps... struct versus string
	type p struct {
		lon float64
		lat float64
	}
	// Collect all unique points
	// This looks like premature optimisation... but it is not. Postgres will throw error on duplicates in the INSERT
	points := map[p]bool{}
	for _, obs := range observations {
		point := obs.GetObsMdata().GetGeoPoint()
		points[p{point.Lon, point.Lat}] = true
	}

	index := 0
	// Loop over unique points
	for point := range points {
		// TODO: CLean this up
		valsExpr0 := fmt.Sprintf(`(ST_MakePoint($%d, $%d)::geography)`,
			index+1,
			index+2,
		)
		phVals0 := []interface{}{point.lon, point.lat}

		valsExpr = append(valsExpr, valsExpr0)
		phVals = append(phVals, phVals0...)
		index += len(phVals0)
	}

	// This uses https://stackoverflow.com/a/42217872 under "Without concurrent write load",
	// with the following modifications:
	// 1. Deal with "Concurrency issue 1" by retrying the whole query is returned number of rows is wrong.
	// 2. Deal with deadlocks by ordering the data
	// TODO?: Look at "Concurrency issue 2"
	cmd := fmt.Sprintf(`
	WITH input_rows AS (
		SELECT * FROM (
			(SELECT point FROM geo_point LIMIT 0)  -- only copies column names and types
			UNION ALL
			VALUES %s
		) t ORDER BY point  -- ORDER BY for consistent order to avoid deadlocks
	)
   , ins AS (
		INSERT INTO geo_point (point)
			SELECT * FROM input_rows
			ON CONFLICT (point) DO NOTHING
			RETURNING id, point
	)
	SELECT id, ST_X(point::geometry), ST_Y(point::geometry) FROM ins
	UNION
	SELECT c.id, ST_X(c.point::geometry), ST_Y(c.point::geometry) FROM input_rows
	JOIN geo_point c USING (point)
	`, strings.Join(valsExpr, ","))

	for range 3 { // try at most 3 times
		rows, err := db.Query(cmd, phVals...)
		if err != nil {
			log.Printf("db.Query() failed: %v", err)
			if e, ok := err.(*pq.Error); ok {
				if len(e.Detail) > 0 {
					log.Printf("db.Query() failed: DETAIL: %v", e.Detail)
				}
				if len(e.Hint) > 0 {
					log.Printf("db.Query() failed: HINT: %v", e.Hint)
				}
			}
			return nil, fmt.Errorf("tx.Query() failed: %v", err)
		}

		gpIDmap := map[string]int64{}
		var id int64
		var x, y float64
		for rows.Next() {
			rows.Scan(&id, &x, &y)
			gpIDmap[fmt.Sprintf("%v %v", x, y)] = id
		}

		// Under concurrent load, if another process is adding the same entry, in which case this transaction
		// waited for it to complete. Once completed, this transaction would not change it (because of the WHERE),
		// and therefore not return the row. The SELECT would also not return it, because it see the snapshot
		// at the start of this transaction.
		// A simple solution is to just rerun the query.
		// See under "Concurrency issue 1" for a similar case here: https://stackoverflow.com/a/42217872
		if len(gpIDmap) == len(points) {
			return gpIDmap, nil
		}
		log.Printf("In getGeoPointIDs(): concurrency issue detected: 'len(gpIDmap)=%v', 'len(points)=%v', "+
			"retrying db query...", len(gpIDmap), len(points))
	}
	return nil, fmt.Errorf("getGeoPointIDs() failed: still concurrency issues afer 3 retries")
}

// createInsertVals generates from (tsID, obsTimes, gpIDs, and omds) two arrays:
//   - in valsExpr: the list of arguments to the VALUES clause in the SQL INSERT
//     statement, and
//   - in phVals: the total, flat list of all placeholder values.
func createInsertVals(
	tsInfos map[int64]tsInfo, valsExpr *[]string, phVals *[]interface{}) {

	index := 0
	for tsID, tsInfo := range tsInfos {
		obsTimes := tsInfo.obsTimes
		omds := tsInfo.omds
		gpIDs := tsInfo.gpIDs
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
}

// upsertObs inserts new observations and/or updates existing ones.
//
// Returns nil upon success, otherwise error.
func upsertObs(
	db *sql.DB, tsInfos map[int64]tsInfo) error {
	//db *sql.DB, tsID int64, obsTimes *[]*timestamppb.Timestamp, gpIDs *[]int64,
	//omds *[]*datastore.ObsMetadata) error {

	for _, tsInfo := range tsInfos {
		obsTimes := tsInfo.obsTimes
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
	}

	valsExpr := []string{}
	phVals := []interface{}{}
	createInsertVals(tsInfos, &valsExpr, &phVals)

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
		ON CONFLICT ON CONSTRAINT observation_pkey DO UPDATE
		SET
	    	id = EXCLUDED.id,
	 		geo_point_id = EXCLUDED.geo_point_id,
	 		pubtime = EXCLUDED.pubtime,
	 		data_id = EXCLUDED.data_id,
	 		history = EXCLUDED.history,
	 		processing_level = EXCLUDED.processing_level,
			quality_code = EXCLUDED.quality_code,
			camsl = EXCLUDED.camsl,
	 		value = EXCLUDED.value
		WHERE
		    observation.id IS DISTINCT FROM EXCLUDED.id OR
			observation.geo_point_id IS DISTINCT FROM EXCLUDED.geo_point_id OR
			observation.pubtime IS DISTINCT FROM EXCLUDED.pubtime OR
			observation.data_id IS DISTINCT FROM EXCLUDED.data_id OR
			observation.history IS DISTINCT FROM EXCLUDED.history OR
			observation.processing_level IS DISTINCT FROM EXCLUDED.processing_level OR
			observation.quality_code IS DISTINCT FROM EXCLUDED.quality_code OR
			observation.camsl IS DISTINCT FROM EXCLUDED.camsl
	`, strings.Join(valsExpr, ","))

	_, err := db.Exec(cmd, phVals...)
	if err != nil {
		log.Printf("db.Exec() failed: %v", err)
		if e, ok := err.(*pq.Error); ok {
			if len(e.Detail) > 0 {
				log.Printf("db.Exec() failed: DETAIL: %v", e.Detail)
			}
			if len(e.Hint) > 0 {
				log.Printf("db.Exec() failed: HINT: %v", e.Hint)
			}
		}
		return fmt.Errorf("db.Exec() failed: %v", err)
	}

	return nil
}

type tsInfo struct {
	obsTimes *[]*timestamppb.Timestamp
	gpIDs    *[]int64 // geo point IDs
	omds     *[]*datastore.ObsMetadata
}

// PutObservations ... (see documentation in StorageBackend interface)
func (sbe *PostgreSQL) PutObservations(request *datastore.PutObsRequest) (codes.Code, string) {

	// TODO: Move this to init
	log.SetFlags(log.LstdFlags | log.Lmicroseconds | log.Lshortfile)
	log.Printf("Entered PutObservations with %v observations...", len(request.Observations))

	// Chunk observations by 2000, as otherwise the SQL queries have to many parameters
	for observations := range slices.Chunk(request.Observations, 1000) {
		tsInfos := map[int64]tsInfo{}

		loTime, hiTime := common.GetValidTimeRange()

		// reject call if # of observations exceeds limit
		if len(observations) > putObsLimit {
			return codes.OutOfRange, fmt.Sprintf(
				"too many observations in a single call: %d > %d",
				len(observations), putObsLimit)
		}

		gpIDMap, err := getGeoPointIDs(sbe.Db, observations)
		if err != nil {
			return codes.Internal, fmt.Sprintf("getGeoPointIDs() failed: %v", err)
		}

		//log.Printf("Returned %v unique points", len(gpIDMap))

		tsIDMap, err := upsertTSs(sbe.Db, observations)
		if err != nil {
			return codes.Internal, fmt.Sprintf("upsertTSs() failed: %v", err)
		}
		//log.Printf("Returned %v unique timseries", len(tsIDMap))

		// populate tsInfos
		for _, obs := range observations {

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

			// Look up timeseries key.
			// TODO: This feels inefficient, calling getTSColVals again...
			tsMdata := obs.GetTsMdata()
			_, colValsUnique, err := getTSColVals(tsMdata)
			if err != nil {
				return codes.Internal, fmt.Sprintf("getTSColVals() failed: %v", err)
			}
			key := fmt.Sprintf("%v", colValsUnique)
			tsID := tsIDMap[key]

			point := obs.GetObsMdata().GetGeoPoint()
			gpID := gpIDMap[fmt.Sprintf("%v %v", point.GetLon(), point.GetLat())]

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

		//log.Printf("Got tsInfo of size %v...", len(tsInfos))

		// insert/update observations for all time series in this chunck
		if err := upsertObs(sbe.Db, tsInfos); err != nil {
			return codes.Internal, fmt.Sprintf("upsertObs() failed: %v", err)
		}

		//log.Printf("Inserted observations")
	}

	return codes.OK, ""
}
