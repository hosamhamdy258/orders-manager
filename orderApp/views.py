from threading import Timer

from channels.layers import get_channel_layer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import HttpResponse as HttpResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.groupContext import group_context
from orderApp.models import Client, Group, MenuItem
from orderApp.orderContext import order_context
from orderApp.restaurantContext import restaurant_context

decorators = [never_cache]


@method_decorator(decorators, name="dispatch")
class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "base/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        ctx = get_context(user=user, view=CV.GROUP_VIEW)
        context = super().get_context_data(**kwargs)
        context.update({GC.WS_URL: "/ws/index/", **ctx})
        return context


class OrderView(LoginRequiredMixin, TemplateView):
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
        context = super().get_context_data(**kwargs)
        context.update({GC.GROUP_NAME: self.group.name, GC.WS_URL: f"/ws/order/{self.group.room_number}/", **ctx})
        return context


class RestaurantView(LoginRequiredMixin, TemplateView):
    template_name = "base/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        ctx = get_context(user=user, view=CV.RESTAURANT_VIEW)
        context = super().get_context_data(**kwargs)
        context.update({GC.WS_URL: f"/ws/restaurant/", **ctx})
        return context


def get_context(user, view=CV.ORDER_VIEW, group=None):
    match view:
        case CV.ORDER_VIEW:
            return order_context(user=user, group=group)
        case CV.RESTAURANT_VIEW:
            return restaurant_context(view=view)
        case CV.GROUP_VIEW:
            return group_context(view=view)
        case __:
            raise NotImplementedError(f"Unknown view: {view}")


def menuitems(request):
    restaurant = request.GET.get("fk_restaurant")
    menuItems = MenuItem.objects.filter(fk_restaurant=restaurant)
    return render(request, "order/bottomSection/form/menuItems.html", {"menuItems": menuItems})


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


def run_after_delay(func, delay_in_seconds, *args, **kwargs):
    timer = Timer(delay_in_seconds, func, args=args, kwargs=kwargs)
    timer.start()
    print(timer.name)
    print(timer.native_id)


def my_background_function():
    # Group.objects.all().delete()
    print("This function runs after a delay in the background.")


# run_after_delay(my_background_function, 20)
