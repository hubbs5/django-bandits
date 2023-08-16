import numpy as np
from scipy.stats import ttest_ind
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth import models as auth_models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from abc import ABC, abstractmethod

from waffle.models import Flag #as WaffleFlag
from waffle.models import AbstractUserFlag

DEBUG = settings.DEBUG if hasattr(settings, "DEBUG") else False

BANDIT_ALGORITHMS = [
  ("EG", "Epsilon Greedy"),
  ("ED", "Epsilon Decay"),
  ("UCB1", "Upper Confidence Bound"),
]

class BanditFlag(AbstractUserFlag):
  # TODO: Are content_type and object_id necessary?
  content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
  object_id = models.PositiveIntegerField(null=True, blank=True)
  content_object = GenericForeignKey('content_type', 'object_id')
  
  def is_active_for_user(self, user):
    # TODO: Update to reflect the new bandit model
    User = get_user_model()
    if not user:
      try:
        user = User.objects.get(username='username')  # replace 'username' with actual username
      except User.DoesNotExist:
        user = auth_models.AnonymousUser()

    # Try to retrieve the active bandit model
    bandit_model_instance = None
    for related_set in [self.epsilongreedymodel_set, self.ucb1model_set]:  # Add more sets as needed
        bandit_model_instance = related_set.filter(is_active=True).first()
        if bandit_model_instance:
            break

    if bandit_model_instance is None:
        return super().is_active_for_user(user)

    # Call pull method on the bandit model instance
    active = bandit_model_instance.pull()
    return active


class URLSanitizationMixin:
  url_field_names = ["url", "source_url", "target_url"]

  def save(self, *args, **kwargs):
    for field_name in self.url_field_names:
      url = getattr(self, field_name, None)
      if url is None:
        continue
      setattr(self, field_name, self.ensure_trailing_slash(url))
    super().save(*args, **kwargs)
    
  @staticmethod
  def ensure_trailing_slash(url):
    # Ensure it has a trailing and leading slash
    if not url.endswith('/'):
      url += '/'

    if not url.startswith('/'):
      url = '/' + url
      
    return url


class FlagUrl(URLSanitizationMixin, models.Model):
  flag = models.OneToOneField(BanditFlag, on_delete=models.CASCADE)
  source_url = models.CharField(null=True, max_length=200, blank=True)
  target_url = models.CharField(null=True, max_length=200, blank=True)
  active_flag_views = models.IntegerField(default=0)
  inactive_flag_views = models.IntegerField(default=0)
  active_flag_conversions = models.IntegerField(default=0)
  inactive_flag_conversions = models.IntegerField(default=0)
    

class UserActivity(URLSanitizationMixin, models.Model):
  user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
  session_key = models.CharField(max_length=40, null=True)
  url = models.URLField()
  target_url_visit = models.BooleanField(default=False)
  timestamp = models.DateTimeField(auto_now_add=True)
  flags = models.ManyToManyField(BanditFlag, blank=True)
  is_staff = models.BooleanField(default=False)


class UserActivityFlag(models.Model):
  user_activity = models.ForeignKey(UserActivity, on_delete=models.CASCADE)
  flag = models.ForeignKey(BanditFlag, on_delete=models.CASCADE)
  timestamp = models.DateTimeField(auto_now_add=True)
  is_active = models.BooleanField(default=False, null=True)

    
class Bandit(models.Model):
  name = models.CharField(max_length=200, choices=BANDIT_ALGORITHMS, default="EG")
  content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
  object_id = models.PositiveIntegerField()
  content_object = GenericForeignKey('content_type', 'object_id')
  is_active = models.BooleanField(default=False)
  timestamp = models.DateTimeField(auto_now_add=True)

  def save(self, *args, **kwargs):
    '''Ensure only one active bandit is available at a time.'''
    if self.is_active and isinstance(self.content_object, BanditFlag):
      bandit_flag_content_type = ContentType.objects.get_for_model(BanditFlag)
      active_bandits = Bandit.objects.filter(
          content_type=bandit_flag_content_type,
          object_id=self.content_object.id,
          is_active=True
      )
      if self.pk:
        active_bandits = active_bandits.exclude(pk=self.pk)
      if active_bandits.exists():
        raise ValidationError("Only one bandit can be active at a time.")
    super().save(*args, **kwargs)

class BanditInstance(models.Model):
  # Used for Admin purposes
  flag = models.ForeignKey(BanditFlag, on_delete=models.CASCADE)
  bandit = models.OneToOneField(Bandit, on_delete=models.CASCADE)
  
