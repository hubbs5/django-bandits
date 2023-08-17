from django.contrib import admin
from .models import (UserActivity, FlagUrl, UserActivityFlag, BanditFlag,
                     EpsilonGreedyModel, EpsilonDecayModel,
                     UCB1Model)
from .forms import BanditAdminForm # Deprecated? Delete?

class FlagUrlInline(admin.StackedInline):
    model = FlagUrl
    extra = 0


class BaseBanditInline(admin.TabularInline):
  extra = 0
  fk_name = "flag"
  readonly_fields = ["display_conversion_rate", "display_confidence_intervals"]
  fields = ["is_active", "significance_level", "min_views", "winning_arm", 
            "display_conversion_rate", "display_confidence_intervals"]
  new_fields = []
  new_field_positions = []

  def display_conversion_rate(self, obj):
    return obj.display_conversion_rate()
  display_conversion_rate.short_description = "Conversion Rate"

  def display_confidence_intervals(self, obj):
    return obj.display_confidence_intervals()
  display_confidence_intervals.short_description = "Confidence Intervals"

  def insert_bandit_fields(self, bandit_fields: list, positions: list) -> None:
    '''For inserting bandit specific fields into the admin display'''
    new_fields = list(self.fields) # Make a copy to avoid overwriting for all classes
    for i, f in zip(positions, bandit_fields):
      new_fields.insert(i, f)
    self.fields = new_fields

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.insert_bandit_fields(self.new_fields, self.new_field_positions)



class EpsilonDecayModelInline(BaseBanditInline):
  model = EpsilonDecayModel
  new_fields = ["beta"]
  new_field_positions = [1]


class EpsilonGreedyModelInline(BaseBanditInline):
  model = EpsilonGreedyModel
  new_fields = ["epsilon"]
  new_field_positions = [1]


class UCB1ModelInline(BaseBanditInline):
  model = UCB1Model
  new_fields = ["c"]
  new_field_positions = [1]


# Define the admin interface for Flag
class FlagAdmin(admin.ModelAdmin):
  inlines = [FlagUrlInline,
             EpsilonGreedyModelInline, 
             EpsilonDecayModelInline,
             UCB1ModelInline,
            ]


class UserActivityFlagInline(admin.TabularInline):
  model = UserActivityFlag
  extra = 1


class UserActivityInline(admin.TabularInline):
  model = UserActivity


class UserActivityAdmin(admin.ModelAdmin):
  inlines = [UserActivityFlagInline]
  fieldsets = [
    (None, {'fields': ['user',
                       'session_key',
                       'url',
                       'is_staff',
                       'flags',
                       'target_url_visit',
                       ]
            })
  ]
  readonly_fields = ['timestamp']
  list_display = ['user', 'is_staff', 'session_key', 'url', 'timestamp']

# Unregister the original Flag admin form provided by Django Waffle
# admin.site.unregister(Flag)

# Register the new FlagAdmin
admin.site.register(BanditFlag, FlagAdmin)
admin.site.register(UserActivity, UserActivityAdmin)