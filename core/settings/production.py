# flake8:noqa


DEBUG = False

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "hosamhamdy.koyeb.app"]

CSRF_TRUSTED_ORIGINS = ["https://127.0.0.1", "https://localhost", "https://hosamhamdy.koyeb.app"]

# =========================
# ! this section is handled by nginx

# SECURE_SSL_REDIRECT = True

# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# SECURE_HSTS_PRELOAD = True

# SECURE_HSTS_SECONDS = 120
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_SECURE = True
# =========================
