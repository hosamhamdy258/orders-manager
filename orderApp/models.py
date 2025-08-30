import math
import time
from datetime import timedelta

from channels_presence.models import Room
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.db.models.constraints import UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import configuration, join_retry_limit
from orderApp.enums import ORDER_SELECTION_CHANNEL_GROUP
from orderApp.utils import PositiveValueValidator

SMALL_NAME_LENGTH = 50

UserModel = get_user_model()


def generate_group_number():
    return time.time_ns()


def generate_str(keys):
    return " | ".join(list(map(str, keys)))


class Client(models.Model):
    channel_name = models.CharField(_("channel name"), max_length=SMALL_NAME_LENGTH)


class Invitation(models.Model):
    pass


class JoinRequest(models.Model):
    pass


class OrderGroup(models.Model):
    name = models.CharField(_("Group Name"), max_length=SMALL_NAME_LENGTH)
    m2m_users = models.ManyToManyField(UserModel, verbose_name=_("Group Members"), blank=True, related_name="group_members")
    fk_owner = models.ForeignKey(UserModel, on_delete=models.CASCADE, verbose_name=_("Group Owner"))
    group_number = models.CharField(_("Group Number"), max_length=SMALL_NAME_LENGTH, default=generate_group_number)  # ! add default value
    pin = models.PositiveSmallIntegerField(_("PIN"), default=0000, validators=[MaxValueValidator(9999)])  # ! hash the value

    def __str__(self):
        keys = [self.name, self.get_group_members_count()]
        return generate_str(keys=keys)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["name", "fk_owner"], name="unique_name_fk_owner"),
        ]

    def get_group_members_count(self):
        return len(self.m2m_users.all())

    def add_user_to_group(self, user):
        return self.m2m_users.add(user)

    def remove_user_from_group(self, user):
        return self.m2m_users.remove(user)

    def can_join_group(self, user):
        return self.__class__.objects.filter(Q(m2m_users=user) | Q(fk_owner=user), pk=self.pk).exists()


class GroupRetries(models.Model):
    retry = models.PositiveSmallIntegerField(_("Retry"), default=join_retry_limit)
    fk_user = models.ForeignKey(UserModel, verbose_name=_("User"), on_delete=models.CASCADE)
    fk_order_group = models.ForeignKey(OrderGroup, verbose_name=_("Group"), on_delete=models.CASCADE)
    lock_time = models.DateTimeField(_("Lock Time"), blank=True, null=True)

    def __str__(self):
        keys = [self.fk_user, self.fk_order_group, self.retry, self.lock_time]
        return generate_str(keys=keys)

    def failed_retry(self):
        self.__class__.objects.filter(pk=self.pk).update(retry=models.F("retry") - 1)
        self.refresh_from_db(fields=["retry"])

    def can_retry(self):
        self.refresh_from_db(fields=["retry"])
        self.get_lock_time_left()
        retry = self.retry > 0
        self.create_lock_timer(retry)
        return retry

    def create_lock_timer(self, retry):
        if not retry and self.lock_time is None:
            self.lock_time = timezone.now()
            self.save()

    def get_lock_time_left(self):
        if self.lock_time:
            end_time = self.lock_time + timedelta(minutes=configuration().lock_time_limit)
            current_time = timezone.now()
            time_diff = end_time - current_time
            remaining_time = int(time_diff.total_seconds())
            self.refresh_retries(remaining_time)
            return math.ceil(remaining_time / 60)
        return 0

    def refresh_retries(self, remaining_time):
        if remaining_time <= 0:
            self.lock_time = None
            self.retry = configuration().join_retry_limit
            self.save()


