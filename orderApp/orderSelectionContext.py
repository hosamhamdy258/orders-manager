from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import configuration
from orderApp.context import BaseContext, get_current_view
from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.enums import OrderContextKeys as OC
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import MenuItem, Order, OrderItem, OrderRoomUser, Restaurant


class OrderSelectionContext(BaseContext):
    view_type = CV.ORDER_SELECTION
    room_user = None
    restaurant = None

    def __init__(self, user, order_group, order_room):
        super().__init__(user)
        self.order_group = order_group
        self.order_room = order_room
        self.get_room_user()

    def get_order_room(self):
        if self.order_room is None:
            raise NotImplementedError("Subclasses must define order_room or implement get_order_room()")
        return self.order_room

    def get_room_user(self):
        if self.room_user is None:
            self.room_user = OrderRoomUser.objects.get(fk_order_room=self.get_order_room(), fk_user=self.get_user())
        return self.room_user

    def get_restaurant(self):
        if self.restaurant is None:
            raise KeyError("Did you forget to pass restaurant value to class")
        return self.restaurant

    def get_base_context(self):
        ctx = super().get_base_context()
        ctx.update(
            {
                VC.MAIN_TITLE: _("Orders"),
                VC.TITLE_ACTION: _("Add Restaurant"),
                GC.ROOM_NUMBER: self.get_order_room().name,
                OC.TIME_LEFT: self.get_room_user().get_time_left(),
            }
        )
        return ctx

    def get_list_context(self, instance=None, all_orders=True):
        ctx = super().get_list_context()
        ctx.update(
            {
                VC.LIST_SECTION_ID: "members_orders",
                VC.LIST_TABLE_ID: "group_table_id",
                VC.LIST_TABLE_BODY_ID: "group_table_body",
                VC.LIST_SECTION_TITLE: _("Members Orders"),
                VC.LIST_MESSAGE_TYPE: "showMemberItemOrders",
                VC.LIST_SECTION_DATA: (
                    [instance]
                    if instance
                    else (
                        self.get_all_orders(user=self.get_user(), order_room=self.get_order_room())
                        if not all_orders
                        else self.get_all_orders(order_room=self.get_order_room())
                    )
                ),
                VC.LIST_TABLE_HEADERS: [_("User"), _("Total")],
            }
        )
        return ctx

    def get_details_context(self, instance=None, order_instance=None, disable_remove_button=False):
        ctx = super().get_details_context()
        ctx.update(
            {
                VC.DETAILS_SECTION_ID: "order_items",
                VC.DETAILS_TABLE_BODY_ID: "details_table_body",
                VC.DETAILS_SECTION_TITLE: _("Order Items"),
                VC.DETAILS_MESSAGE_TYPE: "deleteOrderItem",
                OC.DISABLE_REMOVE_BUTTON: disable_remove_button,
                VC.DETAILS_SECTION_DATA: (
                    [instance] if instance else self.get_last_order_items() if not order_instance else self.get_order_items(order_instance)
                ),
                VC.DETAILS_TABLE_HEADERS: [_("Item"), _("Quantity"), _("Price"), _("Total")],
            }
        )
        return ctx

    def get_form_context(self, restaurant_instance=None):
        ctx = super().get_form_context()

        disable = any(
            [
                self.check_ordering_timeout()["disabled"],
                self.check_order_limit_per_room()["disabled"],
            ]
        )
        order = None
        if not disable:
            order = get_last_order(user=self.get_user(), order_room=self.get_order_room())
        ctx.update(
            {
                OC.RESTAURANTS: self.get_restaurant_list(),
                OC.MENU_ITEMS: MenuItem.get_restaurant_menu_items(restaurant=restaurant_instance) if restaurant_instance else [],
                OC.DISABLE_ORDER_ITEM_FORM: disable,
                OC.ORDER: order,
                OC.FORM_ORDER_ID: OC.FORM_ORDER_ID,
            }
        )
        return ctx

    def get_all_orders(self, user=None, order_room=None):
        filter_kwargs = {"finished_ordering": True}
        if user:
            filter_kwargs.update({"fk_user": user})
        if order_room:
            filter_kwargs.update({"fk_order_room": order_room})
        orders = orders_query().filter(**filter_kwargs)
        return orders

    def get_extra_context(self, all_orders=True):
        ctx = super().get_extra_context()
        ctx.update(
            {
                **({} if all_orders else {OC.ALL_ORDERS: OC.ALL_ORDERS}),
                **({OC.ALL_ORDERS_BUTTON: _("My Orders")} if all_orders else {OC.ALL_ORDERS_BUTTON: _("All Orders")}),
            }
        )
        return ctx

    def check_order_limit_per_room(self):
        return Order.check_order_limit_per_room(user=self.get_user(), order_room=self.get_order_room())

    def check_ordering_timeout(self):
        return OrderRoomUser.check_ordering_timeout(user=self.get_user(), order_room=self.get_order_room())

    def get_last_order_items(self):
        order = get_last_order(user=self.get_user(), order_room=self.get_order_room())
        items = self.get_order_items(instance=order)
        return items

    def get_order_items(self, instance):
        orderItems = OrderItem.objects.filter(fk_order=instance)
        return orderItems

    def get_restaurant_list(self):
        return Restaurant.objects.all()


def orders_query():
    # TODO check this date condition is it valid for orders around midnight
    return Order.objects.filter(created__date=timezone.now())


def get_last_order(user, order_room, finished=False):
    return orders_query().filter(fk_user=user, fk_order_room=order_room, finished_ordering=finished).last()


def finish_order(order):
    error_msg = {"finished": False, "reason": "add_items"}
    if not order:
        return error_msg

    order = Order.objects.get(id=order)
    orderItems = OrderItem.objects.filter(fk_order=order).exists()

    if orderItems:
        order.finished_ordering = True
        order.save()
        return {"finished": True}
    else:
        return error_msg


def get_order(user, order_room):
    check = create_order_checks(user, order_room)
    if check["disabled"]:
        return check
    # * get last unfinished order or create new one
    order = Order.objects.get_or_create(fk_user=user, fk_order_room=order_room, finished_ordering=False)[0]
    return {"order": order, "created": True}


def create_order_checks(user, order_room):
    check = Order.check_order_limit_per_room(user=user, order_room=order_room)
    if check["disabled"]:
        return check
    check = OrderRoomUser.check_ordering_timeout(user=user, order_room=order_room)
    if check["disabled"]:
        return check
    check = {"disabled": False}
    return check
