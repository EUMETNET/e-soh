import pytest
from google.protobuf.timestamp_pb2 import Timestamp

from utilities import get_levels_values
from utilities import get_datetime_range
from contextlib import nullcontext as does_not_raise
from fastapi import HTTPException

levels_in_out = [
    ("1", ["100"]),
    ("1,2", ["100", "200"]),
    ("1,2, 3", ["100", "200", "300"]),
    ("1/3", ["100/300"]),
    ("../3", ["../300"]),
    ("1/..", ["100/.."]),
    ("R3/1.2/0.3", ["120", "150", "180"]),
    ("1, 3/5, R3/5/0.1,11", ["100", "300/500", "500", "510", "520", "1100"]),
]


@pytest.mark.parametrize("levels_in, levels_out", levels_in_out)
def test_get_levels_values(levels_in, levels_out):
    assert get_levels_values(levels_in) == levels_out


datetime_in_out = [
    (
        "2026-01-01T00:00Z/2026-01-01T02:00Z",
        (
            Timestamp(seconds=1767225600),
            Timestamp(seconds=1767232801),
        ),
        False,
    ),
    (
        "2026-01-01T00:00:00Z/..",
        (
            Timestamp(seconds=1767225600),
            Timestamp(seconds=253402300799, nanos=999999000),
        ),
        False,
    ),
    (
        "../2026-01-01T00:00Z",
        (
            Timestamp(seconds=-62135596800),
            Timestamp(seconds=1767225601),
        ),
        False,
    ),
    (
        "2026-01-01T00:00:00.123Z",
        (
            Timestamp(seconds=1767225600, nanos=123000000),
            Timestamp(seconds=1767225601, nanos=123000000),
        ),
        False,
    ),
    (
        "2026-01-01T00:00+02:00/2026-01-05T00:00-02:00",
        (
            Timestamp(seconds=1767218400),
            Timestamp(seconds=1767578401),
        ),
        False,
    ),
    (
        "2026-01-01/2026-01-02",
        None,
        True,
    ),
    (
        "2026-01-01T00:00Z/2025-12-31T23:59Z",
        None,
        True,
    ),
]


@pytest.mark.parametrize("datetime_in, timestamps_out, raise_error", datetime_in_out)
def test_get_datetime_range(datetime_in, timestamps_out, raise_error):
    with pytest.raises(HTTPException) if raise_error else does_not_raise():
        assert get_datetime_range(datetime_in) == timestamps_out
