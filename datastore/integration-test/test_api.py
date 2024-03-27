import json
import logging
import os
from pathlib import Path

import requests
from deepdiff import DeepDiff

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8008")


def load_json(expected_path):
    file_path = Path(Path(__file__).parent, expected_path).resolve()
    with open(file_path) as file:
        expected_json = json.load(file)
    return expected_json


def actual_response_is_expected_response(actual_response, expected_json, **kwargs):
    diff = DeepDiff(expected_json, actual_response.json(), **kwargs)
    assert diff == {}
    # TODO: maybe this check should be a unit test instead of integration.
    # Deep diff does not check dict keys for order, manually validate if the order is correct.
    validate_if_the_dict_keys_are_in_alphabetic_order(actual_response=actual_response, expected_json=expected_json)


def validate_if_the_dict_keys_are_in_alphabetic_order(actual_response, expected_json):
    """Python dictionaries used to be unordered. Resulting that the keys of dictionaries are not checked for the right
    order. Therefore dictionaries where the parameter names are the keys are checked manually for the correct sequence
    in this function."""
    actual_json = actual_response.json()

    if actual_json.get("ranges") or expected_json.get("ranges"):
        actual_ranges = actual_json["ranges"]
        expected_ranges = expected_json["ranges"]
        assert list(actual_ranges.keys()) == list(expected_ranges.keys())
    if actual_json.get("parameters") or expected_json.get("parameters"):
        actual_parameters = actual_json["parameters"]
        expected_parameters = expected_json["parameters"]
        assert list(actual_parameters.keys()) == list(expected_parameters.keys())
    if actual_json.get("coverages") or expected_json.get("coverages"):
        actual_coverages = actual_json["coverages"]
        expected_coverages = expected_json["coverages"]
        for actual_covjson, expected_covjson in zip(actual_coverages, expected_coverages):
            assert list(actual_covjson["ranges"].keys()) == list(expected_covjson["ranges"].keys())
            assert list(actual_covjson["parameters"].keys()) == list(expected_covjson["parameters"].keys())


def test_that_a_collection_of_all_collections_is_the_same_as_a_single_collection():
    response_all_collections = requests.get(url=BASE_URL + "/collections")
    response_single_collection = requests.get(url=BASE_URL + "/collections/observations")

    assert response_all_collections.status_code == 200
    assert response_single_collection.status_code == 200
    diff = DeepDiff(
        response_all_collections.json()["collections"][0],
        response_single_collection.json(),
        exclude_paths=["root['links'][0]['rel']"],
    )
    assert diff == {}


def test_get_all_collections():
    actual_response = requests.get(url=BASE_URL + "/collections")

    expected_json = load_json("response/metadata_collections_all_collections.json")

    assert actual_response.status_code == 200
    actual_response_is_expected_response(actual_response, expected_json, exclude_regex_paths=r"\['href'\]$")


def test_get_a_single_existing_collection():
    collection_id = "observations"
    actual_response = requests.get(url=BASE_URL + f"/collections/{collection_id}")

    # Use all_collections to reduce duplication.
    expected_json = load_json("response/metadata_collections_all_collections.json")["collections"][0]
    expected_json["links"][0]["rel"] = "self"

    assert actual_response.status_code == 200
    actual_response_is_expected_response(actual_response, expected_json, exclude_regex_paths=r"\['href'\]$")


def test_from_a_single_collection_get_locations_within_a_bbox():
    collection_id = "observations"
    bbox = "5.0,52.0,6.0,52.1"
    actual_response = requests.get(url=BASE_URL + f"/collections/{collection_id}/locations?bbox={bbox}")

    expected_json = load_json("response/data_locations_two_points_with_multiple_parameters.json")

    assert actual_response.status_code == 200
    actual_response_is_expected_response(actual_response, expected_json)


def test_from_a_single_collection_get_locations_within_a_bbox_with_parameter_name_filtering():
    collection_id = "observations"
    bbox = "5.0,52.0,6.0,52.1"
    parameters = "air_temperature:0.1:minimum:PT10M, air_pressure_at_sea_level:1:mean:PT1M"
    actual_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/locations?bbox={bbox}&parameter-name={parameters}"
    )

    expected_json = load_json("response/data_locations_two_points_with_two_parameters.json")

    assert actual_response.status_code == 200
    actual_response_is_expected_response(actual_response, expected_json)


def test_from_a_single_collection_get_a_single_location():
    collection_id = "observations"
    location_id = "0-20000-0-06260"
    parameters = (
        "air_temperature:1.5:maximum:PT10M , wind_from_direction:2.0:mean:PT10M,relative_humidity:2.0:mean:PT1M"
    )
    datetime = "../2022-12-31T01:10:00Z"
    actual_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/locations/{location_id}"
        f"?parameter-name={parameters}&datetime={datetime}"
    )

    expected_json = load_json("response/data_locations_one_location_with_three_parameters.json")

    assert actual_response.status_code == 200
    actual_response_is_expected_response(actual_response, expected_json)


