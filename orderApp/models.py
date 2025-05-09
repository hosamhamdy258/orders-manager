from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import F, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import configuration
from orderApp.utils import PositiveValueValidator

SMALL_NAME_LENGTH = 50

UserModel = get_user_model()


class Client(models.Model):
    channel_name = models.CharField(_("channel name"), max_length=SMALL_NAME_LENGTH)


class Invitation(models.Model):
    pass


class JoinRequest(models.Model):
    pass


class OrderGroup(models.Model):
    name = models.CharField(_("Group Name"), max_length=SMALL_NAME_LENGTH, unique=True)
    m2m_users = models.ManyToManyField(UserModel, verbose_name=_("Group Members"), blank=True, related_name="group_members")
    fk_owner = models.ForeignKey(UserModel, on_delete=models.CASCADE, verbose_name=_("Group Owner"))


class OrderRoom(models.Model):
    name = models.CharField(_("Group Name"), max_length=SMALL_NAME_LENGTH, unique=True)
    m2m_users = models.ManyToManyField(UserModel, verbose_name=_("Order Members"), blank=True, related_name="order_members")
    room_number = models.CharField(_("Room Number"), max_length=SMALL_NAME_LENGTH)
    fk_order_group = models.ForeignKey(OrderGroup, verbose_name=_("Group"), on_delete=models.CASCADE)

    def __str__(self):
        keys = [self.name, self.connected_users()]
        return " | ".join(list(map(str, keys)))

    def connected_users(self):
        return len(self.m2m_users.all())


class OrderRoomUser(models.Model):
    fk_user = models.ForeignKey(UserModel, verbose_name=_("Users"), on_delete=models.CASCADE)
    fk_order_room = models.ForeignKey(OrderRoom, verbose_name=_("Room"), on_delete=models.CASCADE)
    joined = models.DateTimeField(_("Created"), default=timezone.now)

    def get_time_left(self):
        end_time = self.joined + timedelta(minutes=configuration().order_time_limit)
        current_time = timezone.now()
        remaining_time = end_time - current_time
        return int(remaining_time.total_seconds())


class Restaurant(models.Model):
    name = models.CharField(_("Restaurant Name"), max_length=SMALL_NAME_LENGTH, unique=True)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    fk_restaurant = models.ForeignKey(Restaurant, verbose_name=_("Restaurant"), on_delete=models.CASCADE)
    name = models.CharField(_("Menu Item"), max_length=SMALL_NAME_LENGTH)
    price = models.DecimalField(_("Price"), max_digits=9, decimal_places=2, validators=[PositiveValueValidator(0)])

    def __str__(self):
        keys = [self.fk_restaurant, self.name]
        return " | ".join(list(map(str, keys)))


class CustomOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(order_archived=True)


def archive_time():
    return timezone.now() + timedelta(hours=configuration().order_archive_delay)


class Order(models.Model):
    fk_user = models.ForeignKey(UserModel, verbose_name=_("User"), on_delete=models.CASCADE)
    fk_group = models.ForeignKey(OrderRoom, verbose_name=_("Group"), on_delete=models.CASCADE)
    created = models.DateTimeField(_("Created"), default=timezone.now)
    finished_ordering = models.BooleanField(_("Finished Ordering"), default=False)
    delete_timer = models.DateTimeField(_("Created"), default=archive_time)
    order_archived = models.BooleanField(_("Is Done ?"), default=False)
    objects = CustomOrderManager()

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
