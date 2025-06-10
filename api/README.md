# E-SOH API

## Enviorment variable
These enviorment variables should be set when you are starting the container or be set in the enviorment where you are running the application.
### DSHOST

IP address to datastore

### DSPORT

Port the datastore is available on.

### FORWARDED_ALLOW_IPS

Environment variable used to set the `forwarded-allow-ips` in gunicorn. If this API is set behind a proxy, `FORWARDED_ALLOW_IPS` should be set to the proxy IP. Setting this to `*` is possible, but should only be set if you have ensured the API is only reachable from the proxy, and not directly from the internet. If not using docker compose this have to be passed to docker using the `-e` argument.

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
