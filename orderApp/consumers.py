import time

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.db.models import DecimalField, F, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from orderApp.enums import CurrentViews as CV
from orderApp.enums import ErrorMessage as EM
from orderApp.forms import GroupForm, MenuItemForm, OrderItemForm, RestaurantForm
from orderApp.groupContext import (
    group_context,
    group_details_section,
    group_list_section,
)
from orderApp.models import Client, Group, MenuItem, OrderItem, Restaurant
from orderApp.orderContext import (
    check_disable_form,
    create_order,
    finish_order,
    get_all_orders,
    order_actions_section,
    order_details_section,
    order_form_section,
    order_list_section,
)
from orderApp.restaurantContext import (
    restaurant_context,
    restaurant_details_section,
    restaurant_list_section,
)
from orderApp.utils import calculate_totals, group_nested_data, templates_joiner
from orderApp.views import get_context

UserModel = get_user_model()
HOME_ROOM_NAME = "home_room"
HOME_GROUP_NAME = f"group_{HOME_ROOM_NAME}"
RESTAURANT_ROOM_NAME = "restaurant_room"
RESTAURANT_GROUP_NAME = f"group_{RESTAURANT_ROOM_NAME}"


class GroupConsumer(JsonWebsocketConsumer):
    message_type = "message_type"
    message = "message"

    def connect(self):
        self.room_name = HOME_ROOM_NAME
        self.room_group_name = HOME_GROUP_NAME
        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        print(f"Connected to group: {self.room_group_name} , channel : {self.channel_name}")
        self.accept()
        self.updateGroupBody()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)

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

    def updateGroupBody(self):
        templates = []
        context = {}
        user = self.scope["user"]
        context.update({"user": user})

        view_context = get_context(user=user, view=CV.GROUP_VIEW)

        context.update(view_context)
        templates.append("group/body.html")

        response = templates_joiner(context, templates)
        self.send(text_data=response)

    def updateGroupsList(self, event):
        group = event.get("group", True)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        context.update(**group_list_section(add_view=True))
        templates.append("group/bodySection/listSection.html")
        response = templates_joiner(context, templates)
        self.send(text_data=response)

    def showGroupMembers(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        context.update({**group_details_section(group=event[self.message].get("item_id"), add_view=True)})
        context.update({"remove_errors": True})

        templates.append("group/bodySection/detailsSection.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def addGroup(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        event[self.message].update({"room_number": f"g{time.time_ns()}"})
        form = GroupForm(event[self.message])
        if form.is_valid():
            instance = form.save(True)
            context.update(**group_list_section())
            context.update(**group_context(group=instance.id))
            self.updateGroupsList({"message": {"message_type": "updateGroupsList"}})

        else:
            context.update({"form": form})

        templates.append("group/bottomSection/form/formGroupItem.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    # ! for testing
    def sendNotification(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
        else:
            templates = []
            context = {}

            templates.append("base/helpers/notification.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)

    def updateConnectedUsers(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        context.update(event[self.message]["ctx"])
        templates.append("group/bodySection/connectedUsers.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)


class OrderConsumer(JsonWebsocketConsumer):
    message_type = "message_type"
    message = "message"

    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["group_name"]
        self.room_group_name = f"group_{self.room_name}"
        # Join room group
        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        Client.objects.create(channel_name=self.channel_name)
        self.group = Group.objects.get(room_number=self.room_name)
        user = self.scope["user"]
        self.group.m2m_users.add(user)
        self.updateUsersConnectedCount()
        self.accept()
        self.updateOrderBody()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)
        Client.objects.filter(channel_name=self.channel_name).delete()
        user = self.scope["user"]
        self.group.m2m_users.remove(user)
        self.updateUsersConnectedCount()

    # Receive message from room group
    def receive_json(self, content, **kwargs):
        event_type = content.get(self.message_type, "")
        message = dict(message=content)
        handler = getattr(self, event_type, self.default_handler)
        handler(message)

    def default_handler(self, message):
        print(f"Unknown event type received: {message}")

    def self_dispatch(self, event):
        # ! add handle for this 2 cases
        # ! from regular dispatch inside consumer
        #  ?{"message": {"message_type": "membersOrders"}}
        # ! from outside consumers
        # ?{"type": "sendNotification", "message": {"message_type": "sendNotification"}}

        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": event[self.message][self.message_type], self.message: event[self.message], "group": False}
        )

    def updateOrderBody(self):
        templates = []
        context = {}
        user = self.scope["user"]
        context.update({"user": user})

        view_context = get_context(user=user, view=CV.ORDER_VIEW, group=self.group)

        context.update(view_context)
        templates.append("order/body.html")

        response = templates_joiner(context, templates)
        # print("send",response)
        self.send(text_data=response)

    def addOrderItem(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        user = self.scope["user"]
        context = {"user": user}

        form_state = check_disable_form(group=self.group, user=user)
        if form_state["force_disable"]:
            context.update(EM.TIME_UP)
            templates.append("order/bottomSection/error_time_expired.html")
        else:
            if not event[self.message].get("fk_order"):
                state, order = create_order(user=user, group=self.group)

                if state:
                    event[self.message]["fk_order"] = order
                else:
                    context.update(EM.CREATE_ORDER)

            form = OrderItemForm(event[self.message])
            if form.is_valid():
                form.save(True)

                form = OrderItemForm(initial={**form.cleaned_data, "fk_menu_item": None, "quantity": None})
                context.update({"form": form})
                context.update({"remove_errors": True})

                context.update(**order_details_section(order=event[self.message]["fk_order"], add_view=True))
                templates.append("order/bodySection/detailsSection.html")

                context.update(**order_actions_section())
                templates.append("order/bottomSection/actions/finish_order_id.html")
            else:
                context.update({"form": form})

            templates.append("order/bottomSection/form/formOrderItem.html")
            context.update(**order_form_section(user=user, group=self.group, restaurant=event[self.message].get("fk_restaurant")))

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def finishOrder(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}
        user = self.scope["user"]

        form_state = check_disable_form(group=self.group, user=user)
        if form_state["force_disable"]:
            context.update(EM.TIME_UP)
            templates.append("order/bottomSection/error_time_expired.html")
        else:
            isFinished, order = finish_order(event[self.message].get("fk_order"))

            if isFinished:
                context.update({"remove_errors": True})

                context.update(**order_form_section(user=user, group=self.group))
                templates.append("order/bottomSection/form/formOrderItem.html")

                context.update(**order_details_section(disable_remove_button=True))
                templates.append("order/bodySection/detailsSection.html")

                context.update(**order_actions_section())

                self.membersOrders({"message": {"message_type": "membersOrders"}})
            else:
                context.update(EM.FINISH_ORDER)
                context.update(**order_actions_section(order=order, add_order_id=True))

            templates.append("order/bottomSection/actions/finishOrder.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def membersOrders(self, event):
        group = event.get("group", True)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        context.update(**order_list_section(group=self.group))
        templates.append("order/bodySection/listSection.html")
        response = templates_joiner(context, templates)
        self.send(text_data=response)

    def OrdersList(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}
        user = self.scope["user"]

        all_orders = event[self.message].get("all_orders")

        if all_orders:
            context.update(**order_list_section(group=self.group))
            context.update(**order_actions_section())
        else:
            context.update(**order_list_section(user=user, group=self.group))
            context.update(**order_actions_section(all_orders=True))

        templates.append("order/bodySection/listSection.html")
        templates.append("order/bottomSection/actions/getOrderList.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def deleteOrderItem(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}
        user = self.scope["user"]
        context.update({"user": user})

        orderItemObj = OrderItem.objects.get(pk=event[self.message].get("item_id"))
        if orderItemObj.fk_order.fk_user != user:
            return

        order_id = orderItemObj.fk_order

        context.update({**order_details_section(order=order_id, add_view=True)})
        templates.append("order/bodySection/detailsSection.html")

        orderItemObj.delete()
        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def showMemberItemOrders(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}
        user = self.scope["user"]
        context.update({"user": user})

        context.update({**order_details_section(order=event[self.message].get("item_id"), add_view=True, disable_remove_button=True)})
        templates.append("order/bodySection/detailsSection.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def groupOrderSummary(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}
        user = self.scope["user"]

        UserModel = get_user_model()

        if get_all_orders(group=self.group).count() == 0:
            templates.append("order/bottomSection/actions/orderSummary.html")
            context.update(EM.ORDER_SUMMARY)
        else:

            orderTotalSummary = (
                Restaurant.objects.filter(
                    menuitem__orderitem__fk_order__created__date=timezone.now(), menuitem__orderitem__fk_order__fk_group=self.group
                )
                .values(
                    restaurant=F("name"),
                    item=F("menuitem__name"),
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
                Restaurant.objects.filter(
                    menuitem__orderitem__fk_order__created__date=timezone.now(), menuitem__orderitem__fk_order__fk_group=self.group
                )
                .values(
                    restaurant=F("name"),
                    item=F("menuitem__name"),
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
                UserModel.objects.filter(order__created__date=timezone.now(), order__finished_ordering=True, order__fk_group=self.group)
                .values(
                    user=F("username"),
                    restaurant=F("order__orderitem__fk_menu_item__fk_restaurant__name"),
                    item=F("order__orderitem__fk_menu_item__name"),
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

            templates.append("order/bottomSection/actions/summaryTables.html")

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
                    "table_headers": ["#", _("Item"), _("Price"), _("Quantity"), _("Total")],
                }
            )
        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def switchView(self, event):
        templates = []
        context = {}
        user = self.scope["user"]
        context.update({"user": user})

        view_context = get_context(user=user, group=self.group, view=event[self.message].get("next_view"))

        context.update(view_context)
        templates.append("base/body.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def sendNotification(self, event):
        group = event.get("group", True)
        if group:
            self.self_dispatch(event)
            return
        templates = []
        context = {}
        user = self.scope["user"]

        templates.append("base/helpers/notification.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def updateUsersConnectedCount(self):
        async_to_sync(self.channel_layer.group_send)(
            HOME_GROUP_NAME,
            {
                "type": "updateConnectedUsers",
                "message": {
                    "message_type": "updateConnectedUsers",
                    "ctx": {
                        "item": {
                            "name": self.group.name,
                            "room_number": self.group.room_number,
                            "connected_users": self.group.connected_users(),
                        }
                    },
                },
            },
        )


class RestaurantConsumer(JsonWebsocketConsumer):
    message_type = "message_type"
    message = "message"

    def connect(self):
        self.room_name = RESTAURANT_ROOM_NAME
        self.room_group_name = RESTAURANT_GROUP_NAME
        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        print(f"Connected to group: {self.room_group_name} , channel : {self.channel_name}")
        self.accept()
        self.updateRestaurantBody()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)

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

    def updateRestaurantBody(self):
        templates = []
        context = {}
        user = self.scope["user"]
        context.update({"user": user})

        view_context = get_context(user=user, view=CV.RESTAURANT_VIEW)

        context.update(view_context)
        templates.append("restaurant/body.html")

        response = templates_joiner(context, templates)
        self.send(text_data=response)

    def showRestaurantItems(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        context.update({**restaurant_details_section(restaurant=event[self.message].get("item_id"), add_view=True)})
        context.update({"remove_errors": True})

        templates.append("restaurant/bodySection/detailsSection.html")
        templates.append("restaurant/bottomSection/form/formMenuItem.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def addRestaurant(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        form = RestaurantForm(event[self.message])
        if form.is_valid():
            instance = form.save(True)
            context.update(**restaurant_list_section())
            context.update(**restaurant_context(restaurant=instance.id))
            templates.append("restaurant/bodySection/listSection.html")
            templates.append("restaurant/bodySection/detailsSection.html")
            templates.append("restaurant/bottomSection/form/formMenuItem.html")
        else:
            context.update({"form": form})

        templates.append("restaurant/bottomSection/form/formRestaurant.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def deleteMenuItem(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        MenuItemObj = MenuItem.objects.get(pk=event[self.message].get("item_id"))

        restaurant_id = MenuItemObj.fk_restaurant.id

        context.update({**restaurant_details_section(restaurant=restaurant_id, add_view=True)})

        templates.append("restaurant/bodySection/detailsSection.html")

        MenuItemObj.delete()

        response = templates_joiner(context, templates)

        self.send(text_data=response)

    def addMenuItem(self, event):
        group = event.get("group", False)
        if group:
            self.self_dispatch(event)
            return

        templates = []
        context = {}

        form = MenuItemForm(event[self.message])
        if form.is_valid():
            form.save(True)
            context.update({**restaurant_details_section(restaurant=event[self.message].get("fk_restaurant"), add_view=True)})
            templates.append("restaurant/bodySection/detailsSection.html")
        else:
            context.update({"form": form})

        templates.append("restaurant/bottomSection/form/formMenuItem.html")

        response = templates_joiner(context, templates)

        self.send(text_data=response)
