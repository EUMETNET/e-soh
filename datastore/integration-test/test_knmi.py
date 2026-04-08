# Note that this assumes that the KNMI test data is loader (using loader container)
import os
from datetime import datetime

import grpc
import pytest
from google.protobuf.timestamp_pb2 import Timestamp

import datastore_pb2 as dstore
import datastore_pb2_grpc as dstore_grpc

NUMBER_OF_PARAMETERS = 44
NUMBER_OF_STATIONS = 55


@pytest.fixture(scope="session")
def grpc_stub():
    with grpc.insecure_channel(f"{os.getenv('DSHOST', 'localhost')}:{os.getenv('DSPORT', '50050')}") as channel:
        yield dstore_grpc.DatastoreStub(channel)


def test_find_series_single_station_single_parameter(grpc_stub):
    request = dstore.GetObsRequest(
        filter=dict(
            platform=dstore.Strings(values=["0-20000-0-06260"]),
            parameter_name=dstore.Strings(values=["relative_humidity:2.0:mean:PT1M"]),
        )
    )
    response = grpc_stub.GetObservations(request)

    assert len(response.observations) == 1
    obs_mdata = response.observations[0].obs_mdata[0]
    assert obs_mdata.geo_point.lat == 52.098821802977
    assert obs_mdata.geo_point.lon == 5.1797058644882


def test_find_series_all_stations_single_parameter(grpc_stub):
    request = dstore.GetObsRequest(
        filter=dict(parameter_name=dstore.Strings(values=["relative_humidity:2.0:mean:PT1M"]))
    )
    response = grpc_stub.GetObservations(request)

    assert len(response.observations) == 46  # Not all station have RH


def test_find_series_single_station_all_parameters(grpc_stub):
    request = dstore.GetObsRequest(filter=dict(platform=dstore.Strings(values=["0-20000-0-06260"])))
    response = grpc_stub.GetObservations(request)

    assert (
        len([obs.ts_mdata.parameter_name for obs in response.observations]) == 31
    )  # Station 06260 doesn't have all parameters


def test_get_values_single_station_single_parameter(grpc_stub):
    ts_request = dstore.GetObsRequest(
        filter=dict(
            platform=dstore.Strings(values=["0-20000-0-06260"]),
            parameter_name=dstore.Strings(values=["relative_humidity:2.0:mean:PT1M"]),
        )
    )
    response = grpc_stub.GetObservations(ts_request)

    assert len(response.observations) == 1
    observations = response.observations[0].obs_mdata
    assert len(observations) == 144
    assert float(observations[0].value) == 95.0
    assert float(observations[-1].value) == 59.0


def test_get_values_single_station_single_parameter_one_hour(grpc_stub):
    start_datetime, end_datetime = Timestamp(), Timestamp()
    start_datetime.FromDatetime(datetime(2022, 12, 31, 11))
    end_datetime.FromDatetime(datetime(2022, 12, 31, 12))

    ts_request = dstore.GetObsRequest(
        filter=dict(
            platform=dstore.Strings(values=["0-20000-0-06260"]),
            parameter_name=dstore.Strings(values=["relative_humidity:2.0:mean:PT1M"]),
        ),
        temporal_interval=dstore.TimeInterval(start=start_datetime, end=end_datetime),
    )
    response = grpc_stub.GetObservations(ts_request)

    assert len(response.observations) == 1
    observations = response.observations[0].obs_mdata
    assert len(observations) == 6


