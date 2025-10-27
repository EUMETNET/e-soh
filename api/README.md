# E-SOH API

## Environment variables

Environment variables that can be used to configure the container or the environment where you are running the application.

| Name                | Description                                                                                                                   | Mandatory |
|---------------------|-------------------------------------------------------------------------------------------------------------------------------|-----------|
| DSHOST              | Address to the datastore                                                                                                      | ☑         |
| DSPORT              | Port where the datastore is available.                                                                                        | ☑         |
| FORWARDED_ALLOW_IPS | Environment variable used to set the `forwarded-allow-ips` in gunicorn. If this API is set behind a proxy, `FORWARDED_ALLOW_IPS` should be set to the proxy IP. Setting this to `*` is possible, but should only be set if you have ensured the API is only reachable from the proxy, and not directly from the internet. If not using docker compose this have to be passed to docker using the `-e` argument. | ☑         |
| GUNICORN_CMD_ARGS   | Command-line arguments for configuring Gunicorn, a Python WSGI HTTP Server.                                                   | ☐         |
| CORS_ORIGINS        | Indicates whether the response can be shared with requesting code from the given origins (passed as a comma separated string) | ☐         |
| CORS_HEADERS        | Indicates what headers should be supported with cross-origin requests (passed as a comma separated string)                    | ☐         |
| JINJA2_TEMPLATES    | Path to a folder with jinja2 templates to override the default templates used by the API. See template section for details    | ☐         |
| OPENAPI_METADATA_PATH | Path to an alternative OpenAPI metadata json file. It need to have the same fields as the openapi/openapi_metadata.py file. | ☐         |

## OpenAPI metadata

To load your own metadata file, mount your new openapi metadata json file, with the same structure and key as the default one, found in openapi_default_files, and point the environment variable `OPENAPI_METADATA_PATH` to the new file. If you mount your folder to the same as the default one, make sure to not overwrite files you have not replaced.

## JINJA2_TEMPLATES

The jinja2 folder must container the following files:

- dataset_metadata_template.j2: this is the metadata template for the observation collection.

### dataset_metadata_template.j2

The current jinja2 filters will be replaced. It's important to use the json j2 filter when inserting these strings.

- spatial_extent
- temporal_extent
- url_base
- url_conformance
- url_docs

All url fields are dynamically generated based on the request url base.

To load a custom template, mount a folder with your new template in to the container and set the `JINJA2_TEMPLATES` environment variable to point your new folder.

## Prerequisites of running locally

### QUDT

Move the `std_unit_names.json`to the api folder with

```bash
just copy-units
```

Generate the file needed for QUDT dictionary by running

```bash
python generate_qudt_units.py
```
