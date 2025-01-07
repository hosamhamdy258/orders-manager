# flake8:noqa


DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "192.168.1.10", "https://net-rosana-hosamhamdy-798965e4.koyeb.app/"]
# CORS_ALLOW_ALL_ORIGINS = True
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 60
# SECURE_HSTS_PRELOAD = True
# SECURE_SSL_REDIRECT = True
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True

CSRF_TRUSTED_ORIGINS = ["http://192.168.1.10:9000", "http://127.0.0.1:9000", "https://net-rosana-hosamhamdy-798965e4.koyeb.app/"]
