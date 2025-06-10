import json

from deepdiff import DeepDiff
from formatters.geojson import convert_to_geojson
from test.utilities import create_mock_obs_response
from test.utilities import load_json


def actual_response_is_expected_response(actual_response, expected_json, **kwargs):
    diff = DeepDiff(expected_json, actual_response, **kwargs)
    assert diff == {}, diff


def test_geojson_conversion():
    test_data = load_json("test/test_data/test_single_proto.json")
    compare_data = load_json("test/test_data/test_ts_expected_geojson.json")

    response = create_mock_obs_response(test_data)
    result = json.loads(
        convert_to_geojson(response.observations, base_url="http://fake.url/").model_dump_json(exclude_none=True)
    )

    actual_response_is_expected_response(result, compare_data)


if __name__ == "__main__":
    test_geojson_conversion()
