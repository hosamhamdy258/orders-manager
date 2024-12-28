from django.urls import re_path

from . import consumers

websocket_urlpatterns_order = [
    re_path(r"ws/index/", consumers.GroupConsumer.as_asgi()),
    re_path(r"ws/order/(?P<group_name>\w+)/$", consumers.OrderConsumer.as_asgi()),
    re_path(r"ws/restaurant/", consumers.RestaurantConsumer.as_asgi()),
]
