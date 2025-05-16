package postgresql

import (
	"database/sql"
	"datastore/common"
	"datastore/datastore"
	"fmt"
	_ "github.com/lib/pq"
	"log"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// PostgreSQL is an implementation of the StorageBackend interface that
// keeps data in a PostgreSQL database.
type PostgreSQL struct {
	Db *sql.DB
}

// Description ... (see documentation in StorageBackend interface)
func (sbe *PostgreSQL) Description() string {
	return "PostgreSQL database"
}

// setTSUniqueMainCols extracts into tsMdataPBNamesUnique the columns comprising constraint
// unique_main in table time_series.
//
// Returns nil upon success, otherwise error.
func (sbe *PostgreSQL) setTSUniqueMainCols() error {

	query := `
		SELECT pg_get_constraintdef(c.oid)
		FROM pg_constraint c
		JOIN pg_namespace n ON n.oid = c.connamespace
		WHERE conrelid::regclass::text = 'time_series'
			AND conname = 'unique_main'
			AND contype = 'u'
	`

	/* typical example of running the above query:

	$ PGPASSWORD=mysecretpassword psql -h localhost -p 5433 -U postgres -d data -c \
	> "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_namespace n
	> ON n.oid = c.connamespace WHERE conrelid::regclass::text = 'time_series'
	> AND conname = 'unique_main' AND contype = 'u'"
									              pg_get_constraintdef
	-----------------------------------------------------------------------------------------------
	-------------
	UNIQUE NULLS NOT DISTINCT (naming_authority, platform, standard_name, level, function, period,
		instrument)
		(1 row)

	*/

	row := sbe.Db.QueryRow(query)

	var result string
	err := row.Scan(&result)
	if err != nil {
		return fmt.Errorf("row.Scan() failed: %v", err)
	}

	pattern := `\((.*)\)`
	re := regexp.MustCompile(pattern)
	matches := re.FindStringSubmatch(result)
	if len(matches) != 2 {
		return fmt.Errorf("'%s' didn't match regexp pattern '%s'", result, pattern)
	}

	// create tsMdataPBNamesUnique
	tsMdataPBNamesUnique = strings.Split(matches[1], ",")
	for i := 0; i < len(tsMdataPBNamesUnique); i++ {
		tsMdataPBNamesUnique[i] = strings.TrimSpace(tsMdataPBNamesUnique[i])
	}

	return nil
}

// setUpsertTSInsertCmd sets upsertTSInsertCmd to be used by upsertTS.
func setUpsertTSInsertCmd() {

	cols := getTSColNames()

	formats := make([]string, len(cols))
	for i := 0; i < len(cols); i++ {
		formats[i] = "$%d"
	}

	updateExpr := []string{}
	for _, col := range getTSColNamesUniqueCompl() {
		updateExpr = append(updateExpr, fmt.Sprintf("%s = EXCLUDED.%s", col, col))
	}

	upsertTSInsertCmd = fmt.Sprintf(`
		INSERT INTO time_series (%s) VALUES (%s)
		ON CONFLICT ON CONSTRAINT unique_main DO UPDATE SET %s
		`,
		strings.Join(cols, ","),
		strings.Join(createPlaceholders(formats), ","),
		strings.Join(updateExpr, ","),
	)
	log.Printf("Insert: %v", upsertTSInsertCmd)
}

// TODO: Move to putobservations.go?
func getUpsertTSInsertCmd(nRows int) string {

	cols := getTSColNames()

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

	insertCmd := fmt.Sprintf(`
		INSERT INTO time_series (%s) VALUES %s
		ON CONFLICT ON CONSTRAINT unique_main DO UPDATE SET %s
		`,
		strings.Join(cols, ","),
		strings.Join(formats, ","),
		strings.Join(updateExpr, ","),
	)
	//log.Printf("Insert: %v", insertCmd)
	return insertCmd
}

// setUpsertTSSelectCmd sets upsertTSSelectCmd to be used by upsertTS.
func setUpsertTSSelectCmd() {

	whereExpr := []string{}
	for i, col := range getTSColNamesUnique() {
		whereExpr = append(whereExpr, fmt.Sprintf("%s=$%d", col, i+1))
	}

	upsertTSSelectCmd = fmt.Sprintf(
		`SELECT id FROM time_series WHERE %s`, strings.Join(whereExpr, " AND "))
	log.Printf("Update: %v", upsertTSInsertCmd)
}

// TODO: Move to putobservations.go?
func getUpsertTSSelectCmd(nRows int) string {
	cols := getTSColNamesUnique()
	whereExpr := make([]string, nRows)
	index := 1
	for i := 0; i < nRows; i++ {
		oneRow := make([]string, len(cols))
		for j, _ := range cols {
			oneRow[j] = fmt.Sprintf("$%d", index)
			index += 1
		}
		whereExpr[i] = "(" + strings.Join(oneRow, ",") + ")"
	}

	selectCmd := fmt.Sprintf(
		`SELECT id,%s FROM time_series WHERE (%s) in (%s)`,
		strings.Join(cols, ","),
		strings.Join(cols, ","),
		strings.Join(whereExpr, ","))
	//log.Printf("Select: %v", selectCmd)

	return selectCmd
}

// openDB opens database identified by host/port/user/password/dbname.
// Returns (DB, nil) upon success, otherwise (..., error).
func openDB(host, port, user, password, dbname, enable_ssl string) (*sql.DB, error) {
	connInfo := fmt.Sprintf(
		"host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		host, port, user, password, dbname, enable_ssl)

	db, err := sql.Open("postgres", connInfo)
	if err != nil {
		return nil, fmt.Errorf("sql.Open() failed: %v", err)
	}

	// Set up connection pooling
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(25)
	db.SetConnMaxLifetime(5 * time.Minute)
	db.SetConnMaxIdleTime(5 * time.Minute)

	return db, nil
}

// NewPostgreSQL creates a new PostgreSQL instance.
// Returns (instance, nil) upon success, otherwise (..., error).
func NewPostgreSQL() (*PostgreSQL, error) {
	sbe := new(PostgreSQL)

	host := common.Getenv("PGHOST", "localhost")
	port := common.Getenv("PGPORT", "5433")
	user := common.Getenv("PGUSER", "postgres")
	password := common.Getenv("PGPASSWORD", "mysecretpassword")
	dbname := common.Getenv("PGDBNAME", "data")
	enable_ssl := common.Getenv("ENABLE_SSL", "disable")
	var err error

	sbe.Db, err = openDB(host, port, user, password, dbname, enable_ssl)
	if err != nil {
		return nil, fmt.Errorf("openDB() failed: %v", err)
	}

	if err = sbe.Db.Ping(); err != nil {
		return nil, fmt.Errorf("sbe.Db.Ping() failed: %v", err)
	}

	err = sbe.setTSUniqueMainCols()
	if err != nil {
		return nil, fmt.Errorf("sbe.setTSUniqueMainCols() failed: %v", err)
	}

	setUpsertTSInsertCmd()
	setUpsertTSSelectCmd()

	// cleanup the database at regular intervals
	ticker := time.NewTicker(cleanupInterval)
	go func() {
		for range ticker.C {
			if err = cleanup(sbe.Db); err != nil {
				log.Printf("cleanup() failed: %v", err)
			}
		}
	}()

	return sbe, nil
}

// getTSColNames returns time series metadata column names.
func getTSColNames() []string {

	// initialize cols with non-reflectable metadata
	cols := []string{
		"link_href",
		"link_rel",
		"link_type",
		"link_hreflang",
		"link_title",
	}

	// extend cols with reflectable metadata of type int64
	cols = append(cols, tsInt64MdataPBNames...)

	// complete cols with reflectable metadata of type string
	cols = append(cols, tsStringMdataPBNames...)

	return cols
}

// getTSColNamesUnique returns the fields defined in constraint unique_main in table
// time_series.
func getTSColNamesUnique() []string {
	return tsMdataPBNamesUnique
}

// getTSColNamesUniqueCompl returns the complement of the set of fields defined in constraint
// unique_main in table time_series, i.e. getTSColNames() - getTSColNamesUnique().
func getTSColNamesUniqueCompl() []string {

	colSet := map[string]struct{}{}

	for _, col := range getTSColNames() { // start with all columns
		colSet[col] = struct{}{}
	}

	for _, col := range getTSColNamesUnique() { // remove columns of the unique_main constraint
		delete(colSet, col)
	}

	// return remaining columns

	result := make([]string, len(colSet))
	i := 0
	for col := range colSet {
		result[i] = col
		i++
	}

	return result
}

// createPlaceholders returns the list of n placeholder strings for
// values in a parameterized query, e.g. $1, to_timestamp($2), ..., $n.
// Items in formats must be strings containing exactly one "$%d" pattern,
// e.g. "$%d", "to_timestamp($%d)" etc.
func createPlaceholders(formats []string) []string {
	phs := []string{}
	for i, format := range formats {
		index := i + 1
		ph := fmt.Sprintf(format, index)
		phs = append(phs, ph)
	}
	return phs
}

// createSetFilter creates expression used in a WHERE clause for testing
// if the value in column colName is included in a set of string values.
// The filter is fully closed (--> return FALSE) if the set non-nil but empty.
// Returns expression, TRUE or FALSE.
func createSetFilter(colName string, vals []string) string {
	// assert(vals != nil)
	if len(vals) == 0 {
		return "FALSE" // set requested, but nothing will match
	}
	return fmt.Sprintf("(%s IN (%s))", colName, strings.Join(vals, ","))
}

// addWhereCondMatchAnyPatternForInt64 appends to whereExpr an expression of the form
// "(cond1 OR cond2 OR ... OR condN)" where condi tests if the ith pattern in patterns matches
// colName assumed to be of type int64/BIGINT. A pattern of the form <int64>/<int64> generates
// a range filter directly on the int type where the from and to values are appended to phVals.
// Otherwise the function generates an expression where the pattern is matched agains a text-version
// of the int type in a case-insensitive way. In this case an asterisk in a pattern matches zero or
// more arbitrary characters, and patterns with '*' replaced with '%' are appended to phVals.
func addWhereCondMatchAnyPatternForInt64(
	colName string, patterns []string, whereExpr *[]string, phVals *[]interface{}) {

	if (patterns == nil) || (len(patterns) == 0) {
		return // nothing to do
	}

	// getInt64RangeBoth checks if ptn is of the form '<int64>/<int64>', in which case
	// (lo, hi, true) is returned, otherwise (..., ..., false) is returned.
	getInt64RangeBoth := func(ptn string) (int64, int64, bool) {

		sm := int64RangeREBoth.FindStringSubmatch(strings.TrimSpace(ptn))
		if len(sm) == 3 {
			lo, err := strconv.ParseInt(sm[1], 10, 64)
			if err != nil {
				return -1, -1, false
			}

			hi, err := strconv.ParseInt(sm[2], 10, 64)
			if err != nil {
				return -1, -1, false
			}

			return lo, hi, true
		}

		return -1, -1, false
	}

	// getInt64RangeLo checks if ptn is of the form '<int64>/..', in which case (lo, true) is
	// returned, otherwise (..., false) is returned.
	getInt64RangeLo := func(ptn string) (int64, bool) {

		sm := int64RangeRELo.FindStringSubmatch(strings.TrimSpace(ptn))
		if len(sm) == 2 {
			lo, err := strconv.ParseInt(sm[1], 10, 64)
			if err != nil {
				return -1, false
			}

			return lo, true
		}

		return -1, false
	}

	// getInt64RangeHi checks if ptn is of the form '../<int64>', in which case (hi, true) is
	// returned, otherwise (..., false) is returned.
	getInt64RangeHi := func(ptn string) (int64, bool) {

		sm := int64RangeREHi.FindStringSubmatch(strings.TrimSpace(ptn))
		if len(sm) == 2 {
			hi, err := strconv.ParseInt(sm[1], 10, 64)
			if err != nil {
				return -1, false
			}

			return hi, true
		}

		return -1, false
	}

	// getInt64RangeNone checks if ptn is of the form '../..', in which case true is returned,
	// otherwise false is returned.
	getInt64RangeNone := func(ptn string) bool {

		sm := int64RangeRENone.FindStringSubmatch(strings.TrimSpace(ptn))
		return len(sm) == 1
	}

	whereExprOR := []string{}

	index := len(*phVals)
	for _, ptn := range patterns {
		if lo, hi, ok := getInt64RangeBoth(ptn); ok { // both lower and upper limit
			index += 2
			expr := fmt.Sprintf("((%s >= $%d) AND (%s <= $%d))", colName, index-1, colName, index)
			whereExprOR = append(whereExprOR, expr)
			*phVals = append(*phVals, lo, hi)
		} else if lo, ok := getInt64RangeLo(ptn); ok { // no upper limit
			index++
			expr := fmt.Sprintf("(%s >= $%d)", colName, index)
			whereExprOR = append(whereExprOR, expr)
			*phVals = append(*phVals, lo)
		} else if hi, ok := getInt64RangeHi(ptn); ok { // no lower limit
			index++
			expr := fmt.Sprintf("(%s <= $%d)", colName, index)
			whereExprOR = append(whereExprOR, expr)
			*phVals = append(*phVals, hi)
		} else if ok := getInt64RangeNone(ptn); ok {
			// disable int range filtering, but note that we still don't want to fall
			// back to regular string matching!
			whereExprOR = append(whereExprOR, "TRUE")
		} else { // fall back to regular string matching
			index++
			expr := fmt.Sprintf("(lower(%s::text) LIKE lower($%d))", colName, index)
			whereExprOR = append(whereExprOR, expr)
			*phVals = append(*phVals, strings.ReplaceAll(ptn, "*", "%"))
		}
	}

	*whereExpr = append(*whereExpr, fmt.Sprintf("(%s)", strings.Join(whereExprOR, " OR ")))
}

// addWhereCondMatchAnyPatternForString appends to whereExpr an expression of the form
// "(cond1 OR cond2 OR ... OR condN)" where condi tests if the ith pattern in patterns matches
// colName assumed to be of type string/TEXT. Matching is case-insensitive and an asterisk in a
// pattern matches zero or more arbitrary characters. The patterns with '*' replaced with '%' are
// appended to phVals.
func addWhereCondMatchAnyPatternForString(
	colName string, patterns []string, whereExpr *[]string, phVals *[]interface{}) {

	if (patterns == nil) || (len(patterns) == 0) {
		return
	}

	whereExprOR := []string{}

	index := len(*phVals)
	for _, ptn := range patterns {
		index++
		expr := fmt.Sprintf("(lower(%s) LIKE lower($%d))", colName, index)
		whereExprOR = append(whereExprOR, expr)
		*phVals = append(*phVals, strings.ReplaceAll(ptn, "*", "%"))
	}

	*whereExpr = append(*whereExpr, fmt.Sprintf("(%s)", strings.Join(whereExprOR, " OR ")))
}

// getInt64MdataFilterFromFilterInfos derives from filterInfos the expression used in a WHERE
// clause for "match any" filtering on a set of attributes. The whereExprGenerator defines the
// expression at the lowest level, and typically depends on the type (typically int64 or string).
//
// The expression will be of the form
//
//	(
//	  ((<attr1 matches pattern1,1>) OR (<attr1 matches pattern1,2>) OR ...) AND
//	  ((<attr2 matches pattern2,1>) OR (<attr1 matches pattern2,2>) OR ...) AND
//	  ...
//	)
//
// Values to be used for query placeholders are appended to phVals.
//
// Returns expression.
func getMdataFilterFromFilterInfos(
	filterInfos []filterInfo, phVals *[]interface{},
	whereExprGenerator func(string, []string, *[]string, *[]interface{})) string {

	whereExprAND := []string{}

	for _, sfi := range filterInfos {
		whereExprGenerator(sfi.colName, sfi.patterns, &whereExprAND, phVals)
	}

	whereExpr := "TRUE" // by default, don't filter
	if len(whereExprAND) > 0 {
		whereExpr = fmt.Sprintf("(%s)", strings.Join(whereExprAND, " AND "))
	}

	return whereExpr
}

// getMdataFilter creates from 'filter' the metadata filter used for querying observations or
// extensions.
// Values to be used for query placeholders are appended to phVals.
// pbType2table defines field->table mapping for the type in question.
// whereExprGenerator defines the expression at the lowest level for the type in question.
//
// Returns a metadata filter for a 'WHERE ... AND ...' clause (possibly just 'TRUE').
func getMdataFilter(
	filter map[string]*datastore.Strings, phVals *[]interface{},
	pbType2table map[string]string,
	whereExprGenerator func(string, []string, *[]string, *[]interface{})) string {

	filterInfos := []filterInfo{}

	for fieldName, ptnObj := range filter {
		tableName, found := pbType2table[fieldName]
		if found {
			patterns := ptnObj.GetValues()
			if len(patterns) > 0 {
				filterInfos = append(filterInfos, filterInfo{
					colName:  fmt.Sprintf("%s.%s", tableName, fieldName),
					patterns: patterns,
				})
			}
		}
	}

	return getMdataFilterFromFilterInfos(filterInfos, phVals, whereExprGenerator)
}

// getInt64MdataFilter is a convenience wrapper around getMdataFilter for type int64.
func getInt64MdataFilter(filter map[string]*datastore.Strings, phVals *[]interface{}) string {
	return getMdataFilter(filter, phVals, pbInt642table, addWhereCondMatchAnyPatternForInt64)
}

// getStringMdataFilter is a convenience wrapper around getMdataFilter for type string.
func getStringMdataFilter(filter map[string]*datastore.Strings, phVals *[]interface{}) string {
	return getMdataFilter(filter, phVals, pbString2table, addWhereCondMatchAnyPatternForString)
}

// cleanup performs various cleanup tasks, like removing old observations from the database.
func cleanup(db *sql.DB) error {

	log.Println("db cleanup started")
	start := time.Now()

	var err error

	// --- BEGIN define removal functions ----------------------------------

	rmObsOutsideValidRange := func() error {

		loTime, hiTime := common.GetValidTimeRange()
		cmd := fmt.Sprintf(`
			DELETE FROM observation
			WHERE (obstime_instant < to_timestamp(%d)) OR (obstime_instant > to_timestamp(%d))
		`, loTime.Unix(), hiTime.Unix())

		_, err = db.Exec(cmd)
		if err != nil {
			return fmt.Errorf(
				"tx.Exec() failed when removing observations outside valid range: %v", err)
		}

		return nil
	}

	rmUnrefRows := func(tableName, fkName string) error {

		cmd := fmt.Sprintf(`
			DELETE FROM %s t
			WHERE NOT EXISTS (
				SELECT FROM observation WHERE %s = t.id
			)
		`, tableName, fkName)

		_, err = db.Exec(cmd)
		if err != nil {
			return fmt.Errorf(
				"tx.Exec() failed when removing unreferenced rows from %s: %v", tableName, err)
		}

		return nil
	}

	// --- END define removal functions ----------------------------------

	// --- BEGIN apply removal functions ------------------------------------------

	// remove observations outside valid range
	err = rmObsOutsideValidRange()
	if err != nil {
		return fmt.Errorf("rmObsOutsideValidRange() failed: %v", err)
	}

	// remove time series that are no longer referenced by any observation
	err = rmUnrefRows("time_series", "ts_id")
	if err != nil {
		return fmt.Errorf("rmUnrefRows(time_series) failed: %v", err)
	}

	// remove geo points that are no longer referenced by any observation
	err = rmUnrefRows("geo_point", "geo_point_id")
	if err != nil {
		return fmt.Errorf("rmUnrefRows(geo_point) failed: %v", err)
	}

	// --- END apply removal functions ------------------------------------------

	log.Printf("db cleanup complete after %v", time.Since(start))

	return nil
}
