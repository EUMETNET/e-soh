package postgresql

import (
	"datastore/common"
	"datastore/datastore"
	"fmt"
	"strings"
)

// getTimeFilter derives from tspec the expression used in a WHERE clause for overall
// (i.e. not time series specific) filtering on obs time.
//
// Returns expression.
func getTimeFilter(tspec common.TemporalSpec) string {

	// by default, restrict only to current valid time range
	loTime, hiTime := common.GetValidTimeRange()
	timeExprs := []string{
		fmt.Sprintf("obstime_instant >= to_timestamp(%d)", loTime.Unix()),
		fmt.Sprintf("obstime_instant <= to_timestamp(%d)", hiTime.Unix()),
	}

	ti := tspec.Interval
	if ti != nil { // restrict filter additionally to specified interval
		// (note the open-ended [from,to> form)
		if start := ti.GetStart(); start != nil {
			timeExprs = append(timeExprs, fmt.Sprintf(
				"obstime_instant >= to_timestamp(%f)", common.Tstamp2float64Secs(start)))
		}
		if end := ti.GetEnd(); end != nil {
			timeExprs = append(timeExprs, fmt.Sprintf(
				"obstime_instant < to_timestamp(%f)", common.Tstamp2float64Secs(end)))
		}
	}

	return fmt.Sprintf("(%s)", strings.Join(timeExprs, " AND "))
}

// createObsQueryVals creates from polygon, circle, camslRange, filter, and tspec values used for
// querying observations.
//
// Values to be used for query placeholders are appended to phVals.
//
// Upon success the function returns five values:
// - time filter used in a 'WHERE ... AND ...' clause (possibly just 'TRUE')
// - geo filter ... ditto
// - filter for reflectable metadata fields of type int64 ... ditto
// - filter for reflectable metadata fields of type string ... ditto
// - nil,
// otherwise (..., ..., ..., ..., error).
func createObsQueryVals(
	polygon *datastore.Polygon, circle *datastore.Circle, camslRange string,
	filter map[string]*datastore.Strings, tspec common.TemporalSpec, phVals *[]interface{}) (
	string, string, string, string, error) {

	timeFilter := getTimeFilter(tspec)

	geoFilter, err := getGeoFilter(polygon, circle, camslRange, phVals)
	if err != nil {
		return "", "", "", "", fmt.Errorf("getGeoFilter() failed: %v", err)
	}

	// --- BEGIN filters for reflectable metadata (of type int64 or string) -------------

	for fieldName := range filter {
		if !supReflFilterFields.Contains(fieldName) {
			return "", "", "", "", fmt.Errorf(
				"no such field: %s; available fields: %s",
				fieldName, strings.Join(supReflFilterFieldsSorted, ", "))
		}
	}

	int64MdataFilter, err := getInt64MdataFilter(filter, phVals)
	if err != nil {
		return "", "", "", "", fmt.Errorf("getInt64MdataFilter() failed: %v", err)
	}

	stringMdataFilter, err := getStringMdataFilter(filter, phVals)
	if err != nil {
		return "", "", "", "", fmt.Errorf("getStringMdataFilter() failed: %v", err)
	}

	// --- END filters for reflectable metadata (of type int64 or string) -------------

	return timeFilter, geoFilter, int64MdataFilter, stringMdataFilter, nil
}
