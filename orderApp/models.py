from datetime import datetime, timedelta, timezone
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import F, Sum
from django.utils.translation import gettext_lazy as _

from orderApp.utils import PositiveValueValidator

UserModel = get_user_model()


class Client(models.Model):
    channel_name = models.CharField(_("channel name"), max_length=50)


class Group(models.Model):
    name = models.CharField(_("Group Name"), max_length=50, unique=True)
    m2m_users = models.ManyToManyField(UserModel, verbose_name=_("Users"), blank=True)
    room_number = models.CharField(_("Room Number"), max_length=50)

    def __str__(self):
        keys = [self.name, self.connected_users()]
        return " | ".join(list(map(str, keys)))

    def connected_users(self):
        return len(self.m2m_users.all())


class GroupUser(models.Model):
    fk_user = models.ForeignKey(UserModel, verbose_name=_("Users"), on_delete=models.CASCADE)
    fk_group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.CASCADE)
    joined = models.DateTimeField(_("Created"), auto_now_add=True)

    def get_time_left(self):
        end_time = self.joined + timedelta(minutes=15)
        current_time = datetime.now(timezone.utc)
        remaining_time = end_time - current_time
        return int(remaining_time.total_seconds())


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
        return " | ".join(list(map(str, keys)))


class Order(models.Model):
    fk_user = models.ForeignKey(UserModel, verbose_name=_("User"), on_delete=models.CASCADE)
    fk_group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.CASCADE)
    created = models.DateTimeField(_("Created"), auto_now_add=True)
    finished_ordering = models.BooleanField(_("finished ordering"), default=False)

    def __str__(self):
        keys = [self.order_user(), self.total_order()]
        return " | ".join(list(map(str, keys)))

    def order_user(self):
        return self.fk_user.username

    def total_order(self):
        return self.orderitem_set.aggregate(total=Sum(F("quantity") * F("fk_menu_item__price"), output_field=models.DecimalField()))["total"]


class OrderItem(models.Model):
    fk_order = models.ForeignKey(Order, verbose_name=_("Order"), on_delete=models.CASCADE)
    fk_menu_item = models.ForeignKey(MenuItem, verbose_name=_("Menu Item"), on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_("Quantity"), validators=[PositiveValueValidator(0)])

    def __str__(self):
        keys = [self.fk_order, self.fk_menu_item, self.quantity, self.total_order_item()]
        return " | ".join(list(map(str, keys)))

    def total_order_item(self):
        if self.fk_menu_item.price and self.quantity:
            return self.fk_menu_item.price * self.quantity
        return 0
