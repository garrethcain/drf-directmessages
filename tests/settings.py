SECRET_KEY = "test-secret-key-for-directmessages"

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "directmessages",
    "rest_framework",
    "drf_spectacular",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "directmessages.urls"

USE_TZ = True

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DRF DirectMessages API",
    "VERSION": "0.9.8",
    "DESCRIPTION": "Direct messaging API for Django REST Framework",
    "SERVE_INCLUDE_SCHEMA": False,
}
