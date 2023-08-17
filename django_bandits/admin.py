from django.contrib import admin
from .models import (UserActivity, FlagUrl, UserActivityFlag, BanditFlag,
                     EpsilonGreedyModel, EpsilonDecayModel,
                     UCB1Model)
from .forms import BanditAdminForm # Deprecated? Delete?

class FlagUrlInline(admin.StackedInline):
    model = FlagUrl
    extra = 0


class EpsilonDecayModelInline(admin.TabularInline):
  model = EpsilonDecayModel
  extra = 0
  fk_name = "flag"
  readonly_fields = ["display_confidence_intervals"]
  fields = ["is_active", "beta", "significance_level", "min_views", "winning_arm"]


class EpsilonGreedyModelInline(admin.TabularInline):
  model = EpsilonGreedyModel
  extra = 0
  fk_name = "flag"
  readonly_fields = ["display_confidence_intervals"]
  fields = ["is_active", "epsilon", "significance_level", "min_views", "winning_arm"]


class UCB1ModelInline(admin.TabularInline):
  model = UCB1Model
  extra = 0
  fk_name = "flag"
  readonly_fields = ["display_conversion_rate", "display_confidence_intervals"]
  fields = ["is_active", "c", "significance_level", "min_views", "winning_arm", "display_conversion_rate", "display_confidence_intervals"]

  def display_conversion_rate(self, obj):
    return obj.display_conversion_rate()
  display_conversion_rate.short_description = "Conversion Rate"

  def display_confidence_intervals(self, obj):
    return obj.display_confidence_intervals()
  display_confidence_intervals.short_description = "Confidence Intervals"


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