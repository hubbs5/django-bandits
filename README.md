# django-bandits

This package enables optimization of your Django site via multi-armed bandits.

This package extends [Django-Waffle](https://waffle.readthedocs.io/en/stable/) by wrapping the feature flipper functions with bandit algorithms. This allows automatic testing and optimization as users interact with your site.

**WARNING**
This is in alpha mode and **NO TESTS** are currently active! If you'd like to contribute, see XXXX.

## Installation

~~Install with: `pip install django-bandits`~~

Not yet active...getting to it soon...

Go to your `settings.py` file and add `waffle` to your installed apps list:
```
INSTALLED_APPS = [
    ...
    "waffle",
    ...
]
```

Additionally, add `django_bandits.middleware.UserActivityMiddleware` to `MIDDLEWARE` after CSRF and authentication middleware, e.g.:

```
MIDDLEWARE = [
    ...
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_bandits.middleware.UserActivityMiddleware", # It goes here!
    ...
]
```

Update `settings.py` to exclude any particular URL from conversion tracking, e.g.:
```
EXCLUDE_FROM_TRACKING = [
    ADMIN_URL,
    "/static/",
]
```

### Migrations


### Enabling Bandits


### Performance Tracking