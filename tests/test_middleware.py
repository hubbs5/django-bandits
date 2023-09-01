import pytest       
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware

from django_bandits.middleware import UserActivityMiddleware
from django_bandits.models import (
    BanditFlag,
    FlagUrl,
    UserActivity,
    UserActivityFlag,
    EpsilonGreedyModel,
    EpsilonDecayModel,
    UCB1Model,
)


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.mark.django_db(transaction=True)
@pytest.fixture
def request_with_session(request_factory):
    request = request_factory.get("/some_path/")
    middleware = SessionMiddleware(lambda req: HttpResponse())
    middleware.process_request(request)
    request.session.save()
    return request


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass"
    )


@pytest.fixture
def flag_and_url(db):
    flag = BanditFlag.objects.create(name="test_flag")
    flag_url = FlagUrl.objects.create(
        flag=flag, source_url="/source/", target_url="/target/"
    )
    return flag, flag_url


# TODO: To reduce redundant code
@pytest.mark.django_db
def test_basic_middleware_call(request_with_session):
    request = request_with_session
    request.user = AnonymousUser()

    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    response = middleware(request)

    urls = [ua.url for ua in UserActivity.objects.all()]
    assert response.status_code == 200
    assert UserActivity.objects.filter(
        url__in=["/some_path", "/some_path/"]
    ).exists(), f"Expected /some_path in {urls}"


@pytest.mark.django_db
def test_url_exclusion(request_with_session, test_user):
    request = request_with_session
    request.user = test_user
    request.path = "/admin"  # or any other path you have in the exclude list

    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    response = middleware(request)

    assert response.status_code == 200
    assert not UserActivity.objects.filter(
        url__in=[request.path, request.path + "/"]
    ).exists()


@pytest.mark.django_db
def test_useractivity_creation_authenticated(request_with_session, test_user):
    request = request_with_session
    request.user = test_user
    request.user.is_staff = False

    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    response = middleware(request)
    # transaction.commit()

    assert response.status_code == 200
    user_activity = UserActivity.objects.filter(url=request.path).first()
    assert user_activity, f"UserActivity not created for {request.path}"
    assert user_activity.user == test_user
    assert user_activity.session_key == request.session.session_key


@pytest.mark.django_db
def test_useractivity_creation_anonymous(request_with_session):
    request = request_with_session
    request.user = AnonymousUser()

    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    response = middleware(request)

    assert response.status_code == 200
    user_activity = UserActivity.objects.filter(url=request.path).first()
    assert user_activity
    assert not user_activity.user
    assert user_activity.session_key == request.session.session_key


@pytest.mark.django_db
def test_flag_activity_recording(request_with_session, test_user, flag_and_url, mocker):
    flag, flag_url = flag_and_url
    request = request_with_session
    request.user = test_user
    request.path = flag_url.source_url

    # Mocking the flag_is_active function to return True
    def print_mock(*args, **kwargs):
        print("Mocked function called with:", args, kwargs)
        return True

    UserActivityMiddleware.flag_is_active = print_mock

    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    response = middleware(request)
    flag_url.refresh_from_db()
    assert response.status_code == 200
    assert UserActivityFlag.objects.filter(
        user_activity__url=request.path, flag=flag, is_active=True
    ).exists(), f"Expected UserActivityFlag for {flag.name} to be active"
    assert (
        flag_url.active_flag_views == 1
    ), f"Expected 1 active flag view, got {flag_url.active_flag_views}"


