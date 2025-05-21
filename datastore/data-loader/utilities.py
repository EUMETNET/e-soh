import isodate
import re
from datetime import timedelta
from isodate import ISO8601Error


regex_level = re.compile(r"first|second|third|[0-9]+(\.[0-9]+)?(?=m)|(?<=Level )[0-9]+", re.IGNORECASE)
regex_level_centimeters = re.compile(r"[0-9]+(\.[0-9]+)?(?=cm)")
regex_time_period = re.compile(r"(\d+) (Hours|Min)", re.IGNORECASE)


def convert_standard_names_to_cf(standard_name):
    standard_name_mapping = {
        "cloud_cover": "cloud_area_fraction",
        "total_downwelling_shortwave_flux_in_air": "surface_downwelling_shortwave_flux_in_air",
        "precipitation_rate": "rainfall_rate",
        "air_pressure_at_sea_level": "air_pressure_at_mean_sea_level",
    }
    return standard_name_mapping.get(standard_name, standard_name)


# NOTE: Only units are converted currently, not values.
def convert_unit_names(unit):
    unit_mapping = {
        "degrees Celsius": "Cel",
        "ft": "m",
        "min": "s",
        "degree": "deg",
        "%": "%",
        "mm": "kg/m2",
        "m s-1": "m/s",
        "octa": "okta",
        "W m-2": "W/m2",
    }
    return unit_mapping.get(unit, unit)


def iso_8601_duration_to_seconds(period: str) -> int:
    try:
        duration = isodate.parse_duration(period)
    except ISO8601Error:
        raise ValueError(f"Invalid ISO 8601 duration: {period}")

    if isinstance(duration, timedelta):
        total_seconds = duration.total_seconds()
    else:
        raise ValueError("Duration not convertable to seconds.")

    return int(total_seconds)


def generate_parameter_name(standard_name, long_name, station_id, station_name, param_id):
    # TODO: HACK To let the loader have a unique parameter ID and make the parameters distinguishable.
    level = "2.0"
    long_name = long_name.lower()
    station_name = station_name.lower()
    if level_raw := re.search(regex_level, long_name):
        level = level_raw[0]
    if level_raw := re.search(regex_level_centimeters, long_name):
        level = str(float(level_raw[0]) / 100.0)
    elif "grass" in long_name:
        level = "0"
    elif param_id in ["pg", "pr", "pwc", "vv", "W10", "W10-10", "ww", "ww-10", "za", "zm"]:
        # https://english.knmidata.nl/open-data/actuele10mindataknmistations
        # Comments code: 2, 3, 11
        # Note: The sensor is not installed at equal heights at all types of measurement sites:
        # At 'AWS' sites the device is installed at 1.80m. At 'AWS/Aerodrome' and 'Mistpost'
        # (note that this includes site Voorschoten (06215) which is 'AWS/Mistpost')
        # the device is installed at 2.50m elevation. Exceptions are Berkhout AWS (06249),
        # De Bilt AWS (06260) and Twenthe AWS (06290) where the sensor is installed at 2.50m.
        # Since WaWa is automatic detection I asssumed that the others stations are AWS, thus 1.80m
        if (
            station_id in ["06215", "06249", "06260", "06290"]
            or "aerodrome" in station_name
            or "mistpost" in station_name
        ):
            level = "2.5"
        else:
            level = "1.8"

    if "minimum" in long_name:
        function = "minimum"
    elif "maximum" in long_name:
        function = "maximum"
    elif "average" in long_name:
        function = "mean"
    else:
        function = "point"

    period = "PT0S"
    if period_raw := re.findall(regex_time_period, long_name):
        if len(period_raw) == 1:
            period_raw = period_raw[0]
        else:
            raise Exception(f"{period_raw}, {long_name}")
        time, scale = period_raw
        if scale == "hours":
            period = f"PT{time}H"
        elif scale == "min":
            period = f"PT{time}M"
    elif param_id == "ww-10":
        period = "PT10M"
    elif param_id == "ww":
        period = "PT01H"

    standard_name = convert_standard_names_to_cf(standard_name)
    return standard_name, level, function, period
