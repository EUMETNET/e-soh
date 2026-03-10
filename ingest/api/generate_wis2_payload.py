import os
import json


from api.model import Link
from api.wis2_model import Wis2MessageSchema
from api.wis2_model import PropertiesWIS2
from api.wis2_model import Content
from api.global_variables import WIS2_TOPIC
from api.global_variables import WIS2_DATA_ID
from api.global_variables import WIS2_METADATA_RECORD_ID


def get_api_timeseries_query(location_id: str, baseURL: str, paramaters: dict[str, str] = {}) -> str:
    query = "/collections/observations/locations/" + location_id
    if paramaters:
        query = query + "?" + "&".join([f"{i}={j}" for i, j in paramaters.items() if j])
    baseURL = os.getenv("EDR_API_URL", baseURL)
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
    json_payload = json.dumps(
        {
            "type": "Feature",
            "geometry": message["geometry"],
            "properties": {
                "observation": message["properties"]["content"]["value"],
                "CF_standard_name": message["properties"]["content"]["standard_name"],
                "unit": message["properties"]["content"]["unit"],
            },
        },
        separators=(",", ":"),
    )
    json_payload = json_payload.encode("utf-8")
    json_payload_bytes_size = len(json_payload)

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
            data_id=WIS2_DATA_ID or message["properties"]["data_id"],
            metadata_id=WIS2_METADATA_RECORD_ID,  # Need to figure out how we generate this? Is it staic or dynamic?
            datetime=message["properties"]["datetime"],
            pubtime=message["properties"]["pubtime"],
            content=Content(
                value=json_payload,
                unit=message["properties"]["content"]["unit"],
                encoding="utf-8",
                size=json_payload_bytes_size,
            ),
        ),
        links=(
            [
                Link(
                    href=get_api_timeseries_query(
                        message["properties"]["platform"],
                        request_url,
                        paramaters={
                            "standard_name": message["properties"]["content"].get("standard_name", ""),
                            "datetime": message["properties"].get("datetime", ""),
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
