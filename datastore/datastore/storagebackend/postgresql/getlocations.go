package postgresql

import (
	"database/sql"
	"datastore/common"
	"datastore/datastore"
	"fmt"
	"sort"

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
		currPoints       []postgis.PointS
		platform         string
		currPlatform     string
		platformName     sql.NullString
		currPlatformName sql.NullString
		paramName        string
		currParamNames   []string
	)

	getRepresentativePoint := func(points *[]postgis.PointS) postgis.PointS {
		sort.Slice(*points, func(i, j int) bool {
			if (*points)[i].Y != (*points)[j].Y { // sort primarily on latitude ...
				return (*points)[i].Y < (*points)[j].Y
			}
			return (*points)[i].X < (*points)[j].X // ... and secondarily on longitude
		})
		return (*points)[0]
	}

	for rows.Next() {

		err = rows.Scan(&point, &platform, &platformName, &paramName)
		if err != nil {
			return fmt.Errorf("rows.Scan() failed: %v", err)
		}

		if platform != currPlatform { // next platform, possibly the first one!
			if currPlatform != "" { // add for previous platform
				if len(currPoints) == 0 {
					return fmt.Errorf("programming error [1]: len(currPoints) == 0")
				}
				addResultItem(
					getRepresentativePoint(&currPoints), currPlatform, currPlatformName.String,
					currParamNames)
			}

			// start new result item
			currPlatform = platform
			currPoints = []postgis.PointS{}
			currParamNames = []string{}
		}

		currPoints = append(currPoints, point)
		currPlatformName = platformName
		currParamNames = append(currParamNames, paramName)
	}

	if len(currParamNames) > 0 { // add for current platform
		if len(currPoints) == 0 {
			return fmt.Errorf("programming error [2]: len(currPoints) == 0")
		}
		addResultItem(
			getRepresentativePoint(&currPoints), currPlatform, currPlatformName.String,
			currParamNames)
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
