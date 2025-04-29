import sys
import re
import isodate

from datetime import datetime
from datetime import timedelta
from typing import Tuple
from itertools import chain

from isodate import ISO8601Error
import datastore_pb2 as dstore
from fastapi import HTTPException
from google.protobuf.timestamp_pb2 import Timestamp
from grpc_getter import get_ts_ag_request
from pydantic import AwareDatetime
from pydantic import TypeAdapter


def get_datetime_range(datetime_string: str | None) -> Tuple[Timestamp, Timestamp] | None:
    if not datetime_string:
        return None

    errors = {}

    start_datetime, end_datetime = Timestamp(), Timestamp()
    aware_datetime_type_adapter = TypeAdapter(AwareDatetime)

    try:
        datetimes = tuple(value.strip() for value in datetime_string.split("/"))
        if len(datetimes) == 1:
            start_datetime.FromDatetime(aware_datetime_type_adapter.validate_python(datetimes[0]))
            end_datetime.FromDatetime(
                aware_datetime_type_adapter.validate_python(datetimes[0]) + timedelta(seconds=1)
            )  # HACK: Add one second so we get some data, as the store returns [start, end)
        else:
            if datetimes[0] != "..":
                start_datetime.FromDatetime(aware_datetime_type_adapter.validate_python(datetimes[0]))
            else:
                start_datetime.FromDatetime(datetime.min)
            if datetimes[1] != "..":
                # HACK add one second so that the end_datetime is included in the interval.
                end_datetime.FromDatetime(
                    aware_datetime_type_adapter.validate_python(datetimes[1]) + timedelta(seconds=1)
                )
            else:
                end_datetime.FromDatetime(datetime.max)

            if start_datetime.seconds > end_datetime.seconds:
                errors["datetime"] = f"Invalid range: {datetimes[0]} > {datetimes[1]}"

    except ValueError:
        errors["datetime"] = f"Invalid format: {datetime_string}"

    if errors:
        raise HTTPException(status_code=400, detail=errors)

    return start_datetime, end_datetime


# @cached(ttl=600)
async def get_current_parameter_names():
    """
    This function get a set of standard_names currently in the datastore
    The ttl_hash should be a value that is updated at the same frequency
    we want the lru_cache to be valid for.
    """

    unique_parameter_names = dstore.GetTSAGRequest(attrs=["parameter_name"])
    unique_parameter_names = await get_ts_ag_request(unique_parameter_names)

    return {i.combo.parameter_name for i in unique_parameter_names.groups}


async def verify_parameter_names(parameter_names: list) -> None:
    """
    Function for verifying that the given parameter names are valid.
    Raises error with unknown names if any are found.
    """
    unknown_parameter_names = []
    current_parameter_names = await get_current_parameter_names()

    for i in parameter_names:
        # HACK: This checking breaks the wildcard support (e.g. air_temperature:*:*:*). Skip if contains wildcards
        if "*" in i:
            continue
        if i not in current_parameter_names:
            unknown_parameter_names.append(i)

    if unknown_parameter_names:
        raise HTTPException(400, detail=f"Unknown parameter-name {unknown_parameter_names}")


def create_url_from_request(request):
    # The server root_path contains the path added by a reverse proxy
    base_path = request.scope.get("root_path")

    # The host will (should) be correctly set from X-Forwarded-Host and X-Forwarded-Scheme
    # headers by any proxy in front of it
    host = request.headers["host"]
    scheme = request.url.scheme

    return f"{scheme}://{host}{base_path}/collections"


def split_and_strip(cs_string: str) -> list[str]:
    return [i.strip() for i in cs_string.split(",")]


def validate_bbox(bbox: str) -> Tuple[float, float, float, float]:
    """
    Function for validating the bbox parameter.
    Raises error with invalid bbox if any are found.
    """
    errors = {}

    try:
        left, bottom, right, top = map(float, map(str.strip, bbox.split(",")))
    except ValueError:
        errors["bbox"] = f"Invalid format: {bbox}"
    else:
        if left > right or bottom > top:
            errors["range"] = f"Invalid bbox range: {bbox}"
        if abs(left - right) > 90 or abs(bottom - top) > 90:
            errors["range"] = f"Maximum bbox range is 90 degrees: {bbox}"
        if not -180 <= left <= 180 or not -180 <= right <= 180:
            errors["longitude"] = f"Invalid longitude: {bbox}"
        if not -90 <= bottom <= 90 or not -90 <= top <= 90:
            errors["latitude"] = f"Invalid latitude: {bbox}"

    if errors:
        raise HTTPException(status_code=400, detail=errors)

    return left, bottom, right, top


async def add_request_parameters(
    request,
    parameter_name: str | None,
    datetime: str | None,
    standard_names: str | None,
    levels: str | None,
    methods: str | None,
    durations: str | None,
):
    if parameter_name:
        parameter_name = split_and_strip(parameter_name)
        await verify_parameter_names(parameter_name)
        request.filter["parameter_name"].values.extend(parameter_name)

    if datetime:
        start, end = get_datetime_range(datetime)
        request.temporal_interval.start.CopyFrom(start)
        request.temporal_interval.end.CopyFrom(end)

    if standard_names:
        request.filter["standard_name"].values.extend(split_and_strip(standard_names))

    if levels:
        request.filter["level"].values.extend(get_levels_values(levels))

    if methods:
        request.filter["function"].values.extend(split_and_strip(methods))

    if durations:
        request.filter["period"].values.extend(get_periods_or_range(durations))