# class Bandit(models.Model):
#   name = models.CharField(max_length=200,
#                           choices=BANDIT_ALGORITHMS,
#                           default="EG")
#   flag = models.ForeignKey(BanditFlag, on_delete=models.CASCADE)
#   content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#   object_id = models.PositiveIntegerField()
#   content_object = GenericForeignKey('content_type', 'object_id')
#   is_active = models.BooleanField(default=False)
#   timestamp = models.DateTimeField(auto_now_add=True)

#   def save(self, *args, **kwargs):
#     '''Ensure only one active bandit is available at a time.'''
#     if self.is_active:
#       active_bandits = Bandit.objects.filter(BanditFlag=self.flag, is_active=True)
#       if self.pk:
#         active_bandits = active_bandits.exclude(pk=self.pk)
#       if active_bandits.exists():
#         raise ValidationError("Only one bandit can be active at a time.")
#     super().save(*args, **kwargs)


class AbstractBanditModel(models.Model):
  # bandit = models.ForeignKey(Bandit, on_delete=models.CASCADE)
  flag = models.ForeignKey(BanditFlag, related_name='%(class)s_set', 
                           on_delete=models.CASCADE, null=True, blank=True)
  is_active = models.BooleanField(default=False)
  
  k = 2 # Number of options
  # TODO: Use caching to speed up the bandit algorithm

  class Meta:
    abstract = True
    constraints = [
        models.UniqueConstraint(fields=['flag', 'is_active'], 
                                condition=models.Q(is_active=True), 
                                name='unique_active_bandit_%(class)s')
    ]

  @abstractmethod
  def pull(self):
    '''Determines whether or not the flag is active 0 = False, 1 = True'''
    raise NotImplementedError("Pull method not implemented.")

  @abstractmethod
  def update(self):
    '''Updates the bandit model'''
    raise NotImplementedError("Update method not implemented.")

  def get_rewards(self):
    '''Returns the rewards for each option'''
    rewards = self.get_number_of_conversions() / np.maximum(self.get_number_of_views(), 1)
    return rewards

  def get_number_of_views(self):
    '''Returns the number of views for each option'''
    flag_url = self.flag.flagurl
    return np.array([flag_url.inactive_flag_views,
                     flag_url.active_flag_views])

  def get_number_of_conversions(self):
    '''Returns the number of conversions for each option'''
    flag_url = self.flag.flagurl
    return np.array([flag_url.inactive_flag_conversions,
                     flag_url.active_flag_conversions])
    
  def save(self, *args, **kwargs):
    '''Ensure only one bandit is active at a time.'''
    if self.is_active:
      active_bandits = type(self).objects.filter(flag=self.flag,
                                                 is_active=True)
      if self.pk:
        active_bandits = active_bandits.exclude(pk=self.pk)
      if active_bandits.exists():
        raise ValidationError("Only one bandit can be active at a time.")
    super().save(*args, **kwargs)

class EpsilonGreedyModel(AbstractBanditModel):
  epsilon = models.FloatField(default=0.1)
  prob_flag = models.FloatField(default=0.5)

  def pull(self) -> bool:
    p = np.random.random()
    if p < self.epsilon:
      if DEBUG:
        print("Making random choice")
      flag = np.random.randint(0, self.k)
    else:
      rewards = self.get_rewards()
      if DEBUG:
        print("Making greedy choice")
        print(f"Rewards: {rewards}")
      if rewards[0] == rewards[1]:
        flag = np.random.randint(0, self.k)
      else:
        flag = np.argmax(rewards)

    return bool(flag)


  def update(self):
    '''
    Updates probability of flag vs. no flag and any other stats
    '''
    rewards = self.get_rewards()
    if rewards[0] == rewards[1]:
      self.prob_flag = 0.5
    else:
      flag = bool(np.argmax(rewards))
      if flag:
        self.prob_flag = (1 - self.epsilon / 2)
      else:
        self.prob_flag = self.epsilon / 2
      

class EpsilonDecayModel(AbstractBanditModel):
  beta = models.FloatField(default=0.99)


class UCB1Model(AbstractBanditModel):
  c = models.FloatField(default=2.0)
  significance_level = models.FloatField(default=0.05)

  def pull(self) -> bool:
    '''
    Pulls the arm with the highest upper confidence bound
    '''
    rewards = self.get_rewards()
    n_views = self.get_number_of_views()
    flag = np.argmax(rewards + self.c * np.sqrt(
      np.log(np.max(n_views.sum(), 1)) / np.maximum(n_views, 1)))
    return bool(flag)