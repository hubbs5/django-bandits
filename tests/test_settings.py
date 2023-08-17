# Settings to run tests for django-bandits

SECRET_KEY = "totally-non-fake-secret-key-for-testing"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "waffle",
    "django_bandits",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_bandits.middleware.UserActivityMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TEST_RUNNER = 'pytest_django.runner.DjangoPytestTestRunner'
WAFFLE_FLAG_MODEL = "django_bandits.BanditFlag"
