FROM python:3.10-slim-bookworm

SHELL ["/bin/bash", "-eux", "-o", "pipefail", "-c"]

ENV DOCKER_PATH="/app"

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y --no-install-recommends git libeccodes-data rapidjson-dev pybind11-dev make g++ libudunits2-0\
    # Cleanup
    && rm -rf /usr/tmp  \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
COPY "./protobuf/datastore.proto" "/protobuf/datastore.proto"
COPY "./api" "${DOCKER_PATH}/api/"
COPY "requirements.txt" "${DOCKER_PATH}/api/"
COPY "./src/" "${DOCKER_PATH}/src/"
COPY "./pyproject.toml" "${DOCKER_PATH}/pyproject.toml"
COPY "./setup.py" "${DOCKER_PATH}/setup.py"

RUN pip install --no-cache-dir --upgrade -r "${DOCKER_PATH}/api/requirements.txt" \
    && pip install --no-cache-dir --upgrade pybind11~="2.11.1"

# hadolint ignore=DL3013
WORKDIR "${DOCKER_PATH}"/src/ingest/bufr/
RUN make
WORKDIR /

# Compiling the protobuf file
RUN python -m grpc_tools.protoc  \
    --proto_path="protobuf" "protobuf/datastore.proto" \
    --python_out="${DOCKER_PATH}"  \
    --grpc_python_out="${DOCKER_PATH}"

WORKDIR "${DOCKER_PATH}"

RUN python "api/generate_standard_name.py"

# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --upgrade "${DOCKER_PATH}/" \
    && mkdir -p /tmp/metrics

ENV PROMETHEUS_MULTIPROC_DIR=/tmp/metrics

CMD ["gunicorn", "api.main:app", "--worker-class=uvicorn.workers.UvicornWorker"]
