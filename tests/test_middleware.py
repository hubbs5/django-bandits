import pytest
from django.db import transaction
from django.http import HttpResponse
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware

from django_bandits.middleware import UserActivityMiddleware
from django_bandits.models import BanditFlag, FlagUrl, UserActivity, UserActivityFlag


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.mark.django_db(transaction=True)
@pytest.fixture
def request_with_session(request_factory):
    request = request_factory.get('/some_path/')
    middleware = SessionMiddleware(lambda req: HttpResponse())
    middleware.process_request(request)
    request.session.save()
    return request


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username='testuser', email='test@example.com', password='testpass'
    )


@pytest.fixture
def flag_and_url(db):
    flag = BanditFlag.objects.create(name="test_flag")
    flag_url = FlagUrl.objects.create(flag=flag,
                                      source_url="/source/",
                                      target_url="/target/")
    return flag, flag_url

@pytest.mark.django_db
def test_basic_middleware_call(request_with_session): #, test_user, flag_and_url):
    request = request_with_session
    request.user = AnonymousUser()

    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    response = middleware(request)

    urls = [ua.url for ua in UserActivity.objects.all()]
    assert response.status_code == 200
    assert UserActivity.objects.filter(url__in=['/some_path', '/some_path/']).exists(), f'Expected /some_path in {urls}'


@pytest.mark.django_db
def test_url_exclusion(request_with_session, test_user):
    request = request_with_session
    request.user = test_user
    request.path = "/admin"  # or any other path you have in the exclude list
    
    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    response = middleware(request)
    
    assert response.status_code == 200
    assert not UserActivity.objects.filter(
        url__in=[request.path, request.path + "/"]).exists()


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
    assert user_activity, f'UserActivity not created for {request.path}'
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
        ).exists(), f'Expected UserActivityFlag for {flag.name} to be active'
    assert flag_url.active_flag_views == 1, \
        f'Expected 1 active flag view, got {flag_url.active_flag_views}'


@pytest.mark.django_db
def test_target_url_visit_after_source(request_with_session, test_user, flag_and_url):
    flag, flag_url = flag_and_url
    request = request_with_session
    request.user = test_user
    request.path = flag_url.source_url
    
    middleware = UserActivityMiddleware(lambda req: HttpResponse())
    middleware(request)  # First visiting the source_url
    
    request.path = flag_url.target_url
    response = middleware(request)  # Now visiting the target_url
    flag_url.refresh_from_db()
    assert response.status_code == 200
    user_activity = UserActivity.objects.filter(url=flag_url.target_url).first()
    assert user_activity
    assert user_activity.target_url_visit, \
        f"Expected target_url_visit to be True, got {user_activity.target_url_visit}"
    assert flag_url.active_flag_conversions == 1, \
        f"Expected 1 active flag conversion, got {flag_url.active_flag_conversions}"
