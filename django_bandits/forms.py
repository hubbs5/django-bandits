from django import forms

from .models import Bandit

class BanditAdminForm(forms.ModelForm):
    class Meta:
        model = Bandit
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        is_active = cleaned_data.get("is_active")
        flag = cleaned_data.get("flag")
        if is_active:
            active_bandits = Bandit.objects.filter(flag=flag, is_active=True)
            if self.instance.pk:
                active_bandits = active_bandits.exclude(pk=self.instance.pk)
            if active_bandits.exists():
                self.add_error(None, "Only one bandit can be active at a time.")