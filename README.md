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
    "django_bandits",
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

Create migrations by running `python manage.py makemigrations` followed by `python manage.py migrate`.

### Enabling Bandits

With migrations complete, go to the Django site admin page. You should see something like this:

![View of Django admin page](docs/images/django_admin_bandit_1.png)

Select `Flags` under `DJANGO_BANDITS` and click "Add."

Make a name for the flag - typically the feature you want to test. Set it to test for whatever group you'd like to test it on. Refer to the [Waffle documentation](https://waffle.readthedocs.io/en/stable/) for details.

The bandit needs a `FLAG URL` to be set - this is the URL where the flag will be shown to users and is needed to track conversions and call the bandit to flip the feature when users reach that URL. Enter this as the `Source URL`.

To track a conversion, then you need to add a `Target URL`, which is where you want the user to end up.

In the example below, we're tracking the homepage (`/`) and want to see how many users click on a link to go to the contact page (`/contact/`).

![FLAG URL settings determines a successful conversion](docs/images/django_admin_bandit_flag_url.png)

This will consider any user who views your source URL and target URL to be a conversion during the session and will update the count shown in the image above.



### Performance Tracking