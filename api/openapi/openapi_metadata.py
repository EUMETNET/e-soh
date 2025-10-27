import os
import json

with open(
    os.getenv("OPENAPI_METADATA_PATH", "/app/openapi_default_files/openapi_metadata.json"),
    "r",
) as file:
    openapi_metadata = json.load(file)
    print(openapi_metadata)
