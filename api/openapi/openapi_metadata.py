import os
import json

with open(
    os.getenv("OPENAPI_METADATA_PATH", "/app/openapi_default_files/openapi_metadata.json"),
    "r",
) as file:
    openapi_metadata = json.load(file)
    valid_keys = [
        "title",
        "version",
        "summary",
        "description",
        "terms_of_service",
        "contact",
        "license_info",
        "openapi_tags",
    ]
    unwanted = set(openapi_metadata) - set(valid_keys)
    for unwanted_key in unwanted:
        del openapi_metadata[unwanted_key]
