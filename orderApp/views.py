from ast import literal_eval

from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages import get_messages
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import HttpResponse as HttpResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.models import Client, MenuItem, OrderGroup, OrderRoom, OrderRoomUser
from orderApp.orderGroupContext import OrderGroupContext
from orderApp.orderRoomContext import OrderRoomContext
from orderApp.orderSelectionContext import OrderSelectionContext
from orderApp.restaurantContext import RestaurantContext

decorators = [never_cache]


class BaseView(LoginRequiredMixin, TemplateView):
    template_name = "base/index.html"
    view_type = None
    ws_url = None
    extra_context = {}
    user = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = getattr(self, "group", None)
        room = getattr(self, "room", None)
        ctx = get_context(user=self.get_user(), view=self.view_type, order_group=group, order_room=room)
        context.update({GC.WS_URL: self.get_ws_url(), **ctx, **self.get_extra_context()})
        return context

    def get_user(self):
        if self.user is None:
            self.user = self.request.user
        return self.user

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
    view_type = CV.ORDER_GROUP
    ws_url = "/ws/index/"


@method_decorator(decorators, name="dispatch")
class OrderRoomView(BaseView):
    view_type = CV.ORDER_ROOM
    ws_url = "/ws/room/"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.group = OrderGroup.objects.get(group_number=kwargs.get(GC.GROUP_NUMBER))
        except ObjectDoesNotExist:
            messages.error(request, {"code": 404})
            return redirect("redirect")

        if not self.group.can_join_group(self.get_user()):
            messages.error(request, {"code": 403, "message": _("You are not allowed to enter here")})
            return redirect("redirect")

        return super().dispatch(request, *args, **kwargs)

    def get_ws_url(self):
        return f"{self.ws_url}{self.group.group_number}/"


class OrderSelectionView(BaseView):
    view_type = CV.ORDER_SELECTION
    ws_url = "/ws/order/"

    def dispatch(self, request, *args, **kwargs):
        try:
            self.group = OrderGroup.objects.get(group_number=kwargs.get(GC.GROUP_NUMBER))
            self.room = OrderRoom.objects.get(room_number=kwargs.get(GC.ROOM_NUMBER))
        except ObjectDoesNotExist:
            messages.error(request, {"code": 404})
            return redirect("redirect")

        if not self.group.can_join_group(self.get_user()):
            messages.error(request, {"code": 403, "message": _("You are not allowed to enter here")})
            return redirect("redirect")

        return super().dispatch(request, *args, **kwargs)

    def get_ws_url(self):
        return f"{self.ws_url}{self.group.group_number}/{self.room.room_number}/"

    def get_extra_context(self):
        return {GC.ROOM_NUMBER: self.room.name, **super().get_extra_context()}

    def get(self, request, *args, **kwargs):
        self.room.add_user_to_room(self.get_user())
        return super().get(request, *args, **kwargs)


class RestaurantView(BaseView):
    view_type = CV.RESTAURANT
    ws_url = "/ws/restaurant/"


def get_context(user, view=CV.ORDER_GROUP, order_group=None, order_room=None):
    match view:
        case CV.ORDER_SELECTION:
            return OrderSelectionContext(user=user, order_group=order_group, order_room=order_room).get_full_context()
        case CV.RESTAURANT:
            return RestaurantContext(user=user).get_full_context()
        case CV.ORDER_ROOM:
            return OrderRoomContext(user=user, order_group=order_group).get_full_context()
        case CV.ORDER_GROUP:
            return OrderGroupContext(user=user).get_full_context()
        case __:
            raise NotImplementedError(f"Unknown view: {view}")


def menuitems(request):
    restaurant = request.GET.get("fk_restaurant")
    menuItems = MenuItem.get_restaurant_menu_items(restaurant)
    return render(request, "orderSelection/bottomSection/form/menuItems.html", {"menuItems": menuItems})


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


def redirect_page(request):
    messages = [literal_eval(message.message) for message in get_messages(request)]
    message = messages[0] if len(messages) == 1 else {}
    context = {
        "code": message.get("code", "404"),
        "message": message.get("message", _("We don't know how you ended up here but you have discovered a secret place")),
    }
    return render(request, "base/helpers/redirect_page.html", context)
