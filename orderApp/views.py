from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils.translation import gettext as _


from orderApp.restaurantContext import restaurant_context
from orderApp.orderContext import order_context


from orderApp.enums import GeneralContextKeys, CurrentViews
from orderApp.models import MenuItem, Clients
from orderApp.forms import OrderItemForm


# Create your views here.

# def index(request):
#     return render(request, "order/index.html")


class GroupView(LoginRequiredMixin, TemplateView):
    template_name = "base/index.html"

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
        CurrentViews.ORDER_VIEW: order_context(user=user, view=view),
        CurrentViews.RESTAURANT_VIEW: restaurant_context(view=view),
    }
    return context.get(view)


def menuitems(request):
    restaurant = request.GET.get("fk_restaurant")
    menuItems = MenuItem.objects.filter(fk_restaurant=restaurant)
    return render(request, "order/bottomSection/form/menuItems.html", {"menuItems": menuItems})


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def announcement(request):
    channels = Clients.objects.all()
    channel_layer = get_channel_layer()
    # print(channel_layer, "xxxxx")
    # async_to_sync(channel_layer.group_send)("group_hosam", {"type": "groupOrderSummary"})

    for channel in channels:
        async_to_sync(channel_layer.send)(channel.channel_name, {"type": "groupOrderSummary"})

    return render(request, "order/bottomSection/form/menuItems.html")
