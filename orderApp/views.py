import asyncio
from time import sleep
from django.shortcuts import render
from django.utils.translation import gettext as _
from asgiref.sync import sync_to_async
from .models import Order, Restaurant, MenuItem

# Create your views here.


def index(request):
    return render(request, "order/index.html")


def group(request, group_name):

    restaurants = Restaurant.objects.all()
    menuItems = MenuItem.objects.all()
    context = {
        "group_name": group_name,
        "restaurants": restaurants,
        "menuItems": menuItems,
    }
    return render(request, "order/order.html", context)
