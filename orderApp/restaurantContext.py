from django.utils.translation import gettext_lazy as _

from orderApp.context import BaseContext
from orderApp.enums import CurrentViews as CV
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import MenuItem, Restaurant

# from orderApp.orderSelectionContext import get_restaurant_menu_items


class RestaurantContext(BaseContext):
    view_type = CV.RESTAURANT

    def get_base_context(self):
        ctx = super().get_base_context()
        ctx.update(
            {
                VC.MAIN_TITLE: _("Restaurants"),
                VC.TITLE_ACTION: _("Add Order"),
            }
        )
        return ctx

    def get_list_context(self, instance=None):
        ctx = super().get_list_context()
        ctx.update(
            {
                VC.LIST_SECTION_TITLE: _("Restaurant List"),
                VC.LIST_MESSAGE_TYPE: "showRestaurantItems",
                VC.LIST_SECTION_DATA: [instance] if instance else Restaurant.objects.all().order_by("-id"),
                VC.LIST_TABLE_HEADERS: [_("Restaurant Name")],
                VC.LIST_SECTION_TEMPLATE: "base/bodySection/listSection.html",
                VC.LIST_SECTION_BODY_TEMPLATE: "base/bodySection/listSectionBody.html",
                VC.LIST_SECTION_TABLE_BODY_TEMPLATE: "restaurant/bodySection/listSectionBodyTable.html",
            }
        )
        return ctx

    def get_details_context(self, instance=None, menu_item=None):
        ctx = super().get_details_context()
        ctx.update(
            {
                VC.DETAILS_SECTION_TITLE: _("Menu Items"),
                VC.DETAILS_MESSAGE_TYPE: "deleteMenuItem",
                VC.DETAILS_SECTION_DATA: MenuItem.get_restaurant_menu_items(restaurant=instance) if instance else [menu_item] if menu_item else None,
                VC.DETAILS_TABLE_HEADERS: [_("Item Name"), _("Price")],
                VC.DETAILS_CURRENT_SELECTION: Restaurant.objects.get(pk=instance) if instance else None,
                VC.DETAILS_SECTION_TEMPLATE: "base/bodySection/detailsSection.html",
                VC.DETAILS_SECTION_BODY_TEMPLATE: "base/bodySection/detailsSectionBody.html",
                VC.DETAILS_SECTION_TABLE_BODY_TEMPLATE: "restaurant/bodySection/detailsSectionBodyTable.html",
            }
        )
        return ctx

    def get_form_context(self):
        ctx = super().get_form_context()
        ctx.update(
            {
                VC.FORM_SECTION_TEMPLATE: "restaurant/bottomSection/form/formRestaurant.html",
                VC.EXTRA_FORM_SECTION_TEMPLATE: "restaurant/bottomSection/form/formMenuItem.html",
            }
        )
        return ctx
