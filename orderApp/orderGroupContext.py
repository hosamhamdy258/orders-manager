from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from orderApp.context import BaseContext
from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import OrderGroup

UserModel = get_user_model()


class OrderGroupContext(BaseContext):
    view_type = CV.ORDER_GROUP

    def get_base_context(self):
        ctx = super().get_base_context()
        ctx.update(
            {VC.MAIN_TITLE: _("Groups"), VC.TITLE_ACTION: _("Refresh"), VC.TOP_SECTION_TEMPLATE: "orderGroup/topSection/titleAction.html"},
        )
        return ctx

    def get_list_context(self, instance=None):
        ctx = super().get_list_context()
        ctx.update(
            {
                VC.LIST_SECTION_TITLE: _("Groups List"),
                VC.LIST_MESSAGE_TYPE: "showGroupMembers",
                VC.LIST_OPEN_ACTION_MESSAGE_TYPE: "enterGroup",
                VC.LIST_OPEN_PIN_ACTION_MESSAGE_TYPE: "enterGroupPin",
                VC.LIST_INVITE_ACTION_MESSAGE_TYPE: "sendInvite",
                VC.LIST_SECTION_DATA: [instance] if instance else self.get_user_order_groups(self.get_user()),
                VC.LIST_TABLE_HEADERS: [_("Group"), _("Members")],
                GC.ACTION_JOIN_BUTTON: {"name": _("Open")},
                GC.ACTION_SHOW_BUTTON: {"name": _("Manage"), "icon": "bi bi-gear-fill"},
                GC.ACTION_INVITE_BUTTON: {"name": _("Invite"), "icon": "bi bi-envelope-plus"},
                VC.LIST_SECTION_TEMPLATE: "base/bodySection/listSection.html",
                VC.LIST_SECTION_BODY_TEMPLATE: "base/bodySection/listSectionBody.html",
                VC.LIST_SECTION_TABLE_BODY_TEMPLATE: "orderGroup/bodySection/listSectionBodyTable.html",
            }
        )
        return ctx

    def get_details_context(self, instance=None):
        ctx = super().get_details_context()
        ctx.update(
            {
                VC.DETAILS_SECTION_TITLE: _("Group Members"),
                VC.DETAILS_SECTION_DATA: self.get_order_group_members(instance) if instance else None,
                VC.DETAILS_TABLE_HEADERS: [_("Name")],
                VC.DETAILS_SECTION_TEMPLATE: "base/bodySection/detailsSection.html",
                VC.DETAILS_SECTION_BODY_TEMPLATE: "base/bodySection/detailsSectionBody.html",
                VC.DETAILS_SECTION_TABLE_BODY_TEMPLATE: "orderGroup/bodySection/detailsSectionBodyTable.html",
            }
        )
        return ctx

    def get_form_context(self):
        ctx = super().get_form_context()
        ctx.update({VC.FORM_SECTION_TEMPLATE: "orderGroup/bottomSection/form/formGroupItem.html"})
        return ctx

    def get_user_order_groups(self, user):
        return OrderGroup.objects.all().order_by("-id")  # ! for testing
        # return OrderGroup.objects.filter(Q(m2m_users=user) | Q(fk_owner=user)).order_by("-id").distinct() # TODO when invitation system ready

    def get_order_group_members(self, group):
        return UserModel.objects.filter(group_members=group)
