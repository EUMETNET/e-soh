# E-SOH API

## Environment variables

Environment variables that can be used to configure the container or the environment where you are running the application.

| Name                | Description                                                                                                                | Mandatory |
|---------------------|----------------------------------------------------------------------------------------------------------------------------|-----------|
| DSHOST              | Address to the datastore                                                                                                   | ☑         |
| DSPORT              | Port where the datastore is available.                                                                                     | ☑         |
| FORWARDED_ALLOW_IPS | Environment variable used to set the `forwarded-allow-ips` in gunicorn. If this APis set behind a proxy, `FORWARDED_ALLOW_IPS` should be set to the proxy IP. Setting this to `*` is possible, but should only be set if you have ensured the API is only reachable from the proxy, and not directly from the internet. If not using docker compose this have to be passed to docker using the `-e` argument. | ☑         |
| GUNICORN_CMD_ARGS   | Command-line arguments for configuring Gunicorn, a Python WSGI HTTP Server.                                                | ☐         |
| CORS_ORIGINS        | Indicates whether the response can be shared with requesting code from the given origin passed as a comma seperated string | ☐         |

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
