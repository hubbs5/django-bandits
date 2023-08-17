import pytest
from django_bandits.models import EpsilonGreedyModel, BanditFlag, FlagUrl

@pytest.fixture
def setup_data(db):
    bandit_flag = BanditFlag.objects.create()
    flag_url = FlagUrl.objects.create(flag=bandit_flag)
    model = EpsilonGreedyModel.objects.create(flag=bandit_flag, epsilon=0.1)
    return bandit_flag, flag_url, model

class TestEpsilonGreedyModel:

    @pytest.mark.parametrize("randint_return, expected_output", [(0, False), (1, True)])
    def test_pull_random_choice(
        self, setup_data, mocker, randint_return, expected_output
    ):
        """Simulate random choice"""
        _, _, eps_greedy_model = setup_data
        mocker.patch("numpy.random.random", return_value=0.05)
        mocker.patch("numpy.random.randint", return_value=randint_return)

        active = eps_greedy_model.pull()
        assert active == expected_output

    @pytest.mark.parametrize(
        "active_flag_conversions, inactive_flag_conversions", [(50, 10), (10, 50)]
    )
    def test_pull_greedy_choice(
        self, setup_data, mocker, active_flag_conversions, inactive_flag_conversions
    ):
        _, flag_url, eps_greedy_model = setup_data

        mocker.patch("numpy.random.random", return_value=1)

        flag_url.active_flag_views = 100
        flag_url.inactive_flag_views = 100
        flag_url.active_flag_conversions = active_flag_conversions
        flag_url.inactive_flag_conversions = inactive_flag_conversions
        flag_url.save()
        active = eps_greedy_model.pull()
        expected_output = active_flag_conversions > inactive_flag_conversions
        assert active == expected_output

    @pytest.mark.parametrize("winning_arm", [0, 1])
    def test_winning_arm(self, setup_data, winning_arm):
        _, _, eps_greedy_model = setup_data

        eps_greedy_model.winning_arm = winning_arm
        eps_greedy_model.save()
        active = eps_greedy_model.pull()
        assert active == bool(winning_arm)