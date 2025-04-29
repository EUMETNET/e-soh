import logging
from datetime import datetime
from datetime import timezone
from typing import Dict

from edr_pydantic.capabilities import ConformanceModel
from edr_pydantic.capabilities import Contact
from edr_pydantic.capabilities import LandingPageModel
from edr_pydantic.capabilities import Provider
from edr_pydantic.collections import Collection
from edr_pydantic.collections import Collections
from edr_pydantic.data_queries import DataQueries
from edr_pydantic.data_queries import EDRQuery
from edr_pydantic.extent import Custom
from edr_pydantic.extent import Extent
from edr_pydantic.extent import Spatial
from edr_pydantic.extent import Temporal
from edr_pydantic.link import EDRQueryLink
from edr_pydantic.link import Link
from edr_pydantic.observed_property import ObservedProperty
from edr_pydantic.parameter import MeasurementType
from edr_pydantic.parameter import Parameter
from edr_pydantic.unit import Unit
from edr_pydantic.variables import Variables
from grpc_getter import get_extents_request
from grpc_getter import get_ts_ag_request

import datastore_pb2 as dstore
from utilities import get_unique_values_for_metadata
from utilities import seconds_to_iso_8601_duration
from utilities import convert_cm_to_m

from openapi.openapi_metadata import openapi_metadata


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def datetime_to_iso_string(value: datetime) -> str:
    """Returns the datetime as ISO 8601 string.
    Changes timezone +00:00 to the military time zone indicator (Z).

    Keyword arguments:
    value -- A datetime

    Returns:
    datetime string -- Returns the datetime as an ISO 8601 string with the military indicator.
    """
    if value.tzinfo is None:
        # This sort of replicates the functionality of Pydantic's AwareDatetime type
        raise ValueError("Datetime object is not timezone aware")

    iso_8601_str = value.isoformat()
    tz_offset_utc = "+00:00"
    if iso_8601_str.endswith(tz_offset_utc):
        return f"{iso_8601_str[:-len(tz_offset_utc)]}Z"
    else:
        return iso_8601_str


def get_landing_page(request):
    return LandingPageModel(
        title=openapi_metadata["title"],
        description=openapi_metadata["description"],
        keywords=[
            "weather",
            "temperature",
            "wind",
            "humidity",
            "pressure",
            "clouds",
            "radiation",
        ],
        provider=Provider(
            name=openapi_metadata["contact"]["name"],
            url=openapi_metadata["contact"]["url"],
        ),
        contact=Contact(email=openapi_metadata["contact"]["email"]),
        links=[
            Link(
                href=f"{request.url}",
                rel="self",
                title="Landing Page in JSON",
                type="application/json",
            ),
            Link(
                href=f"{request.url}docs",
                rel="service-doc",
                title="API description in HTML",
                type="text/html",
            ),
            Link(
                href=f"{request.url}openapi.json",
                rel="service-desc",
                title="API description in JSON",
                type="application/json",
            ),
            Link(
                href=f"{request.url}conformance",
                rel="conformance",
                title="Conformance Declaration in JSON",
                type="application/json",
            ),
            Link(
                href=f"{request.url}collections",
                rel="data",
                title="Collections metadata in JSON",
            ),
        ],
    )


def get_conformance() -> ConformanceModel:
    return ConformanceModel(
        conformsTo=[
            "https://www.opengis.net/spec/ogcapi-edr-1/1.1/conf/core",  # B2 - required
            "https://www.opengis.net/spec/ogcapi-edr-1/1.1/conf/collections",  # B3 - required
            "https://www.opengis.net/spec/ogcapi-edr-1/1.1/conf/json",  # B4
            "https://www.opengis.net/spec/ogcapi-edr-1/1.1/conf/edr-geojson",  # B5
            "https://www.opengis.net/spec/ogcapi-edr-1/1.1/conf/covjson",  # B7
            # TODO: Add when there is a conformance class for Open Api Spec 3.1
            # "https://www.opengis.net/spec/ogcapi-edr-1/1.1/conf/oas31",  # B9
            "https://www.opengis.net/spec/ogcapi-edr-1/1.1/conf/queries",  # B10
        ]
    )


async def get_collection_metadata(base_url: str, is_self) -> Collection:
    ts_request = dstore.GetTSAGRequest(attrs=["parameter_name", "standard_name", "unit", "level", "period", "function"])
    ts_response = await get_ts_ag_request(ts_request)
    # logger.info(ts_response.ByteSize())
    # logger.info(len(ts_response.groups))

    # Sadly, this is a different parameter as in the /locations endpoint, due to an error in the EDR spec
    # See: https://github.com/opengeospatial/ogcapi-environmental-data-retrieval/issues/427
    all_parameters: Dict[str, Parameter] = {}

    for group in ts_response.groups:
        ts = group.combo
        level = convert_cm_to_m(ts.level)
        period = seconds_to_iso_8601_duration(ts.period)
        label = " ".join(ts.standard_name.capitalize().split("_"))

        custom_fields = {
            "rodeo:standard_name": ts.standard_name,
            "rodeo:level": level,
        }

        parameter = Parameter(
            description=f"{label} at {level}m, aggregated over {period} with method '{ts.function}'",
            observedProperty=ObservedProperty(
                id=f"https://vocab.nerc.ac.uk/standard_name/{ts.standard_name}",
                label=label,
            ),
            measurementType=MeasurementType(
                method=ts.function,
                duration=period,
            ),
            unit=Unit(label=ts.unit),
            **custom_fields,
        )
        # There might be parameter inconsistencies (e.g one station is reporting in Pa, and another in hPa)
        # We always return the "last" parameter definition found (in /locations and collection metadata).
        # Note that the correct UoM is always returned in the Coverage parameters for the data endpoints.

        all_parameters[ts.parameter_name] = parameter

    extent_request = dstore.GetExtentsRequest()
    extent_response = await get_extents_request(extent_request)
    spatial_extent = extent_response.spatial_extent
    interval_start = extent_response.temporal_extent.start.ToDatetime(tzinfo=timezone.utc)
    interval_end = extent_response.temporal_extent.end.ToDatetime(tzinfo=timezone.utc)

    # TODO: Check if these make /collections significantly slower. If yes, do we need DB indices on these? And parallel
    levels = [convert_cm_to_m(level) for level in await get_unique_values_for_metadata("level")]
    standard_names = await get_unique_values_for_metadata("standard_name")
    methods = await get_unique_values_for_metadata("function")
    durations = [seconds_to_iso_8601_duration(period) for period in await get_unique_values_for_metadata("period")]

    collection = Collection(
        id="observations",
        links=[
            Link(href=f"{base_url}/observations", rel="self" if is_self else "data"),
        ],
        extent=Extent(
            spatial=Spatial(
                bbox=[
                    [
                        spatial_extent.left,
                        spatial_extent.bottom,
                        spatial_extent.right,
                        spatial_extent.top,
                    ]
                ],
                crs="EPSG:4326",
            ),
            temporal=Temporal(
                interval=[[interval_start, interval_end]],
                values=[f"{datetime_to_iso_string(interval_start)}/{datetime_to_iso_string(interval_end)}"],
                trs="datetime",
            ),
            custom=[
                Custom(
                    id="standard_names",
                    interval=[[standard_names[0], standard_names[-1]]],
                    values=standard_names,
                    reference="https://vocab.nerc.ac.uk/standard_name/",
                ),
                Custom(
                    id="levels",
                    interval=[[levels[0], levels[-1]]],
                    values=levels,
                    reference="Height of measurement above ground level in meters",
                ),
                Custom(
                    id="methods",
                    interval=[[methods[0], methods[-1]]],
                    values=methods,
                    reference="Time aggregation functions",
                ),
                Custom(
                    id="durations",
                    interval=[[durations[0], durations[-1]]],
                    values=durations,
                    reference="https://en.wikipedia.org/wiki/ISO_8601#Durations",
                ),
            ],
        ),
        data_queries=DataQueries(
            position=EDRQuery(
                link=EDRQueryLink(
                    href=f"{base_url}/observations/position",
                    rel="data",
                    variables=Variables(query_type="position", output_format=["CoverageJSON"]),
                )
            ),
            locations=EDRQuery(
                link=EDRQueryLink(
                    href=f"{base_url}/observations/locations",
                    rel="data",
                    variables=Variables(query_type="locations", output_format=["CoverageJSON"]),
                )
            ),
            area=EDRQuery(
                link=EDRQueryLink(
                    href=f"{base_url}/observations/area",
                    rel="data",
                    variables=Variables(query_type="area", output_format=["CoverageJSON"]),
                )
            ),
        ),
        crs=["WGS84"],
        output_formats=["CoverageJSON"],
        parameter_names={parameter_id: all_parameters[parameter_id] for parameter_id in sorted(all_parameters)},
    )
    return collection


async def get_collections(base_url: str) -> Collections:
    return Collections(
        links=[
            Link(href=f"{base_url}", rel="self"),
        ],
        collections=[await get_collection_metadata(base_url, is_self=False)],
    )
