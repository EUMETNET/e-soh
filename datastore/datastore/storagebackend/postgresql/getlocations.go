package postgresql

import (
	"database/sql"
	"datastore/common"
	"datastore/datastore"
	"fmt"

	"github.com/cridenour/go-postgis"
	_ "github.com/lib/pq"
	"google.golang.org/grpc/codes"
)

// getLocs gets into locs the locations of the most recent observation of the distinct platforms
// that match request and tspec.
//
// Returns nil upon success, otherwise error.
func getLocs(
	db *sql.DB, request *datastore.GetLocsRequest, tspec common.TemporalSpec,
	locs *[]*datastore.LocMetadata) error {

	// get values needed for query
	phVals := []interface{}{} // placeholder values
	timeFilter, geoFilter, int64MdataFilter, stringMdataFilter,
		err := createObsQueryVals(
		request.GetSpatialPolygon(), request.GetSpatialCircle(), request.GetFilter(), tspec,
		&phVals)
	if err != nil {
		return fmt.Errorf("createLocsQueryVals() failed: %v", err)
	}

	// define and execute query
	query := fmt.Sprintf(`
		SELECT DISTINCT ON (platform, parameter_name)
			point,
			platform,
			platform_name,
			parameter_name
		FROM observation
		JOIN time_series on observation.ts_id = time_series.id
		JOIN geo_point ON observation.geo_point_id = geo_point.id
		WHERE %s AND %s AND %s AND %s
		ORDER BY platform, parameter_name, obstime_instant DESC
		`,
		timeFilter,
		geoFilter,
		int64MdataFilter,
		stringMdataFilter)

	rows, err := db.Query(query, phVals...)
	if err != nil {
		return fmt.Errorf("db.Query() failed: %v", err)
	}
	defer rows.Close()

	// scan rows

	addResultItem := func(point postgis.PointS, pform, pformName string, paramNames []string) {
		*locs = append(*locs, &datastore.LocMetadata{
			GeoPoint: &datastore.Point{
				Lon: point.X,
				Lat: point.Y,
			},
			Platform:       pform,
			PlatformName:   pformName,
			ParameterNames: paramNames,
		})
	}

	var (
		point            postgis.PointS
		currPoint        postgis.PointS
		platform         string
		currPlatform     string
		platformName     sql.NullString
		currPlatformName sql.NullString
		paramName        string
		currParamName    string
		currParamNames   []string
	)

	for rows.Next() {

		err = rows.Scan(&point, &platform, &platformName, &paramName)
		if err != nil {
			return fmt.Errorf("rows.Scan() failed: %v", err)
		}

		if platform != currPlatform { // next platform, possibly the first one!
			if currPlatform != "" { // add for previous platform
				addResultItem(currPoint, currPlatform, currPlatformName.String, currParamNames)
			}

			// start new result item
			currPlatform = platform
			currParamNames = []string{}
		}

		// update what's now current
		currPoint = point
		currPlatformName = platformName
		currParamName = paramName

		// add param name for current result item
		currParamNames = append(currParamNames, currParamName)
	}

	if len(currParamNames) > 0 { // add for current platform
		addResultItem(currPoint, currPlatform, currPlatformName.String, currParamNames)
	}

	return nil
}

// GetLocations ... (see documentation in StorageBackend interface)
func (sbe *PostgreSQL) GetLocations(
	request *datastore.GetLocsRequest, tspec common.TemporalSpec) (
	*datastore.GetLocsResponse, codes.Code, string) {

	locs := []*datastore.LocMetadata{}
	if err := getLocs(sbe.Db, request, tspec, &locs); err != nil {
		return nil, codes.Internal, fmt.Sprintf("getLocs() failed: %v", err)
	}

	return &datastore.GetLocsResponse{Locations: locs}, codes.OK, ""
}
