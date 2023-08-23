import pytest
from django_bandits.models import EpsilonDecayModel, BanditFlag, FlagUrl


@pytest.fixture
def setup_data(db):
    bandit_flag = BanditFlag.objects.create()
    flag_url = FlagUrl.objects.create(flag=bandit_flag)
    model = EpsilonDecayModel.objects.create(flag=bandit_flag)
    return bandit_flag, flag_url, model


class TestEpsilonDecayModel:
    @pytest.mark.parametrize("randint_return, expected_output", [(0, False), (1, True)])
    def test_pull_random_choice(
        self, setup_data, mocker, randint_return, expected_output
    ):
        """Simulate random choice"""
        _, _, eps_decay_model = setup_data
        mocker.patch("numpy.random.random", return_value=0.05)
        mocker.patch("numpy.random.randint", return_value=randint_return)

        active = eps_decay_model.pull()
        assert active == expected_output

    @pytest.mark.parametrize("randint_return, expected_output", [(0, False), (1, True)])
    def test_pull_greedy_choice_equal_rewards(
        self, setup_data, mocker, randint_return, expected_output
    ):
        """Simulate scenario where rewards are equal"""
        _, flag_url, eps_decay_model = setup_data

        mocker.patch("numpy.random.random", return_value=0.15)
        mocker.patch("numpy.random.randint", return_value=randint_return)

        flag_url.active_flag_views = 100
        flag_url.inactive_flag_views = 100
        flag_url.active_flag_conversions = 50
        flag_url.inactive_flag_conversions = 50
        flag_url.save()

        active = eps_decay_model.pull()
        assert active == expected_output

    @pytest.mark.parametrize(
        "active_flag_conversions, inactive_flag_conversions", [(50, 10), (10, 50)]
    )
    def test_pull_greedy_choice(
        self, setup_data, mocker, active_flag_conversions, inactive_flag_conversions
    ):
        _, flag_url, eps_decay_model = setup_data

        mocker.patch("numpy.random.random", return_value=1)

        flag_url.active_flag_views = 100
        flag_url.inactive_flag_views = 100
        flag_url.active_flag_conversions = active_flag_conversions
        flag_url.inactive_flag_conversions = inactive_flag_conversions
        flag_url.save()
        active = eps_decay_model.pull()
        expected_output = active_flag_conversions > inactive_flag_conversions
        assert active == expected_output

    @pytest.mark.parametrize("winning_arm", [0, 1])
    def test_winning_arm(self, setup_data, winning_arm):
        _, _, eps_decay_model = setup_data

        eps_decay_model.winning_arm = winning_arm
        eps_decay_model.save()
        active = eps_decay_model.pull()
        assert active == bool(winning_arm)