class OrderRoom(models.Model):
    name = models.CharField(_("Room Name"), max_length=SMALL_NAME_LENGTH)
    m2m_users = models.ManyToManyField(UserModel, verbose_name=_("Order Members"), blank=True, related_name="order_members")
    room_number = models.CharField(_("Room Number"), max_length=SMALL_NAME_LENGTH, default=generate_group_number)  # ! add default value
    fk_order_group = models.ForeignKey(OrderGroup, verbose_name=_("Group"), on_delete=models.CASCADE)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["name", "fk_order_group"], name="unique_name_room_name"),
        ]

    def __str__(self):
        keys = [self.name, self.connected_users()]
        return generate_str(keys=keys)

    def connected_users(self):
        try:
            count = Room.objects.get(channel_name=f"{ORDER_SELECTION_CHANNEL_GROUP}{self.pk}").get_users().count()
        except ObjectDoesNotExist:
            count = 0
        return count

    # ! removed in favorite of django-channel-presence
    # def connected_users(self):
    #     return len(self.m2m_users.all())

    def is_member(self, user):
        return self.fk_order_group.objects.filter(Q(m2m_users=user) | Q(fk_owner=user)).exists()

    def add_user_to_room(self, user):
        OrderRoomUser.objects.get_or_create(fk_user=user, fk_order_room=self)
        return self.m2m_users.add(user)

    def remove_user_from_room(self, user):
        return self.m2m_users.remove(user)


class OrderRoomUser(models.Model):
    fk_user = models.ForeignKey(UserModel, verbose_name=_("Users"), on_delete=models.CASCADE)
    fk_order_room = models.ForeignKey(OrderRoom, verbose_name=_("Room"), on_delete=models.CASCADE)
    joined = models.DateTimeField(_("Created"), default=timezone.now)

    def __str__(self):
        keys = [self.fk_user, self.fk_order_room]
        return generate_str(keys=keys)

    def get_time_left(self):
        end_time = self.joined + timedelta(minutes=configuration().order_time_limit)
        current_time = timezone.now()
        remaining_time = end_time - current_time
        return int(remaining_time.total_seconds())

    @classmethod
    def check_ordering_timeout(cls, user, order_room):
        time_left = cls.objects.get(fk_user=user, fk_order_room=order_room).get_time_left()
        return {"disabled": time_left <= 0, "reason": "time_out", "time_left": time_left}


class Restaurant(models.Model):
    name = models.CharField(_("Restaurant Name"), max_length=SMALL_NAME_LENGTH, unique=True)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    # TODO add soft delete active=False
    fk_restaurant = models.ForeignKey(Restaurant, verbose_name=_("Restaurant"), on_delete=models.CASCADE)
    name = models.CharField(_("Menu Item"), max_length=SMALL_NAME_LENGTH, default="")
    price = models.DecimalField(_("Price"), max_digits=9, decimal_places=2, validators=[PositiveValueValidator(0)])

    class Meta:
        constraints = [
            UniqueConstraint(fields=["fk_restaurant", "name"], name="unique_restaurant_item_name"),
        ]

    def __str__(self):
        keys = [self.fk_restaurant, self.name]
        return " | ".join(list(map(str, keys)))

    @classmethod
    def get_restaurant_menu_items(cls, restaurant):
        return cls.objects.filter(fk_restaurant=restaurant).order_by("-id")


class CustomOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(order_archived=True)


def archive_time():
    return timezone.now() + timedelta(hours=configuration().order_archive_delay)


class Order(models.Model):
    fk_user = models.ForeignKey(UserModel, verbose_name=_("User"), on_delete=models.CASCADE)
    fk_order_room = models.ForeignKey(OrderRoom, verbose_name=_("Room"), on_delete=models.CASCADE)
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
        return round(self.orderitem_set.aggregate(total=Sum(F("quantity") * F("fk_menu_item__price"), output_field=models.DecimalField(max_digits=9, decimal_places=2)))["total"], 2)

    @classmethod
    def check_order_limit_per_room(cls, user, order_room):
        disabled = cls.objects.filter(fk_user=user, fk_order_room=order_room, finished_ordering=True).count() >= configuration().order_limit
        return {"disabled": disabled, "reason": "order_limit"}


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
