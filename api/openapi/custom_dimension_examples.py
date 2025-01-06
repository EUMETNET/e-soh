standard_names = {
    "Default": {
        "value": "",
    },
    "List": {
        "summary": "Comma separated list",
        "value": "wind_from_direction,"
        "wind_speed,"
        "relative_humidity,"
        "air_pressure_at_sea_level,"
        "air_temperature",
    },
    "Single": {
        "summary": "Air temperature",
        "value": "air_temperature",
    },
}

levels = {
    "Default": {
        "value": "",
    },
    "List": {
        "summary": "Comma separated list",
        "value": "1.0, 2.0",
    },
    "Range": {
        "summary": "Range",
        "value": "1.0/10.0",
    },
    "Repeating-interval": {
        "summary": "Repeating interval",
        "value": "R5/0.5/0.5",
    },
    "Wildcard": {
        "summary": "Open start range",
        "value": "../10.0",
    },
    "Combination": {
        "summary": "Combination",
        "value": "1.0, 1.5/1.8, R5/2.0/2.0",
    },
}

durations = {
    "Default": {
        "value": "",
    },
    "List": {
        "summary": "Comma separated list",
        "value": "PT0S, PT1M, PT10M",
    },
    "Range": {
        "summary": "Range",
        "value": "PT1M/PT10M",
    },
    "Wildcard": {
        "summary": "Open end range",
        "value": "PT0S/..",
    },
    "Combination": {
        "summary": "Combination",
        "value": "PT0S, PT1M/PT10M",
    },
}

methods = {
    "Default": {
        "value": "",
    },
    "List": {
        "summary": "Comma separated list",
        "value": "mean, maximum, minimum",
    },
    "Single": {
        "summary": "Single method",
        "value": "mean",
    },
}
