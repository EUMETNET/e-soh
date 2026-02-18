FROM --platform=linux/amd64 python:3.11-slim-bookworm

SHELL ["/bin/bash", "-eux", "-o", "pipefail", "-c"]

ENV DOCKER_PATH="/app"

# hadolint ignore=DL3008
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends git libeccodes-data libudunits2-0\
  # Cleanup
  && rm -rf /usr/tmp  \
  && apt-get autoremove -y \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*
COPY "./protobuf/datastore.proto" "/protobuf/datastore.proto"
COPY "./api" "${DOCKER_PATH}/api/"
COPY "requirements.txt" "${DOCKER_PATH}/api/"
COPY "./src/" "${DOCKER_PATH}/src/"

RUN pip install --no-cache-dir --upgrade -r "${DOCKER_PATH}/api/requirements.txt"

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
  && mkdir -p /tmp/metrics

ENV PROMETHEUS_MULTIPROC_DIR=/tmp/metrics

CMD ["gunicorn", "api.main:app", "--worker-class=uvicorn.workers.UvicornWorker"]
