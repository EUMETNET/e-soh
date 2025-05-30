import json

import pytest
from covjson_pydantic.coverage import Coverage
from covjson_pydantic.coverage import CoverageCollection
from fastapi import HTTPException
from formatters.covjson import convert_to_covjson
from test.utilities import create_mock_obs_response
from test.utilities import load_json


# /collections/observations/position?coords=POINT(6.5848470019087%2053.123676213651)&
# datetime=2022-12-31T00%3A00%3A00Z%2F2022-12-31T01%3A00%3A00Z&parameter-name=wind_speed%3A10%3Amean%3APT10M
def test_single_parameter_convert():
    test_data = load_json("test/test_data/test_single_proto.json")
    compare_data = load_json("test/test_data/test_single_covjson.json")

    response = create_mock_obs_response(test_data)
    coverage_collection = convert_to_covjson(response.observations)

    assert coverage_collection is not None

    assert type(coverage_collection) is Coverage

    # Assert that the coverage collection has the correct parameter
    assert "wind_speed:10.0:mean:PT10M" in coverage_collection.parameters

    # Check that correct values exist in the coverage collection
    assert 9.21 in coverage_collection.ranges["wind_speed:10.0:mean:PT10M"].values

    assert len(coverage_collection.domain.axes.t.values) == 7

    # Number of time points should match with the number of observation values
    assert len(coverage_collection.domain.axes.t.values) == len(
        coverage_collection.ranges["wind_speed:10.0:mean:PT10M"].values
    )

    # compare the coverage collection with the compare data
    coverage_collection_json = json.loads(coverage_collection.model_dump_json(exclude_none=True))
    assert coverage_collection_json == compare_data


# /collections/observations/position?coords=POINT(6.5848470019087%2053.123676213651)&
# parameter-name=wind_from_direction%3A2.0%3Amean%3APT10M,wind_speed%3A10%3Amean%3APT10M,relative_humidity%3A2.0%3Amean%3APT1M&
# datetime=2022-12-31T00%3A00%3A00Z%2F2022-12-31T00%3A20%3A00Z
def test_multiple_parameter_convert():
    test_data = load_json("test/test_data/test_multiple_proto.json")
    compare_data = load_json("test/test_data/test_multiple_covjson.json")

    response = create_mock_obs_response(test_data)

    coverage_collection = convert_to_covjson(response.observations)

    assert coverage_collection is not None

    assert type(coverage_collection) is Coverage

    # Check that the coverage collection has the correct parameters
    assert (
        set(["wind_from_direction:2.0:mean:PT10M", "wind_speed:10.0:mean:PT10M", "relative_humidity:2.0:mean:PT1M"])
        == coverage_collection.parameters.root.keys()
    )

    # Check that correct values exist in the coverage collection
    assert 230.7 in coverage_collection.ranges["wind_from_direction:2.0:mean:PT10M"].values
    assert 9.19 in coverage_collection.ranges["wind_speed:10.0:mean:PT10M"].values
    assert 88.0 in coverage_collection.ranges["relative_humidity:2.0:mean:PT1M"].values

    coverage_collection_json = json.loads(coverage_collection.model_dump_json(exclude_none=True))
    assert coverage_collection_json == compare_data


# /collections/observations/area?coords=POLYGON((4.0%2052.4,%205.8%2052.4,5.8%2052.6,4.0%2052.6,%204.0%2052.4))&
# datetime=2022-12-31T00%3A00%3A00Z&parameter-name=air_temperature%3A2.0%3Amean%3APT1M
def test_single_parameter_area_convert():
    test_data = load_json("test/test_data/test_coverages_proto.json")
    compare_data = load_json("test/test_data/test_coverages_covjson.json")

    response = create_mock_obs_response(test_data)

    coverage_collection = convert_to_covjson(response.observations)

    assert coverage_collection is not None

    assert type(coverage_collection) is CoverageCollection

    assert len(coverage_collection.coverages) > 1

    assert all([type(coverage) is Coverage for coverage in coverage_collection.coverages])

    # Check that each coverage has the correct parameter
    assert all(["air_temperature:2.0:mean:PT1M" in coverage.parameters for coverage in coverage_collection.coverages])

    coverage_collection_json = json.loads(coverage_collection.model_dump_json(exclude_none=True))
    assert coverage_collection_json == compare_data


def test_empty_response_convert():
    test_data = load_json("test/test_data/test_empty_observations_proto.json")
    response = create_mock_obs_response(test_data)

    # Expect to get an HTTPException with status code of 404 and detail of
    # "Requested data not found." when converting an empty response
    with pytest.raises(HTTPException) as exception_info:
        convert_to_covjson(response.observations)

    assert exception_info.value.detail == "Requested data not found."
    assert exception_info.value.status_code == 404
