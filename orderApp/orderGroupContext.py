from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from orderApp.commonContext import NAVIGATION_BUTTONS
from orderApp.context import BaseContext, get_current_view
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
            {
                VC.MAIN_TITLE: _("Groups"),
                VC.TITLE_ACTION: _("Refresh"),
            }
        )
        return ctx

    def get_list_context(self, instance=None):
        return {
            **self.current_view(),
            VC.LIST_SECTION_ID: "group_list",
            VC.LIST_TABLE_BODY_ID: "group_table_body",
            VC.LIST_SECTION_TITLE: _("Groups List"),
            VC.LIST_MESSAGE_TYPE: "showGroupMembers",
            VC.LIST_SECTION_DATA: [instance] if instance else self.get_user_order_groups(self.get_user()),
            VC.LIST_TABLE_HEADERS: [_("Group"), _("Members")],
            GC.ACTION_JOIN_BUTTON: {"name": _("Open")},
            GC.ACTION_SHOW_BUTTON: {"name": _("Manage"), "icon": "bi bi-gear-fill"},
        }

    def get_details_context(self, instance=None):
        return {
            **self.current_view(),
            VC.DETAILS_SECTION_ID: "group_members",
            VC.DETAILS_SECTION_TITLE: _("Group Members"),
            VC.DETAILS_SECTION_DATA: self.get_order_group_members(instance) if instance else None,
        }

    def get_user_order_groups(self, user):
        return OrderGroup.objects.all()  # ! for testing
        # return OrderGroup.objects.filter(Q(m2m_users=user) | Q(fk_owner=user)).order_by("-id").distinct()

    def get_order_group_members(self, group):
        return UserModel.objects.filter(group_members=group)
