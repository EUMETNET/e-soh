import isodate


def seconds_to_iso_8601_duration(seconds: int) -> str:
    duration = isodate.Duration(seconds=seconds)
    iso_duration = isodate.duration_isoformat(duration)

    # TODO: find a better way to format these
    # Use PT24H instead of P1D
    if iso_duration == "P1D":
        iso_duration = "PT24H"

    # iso_duration defaults to P0D when seconds is 0
    if iso_duration == "P0D":
        iso_duration = "PT0S"

    return iso_duration


def convert_to_meter(level: int) -> str:
    level = str(float(level) / 100)
    return level
