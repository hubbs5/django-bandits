from django.test import TestCase
from unittest.mock import patch
from django_bandits.models import EpsilonGreedyModel, BanditFlag, FlagUrl


class TestEpsilonGreedyModel(TestCase):
    def setUp(self) -> None:
        self.bandit_flag = BanditFlag.objects.create()
        self.flag_url = FlagUrl.objects.create(flag=self.bandit_flag)
        self.eps_greedy_model = EpsilonGreedyModel.objects.create(
            flag=self.bandit_flag, epsilon=0.1
        )
        return super().setUp()

    @patch("numpy.random.random")
    @patch("numpy.random.randint")
    def test_pull_random_choice(self, mock_randint, mock_random):
        """Simulate random choice"""
        mock_randint.return_value = 0
        mock_random.return_value = 0

        active = self.eps_greedy_model.pull()
        # Mocked randint set to 0, e.g. False
        self.assertFalse(active)

    @patch("numpy.random.random")
    def test_pull_greedy_choice(self, mock_random):
        """Simulate greedy choice"""
        mock_random.return_value = 0.15
        self.flag_url.active_flag_views = 100
        self.flag_url.inactive_flag_views = 100
        self.flag_url.active_flag_conversions = 70
        self.flag_url.inactive_flag_conversions = 50
        self.flag_url.save()

        active = self.eps_greedy_model.pull()
        # Mocked greedy selection with active flag > inactive flag
        self.assertTrue(active)
