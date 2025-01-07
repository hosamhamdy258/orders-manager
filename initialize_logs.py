import os


def create_log_dirs():
    log_dirs = ["/app/logs/gunicorn", "/app/logs/nginx", "/app/logs/supervisord"]

    for log_dir in log_dirs:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)  # Create directory if it doesn't exist


if __name__ == "__main__":
    create_log_dirs()
