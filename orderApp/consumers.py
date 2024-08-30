from datetime import datetime
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from django.db.models import F, Sum, DecimalField
from django.utils.translation import gettext as _


from orderApp.utils import calculate_totals, group_nested_data


from orderApp.models import OrderItem, Restaurant
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
                "user": user,
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

            isFinished, finish_order_error, order = finish_order(event[self.message].get("fk_order"), user)
            if isFinished:
                created, create_error_msg, order = create_order(user)
                if created:
                    context.update({"remove_errors": True})
                else:
                    context.update({"finish_order_error": create_error_msg})

            else:
                context.update({"finish_order_error": finish_order_error})

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
            templates.append("order/orderItems.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def deleteItem(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]
            context.update({"user": user})

            orderItemObj = OrderItem.objects.get(pk=event[self.message].get("orderItem"))
            if orderItemObj.fk_order.fk_user != user:
                return

            order_id = orderItemObj.fk_order
            orderItems = OrderItem.objects.filter(fk_order=order_id)
            context.update({"orderItems": orderItems})
            templates.append("order/orderItems.html")

            orderItemObj.delete()

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def showMemberItemOrders(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]
            context.update({"user": user})

            orderItems = OrderItem.objects.filter(fk_order=event[self.message].get("fk_order"))
            context.update({"orderItems": orderItems})
            templates.append("order/orderItems.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def groupOrderSummary(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]

            UserModel = get_user_model()

            if get_all_orders().count() == 0:
                templates.append("order/orderSummary.html")
                context.update({"order_summary_error": _("there's no orders today yet")})
            else:

                orderTotalSummary = (
                    Restaurant.objects.filter(menuitem__orderitem__fk_order__created__date=datetime.today())
                    .values(
                        restaurant=F("name"),
                        item=F("menuitem__menu_item"),
                        price=F("menuitem__price"),
                        # user=F("menuitem__orderitem__fk_order__fk_user__username"),
                    )
                    .annotate(
                        quantity=Sum("menuitem__orderitem__quantity"),
                        total=Sum(F("menuitem__orderitem__quantity") * F("menuitem__price"), output_field=DecimalField()),
                    )
                    .distinct()
                )
                orderTotalSummary2 = (
                    Restaurant.objects.filter(menuitem__orderitem__fk_order__created__date=datetime.today())
                    .values(
                        restaurant=F("name"),
                        item=F("menuitem__menu_item"),
                        price=F("menuitem__price"),
                        user=F("menuitem__orderitem__fk_order__fk_user__username"),
                    )
                    .annotate(
                        quantity=Sum("menuitem__orderitem__quantity"),
                        total=Sum(F("menuitem__orderitem__quantity") * F("menuitem__price"), output_field=DecimalField()),
                    )
                    .distinct()
                )

                grand_totals_orderTotalSummary = calculate_totals(orderTotalSummary, ["quantity", "total"])

                orderTotalSummaryGrouped = group_nested_data(orderTotalSummary, ["restaurant"])

                totals_orderTotalSummary = {
                    restaurant: calculate_totals(items, ["quantity", "total"]) for restaurant, items in orderTotalSummaryGrouped.items()
                }

                orderUsersTotalSummaryGrouped = group_nested_data(orderTotalSummary2, ["restaurant", "user"])

                totals_orderUsersTotalSummaryGrouped = {
                    restaurant: {user: calculate_totals(orders, ["quantity", "total"]) for user, orders in userItems.items()}
                    for restaurant, userItems in orderUsersTotalSummaryGrouped.items()
                }

                orderUsersSummary = (
                    UserModel.objects.filter(order__created__date=datetime.today(), order__finished_ordering=True)
                    .values(
                        user=F("username"),
                        restaurant=F("order__orderitem__fk_menu_item__fk_restaurant__name"),
                        item=F("order__orderitem__fk_menu_item__menu_item"),
                        price=F("order__orderitem__fk_menu_item__price"),
                    )
                    .annotate(
                        quantity=Sum("order__orderitem__quantity"),
                        total=Sum(F("order__orderitem__quantity") * F("order__orderitem__fk_menu_item__price"), output_field=DecimalField()),
                    )
                    .distinct()
                )

                orderUsersRestaurantSummaryGrouped = group_nested_data(orderUsersSummary, ["user", "restaurant"])

                orderUsersSummaryGrouped = group_nested_data(orderUsersSummary, ["user"])

                totals_orderUsersSummaryGrouped = {
                    user: calculate_totals(items, ["quantity", "total"]) for user, items in orderUsersSummaryGrouped.items()
                }

                templates.append("order/summaryTables.html")

                context.update(
                    {
                        "orderTotalSummaryGrouped": orderTotalSummaryGrouped,
                        "totals_orderTotalSummary": totals_orderTotalSummary,
                        "grand_totals_orderTotalSummary": grand_totals_orderTotalSummary,
                        "orderUsersTotalSummaryGrouped": orderUsersTotalSummaryGrouped,
                        "totals_orderUsersTotalSummaryGrouped": totals_orderUsersTotalSummaryGrouped,
                        "orderUsersRestaurantSummaryGrouped": orderUsersRestaurantSummaryGrouped,
                        "totals_orderUsersSummaryGrouped": totals_orderUsersSummaryGrouped,
                        "showTables": True,
                    }
                )

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass
