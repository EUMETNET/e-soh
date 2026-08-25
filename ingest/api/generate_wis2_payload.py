import os

from dateutil.parser import parse
from datetime import datetime
from datetime import timezone


from api.model import Link
from api.wis2_model import Wis2MessageSchema
from api.wis2_model import PropertiesWIS2
from api.wis2_model import Content
from api.global_variables import WIS2_TOPIC
from api.global_variables import WIS2_METADATA_RECORD_ID


def get_api_timeseries_query(location_id: str, baseURL: str, parameters: dict[str, str] = {}) -> str:
    query = "/collections/observations/locations/" + location_id
    if parameters:
        query = query + "?" + "&".join([f"{i}={j}" for i, j in parameters.items() if j])
    baseURL = os.getenv("EDR_API_URL", baseURL).strip("/")
    return baseURL + query


def generate_wis2_topic() -> str:
    """This function will generate the WIS2 complient toipc name"""
    if not WIS2_TOPIC:
        raise ValueError("WIS2_TOPIC env variable not set. Aborting publish to wis2")
    return WIS2_TOPIC


def generate_wis2_payload(message: dict, request_url: str) -> Wis2MessageSchema:
    """
    This function will generate the WIS2 complient payload based on the JSON schema for ESOH
    """
    standard_name = message["properties"]["content"].get("standard_name", "")
    value = message["properties"]["content"]["value"]
    value_size = len(value)
    date_str = message["properties"]["datetime"].replace("+00:00", "Z").replace("-", "").replace(":", "")
    data_id = (
        WIS2_TOPIC.removeprefix("origin/a/")
        + "/"
        + message["properties"]["platform"]
        + "_"
        + date_str
        + "_"
        + standard_name
    )

    wis2_payload = Wis2MessageSchema(
        type="Feature",
        id=message["id"],
        conformsTo=["http://wis.wmo.int/spec/wnm/1/conf/core"],
        geometry={
            "type": "Point",
            "coordinates": [
                message["geometry"]["coordinates"]["lon"],
                message["geometry"]["coordinates"]["lat"],
            ],
        },
        properties=PropertiesWIS2(
            producer=message["properties"]["naming_authority"],
            data_id=data_id or message["properties"]["data_id"],
            metadata_id=WIS2_METADATA_RECORD_ID,  # Need to figure out how we generate this? Is it staic or dynamic?
            datetime=message["properties"]["datetime"],
            pubtime=message["properties"]["pubtime"],
            standard_name=standard_name,
            hamsl=message["properties"]["hamsl"],
            function=message["properties"]["function"],
            period=message["properties"]["period"],
            content=Content(
                value=value,
                unit=message["properties"]["content"]["unit"],
                encoding="utf-8",
                size=value_size,
            ),
        ),
        links=(
            [
                Link(
                    href=get_api_timeseries_query(
                        message["properties"]["platform"],
                        request_url,
                        parameters={
                            "standard_name": standard_name,
                            "datetime": (
                                lambda dt: (
                                    dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                                    if isinstance(dt, datetime)
                                    else (
                                        parse(dt)
                                        .astimezone(timezone.utc)
                                        .isoformat(timespec="seconds")
                                        .replace("+00:00", "Z")
                                        if dt
                                        else ""
                                    )
                                )
                            )(message["properties"].get("datetime", "")),
                            "level": message["properties"].get("level", ""),
                            "method": message["properties"].get("method", ""),
                            "duration": message["properties"].get("duration", ""),
                        },
                    ),
                    rel="canonical",
                    type="application/prs.coverage+json",
                )
            ]
        )
        + (lambda x: x if x else [])(message["links"]),
    )

    return wis2_payload
