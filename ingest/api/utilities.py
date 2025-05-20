import isodate
from fastapi import Request


def get_base_url_from_request(request: Request) -> str:
    # The server root_path contains the path added by a reverse proxy
    base_path = request.scope.get("root_path")

    # The host will (should) be correctly set from X-Forwarded-Host and X-Forwarded-Scheme
    # headers by any proxy in front of it
    host = request.headers["host"]
    scheme = request.url.scheme

    return f"{scheme}://{host}{base_path}"


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
