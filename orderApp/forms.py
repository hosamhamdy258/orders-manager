from django.forms import ModelChoiceField, ModelForm
from django.utils.translation import gettext_lazy as _

from .models import MenuItem, Order, OrderGroup, OrderItem, OrderRoom, Restaurant


class OrderItemForm(ModelForm):
    fk_restaurant = ModelChoiceField(Restaurant.objects.all(), required=True)

    class Meta:
        model = OrderItem
        fields = ["fk_order", "fk_menu_item", "quantity"]


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = ["fk_user"]


class MenuItemForm(ModelForm):
    class Meta:
        model = MenuItem
        fields = ["fk_restaurant", "name", "price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fk_restaurant"].error_messages = {"required": _("Select Restaurant From List Above To Add Menu Item")}


class RestaurantForm(ModelForm):
    class Meta:
        model = Restaurant
        fields = ["name"]


class OrderRoomForm(ModelForm):
    class Meta:
        model = OrderRoom
        fields = ["name", "room_number"]


class OrderGroupForm(ModelForm):
    class Meta:
        model = OrderGroup
        fields = ["name", "group_number", "fk_owner"]
