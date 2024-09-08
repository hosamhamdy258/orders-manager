from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime
from django.shortcuts import render
from django.utils.translation import gettext as _

from .enums import GeneralContextKeys, OrderContextKeys, RestaurantContextKeys, ViewContextKeys, CurrentViews
from .models import Order, OrderItem, Restaurant, MenuItem, Clients
from .forms import OrderItemForm


# Create your views here.
order_limit = 2

# def index(request):
#     return render(request, "order/index.html")


class GroupView(LoginRequiredMixin, TemplateView):
    template_name = "order/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        group_name = kwargs.get(GeneralContextKeys.GROUP_NAME)
        ctx = get_context(user=user, view=CurrentViews.ORDER_VIEW)
        form = OrderItemForm()

        context = super().get_context_data(**kwargs)
        context.update({GeneralContextKeys.GROUP_NAME: group_name, "form": form, **ctx})
        return context


def get_context(user, view=CurrentViews.ORDER_VIEW):
    context = {
        CurrentViews.ORDER_VIEW: order_context(user, view),
        CurrentViews.RESTAURANT_VIEW: restaurant_context(view),
    }
    return context.get(view)


def restaurant_context(view=CurrentViews.RESTAURANT_VIEW, restaurant=None):
    return {
        **get_current_view(view=view),
        ViewContextKeys.MAIN_TITLE: "Restaurant Screen",
        ViewContextKeys.TITLE_ACTION: "Add Order",
        ViewContextKeys.NEXT_VIEW: CurrentViews.ORDER_VIEW,
        # ==============
        **restaurant_list_section(),
        #
        **restaurant_details_section(restaurant),
        #
        RestaurantContextKeys.FORM_MENU_ITEM_DISABLE: True,
    }


def order_context(user, view=CurrentViews.ORDER_VIEW, restaurant=None):
    all_orders = get_all_orders()
    orders = get_user_orders(user)
    disable = disable_form(orders)
    if disable:
        order = Order.objects.none().first()
        restaurants = Restaurant.objects.none()
        menuItems = MenuItem.objects.none()
    else:
        order = get_or_create_order(user)
        restaurants, menuItems = get_restaurant_with_menu_items(restaurant)

    return {
        OrderContextKeys.ORDER: order,
        OrderContextKeys.RESTAURANTS: restaurants,
        OrderContextKeys.MENU_ITEMS: menuItems,
        OrderContextKeys.DISABLE_FORM: disable,
        # OrderContextKeys.ORDER_ITEMS: get_order_items(order),
        #
        **get_current_view(view=view),
        ViewContextKeys.MAIN_TITLE: "Orders Screen",
        ViewContextKeys.TITLE_ACTION: "Add Restaurant",
        ViewContextKeys.NEXT_VIEW: CurrentViews.RESTAURANT_VIEW,
        #
        ViewContextKeys.LIST_SECTION_ID: "members_orders",
        ViewContextKeys.LIST_SECTION_TITLE: "Members Orders",
        ViewContextKeys.LIST_MESSAGE_TYPE: "showMemberItemOrders",
        ViewContextKeys.LIST_SECTION_DATA: all_orders,
        #
        **order_details_section(order),
    }


def get_current_view(view):
    views = {
        CurrentViews.ORDER_VIEW: {ViewContextKeys.CURRENT_VIEW: CurrentViews.ORDER_VIEW},
        CurrentViews.RESTAURANT_VIEW: {ViewContextKeys.CURRENT_VIEW: CurrentViews.RESTAURANT_VIEW},
    }
    return views.get(view)


def order_details_section(order, view=CurrentViews.ORDER_VIEW, add_view=False):
    return {
        ViewContextKeys.DETAILS_SECTION_ID: "order_items",
        ViewContextKeys.DETAILS_SECTION_TITLE: "Order Items",
        ViewContextKeys.DETAILS_MESSAGE_TYPE: "deleteOrderItem",
        ViewContextKeys.DETAILS_SECTION_DATA: get_order_items(order),
        **(get_current_view(view=view) if add_view else {}),
    }


def restaurant_details_section(restaurant, view=CurrentViews.RESTAURANT_VIEW, add_view=False):
    return {
        ViewContextKeys.DETAILS_SECTION_ID: "menu_items",
        ViewContextKeys.DETAILS_SECTION_TITLE: "Menu Items",
        ViewContextKeys.DETAILS_MESSAGE_TYPE: "deleteMenuItem",
        ViewContextKeys.DETAILS_SECTION_DATA: get_restaurant_menu_items(restaurant),
        ViewContextKeys.DETAILS_CURRENT_SELECTION: Restaurant.objects.get(pk=restaurant) if restaurant else None,
        **(get_current_view(view=view) if add_view else {}),
    }


def restaurant_list_section(view=CurrentViews.RESTAURANT_VIEW, add_view=False):
    return {
        ViewContextKeys.LIST_SECTION_ID: "restaurant_list",
        ViewContextKeys.LIST_SECTION_TITLE: "Restaurant List",
        ViewContextKeys.LIST_MESSAGE_TYPE: "showRestaurantItems",
        ViewContextKeys.LIST_SECTION_DATA: Restaurant.objects.all().order_by("-id"),
        **(get_current_view(view=view) if add_view else {}),
    }


def get_order_items(order):
    orderItems = OrderItem.objects.filter(fk_order=order)
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


def get_user_orders(user):
    orders = orders_query().filter(finished_ordering=True, fk_user=user)
    return orders


def get_all_orders():
    orders = orders_query().filter(finished_ordering=True)
    return orders


def disable_form(orders):
    return orders.count() >= order_limit


def get_or_create_order(user):
    order = get_last_order(user)
    if not order:
        created, msg, order = create_order(user)
    return order


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

    order = Order.objects.create(fk_user=user, finished_ordering=False)
    return True, "", order


def finish_order(order, user):
    if order:
        orderItems = OrderItem.objects.filter(fk_order=order).count()
        order = Order.objects.get(id=order)

        if orderItems == 0:
            return False, _("Add order item to finish order"), order
        else:
            order.finished_ordering = True
            order.save()
            return True, "", order

    return False, _(f"Only {order_limit} orders per day"), None


def menuitems(request):
    restaurant = request.GET.get("fk_restaurant")
    menuItems = MenuItem.objects.filter(fk_restaurant=restaurant)
    return render(request, "order/menuItems.html", {"menuItems": menuItems})


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def announcement(request):
    channels = Clients.objects.all()
    channel_layer = get_channel_layer()
    # print(channel_layer, "xxxxx")
    # async_to_sync(channel_layer.group_send)("group_hosam", {"type": "groupOrderSummary"})

    for channel in channels:
        async_to_sync(channel_layer.send)(channel.channel_name, {"type": "groupOrderSummary"})

    return render(
        request,
        "order/menuItems.html",
    )
