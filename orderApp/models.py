from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.db.models import Sum, F

from orderApp.utils import PositiveValueValidator

UserModel = get_user_model()
# to be as == connected to channel
minium_accepting_users = 2


class Client(models.Model):
    channel_name = models.CharField(_("channel name"), max_length=50)


class Group(models.Model):
    name = models.CharField(_("group name"), max_length=50)
    m2m_users = models.ManyToManyField(UserModel, verbose_name=_("Users"), blank=True)
    accepted_order_users = models.ManyToManyField(UserModel, related_name="accepted_order_users", verbose_name=_("Accepted Order Users"), blank=True)
    completed = models.BooleanField(_("completed"), default=False)

    def __str__(self):
        keys = [self.name, len(self.m2m_users.all())]
        return " / ".join(list(map(str, keys)))

    def add_user_to_accepted_order_users(self, user):
        self.accepted_order_users.add(user)

    def is_order_completed(self, user):
        # ! user must be in order do complete it
        # ! empty order issue
        # ! check for unfinished from connected users
        # ! timer to finish unfinished orders to don't lock orders
        data = self.order_set.filter(finished_ordering=False).values_list("fk_user__username", flat=True)

        if data.exists():
            members = ", ".join(data)
            error_msg = _(f"Some Members Didn't Finish Ordering Yet:\n{members}")
            return False, error_msg

        self.add_user_to_accepted_order_users(user)

        if self.accepted_order_users.count() >= minium_accepting_users:
            self.completed = True
            self.save()
            return True, ""
        else:
            return False, ""


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
    fk_group = models.ForeignKey(Group, verbose_name=_("Group"), on_delete=models.CASCADE)
    created = models.DateTimeField(_("Created"), auto_now_add=True)
    finished_ordering = models.BooleanField(_("finished ordering"), default=False)

    def __str__(self):
        keys = [self.fk_user.username, self.total_order()]
        return " / ".join(list(map(str, keys)))

    def total_order(self):
        return self.orderitem_set.aggregate(total=Sum(F("quantity") * F("fk_menu_item__price"), output_field=models.DecimalField()))["total"]


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
