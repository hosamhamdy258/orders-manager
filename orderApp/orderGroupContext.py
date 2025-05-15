from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from orderApp.context import get_current_view
from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import OrderGroup, OrderRoom

UserModel = get_user_model()

navigation_buttons = [
    {"view": CV.ORDER_GROUP, "url": "order_groups", "display": _("Groups")},
    {"view": CV.RESTAURANT, "url": "restaurants", "display": _("Restaurants")},
]


def order_group_context(user, view=CV.ORDER_GROUP, group=None):
    return {
        **get_current_view(view=view),
        VC.MAIN_TITLE: _("Groups"),
        VC.TITLE_ACTION: _("Refresh"),
        **order_group_list_section(user),
        **order_group_details_section(),
        "navigation_buttons": navigation_buttons,
    }


def order_group_details_section(group=None, view=CV.ORDER_ROOM, add_view=False):
    return {
        VC.DETAILS_SECTION_ID: "group_members",
        VC.DETAILS_SECTION_TITLE: _("Group Members"),
        VC.DETAILS_SECTION_DATA: get_order_group_members(group) if group else None,
        **(get_current_view(view=view) if add_view else {}),
    }


def order_group_list_section(user, view=CV.ORDER_ROOM, add_view=False):
    return {
        VC.LIST_SECTION_ID: "group_list",
        VC.LIST_SECTION_TITLE: _("Groups List"),
        VC.LIST_MESSAGE_TYPE: "showGroupMembers",
        VC.LIST_SECTION_DATA: get_user_order_groups(user),
        VC.LIST_TABLE_HEADERS: [_("Group"), _("Members")],
        **(get_current_view(view=view) if add_view else {}),
        GC.ACTION_JOIN_BUTTON: {"name": _("Open")},
        GC.ACTION_SHOW_BUTTON: {"name": _("Manage"), "icon": "bi bi-gear-fill"},
    }


def get_user_order_groups(user):
    return OrderGroup.objects.filter(Q(m2m_users=user) | Q(fk_owner=user)).distinct()


def get_order_group_members(group):
    return UserModel.objects.filter(group_members=group)