@pytest.mark.django_db
@pytest.mark.parametrize("active_flag", [True, False])
def test_flag_conversion_recording(
    request_with_session, test_user, flag_and_url, mocker, active_flag
):
    flag, flag_url = flag_and_url
    request = request_with_session
    request.user = test_user

    mocker.patch.object(
        UserActivityMiddleware, "flag_is_active", return_value=active_flag
    )

    # Simulate the user visiting the source_url first
    request.path = flag_url.source_url
    middleware_source = UserActivityMiddleware(lambda req: HttpResponse())
    response_source = middleware_source(request)
    assert (
        response_source.status_code == 200
    ), "Expected 200 response code from source_url"

    # Simulate visiting the target_url
    request.path = flag_url.target_url
    middleware_target = UserActivityMiddleware(lambda req: HttpResponse())
    response_target = middleware_target(request)
    assert (
        response_target.status_code == 200
    ), "Expected 200 response code from target_url"
    flag_url.refresh_from_db()

    active_source_flag = middleware_target._get_latest_flagged_source_url(
        request.session.session_key, flag_url.source_url
    )

    assert (
        active_source_flag == active_flag
    ), f"Expected {active_flag}, got {active_source_flag}"
    if active_source_flag:
        assert (
            flag_url.active_flag_conversions == 1
        ), f"Expected 1 active flag conversion, got {flag_url.active_flag_conversions}"
    else:
        assert (
            flag_url.inactive_flag_conversions == 1
        ), f"Expected 1 inactive flag conversion, got {flag_url.inactive_flag_conversions}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "active_flag_conversions, inactive_flag_conversions," + "winning_arm, bandit_model",
    [
        (100, 50, 1, EpsilonGreedyModel),
        (50, 100, 0, EpsilonGreedyModel),
        (100, 50, 1, EpsilonDecayModel),
        (50, 100, 0, EpsilonDecayModel),
        (100, 50, 1, UCB1Model),
        (50, 100, 0, UCB1Model),
    ],
)
def test_bandit_test_arms(
    request_with_session,
    test_user,
    flag_and_url,
    active_flag_conversions,
    inactive_flag_conversions,
    winning_arm,
    bandit_model,
):
    flag, flag_url = flag_and_url
    request = request_with_session
    request.user = test_user

    bandit = bandit_model.objects.create(flag=flag, is_active=True)
    flag_url.active_flag_views = 120
    flag_url.inactive_flag_views = 120
    flag_url.active_flag_conversions = active_flag_conversions
    flag_url.inactive_flag_conversions = inactive_flag_conversions
    flag_url.save()

    # Simulate the user visiting the source_url first
    request.path = flag_url.source_url
    middleware_source = UserActivityMiddleware(lambda req: HttpResponse())
    response_source = middleware_source(request)
    assert (
        response_source.status_code == 200
    ), "Expected 200 response code from source_url"

    # Bandit is only updated after a conversion
    request.path = flag_url.target_url
    middleware_target = UserActivityMiddleware(lambda req: HttpResponse())
    response_target = middleware_target(request)
    assert (
        response_target.status_code == 200
    ), "Expected 200 response code from target_url"

    flag_url.refresh_from_db()
    bandit.refresh_from_db()

    assert (
        bandit.get_number_of_views().sum() > bandit.min_views
    ), f"Insufficient views for test: {bandit.get_number_of_views().sum()}<{bandit.min_views}"
    assert (
        bandit.winning_arm == winning_arm
    ), f"Expected the winning arm to be {winning_arm}, but got {bandit.winning_arm}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path, regex, should_create",
    [
        ("/admin", "", False),  # Should not be created based on settings
        ("/some_php_page.php", r"\.php", False),  # Should not be created based on .php
        (
            "/some_wordpress_page",
            r"wordpress",
            False,
        ),  # Should not be created based on 'wordpress'
        ("/wp-login", r"\/wp-", False),  # Should not be created based on 'wp-'
        ("/normal_page", r"\.php|wordpress|\/wp-", True),  # Should be created
        ("/xmlrpc.php/", r"\.php|wordpress|\/wp-", False),
        ("/visit-page/", r"", True),
    ],
)
def test_url_exclusion(request_with_session, test_user, path, regex, should_create):
    """Tests to see if URLs on the excluded list or in regex result in the creation of UserActivity objects or not."""
    request = request_with_session
    request.user = test_user
    request.path = path

    settings.EXCLUDE_FROM_TRACKING_REGEX = regex

    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    response = middleware(request)

    assert response.status_code == 200

    exists = UserActivity.objects.filter(url__in=[path, path + "/"]).exists()

    assert (
        exists is should_create
    ), f"Unexpected UserActivity creation for {path}. Exists = {exists}"
