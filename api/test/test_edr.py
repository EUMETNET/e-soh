from unittest.mock import patch

import datastore_pb2 as dstore
from fastapi.testclient import TestClient
from main import app
from test.utilities import create_mock_obs_response
from test.utilities import load_json


client = TestClient(app)

# expected response fields for endpoints
expected_metadata_endpoint_response_fields = [
    "parameter_name",
    "platform",
    "platform_name",
    "geo_point",
    "standard_name",
    "unit",
    "level",
    "period",
    "function",
]

expected_data_endpoint_response_fields = [
    "parameter_name",
    "platform",
    "geo_point",
    "standard_name",
    "level",
    "period",
    "function",
    "unit",
    "obstime_instant",
    "value",
]


def test_get_locations_without_query_params():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request, patch(
        "utilities.verify_parameter_names"
    ) as mock_verify_parameter_names:
        # Load arbitrary test data for making a mock_obs_request
        test_data = load_json("test/test_data/test_feature_collection_proto.json")

        mock_verify_parameter_names.return_value = None
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        # Create a GetObsRequest object with the expected arguments
        expected_args = dstore.GetObsRequest(
            temporal_latest=True, included_response_fields=expected_metadata_endpoint_response_fields
        )

        response = client.get("/collections/observations/locations")

        # Check that getObsRequest gets called with correct arguments when no parameters
        # given in query
        mock_get_obs_request.assert_called_once()
        m_args = mock_get_obs_request.call_args[0][0]

        assert m_args == expected_args
        assert response.status_code == 200


def test_get_locations_with_empty_response():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:
        test_data = load_json("test/test_data/test_empty_proto.json")

        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get("/collections/observations/locations")

        assert response.status_code == 404
        assert response.json() == {"detail": "Query did not return any locations."}


def test_get_locations_with_query_params():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request, patch(
        "utilities.verify_parameter_names"
    ) as mock_verify_parameter_names:
        test_data = load_json("test/test_data/test_feature_collection_proto.json")
        compare_data = load_json("test/test_data/test_feature_collection.json")

        mock_verify_parameter_names.return_value = None
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get(
            "/collections/observations/locations?bbox=5.1,52.0,6.0,52.1"
            "&datetime=2022-12-31T00:00:00Z/2022-12-31T01:00:00Z"
            "&parameter-name=wind_speed:10.0:mean:PT10M, air_temperature:0.1:minimum:PT10M"
        )

        # Check that getObsRequest gets called with correct arguments given in query
        mock_get_obs_request.assert_called_once()
        m_args = mock_get_obs_request.call_args[0][0]

        assert {"wind_speed:10.0:mean:PT10M", "air_temperature:0.1:minimum:PT10M"} == set(
            m_args.filter["parameter_name"].values
        )
        assert m_args.temporal_latest
        assert len(m_args.spatial_polygon.points) == 5
        assert m_args.spatial_polygon.points[0].lon == 5.1
        assert "2022-12-31 00:00:00" == m_args.temporal_interval.start.ToDatetime().strftime("%Y-%m-%d %H:%M:%S")
        assert "2022-12-31 01:00:01" == m_args.temporal_interval.end.ToDatetime().strftime("%Y-%m-%d %H:%M:%S")

        assert response.status_code == 200
        assert response.json() == compare_data


def test_get_locations_with_too_few_bbox_parameters():
    response = client.get("/collections/observations/locations?bbox=5.1,52.0,6.0")

    assert response.status_code == 400
    assert response.json() == {"detail": {"bbox": "Invalid format: 5.1,52.0,6.0"}}


def test_get_locations_with_incorrect_bbox_parameters():
    response = client.get("/collections/observations/locations?bbox=180,52.0,6.0,-180,5.1")

    assert response.status_code == 400
    assert response.json() == {"detail": {"bbox": "Invalid format: 180,52.0,6.0,-180,5.1"}}


def test_get_locations_with_too_large_bbox():
    response = client.get("/collections/observations/locations?bbox=-180, -90, 180, 90")

    assert response.status_code == 400
    assert response.json() == {"detail": {"range": "Maximum bbox range is 90 degrees: -180, -90, 180, 90"}}


