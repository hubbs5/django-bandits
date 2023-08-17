import pytest
from django_bandits.models import UCB1Model, BanditFlag, FlagUrl


@pytest.fixture
def setup_data(db):
    bandit_flag = BanditFlag.objects.create()
    flag_url = FlagUrl.objects.create(flag=bandit_flag)
    model = UCB1Model.objects.create(flag=bandit_flag)
    return bandit_flag, flag_url, model

class TestUCB1Model:

    @pytest.mark.parametrize("winning_arm", [0, 1])
    def test_winning_arm(self, setup_data, winning_arm):
        _, _, ucb1_model = setup_data

        ucb1_model.winning_arm = winning_arm
        ucb1_model.save()
        active = ucb1_model.pull()
        assert active == bool(winning_arm)

    @pytest.mark.parametrize("active_flag_conversions, inactive_flag_conversions", [(10, 50), (50, 10)])
    def test_exploitation(self, setup_data, active_flag_conversions, inactive_flag_conversions):
        _, flag_url, ucb1_model = setup_data

        flag_url.active_flag_views = 100
        flag_url.inactive_flag_views = 100
        flag_url.active_flag_conversions = active_flag_conversions
        flag_url.inactive_flag_conversions = inactive_flag_conversions
        flag_url.save()

        active = ucb1_model.pull()
        expected_output = active_flag_conversions > inactive_flag_conversions
        assert active == expected_output
