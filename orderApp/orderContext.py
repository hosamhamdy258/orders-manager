from datetime import datetime
from django.utils.translation import gettext as _

from orderApp.context import get_current_view


from orderApp.enums import OrderContextKeys, ViewContextKeys, CurrentViews
from orderApp.models import Order, OrderItem, Restaurant, MenuItem

order_limit = 50


def order_context(user, view=CurrentViews.ORDER_VIEW, restaurant=None):
    form_section = order_form_section(user=user, restaurant=restaurant)

    return {
        **order_title_section(),
        **order_list_section(),
        **order_details_section(order=form_section.get(OrderContextKeys.ORDER)),
        **form_section,
        **order_actions_section(),
    }


def order_title_section():
    return {
        **get_current_view(view=CurrentViews.ORDER_VIEW),
        ViewContextKeys.MAIN_TITLE: _("Orders Screen"),
        ViewContextKeys.TITLE_ACTION: _("Add Restaurant"),
        ViewContextKeys.NEXT_VIEW: CurrentViews.RESTAURANT_VIEW,
    }


def order_list_section(user=None, view=CurrentViews.ORDER_VIEW, add_view=False):
    return {
        ViewContextKeys.LIST_SECTION_ID: "members_orders",
        ViewContextKeys.LIST_SECTION_TITLE: _("Members Orders"),
        ViewContextKeys.LIST_MESSAGE_TYPE: "showMemberItemOrders",
        ViewContextKeys.LIST_SECTION_DATA: get_all_orders(user),
        **(get_current_view(view=view) if add_view else {}),
    }


def order_details_section(order=None, view=CurrentViews.ORDER_VIEW, add_view=False):
    return {
        ViewContextKeys.DETAILS_SECTION_ID: "order_items",
        ViewContextKeys.DETAILS_SECTION_TITLE: _("Order Items"),
        ViewContextKeys.DETAILS_MESSAGE_TYPE: "deleteOrderItem",
        ViewContextKeys.DETAILS_SECTION_DATA: get_order_items(order),
        **(get_current_view(view=view) if add_view else {}),
    }


def order_form_section(user, restaurant=None):
    disable = disable_form(user=user)
    if disable:
        order = Order.objects.none().first()
        restaurants = Restaurant.objects.none()
        menuItems = MenuItem.objects.none()
    else:
        order = get_last_order(user)
        restaurants, menuItems = get_restaurant_with_menu_items(restaurant)
    return {
        OrderContextKeys.RESTAURANTS: restaurants,
        OrderContextKeys.MENU_ITEMS: menuItems,
        OrderContextKeys.DISABLE_FORM: disable,
        **order_form_id(order),
    }


def order_form_id(order=None):
    return {
        OrderContextKeys.ORDER: order,
        OrderContextKeys.FORM_ORDER_ID: OrderContextKeys.FORM_ORDER_ID,
    }


def order_actions_section(order=None, add_order_id=False):

    return {
        OrderContextKeys.FINISH_ORDER_ID: OrderContextKeys.FINISH_ORDER_ID,
        **({OrderContextKeys.ORDER: order} if add_order_id else {}),
    }


def get_order_items(order):
    if order:
        orderItems = OrderItem.objects.filter(fk_order=order)
    else:
        orderItems = OrderItem.objects.none()
    return orderItems


def get_restaurant_with_menu_items(restaurant):
    restaurants = Restaurant.objects.all()
    menuItems = get_restaurant_menu_items(restaurant)
    return restaurants, menuItems


def get_restaurant_menu_items(restaurant):
    menuItems = MenuItem.objects.filter(fk_restaurant=restaurant).order_by("-id")
    return menuItems


def orders_query():
    return Order.objects.filter(created__date=datetime.today())


def get_all_orders(user=None):
    if user:
        orders = orders_query().filter(finished_ordering=True, fk_user=user)
    else:
        orders = orders_query().filter(finished_ordering=True)
    return orders


def disable_form(user):
    orders = get_all_orders(user=user)
    return orders.count() >= order_limit


def get_last_order(user):
    order = orders_query().filter(fk_user=user, finished_ordering=False).last()
    return order


def create_order(user):

    orders = orders_query().filter(fk_user=user).count()
    order = get_last_order(user)
    if orders == order_limit:
        return False, "", order
    elif orders > order_limit:
        return False, _(f"Only {order_limit} orders per day"), order

    order = Order.objects.create(fk_user=user)
    return True, "", order


def create_order_updated(user):
    # !check for max allowed orders per day and use create_order function
    order = Order.objects.create(fk_user=user)
    return order


def finish_order(order):
    if order:
        orderItems = OrderItem.objects.filter(fk_order=order).exists()
        order = Order.objects.get(id=order)

        if orderItems:
            order.finished_ordering = True
            order.save()
            return True, "", order
        else:
            return False, _("Add Order Items"), order
    else:
        return False, _("Add Order Items"), None
        # !check for max allowed orders per day
        # return False, _(f"Only {order_limit} orders per day"), None
