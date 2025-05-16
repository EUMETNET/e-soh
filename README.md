# E-SOH

## EURODEO

The RODEO project develops a user interface and Application Programming Interfaces (API) for accessing meteorological datasets declared as High Value Datasets (HVD) by the EU Implementing Regulation (EU) 2023/138 under the EU Open Data Directive (EU) 2019/1024. The project also fosters the engagement between data providers and data users for enhancing the understanding of technical solutions being available for sharing and accessing the HVD datasets.
This project provides a sustainable and standardized system for sharing real-time surface weather observations in line with the HVD regulation and WMO WIS 2.0 strategy. The real-time surface weather observations are made available through open web services, so that they can be accessed by anyone.

## Near real-time observational data

E-SOH is part of the RODEO project. The goal for this project is to make near real-time weather observations from land based station easily available. The data will be published on both a message queue using [MQTT](https://mqtt.org/) and [EDR](https://ogcapi.ogc.org/edr/) compliant APIs. Metadata will also be made available through [OGC Records](https://ogcapi.ogc.org/records/) APIs. The system architecture is portable, scalable and modular for taking into account possible future extensions to existing networks and datasets (e.g. 3rd party surface observations).

## Structure

The E-SOH service consist of three parts.

* Ingestion API
  * The ingest API handles incoming observation from partners. It will verify the incoming data and publish them to the MQTT queue and submit the observations to the datastore.
* Datastore
  * Datastore stores all observations for 24h and is the backend storage for EDR and Records APIs.
* EDR API
  * The EDR api is the main endpoint to download observational data available in E-SOH.
* Records API
  * The records api will serve all metadata for each timeseries available in E-SOH.

## Usage

All three parts of the service is kept in this repository and can be built and setup using docker-compose. For more documentation on each part of the service see README.md in each relevant folder in this repository.

To keep a small docker context and not have the extra maintenance of a .dockerignore, it is necessary when running locally to copy the protobuf file to the Dockerfile directories. You can do this by running: `just copy-proto`. Which copies the protobuf files to all specified Dockerfile directories. At the moment the ingestor is not included.

## Just run command

The Justfile is a simple way to define and run common tasks for a project. It’s similar to Makefiles, but simpler and more cross-platform.

### Install

Install by running:

```bash
ci/scripts/install-just.sh
```

### How does it work?

The Justfile is a simple text file that contains a list of tasks. Each task is a shell command. For example:

To run build and run the services locally without the monitoring:

```bash
just up test
```

To run build and run the services locally with the monitoring:

```bash
just local test
```

To run everything including client and do a cleanup of the database afterward:

```bash
just all destroy
```

## Pre-commit

### Setup

1. Go to the root of the repository.
2. Install the python pre-commit package with `pip install pre-commit`.
3. Reinitialize the repository with `git init`.
4. Install the hooks defined in `.pre-commit-config.yaml` with `pre-commit install`.

### Useful Commands

* To update the pre-commit hooks in `.pre-commit-config.yaml`, run `pre-commit autoupdate`

* To apply the pre-commit for every file in the repository, run `pre-commit run --config './.pre-commit-config.yaml' --all-files`

* To see all options to `pre-commit run`, run `pre-commit help run` (in particular, the `--files` option can be used to apply the command to selected files only).

* To commit without the pre-commit hook, run `git commit -m "Some message" --no-verify`
