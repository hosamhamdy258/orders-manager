from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime
from django.shortcuts import render
from django.utils.translation import gettext as _
from .models import Order, OrderItem, Restaurant, MenuItem
from .forms import OrderItemForm

# Create your views here.
order_limit = 2

# def index(request):
#     return render(request, "order/index.html")


class GroupView(LoginRequiredMixin, TemplateView):
    template_name = "order/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        group_name = kwargs.get("group_name")
        order, restaurants, menuItems, all_orders, disable_form = shared_context(user)
        orderItems = OrderItem.objects.filter(fk_order=order)
        form = OrderItemForm()

        context = super().get_context_data(**kwargs)
        context.update(
            {
                "group_name": group_name,
                "restaurants": restaurants,
                "menuItems": menuItems,
                "orderItems": orderItems,
                "order": order,
                "orders": all_orders,
                "form": form,
                "disable_form": disable_form,
            }
        )
        return context


def shared_context(user, restaurant=None):
    all_orders = get_all_orders()
    orders = get_user_orders(user)
    disable = disable_form(orders)
    if disable:
        order = Order.objects.none().first()
        restaurants = Restaurant.objects.none()
        menuItems = MenuItem.objects.none()
    else:
        order = get_or_create_order(user)
        restaurants = Restaurant.objects.all()
        menuItems = MenuItem.objects.filter(fk_restaurant=restaurant)
    return order, restaurants, menuItems, all_orders, disable


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
