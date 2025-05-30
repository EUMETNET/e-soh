package postgresql

import (
	"database/sql"
	"datastore/common"
	"datastore/datastore"
	"fmt"
	"reflect"
	"strings"
	"time"

	"github.com/cridenour/go-postgis"
	"github.com/lib/pq"
	"google.golang.org/grpc/codes"
	"google.golang.org/protobuf/types/known/timestamppb"
)

// addInt64Mdata assigns the values of colVals to the corresponding struct fields in
// int64MdataGoNames (value i corresponds to field i ...). The struct is represented by rv.
//
// Returns nil upon success, otherwise error.
func addInt64Mdata(rv reflect.Value, int64MdataGoNames []string, colVals []interface{}) error {

	for i, goName := range int64MdataGoNames {
		var val int64

		switch v := colVals[i].(type) {
		case int64:
			val = v
		case sql.NullInt64:
			val = v.Int64
		case nil:
			val = 0
		default:
			return fmt.Errorf("colVals[%d] neither int64, sql.NullInt64, nor nil: %v (type: %T)",
				i, colVals[i], colVals[i])
		}

		field := rv.Elem().FieldByName(goName)

		// NOTE: we assume the following assignment will never panic, hence we don't do
		// any pre-validation of field
		field.SetInt(val)
	}

	return nil
}

// addStringMdata assigns the values of colVals to the corresponding struct fields in
// stringMdataGoNames (value i corresponds to field i ...). The struct is represented by rv.
//
// Returns nil upon success, otherwise error.
func addStringMdata(rv reflect.Value, stringMdataGoNames []string, colVals []interface{}) error {

	for i, goName := range stringMdataGoNames {
		var val string

		switch v := colVals[i].(type) {
		case string:
			val = v
		case sql.NullString:
			val = v.String
		case nil:
			val = ""
		default:
			return fmt.Errorf("colVals[%d] neither string, sql.NullString, nor nil: %v (type: %T)",
				i, colVals[i], colVals[i])
		}

		field := rv.Elem().FieldByName(goName)

		// NOTE: we assume the following assignment will never panic, hence we don't do
		// any pre-validation of field
		field.SetString(val)
	}

	return nil
}

// scanTSRow scans all columns from the current result row in rows and converts to a TSMetadata
// object.
//
// Returns (TSMetadata object, time series ID, nil) upon success, otherwise (..., ..., error).
func scanTSRow(rows *sql.Rows) (*datastore.TSMetadata, int64, error) {

	var (
		tsID         int64
		linkHref     pq.StringArray
		linkRel      pq.StringArray
		linkType     pq.StringArray
		linkHrefLang pq.StringArray
		linkTitle    pq.StringArray
	)

	// initialize colValPtrs with non-reflectable metadata
	colValPtrs := []interface{}{
		&tsID,
		&linkHref,
		&linkRel,
		&linkType,
		&linkHrefLang,
		&linkTitle,
	}

	// extend colValPtrs with reflectable metadata of type int64
	colValsInt64 := make([]interface{}, len(tsInt64MdataGoNames))
	for i := range tsInt64MdataGoNames {
		colValPtrs = append(colValPtrs, &colValsInt64[i])
	}

	// complete colValPtrs with reflectable metadata of type string
	colValsString := make([]interface{}, len(tsStringMdataGoNames))
	for i := range tsStringMdataGoNames {
		colValPtrs = append(colValPtrs, &colValsString[i])
	}

	// scan row into column value pointers
	if err := rows.Scan(colValPtrs...); err != nil {
		return nil, -1, fmt.Errorf("rows.Scan() failed: %v", err)
	}

	// initialize tsMdata with non-reflectable metadata
	links := []*datastore.Link{}
	for i := 0; i < len(linkHref); i++ {
		links = append(links, &datastore.Link{
			Href:     linkHref[i],
			Rel:      linkRel[i],
			Type:     linkType[i],
			Hreflang: linkHrefLang[i],
			Title:    linkTitle[i],
		})
	}
	tsMdata := datastore.TSMetadata{
		Links: links,
	}

	var err error

	// extend tsMdata with reflectable metadata of type int64
	err = addInt64Mdata(reflect.ValueOf(&tsMdata), tsInt64MdataGoNames, colValsInt64)
	if err != nil {
		return nil, -1, fmt.Errorf("addInt64Mdata() failed: %v", err)
	}

	// complete tsMdata with reflectable metadata of type string
	err = addStringMdata(reflect.ValueOf(&tsMdata), tsStringMdataGoNames, colValsString)
	if err != nil {
		return nil, -1, fmt.Errorf("addStringMdata() failed: %v", err)
	}

	return &tsMdata, tsID, nil
}

