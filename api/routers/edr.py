# For developing:    uvicorn main:app --reload
from typing import Annotated
from typing import Dict
from typing import Set

import datastore_pb2 as dstore
import formatters
from openapi import custom_dimension_examples
from openapi import openapi_examples
from openapi import edr_query_parameter_descriptions
from covjson_pydantic.coverage import Coverage
from covjson_pydantic.coverage import CoverageCollection
from covjson_pydantic.parameter import Parameter
from custom_geo_json.edr_feature_collection import EDRFeatureCollection
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from formatters.covjson import make_parameter
from geojson_pydantic import Feature
from geojson_pydantic import Point
from grpc_getter import get_obs_request
from grpc_getter import get_locations_request
from grpc_getter import get_ts_ag_request
from response_classes import CoverageJsonResponse
from response_classes import GeoJsonResponse
from shapely import geometry
from shapely import wkt
from shapely.errors import GEOSException
from utilities import add_request_parameters
from utilities import validate_bbox

router = APIRouter(prefix="/collections/observations")

response_fields_needed_for_data_api = [
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


@router.get(
    "/locations",
    tags=["Collection data queries"],
    response_model=EDRFeatureCollection,
    response_model_exclude_none=True,
    response_class=GeoJsonResponse,
)
# We can currently only query data, even if we only need metadata like for this endpoint
# Maybe it would be better to only query a limited set of data instead of everything (meaning 24 hours)
async def get_locations(
    bbox: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.bbox,
            openapi_examples=openapi_examples.bbox,
        ),
    ] = None,
    datetime: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.datetime,
            openapi_examples=openapi_examples.datetime,
        ),
    ] = None,
    parameter_name: Annotated[
        str | None,
        Query(
            alias="parameter-name",
            description=edr_query_parameter_descriptions.parameter_name,
            openapi_examples=openapi_examples.parameter_name,
        ),
    ] = None,
    standard_names: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.standard_names,
            openapi_examples=custom_dimension_examples.standard_names,
        ),
    ] = None,
    levels: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.levels,
            openapi_examples=custom_dimension_examples.levels,
        ),
    ] = None,
    methods: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.methods,
            openapi_examples=custom_dimension_examples.methods,
        ),
    ] = None,
    durations: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.durations,
            openapi_examples=custom_dimension_examples.durations,
        ),
    ] = None,
) -> EDRFeatureCollection:  # Hack to use string
    loc_request = dstore.GetLocsRequest()

    # Add spatial polygon to the time series request if bbox exists.
    if bbox:
        left, bottom, right, top = validate_bbox(bbox)
        poly = geometry.Polygon([(left, bottom), (right, bottom), (right, top), (left, top)])
        loc_request.spatial_polygon.points.extend(
            [dstore.Point(lat=coord[1], lon=coord[0]) for coord in poly.exterior.coords],
        )

    await add_request_parameters(loc_request, parameter_name, datetime, standard_names, levels, methods, durations)

    grpc_response = await get_locations_request(loc_request)
    locations = grpc_response.locations

    if len(locations) == 0:
        raise HTTPException(
            status_code=404,
            detail="Query did not return any locations.",
        )

    features = []
    uniq_parameters: Set[str] = set()
    for loc in locations:
        features.append(
            Feature(
                type="Feature",
                id=loc.platform,
                properties={
                    "name": loc.platform_name if loc.platform_name else f"platform-{loc.platform}",
                    "detail": f"https://oscar.wmo.int/surface/rest/api/search/station?wigosId={loc.platform}",
                    "parameter-name": list(loc.parameter_names),
                },
                geometry=Point(
                    type="Point",
                    coordinates=(loc.geo_point.lon, loc.geo_point.lat),
                ),
            )
        )
        uniq_parameters.update(loc.parameter_names)

    ts_request = dstore.GetTSAGRequest(attrs=["parameter_name", "standard_name", "unit", "level", "period", "function"])
    ts_response = await get_ts_ag_request(ts_request)

    all_parameters: Dict[str, Parameter] = {}
    for group in ts_response.groups:
        ts = group.combo
        all_parameters[ts.parameter_name] = make_parameter(ts)

    return_parameters = {parameter_name: all_parameters[parameter_name] for parameter_name in sorted(uniq_parameters)}
    return EDRFeatureCollection(features=features, type="FeatureCollection", parameters=return_parameters)


@router.get(
    "/locations/{location_id}",
    tags=["Collection data queries"],
    response_model=Coverage | CoverageCollection,
    response_model_exclude_none=True,
    response_class=CoverageJsonResponse,
)
async def get_data_location_id(
    location_id: Annotated[
        str, Path(description=edr_query_parameter_descriptions.wigos_id, openapi_examples=openapi_examples.wigos_id)
    ],
    parameter_name: Annotated[
        str | None,
        Query(
            alias="parameter-name",
            description=edr_query_parameter_descriptions.parameter_name,
            openapi_examples=openapi_examples.parameter_name,
        ),
    ] = None,
    datetime: Annotated[
        str | None,
        Query(description=edr_query_parameter_descriptions.datetime, openapi_examples=openapi_examples.datetime),
    ] = None,
    f: Annotated[
        formatters.Formats, Query(description=edr_query_parameter_descriptions.format)
    ] = formatters.Formats.covjson,
    standard_names: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.standard_names,
            openapi_examples=custom_dimension_examples.standard_names,
        ),
    ] = None,
    levels: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.levels,
            openapi_examples=custom_dimension_examples.levels,
        ),
    ] = None,
    methods: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.methods,
            openapi_examples=custom_dimension_examples.methods,
        ),
    ] = None,
    durations: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.durations,
            openapi_examples=custom_dimension_examples.durations,
        ),
    ] = None,
):
    request = dstore.GetObsRequest(
        filter=dict(
            platform=dstore.Strings(values=[location_id]),
        ),
        included_response_fields=response_fields_needed_for_data_api,
    )

    await add_request_parameters(request, parameter_name, datetime, standard_names, levels, methods, durations)

    grpc_response = await get_obs_request(request)
    observations = grpc_response.observations
    response = formatters.formatters[f](observations)

    return response


