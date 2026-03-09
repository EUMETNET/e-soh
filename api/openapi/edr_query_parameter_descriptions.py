bbox = (
    "Bounding box to query data from, specified as four comma-separated values: "
    "westmost longitude, southmost latitude, eastmost longitude, northmost latitude. "
    "Longitude values must be in the range [`-180`, `180`] and latitude values in the range [`-90`, `90`]."
)
datetime = (
    "Time to query data from. This may be a single timestamp (a point) or an interval. "
    "Expressions follow ISO 8601 (RFC 3339 recommended). Supported forms include a single "
    "date-time or an interval `start/end`. Use `..` to indicate an unbounded side. "
    "Common ISO 8601 variants accepted include omitting trailing zero components "
    "(e.g. `2026-01-01T00:00Z` vs `2026-01-01T00:00:00Z`) and fractional seconds (e.g. `2026-01-01T00:00:00.123Z`). "
    "A timezone indicator (`Z` or `±HH:MM`) is required. Date-only values without a time are not supported. "
)
parameter_name = (
    "Comma separated list of parameter names. Each consists of four components separated by colons."
    " The components are standard name, level in meters, aggregation method, and period. "
    "Each of the components can be replaced by the wildcard character `*`. "
    "To get all the air temperatures measured at 1.5 meter, use `air_temperature:1.5:*:*`."
)
standard_name = "Comma separated list of parameter standard_name(s) to query."
level = (
    "Define the vertical level(s) to return data from using either a comma separated list, "
    "a range or a repeating interval. <br /> Repeating intervals are defined in the format of "
    "'__R__ *`number of intervals` / `min-level` / `height to increment by`*'."
)
method = "Comma separated list of parameter aggregation methods to query."
duration = "Define the aggregation period(s) to return data from using either a comma separated list or " "a range."
wigos_id = "WIGOS Station Identifier (WSI) of the station to query data from."
format = "Specify wanted return format."
point = (
    "Point to query all data within 10 meters, specified as a Well-Known Text (WKT) `POINT`. "
    "Coordinates are given as longitude then latitude (`lon` `lat`) in degrees. Only 2D points are supported."
)

area = (
    "Area to query data from, specified as a Well-Known Text (WKT) `POLYGON`. "
    "Each coordinate is given as longitude then latitude (`lon` `lat`) in degrees and the polygon's linear ring must "
    "be closed (i.e. the first and last coordinate *MUST* be identical). Edges are interpreted as *great-circle arcs* "
    "on the sphere, so long edges follow the shortest path over the globe. Only 2D polygons are supported."
)
