from orderApp.enums import RestaurantContextKeys as RC, ViewContextKeys as VC, CurrentViews as CV
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model


from orderApp.context import get_current_view
from orderApp.models import Group

UserModel = get_user_model()


def group_context(view=CV.GROUP_VIEW, group=None):
    return {
        **get_current_view(view=view),
        VC.MAIN_TITLE: _("Groups Screen"),
        VC.TITLE_ACTION: _("Refresh Groups"),
        **group_list_section(),
        **group_details_section(group),
    }


def group_details_section(group, view=CV.GROUP_VIEW, add_view=False):
    return {
        VC.DETAILS_SECTION_ID: "group_members",
        VC.DETAILS_SECTION_TITLE: _("Group Members"),
        VC.DETAILS_SECTION_DATA: get_group_members(group) if group else None,
        VC.DETAILS_CURRENT_SELECTION: Group.objects.get(pk=group) if group else None,
        **(get_current_view(view=view) if add_view else {}),
    }


def group_list_section(view=CV.GROUP_VIEW, add_view=False):
    return {
        VC.LIST_SECTION_ID: "group_list",
        VC.LIST_SECTION_TITLE: _("Group List"),
        VC.LIST_MESSAGE_TYPE: "showGroupMembers",
        VC.LIST_SECTION_DATA: Group.objects.all().order_by("-id"),
        **(get_current_view(view=view) if add_view else {}),
    }


def get_group_members(group):
    groupMembers = UserModel.objects.filter(group=group)
    return groupMembers