@router.get(
    "/position",
    tags=["Collection data queries"],
    response_model=Coverage | CoverageCollection,
    response_model_exclude_none=True,
    response_class=CoverageJsonResponse,
)
async def get_data_position(
    coords: Annotated[
        str, Query(description=edr_query_parameter_descriptions.point, openapi_examples=openapi_examples.point)
    ],
    parameter_name: Annotated[
        str | None,
        Query(
            alias="parameter-name",
            description=edr_query_parameter_descriptions.parameter_name,
            openapi_examples=openapi_examples.parameter_name,
        ),
    ] = None,
    datetime: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.datetime,
            openapi_examples=openapi_examples.datetime,
        ),
    ] = None,
    f: Annotated[
        formatters.Formats, Query(description=edr_query_parameter_descriptions.format)
    ] = formatters.Formats.covjson,
    standard_names: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.standard_names,
            openapi_examples=custom_dimension_examples.standard_names,
        ),
    ] = None,
    levels: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.levels,
            openapi_examples=custom_dimension_examples.levels,
        ),
    ] = None,
    methods: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.methods,
            openapi_examples=custom_dimension_examples.methods,
        ),
    ] = None,
    durations: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.durations,
            openapi_examples=custom_dimension_examples.durations,
        ),
    ] = None,
):
    try:
        point = wkt.loads(coords)
        if point.geom_type != "Point":
            raise TypeError
    except GEOSException:
        raise HTTPException(
            status_code=400,
            detail={"coords": f"Invalid or unparseable wkt provided: {coords}"},
        )
    except TypeError:
        raise HTTPException(
            status_code=400,
            detail={"coords": f"Invalid geometric type: {point.geom_type}"},
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"coords": f"Unexpected error occurred during wkt parsing: {coords}"},
        )

    request = dstore.GetObsRequest(
        # 10 meters around the point
        spatial_circle=dstore.Circle(center=dstore.Point(lat=point.y, lon=point.x), radius=0.01),
        included_response_fields=response_fields_needed_for_data_api,
    )

    await add_request_parameters(request, parameter_name, datetime, standard_names, levels, methods, durations)

    grpc_response = await get_obs_request(request)
    observations = grpc_response.observations
    response = formatters.formatters[f](observations)

    return response


@router.get(
    "/area",
    tags=["Collection data queries"],
    response_model=Coverage | CoverageCollection,
    response_model_exclude_none=True,
    response_class=CoverageJsonResponse,
)
async def get_data_area(
    coords: Annotated[
        str, Query(description=edr_query_parameter_descriptions.area, openapi_examples=openapi_examples.polygon)
    ],
    parameter_name: Annotated[
        str | None,
        Query(
            alias="parameter-name",
            description=edr_query_parameter_descriptions.parameter_name,
            openapi_examples=openapi_examples.parameter_name,
        ),
    ] = None,
    datetime: Annotated[
        str | None,
        Query(description=edr_query_parameter_descriptions.datetime, openapi_examples=openapi_examples.datetime),
    ] = None,
    f: Annotated[
        formatters.Formats, Query(description=edr_query_parameter_descriptions.format)
    ] = formatters.Formats.covjson,
    standard_names: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.standard_names,
            openapi_examples=custom_dimension_examples.standard_names,
        ),
    ] = None,
    levels: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.levels,
            openapi_examples=custom_dimension_examples.levels,
        ),
    ] = None,
    methods: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.methods,
            openapi_examples=custom_dimension_examples.methods,
        ),
    ] = None,
    durations: Annotated[
        str | None,
        Query(
            description=edr_query_parameter_descriptions.durations,
            openapi_examples=custom_dimension_examples.durations,
        ),
    ] = None,
):
    try:
        poly = wkt.loads(coords)
        if poly.geom_type != "Polygon":
            raise TypeError
    except GEOSException:
        raise HTTPException(
            status_code=400,
            detail={"coords": f"Invalid or unparseable wkt provided: {coords}"},
        )
    except TypeError:
        raise HTTPException(
            status_code=400,
            detail={"coords": f"Invalid geometric type: {poly.geom_type}"},
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"coords": f"Unexpected error occurred during wkt parsing: {coords}"},
        )

    request = dstore.GetObsRequest(
        spatial_polygon=dstore.Polygon(
            points=[dstore.Point(lat=coord[1], lon=coord[0]) for coord in poly.exterior.coords]
        ),
        included_response_fields=response_fields_needed_for_data_api,
    )

    await add_request_parameters(request, parameter_name, datetime, standard_names, levels, methods, durations)

    grpc_response = await get_obs_request(request)
    observations = grpc_response.observations
    response = formatters.formatters[f](observations)

    return response
