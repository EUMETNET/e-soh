import os
import json

from functools import cache


@cache
def get_openapi_metadata():
    with open(os.environ["OPENAPI_METADATA_PATH"], "r") as f:
        openapi_metadata = json.load(f)
    return openapi_metadata


if "OPENAPI_METADATA_PATH" in os.environ:
    openapi_metadata = get_openapi_metadata()
else:
    openapi_metadata = {
        "title": "EDR Observations API Europe EUMETNET",
        "description": (
            "OGC EDR API data service for European meteorological observations from EUMETNET,"
            " co-funded by the European Union."
        ),
        "contact": {
            "name": "EUMETNET",
            "url": "https://www.eumetnet.eu/about-us/",
            "email": "eucos@metoffice.gov.uk",
        },
        "license_info": {
            "name": "CC-BY-4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/",
        },
    }
