from django.conf import settings
from django.http import HttpRequest, HttpResponse
from .models import UserActivity, FlagUrl, UserActivityFlag
from .models import BanditFlag

from waffle import flag_is_active

DEBUG = settings.DEBUG if hasattr(settings, "DEBUG") else False
class UserActivityMiddleware:
  # TODO: Exclude 404 pages
  exclude = settings.EXCLUDE_FROM_TRACKING if hasattr(settings, "EXCLUDE_FROM_TRACKING") else ["/admin"]
  exclude = [path if path.startswith("/") else "/" + path for path in exclude]

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request: HttpRequest) -> HttpResponse:
    session_key = request.session.session_key
    current_url = request.path

    if any(current_url.startswith(path) for path in self.exclude):
      return self.get_response(request)

    # If the user is authenticated, add their user instance to the UserActivity
    if request.user.is_authenticated:
      user_activity = UserActivity.objects.create(
        user=request.user,
        is_staff=request.user.is_staff,
        session_key=session_key,
        url=current_url)
    else:
      user_activity = UserActivity.objects.create(
        session_key=session_key,
        url=current_url)

    # Checks to see which flags are active on the source page, if any
    for flag in BanditFlag.objects.all():
      flag_url = FlagUrl.objects.filter(flag=flag).first()
      if flag_url:
        if current_url == flag_url.source_url:
          # is_flag_active determines whether or not the user sees the feature
          is_flag_active = flag_is_active(request, flag.name)
          if DEBUG:
            print(f"Checking flag {flag.name} for user {request.user}\nFlag URL: {flag_url.source_url}\nFlag is active: {is_flag_active}")
          if is_flag_active is not None:
            ua_flag = UserActivityFlag.objects.create(
              user_activity=user_activity,
              flag=flag,
              is_active=is_flag_active)
            ua_flag.save()
            if is_flag_active:
              flag_url.active_flag_views += 1
            else:
              flag_url.inactive_flag_views += 1
            flag_url.save()
          
        # Checks to see if the user has reached the target URL
        elif current_url == flag_url.target_url:
          source_reached = UserActivity.objects.filter(
            session_key=session_key, url=flag_url.source_url).exists()
          if source_reached:
            user_activity.target_url_visit = True
            user_activity.save()
            # Need to see which source flag the user saw before, if any
            active_source_flag = self._get_latest_flagged_source_url(
              session_key, flag_url.source_url)
            # TODO: Update to handle cases where users didn't see the particular
            # landing page or feature flag at all
            if DEBUG:
              print(f"User reached target URL {flag_url.target_url}\nActive source flag: {active_source_flag}")
            if active_source_flag:
              flag_url.active_flag_conversions += 1
            else:
              flag_url.inactive_flag_conversions += 1
            flag_url.save()
            # Update bandit stats for display in admin: Move to admin so updates when Admin views it
            # for related_set in [flag.epsilongreedymodel_set, flag.epsilondecaymodel_set, flag.ucb1model_set]:
            #   bandit_model_instance = related_set.filter(is_active=True).first()
            #   if bandit_model_instance:
            #     bandit_model_instance.update()
            #     bandit_model_instance.save()
            #     break
              
    response = self.get_response(request)

    return response


  def _get_latest_flagged_source_url(self, session_key: str,
                                     source_url: str) -> UserActivityFlag:
    '''
    Gets the most recent flagged source URL to see whether or not the flagged
    feature was active.
    '''
    source_user_activity = UserActivity.objects.filter(
      session_key=session_key, url=source_url).order_by('-timestamp').first()
    source_uaf = UserActivityFlag.objects.filter(user_activity=source_user_activity).first()
    return source_uaf.is_active


