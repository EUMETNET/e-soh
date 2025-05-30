# e-soh-event-queue

## Enviornment variables

| Variable                   | Default Value              | Description                                                                 |
|----------------------------|----------------------------|-----------------------------------------------------------------------------|
| `DSHOST`                   | `store`                    | Host address for the data store. Defaults to `store` if not set.            |
| `DSPORT`                   | `50050`                    | Port for the data store connection. Defaults to `50050` if not set.         |
| `MQTT_HOST`                |                            | Host address for the MQTT broker.                                           |
| `MQTT_USERNAME`            |                            | Username for authentication with the MQTT broker.                           |
| `MQTT_PASSWORD`            |                            | Password for authentication with the MQTT broker.                           |
| `MQTT_TLS`                 | `True`                     | Whether to use TLS (True/False) for the MQTT connection. Defaults to `True`.|
| `WIS2_MQTT_HOST`                |                            | Host address for the MQTT broker.                                           |
| `WIS2_MQTT_USERNAME`            |                            | Username for authentication with the MQTT broker.                           |
| `WIS2_MQTT_PASSWORD`            |                            | Password for authentication with the MQTT broker.                           |
| `WIS2_MQTT_TLS`                 | `True`                     | Whether to use TLS (True/False) for the MQTT connection. Defaults to `True`.|
| `WIS2_METADATA_RECORD_ID`                 |    | The ID of the WIS2 global metadata ID for this data service.|
| `WIS2_TOPIC`  | | The WIS2 MQTT topic the messages should be published under. |
| `EDR_API_URL`                 |                     | If the EDR API is hosted on a different URL then the ingest API, set this to the correct URL for the EDR API.|
| `PROMETHEUS_MULTIPROC_DIR` | `/tmp/metrics`             | Directory for Prometheus multiprocess mode metrics. Defaults to `/tmp/metrics`. |
| `INGEST_LOGLEVEL`          |                            | Logging level for the ingestion process.                                     |
| `GUNICORN_CMD_ARGS`        |                            | Command-line arguments for configuring Gunicorn, a Python WSGI HTTP Server.  |
| `FASTAPI_ROOT_PATH`        |                            | If this api is behind proxy, this need to be set to the root path |

## Dev install

To install in dev mode run `pip install --editable .` from the top level of this repository.

## C++ dependencies

| Module          | Version |
| --------------- | ------- |
| libeccodes-data | 2.24.2  |
| rapidjson-dev   | 1.1.0   |
| pybind11-dev    | 2.9.1   |


## Prerequisites of running locally
Move the `std_unit_names.json`to the ingest/api folder with
```bash
just copy-units
```
