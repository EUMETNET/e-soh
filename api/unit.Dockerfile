FROM python:3.11-slim-bookworm

SHELL ["/bin/bash", "-eux", "-o", "pipefail", "-c"]

ENV DOCKER_PATH="/app"

RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get install -y --no-install-recommends git \
    # Cleanup
    && rm -rf /usr/tmp  \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY "./protobuf/datastore.proto" "/protobuf/datastore.proto"
COPY "./dev_requirements.txt" "${DOCKER_PATH}/dev_requirements.txt"

# hadolint ignore=DL3013
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --upgrade  \
    -r "${DOCKER_PATH}/dev_requirements.txt"

# Compiling the protobuf file
RUN python -m grpc_tools.protoc  \
    --proto_path="protobuf" "protobuf/datastore.proto" \
    --python_out="${DOCKER_PATH}"  \
    --grpc_python_out="${DOCKER_PATH}"

COPY "." "${DOCKER_PATH}/"

# Create folder for metrics
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/metrics
RUN mkdir -p /tmp/metrics

WORKDIR "${DOCKER_PATH}"
RUN python "generate_qudt_units.py"
CMD ["/bin/sh", "-c", "{ python -m pytest \
    --timeout=60 \
    --junitxml=./output/pytest.xml \
    --cov-report=term-missing \
    --cov=. \
    --cov-config=./test/.coveragerc 2>&1; \
    echo $? > ./output/exit-code; } | \
    tee ./output/pytest-coverage.txt; \
    exit $(cat ./output/exit-code)"]
