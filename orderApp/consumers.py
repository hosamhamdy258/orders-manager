from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync


from orderApp.models import OrderItem
from orderApp.forms import OrderItemForm
from orderApp.views import create_order, disable_form, finish_order, get_all_orders, get_user_orders, shared_context
from orderApp.utils import templates_joiner

UserModel = get_user_model()


class GroupConsumer(JsonWebsocketConsumer):
    message_type = "message_type"
    message = "message"

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
        event_type = content.get(self.message_type, "")
        message = dict(message=content)
        handler = getattr(self, event_type, self.default_handler)
        handler(message)

    def default_handler(self, message):
        print(f"Unknown event type received: {message}")

    def self_dispatch(self, event):
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": event[self.message][self.message_type], self.message: event[self.message], "group": False}
        )

    def addOrderItem(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            user = self.scope["user"]

            order, restaurants, menuItems, all_orders, disable_form = shared_context(user, event[self.message].get("fk_restaurant", None))

            context = {
                "restaurants": restaurants,
                "menuItems": menuItems,
                "order": order,
                "orders": all_orders,
                "disable_form": disable_form,
            }
            form = OrderItemForm(event[self.message])
            if form.is_valid():
                form.save(True)

                form = OrderItemForm(initial={**form.cleaned_data, "fk_menu_item": None, "quantity": None})
                context.update({"form": form})

                orderItems = OrderItem.objects.filter(fk_order=order)
                context.update({"orderItems": orderItems})
                templates.append("order/orderItems.html")
            else:
                context.update({"form": form})

            templates.append("order/formOrderItem.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)

    def finishOrder(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:

            templates = []
            context = {}
            user = self.scope["user"]

            isFinished, finish_order_error, order = finish_order(event[self.message]["fk_order"], user)
            if isFinished:
                created, create_error_msg, order = create_order(user)
                if created:
                    context.update({"remove_errors": True})
                else:
                    context.update({"error": create_error_msg})

            else:
                context.update({"error": finish_order_error})

            user_orders = get_user_orders(user)

            disable = disable_form(user_orders)
            if disable:
                context.update({"disable_form": disable})
                templates.append("order/formOrderItem.html")

            context.update({"order": order})

            templates.append("order/orderItems.html")
            templates.append("order/orderID.html")
            templates.append("order/finishOrder.html")

            self.membersOrders({"message": {"message_type": "membersOrders"}})

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def membersOrders(self, event):
        group = event.get("group", True)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            orders = get_all_orders()
            context.update({"orders": orders})
            templates.append("order/membersOrders.html")
            response = templates_joiner(context, templates)
            self.send(text_data=response)
            pass

    def ordersList(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]

            orders = get_user_orders(user)
            context.update({"orders": orders})

            templates.append("order/membersOrders.html")
            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass
