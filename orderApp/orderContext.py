from datetime import datetime

from django.utils.translation import gettext as _

from orderApp.context import get_current_view
from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.enums import OrderContextKeys as OC
from orderApp.enums import ViewContextKeys as VC
from orderApp.models import Group, MenuItem, Order, OrderItem, Restaurant

order_limit = 1


def check_order_complete_status(user, group):
    if user and group:
        return group.completed or user in group.accepted_order_users.all()
    else:
        return False


def order_context(user, group, restaurant=None):
    order_completed = check_order_complete_status(user=user, group=group)

    form_section = order_form_section(user=user, group=group, restaurant=restaurant, force_disable=order_completed)
    return {
        **order_title_section(group=group),
        **order_list_section(group=group),
        **order_details_section(order=form_section.get(OC.ORDER), disable_remove_button=order_completed, skip_check=True),
        **form_section,
        **order_actions_section(force_disable=order_completed),
    }


def order_title_section(group=None):
    return {
        **get_current_view(view=CV.ORDER_VIEW),
        VC.MAIN_TITLE: _("Orders Screen"),
        VC.TITLE_ACTION: _("Add Restaurant"),
        VC.NEXT_VIEW: CV.RESTAURANT_VIEW,
        GC.GROUP_NAME: group.name,
    }


def order_list_section(user=None, group=None, view=CV.ORDER_VIEW, add_view=False):
    return {
        VC.LIST_SECTION_ID: "members_orders",
        VC.LIST_SECTION_TITLE: _("Members Orders"),
        VC.LIST_MESSAGE_TYPE: "showMemberItemOrders",
        VC.LIST_SECTION_DATA: get_all_orders(user=user, group=group),
        **(get_current_view(view=view) if add_view else {}),
    }


def order_details_section(order=None, view=CV.ORDER_VIEW, add_view=False, disable_remove_button=False, user=None, group=None, skip_check=False):

    disable = True if disable_remove_button else check_order_complete_status(user=user, group=group) if not skip_check else False

    return {
        VC.DETAILS_SECTION_ID: "order_items",
        VC.DETAILS_SECTION_TITLE: _("Order Items"),
        VC.DETAILS_MESSAGE_TYPE: "deleteOrderItem",
        OC.DISABLE_REMOVE_BUTTON: disable,
        VC.DETAILS_SECTION_DATA: get_order_items(order),
        **(get_current_view(view=view) if add_view else {}),
    }


def order_form_section(user=None, group=None, restaurant=None, force_disable=False):

    disable = True if force_disable else disable_order_item_form(user=user, group=group)

    if disable:
        order = Order.objects.none().first()
        restaurants = Restaurant.objects.none()
        menuItems = MenuItem.objects.none()
    else:
        order = get_last_order(user=user, group=group)
        restaurants, menuItems = get_restaurant_with_menu_items(restaurant)
    return {
        OC.RESTAURANTS: restaurants,
        OC.MENU_ITEMS: menuItems,
        OC.DISABLE_ORDER_ITEM_FORM: disable,
        **order_form_id(order),
    }


def order_form_id(order=None):
    return {
        OC.ORDER: order,
        OC.FORM_ORDER_ID: OC.FORM_ORDER_ID,
    }


def order_actions_section(order=None, add_order_id=False, all_orders=False, force_disable=False):

    return {
        OC.FINISH_ORDER_ID: OC.FINISH_ORDER_ID,
        OC.DISABLE_COMPLETE_BUTTON: force_disable,
        **({OC.ORDER: order} if add_order_id else {}),
        **({OC.ALL_ORDERS: OC.ALL_ORDERS} if all_orders else {}),
        **({OC.ALL_ORDERS_BUTTON: _("All Orders")} if all_orders else {OC.ALL_ORDERS_BUTTON: _("My Orders")}),
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


def get_all_orders(user=None, group=None):
    if user and group:
        orders = orders_query().filter(finished_ordering=True, fk_user=user, fk_group=group)
    else:
        orders = orders_query().filter(finished_ordering=True, fk_group=group)
    return orders


def disable_order_item_form(user, group):
    orders = get_all_orders(user=user, group=group)
    return orders.count() >= order_limit


def get_last_order(user, group):
    order = orders_query().filter(fk_user=user, fk_group=group, finished_ordering=False).last()
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


def create_order_updated(user, group):
    # !check for max allowed orders per day and use create_order function
    order = Order.objects.create(fk_user=user, fk_group=group)
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