def test_get_locations_id_with_single_parameter_query_without_format():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request, patch(
        "utilities.verify_parameter_names"
    ) as mock_verify_parameter_names:
        test_data = load_json("test/test_data/test_single_proto.json")
        compare_data = load_json("test/test_data/test_single_covjson.json")

        mock_verify_parameter_names.return_value = None
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get(
            "/collections/observations/locations/0-20000-0-06280?"
            + "parameter-name=wind_speed:10.0:mean:PT10M&datetime=2022-12-31T00:00:00Z/2022-12-31T01:00:00Z"
        )

        # Check that getObsRequest gets called with correct arguments given in query
        mock_get_obs_request.assert_called_once()
        m_args = mock_get_obs_request.call_args[0][0]

        assert {"wind_speed:10.0:mean:PT10M"} == set(m_args.filter["parameter_name"].values)
        assert {"0-20000-0-06280"} == set(m_args.filter["platform"].values)
        assert "2022-12-31 00:00:00" == m_args.temporal_interval.start.ToDatetime().strftime("%Y-%m-%d %H:%M:%S")
        assert "2022-12-31 01:00:01" == m_args.temporal_interval.end.ToDatetime().strftime("%Y-%m-%d %H:%M:%S")

        assert response.status_code == 200
        assert response.json()["type"] == "Coverage"
        assert response.json() == compare_data


def test_get_locations_id_without_parameter_names_query():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:
        test_data = load_json("test/test_data/test_multiple_proto.json")
        compare_data = load_json("test/test_data/test_multiple_covjson.json")

        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        # Create a GetObsRequest object with the expected arguments
        expected_args = dstore.GetObsRequest(
            filter=dict(platform=dstore.Strings(values=["0-20000-0-06280"])),
            included_response_fields=expected_data_endpoint_response_fields,
        )

        response = client.get("/collections/observations/locations/0-20000-0-06280?f=CoverageJSON")

        # Check that getObsRequest gets called with correct arguments when no parameter names are given
        # in query
        mock_get_obs_request.assert_called_once()
        m_args = mock_get_obs_request.call_args[0][0]

        assert m_args == expected_args
        assert response.status_code == 200
        assert response.json() == compare_data


def test_get_locations_id_with_incorrect_datetime_format():
    response = client.get(
        "/collections/observations/locations/0-20000-0-06260?datetime=20221231T000000Z/20221231T010000Z"
    )

    assert response.status_code == 400
    assert response.json() == {"detail": {"datetime": "Invalid format: 20221231T000000Z/20221231T010000Z"}}


def test_get_locations_id_with_incorrect_datetime_range():
    response = client.get(
        "/collections/observations/locations/0-20000-0-06260?datetime=2024-12-31T00:00:00Z/2022-12-31T01:00:00Z"
    )

    assert response.status_code == 400
    assert response.json() == {"detail": {"datetime": "Invalid range: 2024-12-31T00:00:00Z > 2022-12-31T01:00:00Z"}}


def test_get_locations_id_with_empty_response():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:
        test_data = load_json("test/test_data/test_empty_proto.json")

        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get("/collections/observations/locations/10000?f=CoverageJSON")

        assert response.status_code == 404
        assert response.json() == {"detail": "Requested data not found."}