def test_that_the_order_of_the_parameters_in_the_response_is_always_the_same():
    """Test that we do not care about the order of parameters passed in the query.
    By comparing two requests with the same parameters but in a different sequence.
    The first request returns the same response as the second request.
    """
    collection_id = "observations"
    location_id = "0-20000-0-06260"
    parameters = " wind_from_direction:2.0:mean:PT10M,wind_speed:10:mean:PT10M ,  relative_humidity:2.0:mean:PT1M"
    first_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/locations/{location_id}" f"?parameter-name={parameters}"
    )

    parameters_2 = (
        " relative_humidity:2.0:mean:PT1M, wind_speed:10:mean:PT10M,   wind_from_direction:2.0:mean:PT10M    "
    )
    second_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/locations/{location_id}" f"?parameter-name={parameters_2}"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    diff = DeepDiff(first_response.json(), second_response.json())
    assert diff == {}


def test_from_a_single_collection_get_a_single_location_which_does_not_exist():
    collection_id = "observations"
    location_id = "does-not-exist"
    parameters = "does-not-exist"
    actual_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/locations/{location_id}?parameter-name={parameters}"
    )

    expected_json = load_json("response/400_not_found.json")

    assert actual_response.status_code == 400
    actual_response_is_expected_response(actual_response, expected_json)


def test_from_a_single_collection_get_a_single_position_with_one_parameter():
    collection_id = "observations"
    coords = "POINT(5.179705 52.0988218)"
    parameters = "air_temperature:1.5:maximum:PT10M"
    datetime = "2022-12-31T00:50:00Z/2022-12-31T02:10:00Z"
    actual_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/position"
        f"?coords={coords}&parameter-name={parameters}&datetime={datetime}"
    )

    expected_json = load_json("response/data_position_one_location_with_one_parameter.json")

    assert actual_response.status_code == 200
    actual_response_is_expected_response(actual_response, expected_json)


def test_from_a_single_collection_get_an_area_with_two_parameters():
    collection_id = "observations"
    coords = "POLYGON((5.0 52.0, 6.0 52.0,6.0 52.1,5.0 52.1, 5.0 52.0))"
    parameters = "relative_humidity:2.0:mean:PT1M ,   wind_speed:10:mean:PT10M"
    datetime = "2022-12-31T22:50:00Z/.."
    actual_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/area"
        f"?coords={coords}&parameter-name={parameters}&datetime={datetime}"
    )

    expected_json = load_json("response/data_area_two_locations_with_two_parameters.json")

    assert actual_response.status_code == 200
    actual_response_is_expected_response(actual_response, expected_json)


def test_items_get_area():
    collection_id = "observations"
    bbox = "4.5,52.4,4.6,52.57"
    actual_response = requests.get(url=BASE_URL + f"/collections/{collection_id}/items?bbox={bbox}")

    assert actual_response.status_code == 200
    expected_json = load_json("response/items_within_area_single_platform.json")
    actual_response_is_expected_response(actual_response, expected_json)


def test_items_get_id():
    collection_id = "observations"
    timeseries_id = "f0d06231a6508f281dbdaea0b5000220"
    actual_response = requests.get(url=BASE_URL + f"/collections/{collection_id}/items/{timeseries_id}")

    assert actual_response.status_code == 200
    expected_json = load_json("response/items_area_with_one_parameter_name.json")
    actual_response_is_expected_response(actual_response, expected_json)


def test_items_get_area_with_one_parameter_name():
    collection_id = "observations"
    bbox = "5.7,52.0,6.0,52.059"
    parameter_name = "air_temperature:2.0:minimum:PT12H"
    actual_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/items?bbox={bbox}&parameter-name={parameter_name}"
    )

    assert actual_response.status_code == 200
    expected_json = load_json("response/items_area_with_one_parameter_name.json")
    actual_response_is_expected_response(actual_response, expected_json)


def test_items_get_one_platform():
    collection_id = "observations"
    platform = "0-20000-0-06225"
    actual_response = requests.get(url=BASE_URL + f"/collections/{collection_id}/items?platform={platform}")

    assert actual_response.status_code == 200
    expected_json = load_json("response/items_within_area_single_platform.json")
    actual_response_is_expected_response(actual_response, expected_json)


# This test can not be made at the moment. Datetime have to limitation on the number
# ts that is returned due to how temporal_mode latest is implemented.
# def test_items_get_within_datetime():
#     collection_id = "observations"
#     datetime = "2022-12-31T00:50:00Z/2022-12-31T02:10:00Z"
#     actual_response = requests.get(url=BASE_URL + f"/collections/{collection_id}/items" f"?datetime={datetime}")

#     assert actual_response.status_code == 200
#     actual_response_is_expected_response(
#         actual_response, "response/collection/items/200/metadata_in_datetime_range"  # TODO: create response file
#     )


def test_items_dont_set_bbox_or_platform():
    collection_id = "observations"
    parameter_name = "this_parameter_name_does_not_exist"
    actual_response = requests.get(
        url=BASE_URL + f"/collections/{collection_id}/items" f"?parameter-name={parameter_name}"
    )

    assert actual_response.status_code == 400
    expected_json = load_json("response/items_no_bbox_or_platform.json")
    actual_response_is_expected_response(actual_response, expected_json)


def test_items_no_data_return():
    collection_id = "observations"
    bbox = "-49.394531,22.593726,-36.386719,31.503629"
    actual_response = requests.get(url=BASE_URL + f"/collections/{collection_id}/items" f"?bbox={bbox}")

    assert actual_response.status_code == 404
    expected_json = load_json("response/items_no_data_found.json")
    actual_response_is_expected_response(actual_response, expected_json)
