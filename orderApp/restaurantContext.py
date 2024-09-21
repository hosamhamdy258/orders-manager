from django.utils.translation import gettext as _

from orderApp.orderContext import get_restaurant_menu_items

from orderApp.context import get_current_view


from orderApp.enums import RestaurantContextKeys as RC, ViewContextKeys as VC, CurrentViews as CV
from orderApp.models import Restaurant


def restaurant_context(view=CV.RESTAURANT_VIEW, restaurant=None):
    return {
        **get_current_view(view=view),
        VC.MAIN_TITLE: _("Restaurant Screen"),
        VC.TITLE_ACTION: _("Add Order"),
        VC.NEXT_VIEW: CV.ORDER_VIEW,
        # ==============
        **restaurant_list_section(),
        #
        **restaurant_details_section(restaurant),
        #
        RC.FORM_MENU_ITEM_DISABLE: True,
    }


def restaurant_details_section(restaurant, view=CV.RESTAURANT_VIEW, add_view=False):
    return {
        VC.DETAILS_SECTION_ID: "menu_items",
        VC.DETAILS_SECTION_TITLE: _("Menu Items"),
        VC.DETAILS_MESSAGE_TYPE: "deleteMenuItem",
        VC.DETAILS_SECTION_DATA: get_restaurant_menu_items(restaurant),
        VC.DETAILS_CURRENT_SELECTION: Restaurant.objects.get(pk=restaurant) if restaurant else None,
        **(get_current_view(view=view) if add_view else {}),
    }


def restaurant_list_section(view=CV.RESTAURANT_VIEW, add_view=False):
    return {
        VC.LIST_SECTION_ID: "restaurant_list",
        VC.LIST_SECTION_TITLE: _("Restaurant List"),
        VC.LIST_MESSAGE_TYPE: "showRestaurantItems",
        VC.LIST_SECTION_DATA: Restaurant.objects.all().order_by("-id"),
        **(get_current_view(view=view) if add_view else {}),
    }
