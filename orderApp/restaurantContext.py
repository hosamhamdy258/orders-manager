from django.utils.translation import gettext as _

from orderApp.orderContext import get_restaurant_menu_items

from orderApp.context import get_current_view


from orderApp.enums import RestaurantContextKeys, ViewContextKeys, CurrentViews
from orderApp.models import Restaurant


def restaurant_context(view=CurrentViews.RESTAURANT_VIEW, restaurant=None):
    return {
        **get_current_view(view=view),
        ViewContextKeys.MAIN_TITLE: _("Restaurant Screen"),
        ViewContextKeys.TITLE_ACTION: _("Add Order"),
        ViewContextKeys.NEXT_VIEW: CurrentViews.ORDER_VIEW,
        # ==============
        **restaurant_list_section(),
        #
        **restaurant_details_section(restaurant),
        #
        RestaurantContextKeys.FORM_MENU_ITEM_DISABLE: True,
    }


def restaurant_details_section(restaurant, view=CurrentViews.RESTAURANT_VIEW, add_view=False):
    return {
        ViewContextKeys.DETAILS_SECTION_ID: "menu_items",
        ViewContextKeys.DETAILS_SECTION_TITLE: _("Menu Items"),
        ViewContextKeys.DETAILS_MESSAGE_TYPE: "deleteMenuItem",
        ViewContextKeys.DETAILS_SECTION_DATA: get_restaurant_menu_items(restaurant),
        ViewContextKeys.DETAILS_CURRENT_SELECTION: Restaurant.objects.get(pk=restaurant) if restaurant else None,
        **(get_current_view(view=view) if add_view else {}),
    }


def restaurant_list_section(view=CurrentViews.RESTAURANT_VIEW, add_view=False):
    return {
        ViewContextKeys.LIST_SECTION_ID: "restaurant_list",
        ViewContextKeys.LIST_SECTION_TITLE: _("Restaurant List"),
        ViewContextKeys.LIST_MESSAGE_TYPE: "showRestaurantItems",
        ViewContextKeys.LIST_SECTION_DATA: Restaurant.objects.all().order_by("-id"),
        **(get_current_view(view=view) if add_view else {}),
    }
