from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import (UserActivity, FlagUrl, UserActivityFlag, BanditFlag,
                     Bandit, BanditInstance, EpsilonGreedyModel, EpsilonDecayModel,
                     UCB1Model)
from .forms import BanditAdminForm

class FlagUrlInline(admin.StackedInline):
    model = FlagUrl
    extra = 0


class EpsilonDecayModelInline(admin.StackedInline):
  model = EpsilonDecayModel
  fk_name = "flag"
  extra = 0
  fields = ["is_active", "beta"]


class EpsilonGreedyModelInline(admin.StackedInline):
  model = EpsilonGreedyModel
  extra = 0
  fk_name = "flag"
  fields = ["is_active", "epsilon", "prob_flag"]


class UCB1ModelInline(admin.StackedInline):
  model = UCB1Model
  extra = 0
  fk_name = "flag"
  fields = ["is_active", "c"]


# class BanditAdmin(admin.ModelAdmin):
#   form = BanditAdminForm
#   # inlines = ['content_object']
#   inlines = [
#     EpsilonGreedyModelInline, 
#     EpsilonDecayModelInline,
#     UCB1ModelInline,
#     ]


# class BanditInline(admin.StackedInline):
#   model = Bandit
#   form = BanditAdminForm
#   extra = 0
#   show_change_link = True
#   # inlines = [
#   #   EpsilonGreedyModelInline, 
#   #   EpsilonDecayModelInline,
#   #   UCB1ModelInline,
#   #   ]


# class BanditInstanceInline(admin.StackedInline):
#   model = BanditInstance
#   extra = 0
#   show_change_link = True


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
# admin.site.register(Bandit, BanditAdmin)
# admin.site.register(EpsilonGreedyBandit, EpsilonGreedyBanditAdmin)