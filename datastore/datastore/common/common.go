package common

import (
	"datastore/datastore"
	"fmt"
	"log"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"google.golang.org/protobuf/types/known/timestamppb"
)

var (
	dynamicTime            bool // whether the valid time range is considered dynamic or static
	loTimeSecs, hiTimeSecs int64
	snakeCaseRE            *regexp.Regexp
)

// initValidTimeRange initializes dynamicTime, loTimeSecs, and hiTimeSecs from environment
// variables DYNAMICTIME, LOTIME, and HITIME.
//
// The valid time range is defined like this if dynamicTime is true:
//
//	[now - loTimeSecs, now - hiTimeSecs]
//
// where {lo|hi}TimeSecs is converted directly as integer seconds from {LO|HI}TIME.
//
// If dynamicTime is false, the valid time range is defined like this:
//
//	[loTimeSecs, hiTimeSecs]
//
// where {lo|hi}TimeSecs is either converted directly as integer seconds from {LO|HI}TIME, or
// converted indirectly from {LO|HI}TIME represented as an ISO-8601 datetime of the exact form
// 2023-10-10T00:00:00Z.
//
// NOTE: if any errors are encountered, warnings will be printed and fallback values will be used.
func initValidTimeRange() {
	dynTime0 := strings.ToLower(Getenv("DYNAMICTIME", "true"))
	dynamicTime = ((dynTime0 != "false") && (dynTime0 != "no") && (dynTime0 != "0"))

	// define function that derives a valid int64 time range component from env.var
	// 'name', with a default value of 'defaultVal', and with the option of
	// expressing the value as an ISO-8601 datetime as a fallback.
	getSecs := func(name string, defaultVal int64, allowIso8601 bool) int64 {
		val0 := strings.ToLower(Getenv(name, fmt.Sprintf("%d", defaultVal)))

		// first attempt to extract directly from int64
		val, err := strconv.ParseInt(val0, 10, 64)
		if err != nil {
			if allowIso8601 {
				// then attempt to extract from ISO-8601 form
				var t time.Time
				if t, err = iso8601ToTime(val0); err != nil {
					log.Printf(
						"WARNING: failed to parse %s as an ISO-8601 datetime of the form "+
							"2023-10-10T00:00:00Z: %s; falling back to default secs: %d",
						name, val0, defaultVal)
					val = defaultVal
				} else {
					val = t.Unix()
				}
			} else {
				log.Printf(
					"WARNING: failed to parse %s as an int64: %s; falling back to default secs: %d",
					name, val0, defaultVal)
				val = defaultVal
			}
		}
		return val
	}

	loTimeName := "LOTIME"
	hiTimeName := "HITIME"
	defaultLoTimeSecs := int64(86400)
	defaultHiTimeSecs := int64(-600) // the reference time of visual observations is the next hour

	if dynamicTime {
		loTimeSecs = getSecs(loTimeName, defaultLoTimeSecs, false)
		hiTimeSecs = getSecs(hiTimeName, defaultHiTimeSecs, false)
	} else {
		// NOTE: in this case the defaults make little sense as they define a negative interval,
		// but are kept like this to keep the documentation (e.g. in README) simple.
		// A negative interval will be caught and fixed below. In any case, it hardly makes any
		// sense to use defaults at all in the static case (i.e. you are likely to always want to
		// specify the valid time range explicitly to match your test setup).
		loTimeSecs = getSecs(loTimeName, defaultLoTimeSecs, true)
		hiTimeSecs = getSecs(hiTimeName, defaultHiTimeSecs, true)

		if hiTimeSecs <= loTimeSecs {
			log.Printf(
				"WARNING: hiTimeSecs (%d) <= loTimeSecs (%d); setting hiTimeSecs to loTimeSecs + 1",
				hiTimeSecs, loTimeSecs)
			hiTimeSecs = loTimeSecs + 1
		}
	}
}