// includeField returns true iff ((incFields is empty) or (incFields contains field)).
func includeField(incFields common.StringSet, field string) bool {
	return (len(incFields) == 0) || incFields.Contains(field)
}

// getTSMetadata retrieves into tsMdatas metadata of time series in table time_series that match
// tsIDs. The keys of tsMdatas are the time series IDs. Fields to include (as non-NULL values) in
// the final result are defined in incFields.
//
// Returns nil upon success, otherwise error
func getTSMetadata(
	db *sql.DB, tsIDs []string, tsMdatas map[int64]*datastore.TSMetadata,
	incFields common.StringSet) error {

	tsColNames := getTSColNames()

	convTSCN := []string{}
	for _, col := range tsColNames {
		aliases := []string{}
		if strings.HasPrefix(col, "link_") {
			aliases = []string{"links"} // NOTE: 'links' is a "group" field, i.e. collectively
			// representing all columns starting with 'link_'
		}
		convTSCN = append(convTSCN, convertSelectCol(incFields, col, "", aliases...))
	}

	query := fmt.Sprintf(
		`SELECT id, %s FROM time_series WHERE %s`,
		strings.Join(convTSCN, ","),
		createSetFilter("id", tsIDs),
	)

	rows, err := db.Query(query)
	if err != nil {
		return fmt.Errorf("db.Query() failed: %v", err)
	}
	defer rows.Close()

	for rows.Next() {
		tsMdata, tsID, err := scanTSRow(rows)
		if err != nil {
			return fmt.Errorf("scanTSRow() failed: %v", err)
		}

		tsMdatas[tsID] = tsMdata
	}

	return nil
}

// TODO: move to postgresql.go since only used there?
type filterInfo struct {
	colName  string
	patterns []string
}

// TODO: add filter info for non-reflectable types

// getPolygonFilter derives the expression used in a WHERE clause for selecting only
// points inside a polygon.
//
// Values to be used for query placeholders are appended to phVals.
//
// Returns (expression, nil) upon success, otherwise (..., error).
func getPolygonFilter(polygon *datastore.Polygon, phVals *[]interface{}) (string, error) {

	if polygon == nil {
		return "TRUE", nil // don't filter by default
	}

	points := polygon.Points

	equal := func(p1, p2 *datastore.Point) bool {
		return (p1.Lat == p2.Lat) && (p1.Lon == p2.Lon)
	}

	if (len(points) > 0) && !equal(points[0], points[len(points)-1]) {
		points = append(points, points[0]) // close polygon
	}

	if len(points) < 4 {
		return "", fmt.Errorf("polygon contains too few points")
	}

	// construct the polygon ring of the WKT representation
	// (see https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry;
	// note that only a single ring is supported for now)
	polygonRing := []string{}
	for _, point := range points {
		polygonRing = append(polygonRing, fmt.Sprintf("%f %f", point.Lon, point.Lat))
	}

	srid := "4326" // spatial reference system ID

	index := len(*phVals) + 1
	whereExpr := fmt.Sprintf(
		"ST_DWITHIN(point, ST_GeomFromText($%d, %s)::geography, 0.0)", index, srid)
	*phVals = append(*phVals, fmt.Sprintf("polygon((%s))", strings.Join(polygonRing, ",")))

	return whereExpr, nil
}

// getCircleFilter derives the expression used in a WHERE clause for selecting only
// points inside a circle.
//
// Values to be used for query placeholders are appended to phVals.
//
// Returns (expression, nil) upon success, otherwise (..., error).
func getCircleFilter(circle *datastore.Circle, phVals *[]interface{}) (string, error) {

	if circle == nil {
		return "TRUE", nil // don't filter by default
	}

	lat := circle.Center.GetLat()
	if (lat < -90) || (lat > 90) {
		return "", fmt.Errorf("latitude not in range [-90, 90]: %f", lat)
	}

	lon := circle.Center.GetLon()
	if (lon < -180) || (lon > 180) {
		return "", fmt.Errorf("longitude not in range [-180, 180]: %f", lon)
	}

	radius := circle.GetRadius() * 1000 // get radius in meters
	if radius < 0 {
		return "", fmt.Errorf("negative radius not allowed: %f", radius)
	}

	srid := "4326" // spatial reference system ID

	index := len(*phVals) + 1
	whereExpr := fmt.Sprintf(
		"ST_DWithin(point, ST_SetSRID(ST_MakePoint($%d, $%d)::geography, %s), $%d)",
		index, index+1, srid, index+2)
	*phVals = append(*phVals, []interface{}{lon, lat, radius}...)

	return whereExpr, nil
}

