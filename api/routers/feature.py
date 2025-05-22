import json
from typing import Annotated

import datastore_pb2 as dstore
import formatters
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Request
from geojson_pydantic import Feature
from geojson_pydantic import FeatureCollection
from grpc_getter import get_extents_request
from grpc_getter import get_obs_request
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape
from openapi import openapi_examples
from response_classes import GeoJsonResponse
from shapely import geometry
from utilities import get_datetime_range
from utilities import split_and_strip

router = APIRouter(prefix="/collections/observations")

env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())


@router.get(
    "/items",
    tags=["Collection items"],
    response_model=Feature | FeatureCollection,
    response_model_exclude_none=True,
    response_class=GeoJsonResponse,
)
async def search_timeseries(
    request: Request,
    bbox: Annotated[
        str | None,
        Query(
            openapi_examples=openapi_examples.bbox,
        ),
    ] = None,
    datetime: Annotated[
        str | None,
        Query(
            openapi_examples=openapi_examples.datetime,
            description="E-SOH database only contains data from the last 24 hours",
        ),
    ] = None,
    id: Annotated[str | None, Query(description="E-SOH time series id")] = None,
    parameter_name: Annotated[str | None, Query(alias="parameter-name", description="E-SOH parameter name")] = None,
    naming_authority: Annotated[
        str | None,
        Query(
            alias="naming-authority",
            description="Naming authority that created the data",
            openapi_examples=openapi_examples.naming_authority,
        ),
    ] = None,
    institution: Annotated[
        str | None,
        Query(description="Institution that published the data", openapi_examples=openapi_examples.institution),
    ] = None,
    platform: Annotated[
        str | None,
        Query(description="Platform ID, WIGOS or WIGOS equivalent.", openapi_examples=openapi_examples.wigos_id),
    ] = None,
    standard_name: Annotated[
        str | None,
        Query(
            alias="standard-name", description="CF 1.9 standard name", openapi_examples=openapi_examples.standard_name
        ),
    ] = None,
    unit: Annotated[
        str | None,
        Query(description="Unit of observed physical property", openapi_examples=openapi_examples.unit),
    ] = None,
    instrument: Annotated[str | None, Query(description="Instrument Id")] = None,
    level: Annotated[
        str | None,
        Query(
            description="Instruments height above ground or distance below surface, in meters",
            openapi_examples=openapi_examples.level,
        ),
    ] = None,
    period: Annotated[
        str | None,
        Query(description="Duration of collection period in ISO8601", openapi_examples=openapi_examples.period),
    ] = None,
    method: Annotated[
        str | None,
        Query(
            description="Aggregation method used to sample observed property", openapi_examples=openapi_examples.method
        ),
    ] = None,
    f: Annotated[
        formatters.Metadata_Formats, Query(description="Specify return format")
    ] = formatters.Metadata_Formats.geojson,
):
    if not bbox and not platform:
        raise HTTPException(400, detail="Have to set at least one of bbox or platform.")
    if bbox:
        left, bottom, right, top = map(str.strip, bbox.split(","))
        poly = geometry.Polygon([(left, bottom), (right, bottom), (right, top), (left, top)])
    if datetime:
        range = get_datetime_range(datetime)

    obs_request = dstore.GetObsRequest(
        filter=dict(
            timeseries_id=dstore.Strings(values=split_and_strip(id) if id else None),
            parameter_name=dstore.Strings(values=split_and_strip(parameter_name) if parameter_name else None),
            naming_authority=dstore.Strings(values=split_and_strip(naming_authority) if naming_authority else None),
            institution=dstore.Strings(values=split_and_strip(institution) if institution else None),
            platform=dstore.Strings(values=split_and_strip(platform) if platform else None),
            standard_name=dstore.Strings(values=split_and_strip(standard_name) if standard_name else None),
            unit=dstore.Strings(values=split_and_strip(unit) if unit else None),
            instrument=dstore.Strings(values=split_and_strip(instrument) if instrument else None),
            level=dstore.Strings(values=split_and_strip(level) if level else None),
            period=dstore.Strings(values=split_and_strip(period) if period else None),
            function=dstore.Strings(values=split_and_strip(method) if method else None),
        ),
        spatial_polygon=(
            dstore.Polygon(points=[dstore.Point(lat=coord[1], lon=coord[0]) for coord in poly.exterior.coords])
            if bbox
            else None
        ),
        temporal_interval=(dstore.TimeInterval(start=range[0], end=range[1]) if datetime else None),
        temporal_latest=True,
    )

    time_series = await get_obs_request(obs_request)

    return formatters.metadata_formatters[f](time_series.observations, str(request.base_url))


@router.get(
    "/items/{item_id}",
    tags=["Collection items"],
    response_model=Feature,
    response_model_exclude_none=True,
    response_class=GeoJsonResponse,
)
async def get_time_series_by_id(
    request: Request,
    item_id: Annotated[str, Path()],
    f: Annotated[
        formatters.Metadata_Formats, Query(description="Specify return format")
    ] = formatters.Metadata_Formats.geojson,
):
    obs_request = dstore.GetObsRequest(
        filter=dict(timeseries_id=dstore.Strings(values=[item_id])), temporal_latest=True
    )
    time_series = await get_obs_request(obs_request)

    return formatters.metadata_formatters[f](time_series.observations, str(request.base_url))


@router.get("/dataset", tags=["E-SOH dataset"], include_in_schema=False)
async def get_dataset_metadata(request: Request):
    base_url = str(request.base_url)

    # need to get spatial extent.
    spatial_request = dstore.GetExtentsRequest()
    extent = await get_extents_request(spatial_request)
    dynamic_fields = {
        "spatial_extents": [
            [
                [extent.spatial_extent.left, extent.spatial_extent.bottom],
                [extent.spatial_extent.right, extent.spatial_extent.bottom],
                [extent.spatial_extent.right, extent.spatial_extent.top],
                [extent.spatial_extent.left, extent.spatial_extent.top],
                [extent.spatial_extent.left, extent.spatial_extent.bottom],
            ]
        ],
        "temporal_extents": [
            [
                f"{extent.temporal_extent.start.ToDatetime().strftime('%Y-%m-%dT%H:%M:%SZ')}",
                f"{extent.temporal_extent.end.ToDatetime().strftime('%Y-%m-%dT%H:%M:%SZ')}",
            ],
        ],
        "url_base": base_url,
        "url_conformance": base_url + "conformance",
        "url_docs": base_url + "docs",
    }

    template = env.get_template("dataset_metadata_template.j2")
    dataset_metadata = template.render(dynamic_fields)
    return json.loads(dataset_metadata)
