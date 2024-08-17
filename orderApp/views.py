from datetime import datetime
from django.shortcuts import render
from django.utils.translation import gettext as _
from .models import Order, OrderItem, Restaurant, MenuItem
from django.contrib.auth.decorators import login_required
from .forms import OrderItemForm

# Create your views here.


def index(request):
    return render(request, "order/index.html")


@login_required
def group(request, group_name):
    if request.method == "GET":
        user = request.user
        order, restaurants, menuItems = shared_context(user)
        orderItems = OrderItem.objects.filter(fk_order=order)
        form = OrderItemForm()
        context = {
            "group_name": group_name,
            "restaurants": restaurants,
            "menuItems": menuItems,
            "orderItems": orderItems,
            "order": order,
            "form": form,
        }
    return render(request, "order/index.html", context)


def shared_context(user):
    order = get_or_create_order(user)
    restaurants = Restaurant.objects.all()
    menuItems = MenuItem.objects.all()
    return order, restaurants, menuItems


def get_or_create_order(user):
    order = Order.objects.filter(fk_user=user, finished_ordering=False, created__date=datetime.today()).last()
    if not order:
        order = create_order(user)
    return order


def create_order(user):
    order = Order.objects.create(fk_user=user, finished_ordering=False)
    return order


def finish_order(order):
    orderItems = OrderItem.objects.filter(fk_order=order).count()
    order = Order.objects.get(id=order)
    if orderItems == 0:
        return False, _("Add order item to finish order"), order
    else:
        order.finished_ordering = True
        order.save()
        return True, "", order
