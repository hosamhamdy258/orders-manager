from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from orderApp.context import BaseContext
from orderApp.enums import CurrentViews as CV
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import OrderRoom

UserModel = get_user_model()


class OrderRoomContext(BaseContext):
    view_type = CV.ORDER_ROOM

    def get_base_context(self):
        ctx = super().get_base_context()
        ctx.update(
            {VC.MAIN_TITLE: _("Rooms"), VC.TITLE_ACTION: _("Refresh"), VC.TOP_SECTION_TEMPLATE: "orderRoom/topSection/titleAction.html"},
        )
        return ctx

    def get_list_context(self, instance=None):
        ctx = super().get_list_context()
        ctx.update(
            {
                VC.LIST_SECTION_TITLE: _("Room List"),
                VC.LIST_MESSAGE_TYPE: "showRoomMembers",
                VC.LIST_SECTION_DATA: [instance] if instance else self.get_order_group_rooms(self.get_order_group()),
                VC.LIST_TABLE_HEADERS: [_("Room Name"), _("Connected Users")],
                # GC.ACTION_JOIN_BUTTON: {"name": _("Join")},
                # GC.ACTION_SHOW_BUTTON: {"name": _("Manage"), "icon": "bi bi-gear-fill"},
                VC.LIST_SECTION_TEMPLATE: "orderRoom/bodySection/listSection.html",
            }
        )
        return ctx

    def get_details_context(self, instance=None):
        ctx = super().get_details_context()
        ctx.update(
            {
                VC.DETAILS_SECTION_TITLE: _("Room Members"),
                VC.DETAILS_SECTION_DATA: self.get_order_room_members(instance) if instance else None,
                VC.DETAILS_TABLE_HEADERS: [_("Name")],
                VC.DETAILS_SECTION_TEMPLATE: "base/bodySection/detailsSection.html",
                VC.DETAILS_SECTION_BODY_TEMPLATE: "base/bodySection/detailsSectionBody.html",
                VC.DETAILS_SECTION_TABLE_BODY_TEMPLATE: "orderRoom/bodySection/detailsSectionBodyTable.html",
            }
        )
        return ctx

    def get_form_context(self):
        ctx = super().get_form_context()
        ctx.update({VC.FORM_SECTION_TEMPLATE: "orderRoom/bottomSection/form/formGroupItem.html"})
        return ctx

    def get_order_group_rooms(self, group):
        return OrderRoom.objects.filter(fk_order_group=group).order_by("-id")

    def get_order_room_members(self, group):
        return UserModel.objects.filter(order_members=group)
