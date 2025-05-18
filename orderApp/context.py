from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from orderApp.commonContext import NAVIGATION_BUTTONS
from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.enums import ViewContextKeys as VC

UserModel = get_user_model()


def get_current_view(view):
    match view:
        case CV.ORDER_SELECTION:
            return {VC.CURRENT: CV.ORDER_SELECTION}
        case CV.RESTAURANT:
            return {VC.CURRENT: CV.RESTAURANT}
        case CV.ORDER_ROOM:
            return {VC.CURRENT: CV.ORDER_ROOM}
        case CV.ORDER_GROUP:
            return {VC.CURRENT: CV.ORDER_GROUP}
        case __:
            raise NotImplementedError(f"Unknown view: {view}")


class BaseContext:
    view_type = None
    group = None
    base_required_keys = [VC.MAIN_TITLE, VC.TITLE_ACTION]
    list_required_keys = [
        VC.LIST_SECTION_ID,
        VC.LIST_TABLE_BODY_ID,
        VC.LIST_SECTION_TITLE,
        VC.LIST_SECTION_DATA,
        VC.LIST_TABLE_HEADERS,
    ]
    details_required_keys = [VC.DETAILS_SECTION_ID, VC.DETAILS_SECTION_TITLE, VC.DETAILS_SECTION_DATA]

    def __init__(self, user):
        self.user = user

    def get_user(self):
        if self.user is None:
            raise NotImplementedError("Subclasses must define user or implement get_user()")
        return self.user

    def get_view_type(self):
        if self.view_type is None:
            raise NotImplementedError("Subclasses must define view_type or implement get_view_type()")
        return self.view_type

    def get_full_context(self):
        ctx = {
            **self.get_base_context(),
            **self.get_list_context(),
            **self.get_details_context(),
        }
        self.validate_keys(self.base_required_keys, ctx)
        self.validate_keys(self.list_required_keys, ctx)
        self.validate_keys(self.details_required_keys, ctx)

        return ctx

    def current_view(self):
        return {VC.CURRENT: self.get_view_type()}

    def get_base_context(self):
        return {GC.NAVIGATION_BUTTONS: NAVIGATION_BUTTONS, **self.current_view()}

    def get_list_context(self, instance=None):
        return dict()

    def get_details_context(self, instance=None):
        return dict()

    def validate_keys(self, keys_list, ctx):
        missing_list = [k for k in keys_list if k not in ctx]
        if missing_list:
            raise KeyError(f"Missing required list context keys: {missing_list}")
