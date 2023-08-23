import numpy as np
from scipy.stats import ttest_ind, norm
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import models as auth_models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from abc import ABC, abstractmethod

from waffle.models import Flag  # as WaffleFlag
from waffle.models import AbstractUserFlag

DEBUG = settings.DEBUG if hasattr(settings, "DEBUG") else False

BANDIT_ALGORITHMS = [
    ("EG", "Epsilon Greedy"),
    ("ED", "Epsilon Decay"),
    ("UCB1", "Upper Confidence Bound"),
]


class BanditFlag(AbstractUserFlag):
    # TODO: Are content_type and object_id necessary?
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    def is_active_for_user(self, user):
        # TODO: Update to reflect the new bandit model
        User = get_user_model()
        if not user:
            try:
                user = User.objects.get(
                    username="username"
                )  # replace 'username' with actual username
            except User.DoesNotExist:
                user = auth_models.AnonymousUser()

        # Try to retrieve the active bandit model
        bandit_model_instance = None
        for related_set in [
            self.epsilongreedymodel_set,
            self.epsilondecaymodel_set,
            self.ucb1model_set,
        ]:  # Add more sets as needed
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
        if not url.endswith("/"):
            url += "/"

        if not url.startswith("/"):
            url = "/" + url

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
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             null=True, on_delete=models.SET_NULL)
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
    content_object = GenericForeignKey("content_type", "object_id")
    is_active = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Ensure only one active bandit is available at a time."""
        if self.is_active and isinstance(self.content_object, BanditFlag):
            bandit_flag_content_type = ContentType.objects.get_for_model(BanditFlag)
            active_bandits = Bandit.objects.filter(
                content_type=bandit_flag_content_type,
                object_id=self.content_object.id,
                is_active=True,
            )
            if self.pk:
                active_bandits = active_bandits.exclude(pk=self.pk)
            if active_bandits.exists():
                raise ValidationError("Only one bandit can be active at a time.")
        super().save(*args, **kwargs)


# TODO: Deprecated, delete
class BanditInstance(models.Model):
    # Used for Admin purposes
    flag = models.ForeignKey(BanditFlag, on_delete=models.CASCADE)
    bandit = models.OneToOneField(Bandit, on_delete=models.CASCADE)


class AbstractBanditModel(models.Model):
    flag = models.ForeignKey(
        BanditFlag,
        related_name="%(class)s_set",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=False)
    significance_level = models.FloatField(default=0.05)
    min_views = models.IntegerField(default=100)
    winning_arm = models.IntegerField(null=True, blank=True)

    k = 2  # Number of options

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["flag", "is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_bandit_%(class)s",
            )
        ]

    # def __str__(self):
    #   return self.display_bounds()

    @abstractmethod
    def pull(self):
        """Determines whether or not the flag is active 0 = False, 1 = True"""
        raise NotImplementedError("Pull method not implemented.")

    def get_rewards(self):
        """Returns the rewards for each option"""
        rewards = self.get_number_of_conversions() / np.maximum(
            self.get_number_of_views(), 1
        )
        return rewards

    def get_number_of_views(self):
        """Returns the number of views for each option"""
        flag_url = self.flag.flagurl
        return np.array([flag_url.inactive_flag_views, flag_url.active_flag_views])

    def get_number_of_conversions(self):
        """Returns the number of conversions for each option"""
        flag_url = self.flag.flagurl
        return np.array(
            [flag_url.inactive_flag_conversions, flag_url.active_flag_conversions]
        )

    def save(self, *args, **kwargs):
        """Ensure only one bandit is active at a time."""
        if self.is_active:
            active_bandits = type(self).objects.filter(flag=self.flag, is_active=True)
            if self.pk:
                active_bandits = active_bandits.exclude(pk=self.pk)
            if active_bandits.exists():
                raise ValidationError("Only one bandit can be active at a time.")
        super().save(*args, **kwargs)

    def test_arms(self):
        """
        Performs a two-sample t-test on the rewards for each arm
        """
        n_views = self.get_number_of_views()
        if n_views.sum() < self.min_views:
            return None

        # Converts outcomes to list of binary outcomes for use with ttest_ind
        n_convs = self.get_number_of_conversions()
        inactive_results = [1] * n_convs[0] + [0] * (n_views[0] - n_convs[0])
        active_results = [1] * n_convs[1] + [0] * (n_views[1] - n_convs[1])

        t, p_value = ttest_ind(inactive_results, active_results)
        if p_value < self.significance_level:
            self.winning_arm = (
                0 if np.mean(inactive_results) > np.mean(active_results) else 1
            )
            self.save()

    def get_confidence_intervals(self, arm: int) -> tuple:
        """Gets upper and lower bounds for the given arm"""
        n_views = self.get_number_of_views()[arm]
        n_convs = self.get_number_of_conversions()[arm]
        alpha = 1 - self.significance_level
        prop = n_convs / n_views
        z = norm.ppf(1 - alpha / 2)
        error = z * np.sqrt(prop * (1 - prop) / n_views)
        return prop - error, prop + error

    def get_inactive_flag_confidence_intervals(self) -> str:
        low, up = self.get_confidence_intervals(0)
        return f"{low:.2f} - {up:.2f}"

    def get_active_flag_confidence_intervals(self) -> str:
        low, up = self.get_confidence_intervals(1)
        return f"{low:.2f} - {up:.2f}"

    def display_confidence_intervals(self):
        inactive = self.get_inactive_flag_confidence_intervals()
        active = self.get_active_flag_confidence_intervals()
        return f"Active Flag:\t{active}\nInactive Flag:\t{inactive}"

    def display_conversion_rate(self):
        rewards = self.get_rewards()
        return f"Active Flag:\t{rewards[1]:.2%}\nInactive Flag:\t{rewards[0]:.2%}"


class EpsilonGreedyModel(AbstractBanditModel):
    epsilon = models.FloatField(default=0.1)
    prob_flag = models.FloatField(default=0.5)

    def pull(self) -> bool:
        if self.winning_arm is not None:
            return bool(self.winning_arm)
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
        """
        Updates probability of flag vs. no flag and any other stats

        TODO: Move this to be calculated on admin page
        """
        rewards = self.get_rewards()
        if rewards[0] == rewards[1]:
            self.prob_flag = 0.5
        else:
            flag = bool(np.argmax(rewards))
            if flag:
                self.prob_flag = 1 - self.epsilon / 2
            else:
                self.prob_flag = self.epsilon / 2


class EpsilonDecayModel(AbstractBanditModel):
    def pull(self) -> bool:
        if self.winning_arm is not None:
            return bool(self.winning_arm)
        p = np.random.random()
        if p < (1 / (1 + self.get_number_of_views().sum() / self.k)):
            flag = np.random.randint(0, self.k)
        else:
            rewards = self.get_rewards()
            if rewards[0] == rewards[1]:
                flag = np.random.randint(0, self.k)
            else:
                flag = np.argmax(rewards)

        return bool(flag)


class UCB1Model(AbstractBanditModel):
    c = models.FloatField(default=2.0)

    def pull(self) -> bool:
        """
        Pulls the arm with the highest upper confidence bound
        """
        if self.winning_arm is not None:
            return bool(self.winning_arm)
        rewards = self.get_rewards()
        n_views = self.get_number_of_views()
        flag = np.argmax(
            rewards
            + self.c
            * np.sqrt(np.log(np.max([n_views.sum(), 1])) / np.maximum(n_views, 1))
        )
        return bool(flag)
