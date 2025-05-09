from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from orderApp.context import get_current_view
from orderApp.enums import CurrentViews as CV
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import OrderRoom

UserModel = get_user_model()


def order_room_context(view=CV.ORDER_ROOM, group=None):
    return {
        **get_current_view(view=view),
        VC.MAIN_TITLE: _("Rooms"),
        VC.TITLE_ACTION: _("Refresh"),
        **order_room_list_section(),
        **order_room_details_section(),
    }


def order_room_details_section(group=None, view=CV.ORDER_ROOM, add_view=False):
    return {
        VC.DETAILS_SECTION_ID: "room_members",
        VC.DETAILS_SECTION_TITLE: _("Room Members"),
        VC.DETAILS_SECTION_DATA: get_order_room_members(group) if group else None,
        **(get_current_view(view=view) if add_view else {}),
    }


def order_room_list_section(view=CV.ORDER_ROOM, add_view=False):
    return {
        VC.LIST_SECTION_ID: "room_list",
        VC.LIST_SECTION_TITLE: _("Room List"),
        VC.LIST_MESSAGE_TYPE: "showRoomMembers",
        VC.LIST_SECTION_DATA: OrderRoom.objects.all().order_by("-id"),
        VC.LIST_TABLE_HEADERS: [_("Room Name"), _("Connected Users")],
        **(get_current_view(view=view) if add_view else {}),
    }


def get_order_room_members(group):
    groupMembers = UserModel.objects.filter(group=group)
    return groupMembers
