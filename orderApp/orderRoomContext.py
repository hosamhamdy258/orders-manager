from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from orderApp.context import BaseContext, get_current_view
from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import OrderRoom

UserModel = get_user_model()


class OrderRoomContext(BaseContext):
    view_type = CV.ORDER_ROOM

    def __init__(self, user, order_group):
        super().__init__(user)
        self.order_group = order_group

    def get_base_context(self):
        ctx = super().get_base_context()
        ctx.update(
            {
                VC.MAIN_TITLE: _("Rooms"),
                VC.TITLE_ACTION: _("Refresh"),
            }
        )
        return ctx

    def get_list_context(self, instance=None):
        ctx = super().get_list_context()
        ctx.update(
            {
                VC.LIST_SECTION_ID: "room_list",
                VC.LIST_TABLE_BODY_ID: "group_table_body",
                VC.LIST_SECTION_TITLE: _("Room List"),
                VC.LIST_MESSAGE_TYPE: "showRoomMembers",
                VC.LIST_SECTION_DATA: [instance] if instance else self.get_order_group_rooms(self.get_order_group()),
                VC.LIST_TABLE_HEADERS: [_("Room Name"), _("Connected Users")],
                # GC.ACTION_JOIN_BUTTON: {"name": _("Join")},
                # GC.ACTION_SHOW_BUTTON: {"name": _("Manage"), "icon": "bi bi-gear-fill"},
            }
        )
        return ctx

    def get_details_context(self, instance=None):
        ctx = super().get_details_context()
        ctx.update(
            {
                VC.DETAILS_SECTION_ID: "room_members",
                VC.DETAILS_TABLE_BODY_ID: "details_table_body",
                VC.DETAILS_SECTION_TITLE: _("Room Members"),
                VC.DETAILS_SECTION_DATA: self.get_order_room_members(instance) if instance else None,
                VC.DETAILS_TABLE_HEADERS: [_("Name")],
            }
        )
        return ctx

    def get_order_group_rooms(self, group):
        return OrderRoom.objects.filter(fk_order_group=group).order_by("-id")

    def get_order_room_members(self, group):
        return UserModel.objects.filter(order_members=group)
