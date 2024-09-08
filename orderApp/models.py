from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.db.models import Sum, F

from orderApp.utils import PositiveValueValidator

UserModel = get_user_model()


class Restaurant(models.Model):
    name = models.CharField(_("Name"), max_length=50, unique=True)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    fk_restaurant = models.ForeignKey(Restaurant, verbose_name=_("Restaurant"), on_delete=models.CASCADE)
    menu_item = models.CharField(_("Menu Item"), max_length=50)
    price = models.DecimalField(_("Price"), max_digits=9, decimal_places=2, validators=[PositiveValueValidator(0)])

    def __str__(self):
        keys = [self.fk_restaurant, self.menu_item]
        return " / ".join(list(map(str, keys)))


class Order(models.Model):
    fk_user = models.ForeignKey(UserModel, verbose_name=_("User"), on_delete=models.CASCADE)
    created = models.DateTimeField(_("Created"), auto_now_add=True)
    completed = models.BooleanField(_("completed"), default=False)
    finished_ordering = models.BooleanField(_("finished ordering"), default=False)

    def __str__(self):
        keys = [self.fk_user.username, self.created.date()]
        return " / ".join(list(map(str, keys)))

    def total_order(self):
        return self.orderitem_set.aggregate(total=Sum(F("quantity") * F("price"), output_field=models.DecimalField()))


class OrderItem(models.Model):
    fk_order = models.ForeignKey(Order, verbose_name=_("Order"), on_delete=models.CASCADE)
    fk_menu_item = models.ForeignKey(MenuItem, verbose_name=_("Menu Item"), on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_("Quantity"), validators=[PositiveValueValidator(0)])

    def __str__(self):
        keys = [self.fk_order, self.fk_menu_item, self.quantity, self.total_order_item()]
        return " / ".join(list(map(str, keys)))

    def total_order_item(self):
        if self.fk_menu_item.price and self.quantity:
            return self.fk_menu_item.price * self.quantity
        return 0


class Clients(models.Model):
    channel_name = models.CharField(_("channel name"), max_length=50)