def get_periods_or_range(periods: str) -> list[str]:
    """
    Function for getting the periods filter list as a list of period ranges or
    periods
    """
    periods = split_and_strip(periods)
    try:
        return [
            get_iso_8601_range(period) if "/" in period else str(iso_8601_duration_to_seconds(period))
            for period in periods
        ]
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"{err}")


def get_levels_values(levels: str) -> list[str]:
    """
    Function for getting the levels filters as a list of levels, ranges,
    range intervals or combination of the previous
    """
    # it can be z=value1,value2,value3: z=2,10,80
    # or z=minimum value/maximum value: z=10/100
    # or z=Rn/min height/height interval: z=R20/100/50
    # or a combination of the above: z=10,30/100,200,300,R20/100/50

    def get_level_or_range(z: str) -> list[str]:
        try:
            split_on_slash = z.split("/")
            if len(split_on_slash) == 2:
                return get_z_values_from_range(split_on_slash)
            elif len(split_on_slash) > 2:
                return get_z_values_from_interval(split_on_slash)
            else:
                return [convert_m_to_cm(z)]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid levels value: {z}")

    return list(chain(*[get_level_or_range(z) for z in split_and_strip(levels)]))


def get_z_values_from_range(range: list[str]) -> list[str]:
    """
    Function for getting the z values from a range.
    """
    start, end = range[0], range[1]
    z_min = convert_m_to_cm(start) if start != ".." else start
    z_max = convert_m_to_cm(end) if end != ".." else end

    return [f"{z_min}/{z_max}"]


def get_z_values_from_interval(interval: list[str]) -> list[str]:
    """
    Function for getting the z values from a repeating-interval pattern.
    """
    # Make sure the pattern is Rn/n/n
    # Allow optional decimals in interval and starting value
    # TODO: Can the starting value be negative? Can the interval be negative to go in reverse?
    pattern = re.compile(r"^R\d+/\d+(\.\d+)?/\d+(\.\d+)?$")
    if not pattern.match("/".join(interval)):
        raise HTTPException(status_code=400, detail=f"Invalid levels repeating-interval: {'/'.join(interval)}")

    amount_of_intervals = int(interval[0][1:])
    min_height = int(float(interval[1]) * 100)
    increment_value = int(float(interval[2]) * 100)

    return [str(min_height + i * increment_value) for i in range(amount_of_intervals)]


def is_float(element: any) -> bool:
    if element is None:
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False


async def get_unique_values_for_metadata(field: str) -> list[str]:
    request = dstore.GetTSAGRequest(attrs=[field])
    response = await get_ts_ag_request(request)
    return [getattr(i.combo, field) for i in response.groups]


def iso_8601_duration_to_seconds(period: str) -> int:
    try:
        duration = isodate.parse_duration(period.upper())
    except ISO8601Error:
        raise ValueError(f"Invalid ISO 8601 duration: {period}")

    if isinstance(duration, isodate.duration.Duration):
        # Years and months need special handling
        years_in_seconds = duration.years * 31556926  # Seconds in year
        months_in_seconds = duration.months * 2629744  # Seconds in month
        days_in_seconds = duration.tdelta.days * 24 * 60 * 60
        seconds_in_seconds = duration.tdelta.seconds
        total_seconds = years_in_seconds + months_in_seconds + days_in_seconds + seconds_in_seconds
    else:
        # It's a simple timedelta, so just get the total seconds
        total_seconds = duration.total_seconds()

    return int(total_seconds)


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


def get_iso_8601_range(range: str) -> str:
    """
    Returns a range in seconds from two ISO 8601 periods.
    """

    split_on_slash = range.split("/")
    if len(split_on_slash) != 2:
        raise HTTPException(status_code=400, detail=f"Invalid ISO 8601 range format: {range}")

    start, end = split_on_slash[0], split_on_slash[1]
    if not start or not end:
        raise HTTPException(status_code=400, detail=f"Invalid ISO 8601 period: {start} / {end}")

    try:
        if start != "..":
            start_seconds = iso_8601_duration_to_seconds(start)
        else:
            start_seconds = 0

        if end != "..":
            end_seconds = iso_8601_duration_to_seconds(end)
        else:
            end_seconds = sys.maxsize

        if start_seconds > end_seconds:
            raise HTTPException(status_code=400, detail=f"Invalid ISO 8601 range: {start} > {end}")

    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"{err}")

    return f"{start_seconds}/{end_seconds}"


def convert_m_to_cm(m: str) -> str:
    """
    Function for converting a meters str to centimeters str
    """
    return str(int(float(m) * 100))


def convert_cm_to_m(cm: int) -> float:
    """
    Function for converting a centimeters int to meters float
    """
    return cm / 100