// getGeoFilter derives from polygon and circle the expression used in a WHERE clause for keeping
// observations inside both of these areas (i.e. in their intersection).
//
// Values to be used for query placeholders are appended to phVals.
//
// Returns (expression, nil) upon success, otherwise (..., error).
func getGeoFilter(
	polygon *datastore.Polygon, circle *datastore.Circle, phVals *[]interface{}) (string, error) {

	var err error

	polygonExpr, err := getPolygonFilter(polygon, phVals)
	if err != nil {
		return "", fmt.Errorf("getPolygonFilter() failed: %v", err)
	}

	circleExpr, err := getCircleFilter(circle, phVals)
	if err != nil {
		return "", fmt.Errorf("getCircleFilter() failed: %v", err)
	}

	return fmt.Sprintf("(%s) AND (%s)", polygonExpr, circleExpr), nil
}

// scanObsRow scans all columns from the current result row in rows and converts to an ObsMetadata
// object.
// Returns (ObsMetadata object, time series ID, nil) upon success, otherwise (..., ..., error).
func scanObsRow(rows *sql.Rows) (*datastore.ObsMetadata, int64, error) {
	var (
		tsID            int64
		obsTimeInstant0 time.Time
		pubTime0        sql.NullTime
		value           sql.NullString
		point           postgis.PointS
	)

	// initialize colValPtrs with non-reflectable metadata
	colValPtrs := []interface{}{
		&tsID,
		&obsTimeInstant0,
		&pubTime0,
		&value,
		&point,
	}

	// extend colValPtrs with reflectable metadata of type int64
	colValsInt64 := make([]interface{}, len(obsInt64MdataGoNames))
	for i := range obsInt64MdataGoNames {
		colValPtrs = append(colValPtrs, &colValsInt64[i])
	}

	// complete colValPtrs with reflectable metadata of type string
	colValsString := make([]interface{}, len(obsStringMdataGoNames))
	for i := range obsStringMdataGoNames {
		colValPtrs = append(colValPtrs, &colValsString[i])
	}

	// scan row into column value pointers
	if err := rows.Scan(colValPtrs...); err != nil {
		return nil, -1, fmt.Errorf("rows.Scan() failed: %v", err)
	}

	// initialize obsMdata with non-reflectable metadata and obs value
	obsMdata := datastore.ObsMetadata{
		Geometry: &datastore.ObsMetadata_GeoPoint{
			GeoPoint: &datastore.Point{
				Lon: point.X,
				Lat: point.Y,
			},
		},
		Obstime: &datastore.ObsMetadata_ObstimeInstant{
			ObstimeInstant: timestamppb.New(obsTimeInstant0),
		},
		Value: value.String,
	}
	if pubTime0.Valid {
		obsMdata.Pubtime = timestamppb.New(pubTime0.Time)
	}

	var err error

	// extend obsMdata with reflectable metadata of type int64
	err = addInt64Mdata(reflect.ValueOf(&obsMdata), obsInt64MdataGoNames, colValsInt64)
	if err != nil {
		return nil, -1, fmt.Errorf("addInt64Mdata() failed: %v", err)
	}

	// complete obsMdata with reflectable metadata of type string
	err = addStringMdata(reflect.ValueOf(&obsMdata), obsStringMdataGoNames, colValsString)
	if err != nil {
		return nil, -1, fmt.Errorf("addStringMdata() failed: %v", err)
	}

	return &obsMdata, tsID, nil
}

// getIncRespFields extracts the set of included response fields from request.
//
// Returns (set of included response fields, nil) upon success, otherwise (..., error)
func getIncRespFields(request *datastore.GetObsRequest) (common.StringSet, error) {

	fields := common.StringSet{}
	for _, field := range request.GetIncludedResponseFields() {
		if !supIncRespFields.Contains(field) {
			return nil, fmt.Errorf(
				"'%s' not among supported fields: %s",
				field, supIncRespFieldsCSV)
		}
		fields[field] = struct{}{}
	}

	return fields, nil
}

// convertSelectCol decides what to extract from a column in a SELECT statement.
//
// Returns '<colName>' if colName (or one of its aliases) is defined - with prefix removed -
// in incFields,
// otherwise 'NULL' to indicate that we're not interested in the column value.
func convertSelectCol(
	incFields common.StringSet, colName, prefix string, aliases ...string) string {

	aliases = append(aliases, colName)
	for _, alias := range aliases {
		if includeField(incFields, strings.TrimPrefix(alias, prefix)) {
			return colName // colName included (either directly or through an alias)
		}
	}

	return "NULL" // colName not included
}

