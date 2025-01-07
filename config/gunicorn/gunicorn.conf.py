import multiprocessing

pythonpath = "/app"

wsgi_app = "core.asgi:application"

# Path to the Unix socket
bind = "unix:///run/gunicorn.sock"

# Number of worker processes
workers = 4 if multiprocessing.cpu_count() * 2 >= 4 else 2  # Adjusted based server CPU count

# The worker class (use `sync` for regular HTTP;or "uvicorn.workers.UvicornWorker" for async)
worker_class = "uvicorn.workers.UvicornWorker"

# Redirect stdout/stderr to specified file in errorlog.
# capture_output = True

# Preload the app for faster startup but ensure enough memory is available
preload_app = True

# reload = True


# Log files (adjust paths as needed)
errorlog = "/app/logs/gunicorn/error.log"
accesslog = "/app/logs/gunicorn/access.log"

loglevel = "debug"
