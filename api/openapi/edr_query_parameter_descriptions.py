bbox = "Bounding box to query data from. The bounding box is an area defined by two longitudes and two latitudes."
datetime = "Time range to query data from."
parameter_name = (
    "Comma seperated list of parameter names. Each consists of four components seperated by colons."
    " The components are standard name, level in meters, aggregation method, and period. "
    "Each of the components can be replaced by the wildcard character `*`. "
    "To get all the air temperatures measured at 1.5 meter, use `air_temperature:1.5:*:*`."
)
standard_names = "Comma seperated list of parameter standard_name(s) to query."
levels = (
    "Define the vertical level(s) to return data from using either a comma separated list, "
    "a range or a repeating interval. <br /> Repeating intervals are defined in the format of "
    "'__R__ *number of intervals / min-level / height to increment by*'."
)
methods = "Comma seperated list of parameter aggregation methods to query."
durations = "Define the aggregation period(s) to return data from using either a comma seperated list or " "a range."
wigos_id = "WIGOS Station Identifier (WSI) of the station to query data from."
format = "Specify wanted return format."
point = "Point to query data from in Well-Known Text (WKT) point coordinates."
area = "Area to query data from in Well-Known Text (WKT) polygon coordinates."