def test_get_area_with_normal_query():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request, patch(
        "utilities.verify_parameter_names"
    ) as mock_verify_parameter_names:
        test_data = load_json("test/test_data/test_coverages_proto.json")
        compare_data = load_json("test/test_data/test_coverages_covjson.json")

        mock_verify_parameter_names.return_value = None
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get(
            "/collections/observations/area?coords=POLYGON((4.0 52.4,5.8 52.4,5.8 52.6,4.0 52.6,4.0 52.4))&"
            "datetime=2022-12-31T00:00:00Z&parameter-name=air_temperature:2.0:mean:PT1M"
        )

        # Check that getObsRequest gets called with correct arguments given in query
        mock_get_obs_request.assert_called_once()
        m_args = mock_get_obs_request.call_args[0][0]

        assert {"air_temperature:2.0:mean:PT1M"} == set(m_args.filter["parameter_name"].values)
        assert len(m_args.spatial_polygon.points) == 5
        assert m_args.spatial_polygon.points[0].lon == 4.0
        assert "2022-12-31 00:00:00" == m_args.temporal_interval.start.ToDatetime().strftime("%Y-%m-%d %H:%M:%S")
        assert "2022-12-31 00:00:01" == m_args.temporal_interval.end.ToDatetime().strftime("%Y-%m-%d %H:%M:%S")

        assert response.status_code == 200
        assert response.json() == compare_data


def test_get_area_with_without_parameter_names_query():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:
        test_data = load_json("test/test_data/test_coverages_proto.json")
        compare_data = load_json("test/test_data/test_coverages_covjson.json")

        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        expected_spatial_polygon_coords = [(4.0, 52.4), (5.8, 52.4), (5.8, 52.6), (4.0, 52.6), (4.0, 52.4)]

        # Create a GetObsRequest object with the expected arguments
        expected_args = dstore.GetObsRequest(
            spatial_polygon=dstore.Polygon(
                points=[dstore.Point(lat=coord[1], lon=coord[0]) for coord in expected_spatial_polygon_coords]
            ),
            included_response_fields=expected_data_endpoint_response_fields,
        )

        response = client.get(
            "/collections/observations/area?coords=POLYGON((4.0 52.4,5.8 52.4,5.8 52.6,4.0 52.6,4.0 52.4))"
        )

        mock_get_obs_request.assert_called_once()
        m_args = mock_get_obs_request.call_args[0][0]

        assert m_args == expected_args
        assert response.status_code == 200
        assert response.json() == compare_data


def test_get_area_with_incorrect_coords():
    response = client.get("/collections/observations/area?coords=POLYGON((22.12 59.86, 24.39 60.41))")

    assert response.status_code == 400
    assert response.json() == {
        "detail": {"coords": "Invalid or unparseable wkt provided: POLYGON((22.12 59.86, 24.39 60.41))"}
    }


def test_get_area_with_incorrect_geometry_type():
    response = client.get("/collections/observations/area?coords=POINT(22.12 59.86)")

    assert response.status_code == 400
    assert response.json() == {"detail": {"coords": "Invalid geometric type: Point"}}


def test_get_position_with_normal_query():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request, patch(
        "utilities.verify_parameter_names"
    ) as mock_verify_parameter_names:
        test_data = load_json("test/test_data/test_coverages_proto.json")
        compare_data = load_json("test/test_data/test_coverages_covjson.json")

        mock_verify_parameter_names.return_value = None
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get(
            "/collections/observations/position?coords=POINT(5.179705 52.0988218)"
            "&parameter-name=air_temperature:2.0:mean:PT1M&datetime=2022-12-31T00:00Z/2022-12-31T00:00Z"
        )

        # Check that getObsRequest gets called with correct arguments given in query
        mock_get_obs_request.assert_called_once()
        m_args = mock_get_obs_request.call_args[0][0]

        assert {"air_temperature:2.0:mean:PT1M"} == set(m_args.filter["parameter_name"].values)
        assert m_args.spatial_circle.radius == 0.01
        assert "2022-12-31 00:00:00" == m_args.temporal_interval.start.ToDatetime().strftime("%Y-%m-%d %H:%M:%S")
        assert "2022-12-31 00:00:01" == m_args.temporal_interval.end.ToDatetime().strftime("%Y-%m-%d %H:%M:%S")

        assert response.status_code == 200
        assert response.json() == compare_data


def test_get_position_with_incorrect_coords():
    response = client.get("/collections/observations/position?coords=POINT(60.41)")

    assert response.status_code == 400
    assert response.json() == {"detail": {"coords": "Invalid or unparseable wkt provided: POINT(60.41)"}}


