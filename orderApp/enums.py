from enum import EnumMeta


class GeneralContextKeys(EnumMeta):
    GROUP_NAME = "group_name"


class CurrentViews(EnumMeta):
    ORDER_VIEW = "order_view"
    RESTAURANT_VIEW = "restaurant_view"


class ViewContextKeys(EnumMeta):
    MAIN_TITLE = "main_title"
    TITLE_ACTION = "title_action"
    NEXT_VIEW = "next_view"
    CURRENT_VIEW = "current_view"

    LIST_SECTION_ID = "list_section_id"
    LIST_SECTION_TITLE = "list_section_title"
    LIST_SECTION_DATA = "list_section_data"
    LIST_MESSAGE_TYPE = "list_message_type"

    DETAILS_SECTION_ID = "details_section_id"
    DETAILS_SECTION_TITLE = "details_section_title"
    DETAILS_MESSAGE_TYPE = "details_message_type"
    DETAILS_SECTION_DATA = "details_section_data"


class OrderContextKeys(EnumMeta):
    RESTAURANTS = "restaurants"
    MENU_ITEMS = "menuItems"
    ORDER_ITEMS = "orderItems"
    ORDER = "order"
    FORM = "form"
    DISABLE_FORM = "disable_form"
    ALL_ORDERS = "all_orders"
