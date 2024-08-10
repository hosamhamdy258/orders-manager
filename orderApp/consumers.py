import json

from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core import serializers
from asgiref.sync import async_to_sync

from orderApp.models import Order

UserModel = get_user_model()


class GroupConsumer(JsonWebsocketConsumer):

    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["group_name"]
        self.room_group_name = f"group_{self.room_name}"

        # Join room group
        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)

        print(f"Connected to group: {self.room_group_name} , channel : {self.channel_name}")

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)

    # Receive message from room group
    def receive_json(self, content, **kwargs):
        event_type = content.get("type", "")
        message = dict(message=content.get("message", ""))
        handler = getattr(self, event_type, self.default_handler)
        handler(message)

    def default_handler(self, message):
        print(f"Unknown event type received: {message}")

    def echo(self, event):
        group = event.get("group", True)
        if group:
            async_to_sync(self.channel_layer.group_send)(self.room_group_name, {"type": "echo", "message": event["message"], "group": False})
        else:
            # Send message to WebSocket
            res = {"message": event["message"]}
            self.send_json(res)

    # def order(self, message, event_type):
    #     user = UserModel.objects.get(pk=1)
    #     order = Order.objects.create(fk_user=user)
    #     serialized = serializers.serialize("json", Order.objects.filter(pk=order.pk))

    #     # Send message to WebSocket
    #     self.send_json({"type": event_type, "message": message, "result": serialized})
