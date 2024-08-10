from django.urls import re_path

from . import consumers

websocket_urlpatterns_order = [
    re_path(r"ws/group/(?P<group_name>\w+)/$", consumers.GroupConsumer.as_asgi()),
]
