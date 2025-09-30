from django.contrib.auth import get_user_model
from django.db.models import DecimalField, F, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from orderApp.context import BaseContext
from orderApp.enums import CurrentViews as CV
from orderApp.enums import ErrorMessage as EM
from orderApp.enums import GeneralContextKeys as GC
from orderApp.enums import OrderContextKeys as OC
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import MenuItem, Order, OrderItem, OrderRoomUser, Restaurant
from orderApp.utils import calculate_totals, group_nested_data, spacial_rounder

UserModel = get_user_model()


class OrderSelectionContext(BaseContext):
    view_type = CV.ORDER_SELECTION
    room_user = None
    restaurant = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
                VC.TOP_SECTION_INFO: "orderSelection/topSection/middleTitle.html",
            }
        )
        return ctx

    def get_list_context(self, instance=None, all_orders=True):
        ctx = super().get_list_context()

        if instance:
            LIST_SECTION_DATA = [instance]
        elif all_orders:
            LIST_SECTION_DATA = self.get_all_orders(order_room=self.get_order_room())
        else:
            LIST_SECTION_DATA = self.get_all_orders(user=self.get_user(), order_room=self.get_order_room())

        ctx.update(
            {
                VC.LIST_TABLE_BODY_ID: "group_table_body",
                VC.LIST_SECTION_TITLE: _("Members Orders"),
                VC.LIST_MESSAGE_TYPE: "showMemberItemOrders",
                VC.LIST_SECTION_DATA: LIST_SECTION_DATA,
                VC.LIST_TABLE_HEADERS: [_("User"), _("Total")],
                VC.LIST_SECTION_TEMPLATE: "base/bodySection/listSection.html",
                VC.LIST_SECTION_BODY_TEMPLATE: "base/bodySection/listSectionBody.html",
                VC.LIST_SECTION_TABLE_BODY_TEMPLATE: "orderSelection/bodySection/listSectionBodyTable.html",
            }
        )
        return ctx

    def get_details_context(self, instance=None, order_instance=None, disable_remove_button=False):
        ctx = super().get_details_context()
        ctx.update(
            {
                VC.DETAILS_SECTION_TITLE: _("Order Items"),
                VC.DETAILS_MESSAGE_TYPE: "deleteOrderItem",
                OC.DISABLE_REMOVE_BUTTON: disable_remove_button,
                VC.DETAILS_SECTION_DATA: ([instance] if instance else self.get_last_order_items() if not order_instance else self.get_order_items(order_instance)),
                VC.DETAILS_TABLE_HEADERS: [_("Item"), _("Restaurant"), _("Quantity"), _("Price"), _("Total")],
                VC.DETAILS_SECTION_TEMPLATE: "base/bodySection/detailsSection.html",
                VC.DETAILS_SECTION_BODY_TEMPLATE: "base/bodySection/detailsSectionBody.html",
                VC.DETAILS_SECTION_TABLE_BODY_TEMPLATE: "orderSelection/bodySection/detailsSectionBodyTable.html",
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
                VC.FORM_SECTION_TEMPLATE: "orderSelection/bottomSection/form/formOrderItem.html",
                VC.EXTRA_FORM_SECTION_TEMPLATE: "orderSelection/bottomSection/actions/orderActions.html",
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

    def groupOrderSummary(self):
        orderTotalSummary = (
            Restaurant.objects.filter(menuitem__orderitem__fk_order__created_at__date=timezone.now(), menuitem__orderitem__fk_order__fk_order_room=self.get_order_room())
            .values(
                restaurant=F("name"),
                item=F("menuitem__name"),
                price=F("menuitem__price"),
                # user=F("menuitem__orderitem__fk_order__fk_user__username"),
            )
            .annotate(
                quantity=Sum("menuitem__orderitem__quantity"),
                total=Sum(F("menuitem__orderitem__quantity") * F("menuitem__price"), output_field=DecimalField(max_digits=9, decimal_places=2)),
            )
            .distinct()
        )
        orderTotalSummary2 = (
            Restaurant.objects.filter(menuitem__orderitem__fk_order__created_at__date=timezone.now(), menuitem__orderitem__fk_order__fk_order_room=self.get_order_room())
            .values(
                restaurant=F("name"),
                item=F("menuitem__name"),
                price=F("menuitem__price"),
                user=F("menuitem__orderitem__fk_order__fk_user__username"),
            )
            .annotate(
                quantity=Sum("menuitem__orderitem__quantity"),
                total=Sum(F("menuitem__orderitem__quantity") * F("menuitem__price"), output_field=DecimalField(max_digits=9, decimal_places=2)),
            )
            .distinct()
        )
        spacial_rounder(orderTotalSummary, ["total", "price"], 2)
        spacial_rounder(orderTotalSummary2, ["total", "price"], 2)

        grand_totals_orderTotalSummary = calculate_totals(orderTotalSummary, ["quantity", "total"])

        orderTotalSummaryGrouped = group_nested_data(orderTotalSummary, ["restaurant"])

        totals_orderTotalSummary = {restaurant: calculate_totals(items, ["quantity", "total"]) for restaurant, items in orderTotalSummaryGrouped.items()}

        orderUsersTotalSummaryGrouped = group_nested_data(orderTotalSummary2, ["restaurant", "user"])

        totals_orderUsersTotalSummaryGrouped = {
            restaurant: {user: calculate_totals(orders, ["quantity", "total"]) for user, orders in userItems.items()} for restaurant, userItems in orderUsersTotalSummaryGrouped.items()
        }

        orderUsersSummary = (
            UserModel.objects.filter(order__created_at__date=timezone.now(), order__finished_ordering=True, order__fk_order_room=self.get_order_room())
            .values(
                user=F("username"),
                restaurant=F("order__orderitem__fk_menu_item__fk_restaurant__name"),
                item=F("order__orderitem__fk_menu_item__name"),
                price=F("order__orderitem__fk_menu_item__price"),
            )
            .annotate(
                quantity=Sum("order__orderitem__quantity"),
                total=Sum(F("order__orderitem__quantity") * F("order__orderitem__fk_menu_item__price"), output_field=DecimalField(max_digits=9, decimal_places=2)),
            )
            .distinct()
        )
        spacial_rounder(orderUsersSummary, ["total", "price"], 2)

        orderUsersRestaurantSummaryGrouped = group_nested_data(orderUsersSummary, ["user", "restaurant"])

        orderUsersSummaryGrouped = group_nested_data(orderUsersSummary, ["user"])

        totals_orderUsersSummaryGrouped = {user: calculate_totals(items, ["quantity", "total"]) for user, items in orderUsersSummaryGrouped.items()}

        return {
            "orderTotalSummaryGrouped": orderTotalSummaryGrouped,
            "totals_orderTotalSummary": totals_orderTotalSummary,
            "grand_totals_orderTotalSummary": grand_totals_orderTotalSummary,
            "orderUsersTotalSummaryGrouped": orderUsersTotalSummaryGrouped,
            "totals_orderUsersTotalSummaryGrouped": totals_orderUsersTotalSummaryGrouped,
            "orderUsersRestaurantSummaryGrouped": orderUsersRestaurantSummaryGrouped,
            "totals_orderUsersSummaryGrouped": totals_orderUsersSummaryGrouped,
            "showTables": True,
            "table_headers": ["#", _("Item"), _("Price"), _("Quantity"), _("Total")],
        }


def orders_query():
    # TODO check this date condition is it valid for orders around midnight
    return Order.objects.filter(created_at__date=timezone.now())


def get_last_order(user, order_room, finished=False):
    return orders_query().filter(fk_user=user, fk_order_room=order_room, finished_ordering=finished).last()


def get_user_order(user, order_room, finished=False):
    return orders_query().filter(fk_user=user, fk_order_room=order_room, finished_ordering=finished)


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
