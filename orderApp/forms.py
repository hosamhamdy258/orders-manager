from django.forms import ModelForm, ModelChoiceField
from .models import OrderItem, Order, MenuItem, Restaurant


class OrderItemForm(ModelForm):
    fk_restaurant = ModelChoiceField(Restaurant.objects.all(), required=True)

    class Meta:
        model = OrderItem
        fields = ["fk_order", "fk_menu_item", "quantity"]

    def save(self, commit):
        return super().save(commit)


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = ["fk_user"]


class MenuItemForm(ModelForm):
    class Meta:
        model = MenuItem
        fields = ["fk_restaurant", "menu_item", "price"]
