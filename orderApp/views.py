from channels.layers import get_channel_layer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import HttpResponse as HttpResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.groupContext import group_context
from orderApp.models import Client, Group, MenuItem
from orderApp.orderContext import order_context
from orderApp.restaurantContext import restaurant_context

decorators = [never_cache]


class BaseView(LoginRequiredMixin, TemplateView):
    template_name = "base/index.html"
    view_type = None
    ws_url = None
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.user = self.request.user
        group = getattr(self, "group", None)
        ctx = get_context(user=self.user, view=self.view_type, group=group)
        context.update({GC.WS_URL: self.get_ws_url(), **ctx, **self.get_extra_context()})
        return context

    def get_view_type(self):
        if self.view_type is None:
            raise NotImplementedError("Subclasses must define view_type or implement get_view_type()")
        return self.view_type

    def get_ws_url(self):
        if self.ws_url is None:
            raise NotImplementedError("Subclasses must define ws_url or implement get_ws_url()")
        return self.ws_url

    def get_extra_context(self):
        return self.extra_context


@method_decorator(decorators, name="dispatch")
class IndexView(BaseView):
    view_type = CV.GROUP_VIEW
    ws_url = "/ws/index/"


class OrderView(BaseView):
    view_type = CV.ORDER_VIEW

    def dispatch(self, request, *args, **kwargs):
        try:
            self.group = Group.objects.get(room_number=kwargs.get(GC.GROUP_NAME))
        except ObjectDoesNotExist:
            return redirect("index")
        return super().dispatch(request, *args, **kwargs)

    def get_ws_url(self):
        return f"/ws/order/{self.group.room_number}/"

    def get_extra_context(self):
        return {GC.GROUP_NAME: self.group.name, **super().get_extra_context()}


class RestaurantView(BaseView):
    view_type = CV.RESTAURANT_VIEW
    ws_url = "/ws/restaurant/"


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
