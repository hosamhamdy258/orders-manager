from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from django.http.response import HttpResponse as HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.forms import OrderItemForm
from orderApp.groupContext import group_context
from orderApp.models import Client, Group, MenuItem
from orderApp.orderContext import order_context
from orderApp.restaurantContext import restaurant_context


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "base/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        ctx = get_context(user=user, view=CV.GROUP_VIEW)

        context = super().get_context_data(**kwargs)
        context.update({GC.WS_URL: "/ws/index/", **ctx})
        return context


class GroupView(LoginRequiredMixin, TemplateView):
    template_name = "base/index.html"

    def get(self, request, *args, **kwargs):
        try:
            self.group = Group.objects.get(room_number=kwargs.get(GC.GROUP_NAME))
        except ObjectDoesNotExist:
            return redirect("index")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user = self.request.user

        ctx = get_context(user=user, view=CV.ORDER_VIEW, group=self.group)
        # !check if this needed
        form = OrderItemForm()

        context = super().get_context_data(**kwargs)
        context.update({GC.GROUP_NAME: self.group.name, GC.WS_URL: f"/ws/group/{self.group.room_number}/", "form": form, **ctx})
        return context


def get_context(user, view=CV.ORDER_VIEW, group=None):
    if view == CV.ORDER_VIEW:
        return order_context(user=user, group=group)
    if view == CV.RESTAURANT_VIEW:
        return restaurant_context(view=view)
    if view == CV.GROUP_VIEW:
        return group_context(view=view)
    return view


def menuitems(request):
    restaurant = request.GET.get("fk_restaurant")
    menuItems = MenuItem.objects.filter(fk_restaurant=restaurant)
    return render(request, "order/bottomSection/form/menuItems.html", {"menuItems": menuItems})


from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def announcement(request):
    # Group.objects.all().delete()
    channels = Client.objects.all()
    channel_layer = get_channel_layer()
    # print(channel_layer.__dict__, "xxxxx")
    # async_to_sync(channel_layer.group_send)("group_index_home_group", {"type": "sendNotification", "message": {"message_type": "sendNotification"}})
    # async_to_sync(channel_layer.send)("group_index_home_group", {"type": "sendNotification"})

    # for channel in channels:
    #     async_to_sync(channel_layer.send)(channel.channel_name, {"type": "sendNotification","type2x": "sendNotification", "message": {"message_type": "sendNotification"}})

    return render(request, "order/bottomSection/form/menuItems.html")


import threading


def run_after_delay(func, delay_in_seconds, *args, **kwargs):
    timer = threading.Timer(delay_in_seconds, func, args=args, kwargs=kwargs)
    timer.start()


def my_background_function():
    Group.objects.all().delete()
    print("This function runs after a delay in the background.")


run_after_delay(my_background_function, 7)
