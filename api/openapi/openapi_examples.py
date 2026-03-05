datetime = {
    "range": {
        "summary": "Range",
        "value": "2022-01-01T00:00Z/2023-01-01T00:00Z",
    },
    "point": {
        "summary": "A point in time",
        "value": "2022-01-01T00:00Z",
    },
    "wildcard": {
        "summary": "Open start range",
        "value": "../2023-01-01T00:00Z",
    },
}

bbox = {
    "Netherlands": {
        "summary": "Bounding box in central Netherlands",
        "value": "5.0,52.0,6.0,52.1",
    },
    "Finland & Norway": {
        "summary": "Bounding box containing the whole of Finland and Norway",
        "value": "2.5,58.0,32.0,72.1",
    },
}

parameter_name = {
    "Default": {"value": ""},
    "List": {
        "summary": "Comma separated list",
        "value": "wind_from_direction:2.0:mean:PT10M,"
        "wind_speed:10.0:mean:PT10M,"
        "relative_humidity:2.0:mean:PT1M,"
        "air_pressure_at_sea_level:1.0:mean:PT1M,"
        "air_temperature:1.5:maximum:PT10M",
    },
    "Wildcard": {
        "summary": "All air temperatures measured at 1.5m",
        "value": "air_temperature:1.5:*:*",
    },
}

wigos_id = {
    "Default": {"value": ""},
    "De Bilt": {
        "summary": "De Bilt AWS",
        "value": "0-20000-0-06260",
    },
    "Helsinki": {
        "summary": "Helsinki Kumpula",
        "value": "0-246-0-101004",
    },
    "Oslo": {"summary": "Oslo Blindern", "value": "0-20000-0-01492"},
}

point = {
    "KNMI": {"summary": "Point in De Bilt", "value": "POINT(5.179705 52.0988218)"},
    "FMI": {"summary": "Point in Helsinki", "value": "POINT(24.9613 60.2031)"},
    "METNO": {"summary": "Point in Oslo", "value": "POINT(10.72 59.9423)"},
}

polygon = {
    "Netherlands": {
        "summary": "Area in central Netherlands",
        "value": "POLYGON((5.0 52.0, 6.0 52.0,6.0 52.1,5.0 52.1, 5.0 52.0))",
    },
    "Finland": {
        "summary": "Southern Finland",
        "value": "POLYGON((20.82 61.46,25.83 61.73,30.62 61.56,28.08 60.08,"
        "24.96 59.86,22.36 59.73,20.91 60.58,20.82 61.46))",
    },
}

naming_authority = {
    "Met.no": {"summary": "Norwegian Meteorological Institute", "value": "no.met"},
    "FMI:": {"summary": "Finnish Meteorological Institute", "value": "fi.fmi"},
    "KNMI": {"summary": "Royal Netherlands Meteorological Institute", "value": "nl.knmi"},
}

institution = {
    "Met.no": {
        "summary": "Norwegian Meteorological Institute",
        "value": "Norwegian Meteorological Institute (MET Norway)",
    },
    "FMI:": {"summary": "Finnish Meteorological Institute", "value": "Finnish Meteorological Institute (FMI)"},
    "KNMI": {
        "summary": "Royal Netherlands Meteorological Institute",
        "value": "Royal Netherlands Meteorological Institute (KNMI)",
    },
}

standard_name = {
    "air_temperature": {"summary": "Air temperature", "value": "air_temperature"},
    "wind_from_direction": {"summary": "Wind direction", "value": "wind_from_direction"},
    "wind_speed": {"summary": "Wind speed", "value": "wind_speed"},
    "relative_humidity": {"summary": "Relative humidity", "value": "relative_humidity"},
    "air_pressure_at_sea_level": {"summary": "Air pressure at sea level", "value": "air_pressure_at_sea_level"},
}

unit = {
    "degC": {"summary": "Degrees Celsius", "value": "degC"},
    "m/s": {"summary": "Meters per second", "value": "m/s"},
    "Pa": {"summary": "Pascals", "value": "Pa"},
    "%": {"summary": "Percentage", "value": "%"},
}

level = {
    "2.0": {"summary": "2 meters above ground", "value": "2.0"},
    "10.0": {"summary": "10 meters above ground", "value": "10.0"},
}

duration = {
    "PT1M": {"summary": "1 minute", "value": "PT1M"},
    "PT10M": {"summary": "10 minutes", "value": "PT10M"},
}

method = {"mean": {"summary": "Mean", "value": "mean"}, "maximum": {"summary": "Maximum", "value": "maximum"}}

z = {
    "Default": {"value": ""},
    "10.0": {"summary": "10 meters above mean sea level", "value": "10.0"},
    "5/200": {"summary": "Range from 5 to 200 meters above mean sea level", "value": "5/200"},
    "R10/5/10": {
        "summary": "Repeating interval of 10 levels, starting at 5 meters above mean sea level, "
        "with an increment of 10 meters",
        "value": "R10/5/10",
    },
}
