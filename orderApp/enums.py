from enum import EnumMeta

from django.utils.translation import gettext_lazy as _


class GeneralContextKeys(EnumMeta):
    GROUP_NAME = "group_name"
    WS_URL = "ws_url"


class CurrentViews(EnumMeta):
    ORDER_VIEW = "order_view"
    RESTAURANT_VIEW = "restaurant_view"
    GROUP_VIEW = "group_view"


class ViewContextKeys(EnumMeta):
    MAIN_TITLE = "main_title"
    TITLE_ACTION = "title_action"
    NEXT_VIEW = "next_view"
    CURRENT_VIEW = "current_view"

    LIST_SECTION_ID = "list_section_id"
    LIST_SECTION_TITLE = "list_section_title"
    LIST_SECTION_DATA = "list_section_data"
    LIST_MESSAGE_TYPE = "list_message_type"
    LIST_TABLE_HEADERS = "list_table_headers"

    DETAILS_SECTION_ID = "details_section_id"
    DETAILS_SECTION_TITLE = "details_section_title"
    DETAILS_MESSAGE_TYPE = "details_message_type"
    DETAILS_SECTION_DATA = "details_section_data"
    DETAILS_CURRENT_SELECTION = "details_current_selection"
    DETAILS_TABLE_HEADERS = "details_table_headers"


class OrderContextKeys(EnumMeta):
    ORDER = "order"
    RESTAURANTS = "restaurants"
    MENU_ITEMS = "menuItems"
    DISABLE_ORDER_ITEM_FORM = "disable_order_item_form"
    DISABLE_FINISH_BUTTON = "disable_finish_button"
    DISABLE_COMPLETE_BUTTON = "disable_complete_button"
    DISABLE_REMOVE_BUTTON = "disable_remove_button"
    FORM_ORDER_ID = "form_order_id"
    FINISH_ORDER_ID = "finish_order_id"

    ALL_ORDERS = "all_orders"
    ALL_ORDERS_BUTTON = "all_orders_button"

    TIME_LEFT = "time_left"


class RestaurantContextKeys(EnumMeta):
    FORM_MENU_ITEM_DISABLE = "form_menu_item_disable"


class ErrorMessage(EnumMeta):
    CREATE_ORDER = {"create_order_error": _("Reached Max Orders Per Group")}
    FINISH_ORDER = {"finish_order_error": _("Add Order Items")}
    ORDER_SUMMARY = {"order_summary_error": _("There's No Orders Created Yet")}
    TIME_UP = {"time_up_error": _("The time to complete the order has expired.")}