// initSnakeCaseConverter initializes regexps used by ToSnakeCase.
func initSnakeCaseConverter() {
	snakeCaseRE = regexp.MustCompile("([a-z0-9])([A-Z])")
}

func init() { // automatically called once on program startup (on first import of this package)
	log.SetFlags(log.LstdFlags | log.Lmicroseconds | log.Lshortfile)
	initValidTimeRange()
	initSnakeCaseConverter()
}

// See https://www.pauladamsmith.com/blog/2011/05/go_time.html
var iso8601layout = "2006-01-02T15:04:05Z" // note upper case!

// iso8601ToTime converts time string ts of the form YYYY-MM-DDThh:mm:ssZ to time.Time.
// Returns (val, nil) upon success, otherwise (time.Time{}, error).
func iso8601ToTime(ts string) (time.Time, error) {
	tm, err := time.Parse(iso8601layout, strings.ToUpper(ts))
	if err != nil {
		return time.Time{}, fmt.Errorf("time.Parse() failed for %s: %v", ts, err)
	}
	return tm, nil
}

// Getenv returns the value of an environment variable or a default value if
// no such environment variable has been set.
func Getenv(key string, defaultValue string) string {
	value, ok := os.LookupEnv(key)
	if (!ok) || (strings.TrimSpace(value) == "") {
		value = defaultValue
	}
	return value
}

// Tstamp2float64secs returns the integer + fractional secs of
// a timestamp as a float64 value.
func Tstamp2float64Secs(tstamp *timestamppb.Timestamp) float64 {
	return float64(tstamp.GetSeconds()) + float64(tstamp.GetNanos())/1e9
}

// GetValidTimeRange returns the current valid time range as (lo time, hi time).
func GetValidTimeRange() (time.Time, time.Time) {
	if dynamicTime { // Case 1: dynamic time, i.e. relative to current time
		now := time.Now().Unix()
		return time.Unix(now-loTimeSecs, 0), time.Unix(now-hiTimeSecs, 0)
	}

	// Case 2: static time, i.e. based on fixed time (useful e.g. for certain testing!)
	return time.Unix(loTimeSecs, 0), time.Unix(hiTimeSecs, 0)
}

// GetValidTimeRangeSettings gets settings (like environment variables) relevant for the
// valid time definition.
// Returns settings formatted as a string.
func GetValidTimeRangeSettings() string {
	s := ""
	s += fmt.Sprintf("dynamicTime: %v", dynamicTime)
	s += fmt.Sprintf("; loTimeSecs: %v", loTimeSecs)
	s += fmt.Sprintf("; hiTimeSecs: %v", hiTimeSecs)
	s += "; env: ("
	s += fmt.Sprintf("DYNAMICTIME: %v", Getenv("DYNAMICTIME", "unset"))
	s += fmt.Sprintf("; LOTIME: %v", Getenv("LOTIME", "unset"))
	s += fmt.Sprintf("; HITIME: %v", Getenv("HITIME", "unset"))
	s += ")"
	return s
}

// ToSnakeCase returns the snake case version of s.
func ToSnakeCase(s string) string {
	return strings.ToLower(snakeCaseRE.ReplaceAllString(s, "${1}_${2}"))
}

type TemporalSpec struct {
	// true: get single latest observation in interval; false: get all observations in interval
	Latest bool

	// nil: interval is entire buffer; non-nil: interval is the specified one
	Interval *datastore.TimeInterval
}

type StringSet map[string]struct{}

// Contains returns true iff sset contains val.
func (sset *StringSet) Contains(val string) bool {
	_, found := (*sset)[val]
	return found
}

// Set adds val to sset.
func (sset *StringSet) Set(val string) {
	(*sset)[val] = struct{}{}
}

// Returns the "values" (i.e. technically the keys!) of sset.
func (sset *StringSet) Values() []string {
	values := []string{}
	for k := range *sset {
		values = append(values, k)
	}
	return values
}
