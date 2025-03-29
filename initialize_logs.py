import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BASE_LOG_DIR = os.path.join(BASE_DIR, "logs")

log_apps = ["gunicorn", "nginx", "supervisord", "django"]


def create_log_dirs():
    for log_app in log_apps:
        log_app_path = os.path.join(BASE_LOG_DIR, log_app)
        if not os.path.exists(log_app_path):
            os.makedirs(log_app_path, exist_ok=True)  # Create directory if it doesn't exist


if __name__ == "__main__":
    create_log_dirs()