input_params_polygon = [
    (
        # Multiple stations within
        ((52.15, 4.90), (52.15, 5.37), (51.66, 5.37), (51.66, 4.90)),
        ["relative_humidity:2.0:mean:PT1M"],
        ["0-20000-0-06260", "0-20000-0-06348", "0-20000-0-06356"],
    ),
    (
        # Multiple stations with a single parameter
        ((52.15, 4.90), (52.15, 5.37), (51.66, 5.37), (51.66, 4.90)),
        ["relative_humidity:2.0:mean:PT1M"],
        ["0-20000-0-06260", "0-20000-0-06348", "0-20000-0-06356"],
    ),
    (
        # Multiple stations with multiple parameters
        ((52.15, 4.90), (52.15, 5.37), (51.66, 5.37), (51.66, 4.90)),
        ["wind_from_direction:2.0:mean:PT10M", "relative_humidity:2.0:mean:PT1M", "air_temperature:2.0:mean:PT1M"],
        ["0-20000-0-06260", "0-20000-0-06348", "0-20000-0-06356"],
    ),
    (
        # One station within
        ((52.11, 5.15), (52.11, 5.204), (52.08, 5.204), (52.08, 5.15)),
        ["relative_humidity:2.0:mean:PT1M"],
        ["0-20000-0-06260"],
    ),
    (
        # Nothing within
        ((51.82, 5.07), (51.82, 5.41), (51.73, 5.41), (51.73, 5.07)),
        ["relative_humidity:2.0:mean:PT1M"],
        [],
    ),
    (
        # Middle top
        ((52.0989, 4.17), (52.0989, 6.18), (52.09, 6.18), (52.09, 4.17)),
        ["relative_humidity:2.0:mean:PT1M"],
        ["0-20000-0-06260"],
    ),
    (
        # Middle bottom, should fall outside since polygon is curved,
        # because the earth is round (postgres geography).
        ((52.1, 4.17), (52.1, 6.18), (52.0989, 6.18), (52.0989, 4.17)),
        ["relative_humidity:2.0:mean:PT1M"],
        [],
    ),
    (
        # Complex polygon
        (
            (51.45, 3.47),
            (51.39, 3.67),
            (51.39, 4.28),
            (51.52, 4.96),
            (51.89, 5.46),
            (52.18, 5.30),
            (51.75, 3.68),
        ),
        ["relative_humidity:2.0:mean:PT1M"],
        [
            "0-20000-0-06260",
            "0-20000-0-06310",
            "0-20000-0-06323",
            "0-20000-0-06340",
            "0-20000-0-06348",
            "0-20000-0-06350",
            "0-20000-0-06356",
        ],
    ),
    (
        # All stations in the Netherlands which have RH
        ((56.00, 2.85), (56.00, 7.22), (50.75, 7.22), (50.75, 2.85)),
        ["relative_humidity:2.0:mean:PT1M"],
        # fmt: off
        [
            "0-20000-0-06203", "0-20000-0-06204", "0-20000-0-06205", "0-20000-0-06207", "0-20000-0-06208",
            "0-20000-0-06211", "0-20000-0-06214", "0-20000-0-06215", "0-20000-0-06235", "0-20000-0-06239",
            "0-20000-0-06240", "0-20000-0-06242", "0-20000-0-06249", "0-20000-0-06251", "0-20000-0-06257",
            "0-20000-0-06260", "0-20000-0-06267", "0-20000-0-06269", "0-20000-0-06270", "0-20000-0-06273",
            "0-20000-0-06275", "0-20000-0-06277", "0-20000-0-06278", "0-20000-0-06279", "0-20000-0-06280",
            "0-20000-0-06283", "0-20000-0-06286", "0-20000-0-06290", "0-20000-0-06310", "0-20000-0-06317",
            "0-20000-0-06319", "0-20000-0-06323", "0-20000-0-06330", "0-20000-0-06340", "0-20000-0-06344",
            "0-20000-0-06348", "0-20000-0-06350", "0-20000-0-06356", "0-20000-0-06370", "0-20000-0-06375",
            "0-20000-0-06377", "0-20000-0-06380", "0-20000-0-06391"
        ],
        # fmt: on
    ),
]


@pytest.mark.parametrize("coords,param_ids,expected_station_ids", input_params_polygon)
def test_get_observations_with_polygon(grpc_stub, coords, param_ids, expected_station_ids):
    polygon = dstore.Polygon(points=[dstore.Point(lat=lat, lon=lon) for lat, lon in coords])
    get_obs_request = dstore.GetObsRequest(
        spatial_polygon=polygon, filter=dict(parameter_name=dstore.Strings(values=param_ids))
    )
    get_obs_response = grpc_stub.GetObservations(get_obs_request)

    actual_station_ids = sorted({ts.ts_mdata.platform for ts in get_obs_response.observations})
    assert actual_station_ids == expected_station_ids
    number_of_parameters = len(param_ids) if param_ids else NUMBER_OF_PARAMETERS
    expected_number_of_timeseries = number_of_parameters * len(expected_station_ids)
    assert len(get_obs_response.observations) == expected_number_of_timeseries
