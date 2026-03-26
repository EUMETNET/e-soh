from uvicorn.workers import UvicornWorker


class UvicornWorkerWithForwardedHeaders(UvicornWorker):
    """Custom Gunicorn worker that uses the ForwardedHostAndPrefixMiddleware to handle
    X-Forwarded-Host and X-Forwarded-Prefix headers.

    This worker should be used when running the application with Gunicorn behind a proxy that sets
    these headers, and you want the application to properly handle them.

    To use this worker, specify it when starting Gunicorn:
    gunicorn main:app --worker-class uvicorn_workers.UvicornWorkerWithForwardedHeaders
    --workers 4 --bind 0.0.0.0:8000
    """

    CONFIG_KWARGS = {"proxy_headers": False}  # Disable uvicorn's default ProxyHeadersMiddleware
