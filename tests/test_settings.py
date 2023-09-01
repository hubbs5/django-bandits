# Settings to run tests for django-bandits

DEBUG = True

SECRET_KEY = "totally-non-fake-secret-key-for-testing"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "waffle",
    "django_bandits",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_bandits.middleware.UserActivityMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TEST_RUNNER = "pytest_django.runner.DjangoPytestTestRunner"
WAFFLE_FLAG_MODEL = "django_bandits.BanditFlag"
USE_TZ = True  # Set to true to avoid django 5.0 warning

EXCLUDE_FROM_TRACKING = ["/admin"]


AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
