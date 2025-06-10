# list recipes
default:
    @just --list

set positional-arguments

# Run all docker services. After running the database needs cleanup, run just destroy
all: lint build unit ingest-unit services monitoring load integration performance client

# Build and run the default docker services
up: build services
# Build and run the default docker services and start up monitoring
local: up monitoring
# Build and run the unit, load and integration tests
test: build unit ingest-load integration

# Build and run the ingest loader and integration tests
ingest-test: build ingest-unit ingest-load integration

# ---------------------------------------------------------------------------- #
#                                  utility                                     #
# ---------------------------------------------------------------------------- #
# Copy the protofile to the Docker directories
copy-proto:
    #!/usr/bin/env bash
    set -euxo pipefail

    declare -a destination_paths=(
        "./api"
        "./datastore/data-loader"
        "./datastore/datastore"
        "./datastore/examples/clients/python"
        "./datastore/integration-test"
        "./datastore/load-test"
        "./ingest"
    )

    for path in "${destination_paths[@]}"
    do
        cp -v -r "./protobuf" "$path"
    done

copy-units:
    #!/usr/bin/env bash
    set -euxo pipefail

    declare -a destination_paths=(
        "./api"
        "./ingest/api"
    )

    for path in "${destination_paths[@]}"
    do
        cp -v -r "./units_config/std_name_units.json" "$path"
    done


# Check if the python version is 3.11 for reproducability
_check-python-version:
    #!/usr/bin/env bash
    set -euxo pipefail

    # Get Python version
    if command -v python &>/dev/null; then
        python_version=$(python --version 2>&1 | cut -d ' ' -f2)
    elif command -v python3 &>/dev/null; then
        python_version=$(python3 --version 2>&1 | cut -d ' ' -f2)
    else
        echo "Python not found. Failing..."
        exit 1
    fi

    # Extract major and minor version numbers
    major_version=$(echo "$python_version" | cut -d '.' -f1)
    minor_version=$(echo "$python_version" | cut -d '.' -f2)

    # Check if Python version is greater than or equal to 3.11
    if [[ "$major_version" -lt 3 || ( "$major_version" -eq 3 && "$minor_version" -lt 11 ) ]]; then
        echo "Error: Python version must be greater than or equal to 3.11"
        exit 1
    fi


# Run pip-compile for all the requirement files
pip-compile: _check-python-version
    #!/usr/bin/env bash
    set -euxo pipefail

    find . \
        -iname "*requirements.in" \
        -type f \
        -print \
        -execdir \
        pip-compile --upgrade --no-emit-index-url \
        {} ';'


# ---------------------------------------------------------------------------- #
#                                    test                                      #
# ---------------------------------------------------------------------------- #
# Run the pre-commit hook
lint: _check-python-version
    #!/usr/bin/env bash
    set -euxo pipefail

    if ! command -v pre-commit &> /dev/null; then
        python -m pip install pre-commit
    fi

    pre-commit run --config './.pre-commit-config.yaml' --all-files --color=always --show-diff-on-failure


# Run the integration tests
integration:
    docker compose --env-file ./ci/config/env.list run --rm integration


# Run the unit tests
unit:
    docker compose run --rm api-unit

ingest-unit:
    docker compose run --rm ingest-unit

# Start the monitoring
monitoring:
    docker compose up prometheus prometheus-postgres-exporter grafana -d


# Run the performance tests
performance:
    docker compose --env-file ./ci/config/env.list run --rm performance


# Run the client test; after running client the database needs cleanup, run just destroy.
client:
    docker compose --env-file ./ci/config/env.list run --rm client


# ---------------------------------------------------------------------------- #
#                                    build                                     #
# ---------------------------------------------------------------------------- #
# Build the docker images
build: copy-proto copy-units
    docker compose --env-file ./ci/config/env.list --profile monitoring --profile test build


# # ---------------------------------------------------------------------------- #
# #                                     local                                    #
# # ---------------------------------------------------------------------------- #
# Start the default docker compose containers
services:
    # HACK: The loading of pg_stat_statements plugin leads to a restart of the DB container.
    #   This makes the health test immediately fail. The trick below is a workaround for this.
    docker compose --env-file ./ci/config/env.list up -d --wait --wait-timeout 120 || true
    sleep 5
    docker compose --env-file ./ci/config/env.list up -d --wait --wait-timeout 120


# Load the data in the database
load:
    docker compose --env-file ./ci/config/env.list run --rm loader

ingest-load:
    docker compose --env-file ./ci/config/env.list run --rm ingest-loader

# Stop all E-SOH containers
down:
    docker compose --profile monitoring --profile test down


# Stop all E-SOH containers and remove their volumes
destroy:
    docker compose --profile monitoring --profile test down --volumes

# Run the rodeo profile test
profile-test:
    docker compose --env-file ./ci/config/env.list run --rm rodeo-profile-test
