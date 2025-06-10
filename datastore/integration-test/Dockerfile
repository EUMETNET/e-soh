FROM python:3.11-slim-bookworm

SHELL ["/bin/bash", "-eux", "-o", "pipefail", "-c"]

ENV DOCKER_PATH="/clients/python"

RUN apt-get update \
    && apt-get -y upgrade \
    # Cleanup
    && rm -rf /usr/tmp  \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY "./protobuf/datastore.proto" "/protobuf/datastore.proto"
COPY "./requirements.txt" "${DOCKER_PATH}/requirements.txt"

# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --upgrade -r "${DOCKER_PATH}/requirements.txt"

# Compiling the protobuf file
RUN python -m grpc_tools.protoc  \
    --proto_path="protobuf" "protobuf/datastore.proto" \
    --python_out="${DOCKER_PATH}"  \
    --grpc_python_out="${DOCKER_PATH}"

COPY "./test_knmi.py" "${DOCKER_PATH}/test_knmi.py"
COPY "./test_delete.py" "${DOCKER_PATH}/test_delete.py"
COPY "./test_api.py" "${DOCKER_PATH}/test_api.py"

COPY "./response/" "${DOCKER_PATH}/response/"

WORKDIR "${DOCKER_PATH}"
CMD ["/bin/sh", "-c", "python -m pytest"]