def test_get_position_with_incorrect_geometry_type():
    response = client.get(
        "/collections/observations/position?coords=POLYGON((22.12 59.86, 24.39 60.41, "
        "24.39 60.41, 24.39 59.86, 22.12 59.86))"
    )

    assert response.status_code == 400
    assert response.json() == {"detail": {"coords": "Invalid geometric type: Polygon"}}


def test_get_data_with_incorrect_duration_range_format():
    response = client.get("/collections/observations/locations/0-20000-0-06260?durations=PT10M/PT1H/PT24H")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid ISO 8601 range format: PT10M/PT1H/PT24H"}


def test_get_data_with_range_parameter_empty():
    response = client.get("/collections/observations/locations/0-20000-0-06260?durations=/PT10M")

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid ISO 8601 period:  / PT10M"}


def test_get_data_with_incorrect_duration_range():
    with patch("utilities.get_ts_ag_request") as mock_get_ts_aq_request, patch(
        "utilities.get_unique_values_for_metadata"
    ) as mock_get_unique_values_for_metadata:

        mock_get_ts_aq_request.return_value = None
        mock_get_unique_values_for_metadata.return_value = ["PT1M", "PT10M", "PT1H"]

        response = client.get("/collections/observations/locations/0-20000-0-06260?durations=PT1H/PT10M")

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid ISO 8601 range: PT1H > PT10M"}


def test_get_data_with_a_duration_not_found_in_datastore():
    with patch("utilities.get_ts_ag_request") as mock_get_ts_aq_request, patch(
        "utilities.get_unique_values_for_metadata"
    ) as mock_get_unique_values_for_metadata:

        mock_get_ts_aq_request.return_value = None
        mock_get_unique_values_for_metadata.return_value = ["PT1M", "PT10M", "PT1H"]

        response = client.get("/collections/observations/locations/0-20000-0-06260?durations=XXXX/PT1M")

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid ISO 8601 duration: XXXX"}


def test_get_data_with_invalid_levels_value():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:

        # Load with random test data for making a mock_obs_request
        test_data = load_json("test/test_data/test_coverages_proto.json")
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get("/collections/observations/locations/0-20000-0-06260?levels=Z/10")

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid levels value: Z/10"}


def test_get_data_with_invalid_levels_repeating_interval():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:

        # Load with random test data for making a mock_obs_request
        test_data = load_json("test/test_data/test_coverages_proto.json")
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get("/collections/observations/locations/0-20000-0-06260?levels=R10/20/100/10")

        assert response.status_code == 400
        assert response.json() == {"detail": "Invalid levels repeating-interval: R10/20/100/10"}


def test_get_data_with_lowercase_duration_range_without_existing_data():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:

        test_data = load_json("test/test_data/test_empty_proto.json")

        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get("/collections/observations/position?coords=POINT(5.179705 52.0988218)&durations=p1m/P1Y")

        assert response.status_code == 404
        assert response.json() == {"detail": "Requested data not found."}


def test_get_data_with_combination_levels_filtering():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:

        # Load with random test data for making a mock_obs_request
        test_data = load_json("test/test_data/test_coverages_proto.json")
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get("/collections/observations/locations/0-20000-0-06260?levels=R6/0.0/0.1, 1.5/1.8, 10")

        m_args = mock_get_obs_request.call_args[0][0]

        assert response.status_code == 200
        assert m_args.filter["level"].values == ["0", "10", "20", "30", "40", "50", "150/180", "1000"]


def test_get_data_with_combination_durations_filtering():
    with patch("routers.edr.get_obs_request") as mock_get_obs_request:

        # Load with random test data for making a mock_obs_request
        test_data = load_json("test/test_data/test_coverages_proto.json")
        mock_get_obs_request.return_value = create_mock_obs_response(test_data)

        response = client.get("/collections/observations/locations/0-20000-0-06260?durations=PT0S, PT1M/PT10M")

        m_args = mock_get_obs_request.call_args[0][0]

        assert response.status_code == 200
        assert m_args.filter["period"].values == ["0", "60/600"]
