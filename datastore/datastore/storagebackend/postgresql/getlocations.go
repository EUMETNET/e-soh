package postgresql

import (
	"cmp"
	"database/sql"
	"datastore/common"
	"datastore/datastore"
	"fmt"
	"maps"
	"slices"

	"github.com/cridenour/go-postgis"
	_ "github.com/lib/pq"
	"google.golang.org/grpc/codes"
)

// getLocs gets the locations of the most recent observation of the distinct platforms that match
// request and tspec.
//
// Returns (locations, nil) upon success, otherwise (..., error).
func getLocs(
	db *sql.DB, request *datastore.GetLocsRequest, tspec common.TemporalSpec) (
	*[]*datastore.LocMetadata, error) {

	locs := []*datastore.LocMetadata{}

	// get values needed for query
	phVals := []interface{}{} // placeholder values
	timeFilter, geoFilter, int64MdataFilter, stringMdataFilter, err := createObsQueryVals(
		request.GetSpatialPolygon(), request.GetSpatialCircle(), request.GetCamslRange(),
		request.GetFilter(), tspec, &phVals)
	if err != nil {
		return nil, fmt.Errorf("createLocsQueryVals() failed: %v", err)
	}

	// define and execute query
	query := fmt.Sprintf(`
		SELECT DISTINCT ON (ts_id)
			point,
			platform,
			platform_name,
			parameter_name
		FROM observation
		JOIN time_series on observation.ts_id = time_series.id
		JOIN geo_point ON observation.geo_point_id = geo_point.id
		WHERE %s AND %s AND %s AND %s
		ORDER BY ts_id, obstime_instant DESC;
		`,
		timeFilter,
		geoFilter,
		int64MdataFilter,
		stringMdataFilter)

	rows, err := db.Query(query, phVals...)
	if err != nil {
		return nil, fmt.Errorf("db.Query() failed: %v", err)
	}
	defer rows.Close()

	// process rows ...

	// per platform info
	type pformInfo struct {
		platformName string
		points       *[]postgis.PointS
		paramNames   *[]string
	}

	pformInfos := map[string]*pformInfo{}

	// populate pformInfos from rows
	for rows.Next() {

		var (
			point        postgis.PointS
			platform     string
			platformName sql.NullString
			paramName    string
		)

		err = rows.Scan(&point, &platform, &platformName, &paramName)
		if err != nil {
			return nil, fmt.Errorf("rows.Scan() failed: %v", err)
		}

		var pi *pformInfo
		pi, found := pformInfos[platform]
		if !found { // create the first one for this platform
			pi = &pformInfo{
				points:     &[]postgis.PointS{},
				paramNames: &[]string{},
			}
			pformInfos[platform] = pi
		}

		// aggregate info for this platform
		pi.platformName = platformName.String
		*pi.points = append(*(pi.points), point)
		*pi.paramNames = append(*(pi.paramNames), paramName)
	}

	// add result items sorted on platform
	for _, platform := range slices.Sorted(maps.Keys(pformInfos)) {
		pformInfo := pformInfos[platform]
		slices.Sort(*pformInfo.paramNames)

		// get representative point
		point := slices.MinFunc(*pformInfo.points, func(a, b postgis.PointS) int {
			if a.Y != b.Y { // sort primarily on latitude ...
				return cmp.Compare(a.Y, b.Y)
			}
			return cmp.Compare(a.X, b.X) // ... and secondarily on longitude
		})

		locs = append(locs, &datastore.LocMetadata{
			GeoPoint: &datastore.Point{
				Lon: point.X,
				Lat: point.Y,
			},
			Platform:       platform,
			PlatformName:   pformInfo.platformName,
			ParameterNames: *pformInfo.paramNames,
		})
	}

	return &locs, nil
}

// GetLocations ... (see documentation in StorageBackend interface)
func (sbe *PostgreSQL) GetLocations(
	request *datastore.GetLocsRequest, tspec common.TemporalSpec) (
	*datastore.GetLocsResponse, codes.Code, string) {

	locs, err := getLocs(sbe.Db, request, tspec)
	if err != nil {
		return nil, codes.Internal, fmt.Sprintf("getLocs() failed: %v", err)
	}

	return &datastore.GetLocsResponse{Locations: *locs}, codes.OK, ""
}
