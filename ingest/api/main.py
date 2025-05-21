import logging
import os

from fastapi import FastAPI
from fastapi import UploadFile
from fastapi import Request
from pydantic import BaseModel

from typing import List
from api.ingest import IngestToPipeline
from api.model import JsonMessageSchema
from api.messages import build_json_payload
from api.api_metrics import add_metrics

log_level = os.environ.get("INGEST_LOGLEVEL", "INFO")

formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setLevel(log_level)
stream_handler.setFormatter(formatter)

# Set logging level and handlers
logging.basicConfig(level=log_level, handlers=[stream_handler])
logger = logging.getLogger(__name__)


class Response(BaseModel):
    status_message: str
    status_code: int


# Define configuration parameters
mqtt_configuration = {
    "host": os.getenv("MQTT_HOST"),
    "username": os.getenv("MQTT_USERNAME"),
    "password": os.getenv("MQTT_PASSWORD"),
    "enable_tls": os.getenv("MQTT_TLS", "False").lower() in ("true", "1", "t"),
    "port": int(os.getenv("MQTT_PORT", 8883)),
}

mqtt_wis2_configuration = {
    "host": os.getenv("WIS2_MQTT_HOST", None),
    "username": os.getenv("WIS2_MQTT_USERNAME", None),
    "password": os.getenv("WIS2_MQTT_PASSWORD", None),
    "enable_tls": os.getenv("WIS2_MQTT_TLS", "False").lower() in ("true", "1", "t"),
    "port": int(os.getenv("WIS2_MQTT_PORT", 8883)),
}

if not all(
    [
        mqtt_wis2_configuration["host"],
    ]
):
    mqtt_wis2_configuration = None

ingester = IngestToPipeline(
    mqtt_conf=mqtt_configuration,
    uuid_prefix="uuid",
    mqtt_WIS2_conf=mqtt_wis2_configuration,
)

app = FastAPI(root_path=os.getenv("FASTAPI_ROOT_PATH", ""))
add_metrics(app)


@app.post("/bufr")
async def upload_bufr_file(http_request: Request, files: UploadFile, publishWIS2: bool = False):
    contents = await files.read()
    json_data = build_json_payload(contents)
    await post_json(http_request, json_data, publishWIS2)

    return Response(status_message="Successfully ingested", status_code=200)


@app.post("/json")
async def post_json(
    http_request: Request,
    request: JsonMessageSchema | List[JsonMessageSchema],
    publishWIS2: bool = False,
) -> Response:
    status = "Successfully ingested"
    if isinstance(request, list):
        hash_list = [i.__hash__() for i in request]
        unique_request = [request[hash_list.index(i)] for i in set(hash_list)]
        if len(unique_request) != len(request):
            status = "Insert accepted, duplicates removed."

        json_data = [item.model_dump(exclude_none=True) for item in unique_request]
    else:
        json_data = [request.model_dump(exclude_none=True)]

    await ingester.ingest(json_data, publishWIS2, str(http_request.base_url))

    return Response(status_message=status, status_code=200)