// getObs gets all observations that match request and tspec. Fields to include
// (as non-NULL values) in the final result are defined in incFields.
//
// Returns (observations, nil) upon success, otherwise (..., error).
func getObs(
	db *sql.DB, request *datastore.GetObsRequest, tspec common.TemporalSpec,
	incFields common.StringSet) (*[]*datastore.Metadata2, error) {

	obs := []*datastore.Metadata2{}

	// get distinct spec
	distinctSpec := ""
	if tspec.Latest {
		// ensure that we select only one observation per time series (which will be the most
		// recent one thanks to '... ORDER BY ts_id, obstime_instant DESC')
		distinctSpec = "DISTINCT ON (ts_id)"
	}

	// get values needed for query
	phVals := []interface{}{} // placeholder values
	timeFilter, geoFilter, int64MdataFilter, stringMdataFilter, err := createObsQueryVals(
		request.GetSpatialPolygon(), request.GetSpatialCircle(), request.GetFilter(), tspec,
		&phVals)
	if err != nil {
		return nil, fmt.Errorf("createObsQueryVals() failed: %v", err)
	}

	// convert obsInt64MdataCols according to incFields
	convOI64MC := []string{}
	for _, col := range obsInt64MdataCols {
		convOI64MC = append(convOI64MC, convertSelectCol(incFields, col, "observation."))
	}

	// convert obsStringMdataCols according to incFields
	convOSMC := []string{}
	for _, col := range obsStringMdataCols {
		convOSMC = append(convOSMC, convertSelectCol(incFields, col, "observation."))
	}

	// define and execute query
	query := fmt.Sprintf(`
		SELECT %s
		    ts_id,
			obstime_instant,
			%s,
			%s,
			point,
			%s,
			%s
		FROM observation
		JOIN time_series on observation.ts_id = time_series.id
		JOIN geo_point ON observation.geo_point_id = geo_point.id
		WHERE %s AND %s AND %s AND %s
		ORDER BY ts_id, obstime_instant DESC
		`,
		distinctSpec,
		convertSelectCol(incFields, "pubtime", "observation."),
		convertSelectCol(incFields, "value", "observation."),
		strings.Join(convOI64MC, ","),
		strings.Join(convOSMC, ","),
		timeFilter,
		geoFilter,
		int64MdataFilter,
		stringMdataFilter)

	rows, err := db.Query(query, phVals...)
	if err != nil {
		return nil, fmt.Errorf("db.Query() failed: %v", err)
	}
	defer rows.Close()

	obsMdatas := make(map[int64][]*datastore.ObsMetadata) // observations per time series ID

	// scan rows
	for rows.Next() {
		obsMdata, tsID, err := scanObsRow(rows)
		if err != nil {
			return nil, fmt.Errorf("scanObsRow() failed: %v", err)
		}

		// Handle obstime_instant as a special case instead of using convertSelectCol. Its value is
		// always loaded in the above SQL call since it is referred to in the 'ORDER BY' clause.
		if !includeField(incFields, "obstime_instant") {
			obsMdata.Obstime = nil
		}

		// Handle geo_point as a special case instead of using convertSelectCol. Its value is always
		// loaded in the above SQL call, since the postgis package does not support a nullable type
		// (such as postgis.NullPointS in addition to postgis.PointS). A NULL value (generated by
		// convertSelectCol) would have caused rows.Scan() to fail in scanObsRow().
		if !includeField(incFields, "geo_point") {
			obsMdata.Geometry = nil
		}

		// prepend obs to time series to get chronological order
		obsMdatas[tsID] = append([]*datastore.ObsMetadata{obsMdata}, obsMdatas[tsID]...)
	}

	// get time series
	tsMdatas := map[int64]*datastore.TSMetadata{}
	tsIDs := []string{}
	for tsID := range obsMdatas {
		tsIDs = append(tsIDs, fmt.Sprintf("%d", tsID))
	}
	if err = getTSMetadata(db, tsIDs, tsMdatas, incFields); err != nil {
		return nil, fmt.Errorf("getTSMetadata() failed: %v", err)
	}

	// assemble final output
	for tsID, obsMdata := range obsMdatas {
		obs = append(obs, &datastore.Metadata2{
			TsMdata:  tsMdatas[tsID],
			ObsMdata: obsMdata,
		})
	}

	return &obs, nil
}

// GetObservations ... (see documentation in StorageBackend interface)
func (sbe *PostgreSQL) GetObservations(
	request *datastore.GetObsRequest, tspec common.TemporalSpec) (
	*datastore.GetObsResponse, codes.Code, string) {

	var err error

	incFields, err := getIncRespFields(request)
	if err != nil {
		return nil, codes.Internal, fmt.Sprintf("getIncRespFields() failed: %v", err)
	}

	obs, err := getObs(sbe.Db, request, tspec, incFields)
	if err != nil {
		return nil, codes.Internal, fmt.Sprintf("getObs() failed: %v", err)
	}

	return &datastore.GetObsResponse{Observations: *obs}, codes.OK, ""
}
