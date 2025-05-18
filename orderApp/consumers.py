import time
from functools import wraps

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.db.models import DecimalField, F, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from orderApp.enums import CurrentViews as CV
from orderApp.enums import ErrorMessage as EM
from orderApp.forms import (
    MenuItemForm,
    OrderGroupForm,
    OrderItemForm,
    OrderRoomForm,
    RestaurantForm,
)
from orderApp.models import MenuItem, OrderItem, OrderRoom, Restaurant
from orderApp.orderContext import (
    check_disable_form,
    create_order,
    finish_order,
    get_all_orders,
    order_selection_actions_section,
    order_selection_details_section,
    order_selection_form_section,
    order_selection_list_section,
)
from orderApp.orderGroupContext import OrderGroupContext
from orderApp.orderRoomContext import (
    order_room_context,
    order_room_details_section,
    order_room_list_section,
)
from orderApp.restaurantContext import (
    restaurant_context,
    restaurant_details_section,
    restaurant_list_section,
)
from orderApp.utils import calculate_totals, group_nested_data, templates_joiner
from orderApp.views import get_context

UserModel = get_user_model()
ORDER_GROUP_ROOM = "order_group_room"
ORDER_GROUP_ROOM_GROUP = f"group_{ORDER_GROUP_ROOM}"

RESTAURANT_ROOM_NAME = "restaurant_room"
RESTAURANT_GROUP_NAME = f"group_{RESTAURANT_ROOM_NAME}"


def group_message(fn):
    @wraps(fn)
    def wrapper(self, event, *args, **kwargs):
        if event.get("group", True):
            return self.self_dispatch(event)
        return fn(self, event, *args, **kwargs)

    return wrapper


class BaseConsumer(JsonWebsocketConsumer):
    message_type = "message_type"
    message = "message"
    room_name = None
    room_group_name = None
    user = None
    view = None
    group = None
    body_template = None
    context_class = None
    context = None

    def get_user(self):
        if self.user is None:
            self.user = self.scope["user"]
        return self.user

    def connect(self):
        self.get_user()
        async_to_sync(self.channel_layer.group_add)(self.get_room_group_name(), self.channel_name)
        self.accept()
        self.after_connect()

    def after_connect(self):
        self.updatePageBody()
        self.context = self.get_context_class()(user=self.get_user())

    def after_disconnect(self):
        pass

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.get_room_group_name(), self.channel_name)
        self.after_disconnect()

    def get_room_name(self):
        if self.room_name is None:
            raise NotImplementedError("Subclasses must define room_name or implement get_room_name()")
        return self.room_name

    def get_context_class(self):
        if self.context_class is None:
            raise NotImplementedError("Subclasses must define context_class or implement get_context_class()")
        return self.context_class

    def get_room_group_name(self):
        if self.room_group_name is None:
            raise NotImplementedError("Subclasses must define room_group_name or implement get_room_group_name()")
        return self.room_group_name

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
            self.get_room_group_name(), {"type": event[self.message][self.message_type], self.message: event[self.message], "group": False}
        )

    def updatePageBody(self):
        templates, context = [], {}

        context.update({"user": self.get_user(), **get_context(user=self.get_user(), view=self.view, group=self.group)})
        templates.append(self.body_template)

        self.response_builder(templates, context)

    def response_builder(self, templates, context):
        response = templates_joiner(context, templates)
        self.send(text_data=response)


class OrderGroupConsumer(BaseConsumer):
    room_name = ORDER_GROUP_ROOM
    room_group_name = ORDER_GROUP_ROOM_GROUP
    view = CV.ORDER_GROUP
    body_template = "orderGroup/body.html"
    context_class = OrderGroupContext

    # @group_message
    def updateGroupsList(self, event):
        templates, context = [], {}
        context.update({**self.context.get_list_context()})
        templates.append("orderGroup/bodySection/listSection.html")
        self.response_builder(templates, context)

    def showGroupMembers(self, event):
        templates, context = [], {}
        context.update({**self.context.get_details_context(instance=event[self.message].get("item_id"))})
        context.update({"remove_errors": True})
        templates.append("orderGroup/bodySection/detailsSection.html")
        self.response_builder(templates, context)

    def addGroup(self, event):
        templates, context = [], {}
        event[self.message].update({"fk_owner": self.get_user()})
        form = OrderGroupForm(event[self.message])
        if form.is_valid():
            instance = form.save(True)
            instance.add_user_to_group()
            context.update(**self.context.get_list_context(instance=instance))
            templates.append("orderGroup/bodySection/listSectionBodyTable.html")
            context.update({"htmx": True})
        else:
            context.update({"form": form})
        templates.append("orderGroup/bottomSection/form/formGroupItem.html")
        self.response_builder(templates, context)

    def updateConnectedUsers(self, event):
        templates, context = [], {}
        context.update(event[self.message]["ctx"])
        templates.append("orderGroup/bodySection/connectedUsers.html")
        self.response_builder(templates, context)


class OrderRoomConsumer(BaseConsumer):
    room_name = ORDER_GROUP_ROOM
    room_group_name = ORDER_GROUP_ROOM_GROUP
    view = CV.ORDER_ROOM
    body_template = "orderRoom/body.html"

    @group_message
    def updateGroupsList(self, event):
        templates, context = [], {}

        context.update(**order_room_list_section(add_view=True))
        templates.append("group/bodySection/listSection.html")

        self.response_builder(templates, context)

    def showGroupMembers(self, event):
        templates, context = [], {}

        context.update({**order_room_details_section(group=event[self.message].get("item_id"), add_view=True)})
        context.update({"remove_errors": True})

        templates.append("group/bodySection/detailsSection.html")

        self.response_builder(templates, context)

    def addGroup(self, event):
        templates, context = [], {}

        event[self.message].update({"room_number": f"g{time.time_ns()}"})
        form = OrderRoomForm(event[self.message])
        if form.is_valid():
            instance = form.save(True)
            context.update(**order_room_list_section())
            context.update(**order_room_context(group=instance.id))
            self.updateGroupsList({"message": {"message_type": "updateGroupsList"}})

        else:
            context.update({"form": form})

        templates.append("group/bottomSection/form/formGroupItem.html")

        self.response_builder(templates, context)

    # ! for testing
    @group_message
    def sendNotification(self, event):
        templates, context = [], {}

        templates.append("base/helpers/notification.html")

        self.response_builder(templates, context)

    def updateConnectedUsers(self, event):
        templates, context = [], {}

        context.update(event[self.message]["ctx"])
        templates.append("group/bodySection/connectedUsers.html")

        self.response_builder(templates, context)


class OrderSelectionConsumer(BaseConsumer):
    view = CV.ORDER_SELECTION
    body_template = "order/body.html"

    def after_connect(self):
        self.add_user_to_group()
        self.updateUsersConnectedCount()
        super().after_connect()

    def get_room_name(self):
        return self.scope["url_route"]["kwargs"]["group_name"]

    def get_room_group_name(self):
        return f"group_{self.room_name}"

    def add_user_to_group(self):
        self.group = OrderRoom.objects.get(room_number=self.get_room_name())
        self.group.m2m_users.add(self.get_user())

    def remove_user_from_group(self):
        self.group.m2m_users.remove(self.get_user())

    def after_disconnect(self):
        super().after_disconnect()
        self.remove_user_from_group()
        self.updateUsersConnectedCount()

    def addOrderItem(self, event):
        templates, context = [], {}

        context.update({"user": self.get_user()})

        form_state = check_disable_form(group=self.group, user=self.get_user())
        if form_state["force_disable"]:
            context.update(EM.TIME_UP)
            templates.append("order/bottomSection/error_time_expired.html")
        else:
            if not event[self.message].get("fk_order"):
                state, order = create_order(user=self.get_user(), group=self.group)

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

                context.update(**order_selection_details_section(order=event[self.message]["fk_order"], add_view=True))
                templates.append("order/bodySection/detailsSection.html")

                context.update(**order_selection_actions_section())
                templates.append("order/bottomSection/actions/finish_order_id.html")
            else:
                context.update({"form": form})

            templates.append("order/bottomSection/form/formOrderItem.html")
            context.update(
                **order_selection_form_section(user=self.get_user(), group=self.group, restaurant=event[self.message].get("fk_restaurant"))
            )

        self.response_builder(templates, context)

    def finishOrder(self, event):
        templates, context = [], {}

        form_state = check_disable_form(group=self.group, user=self.get_user())
        if form_state["force_disable"]:
            context.update(EM.TIME_UP)
            templates.append("order/bottomSection/error_time_expired.html")
        else:
            isFinished, order = finish_order(event[self.message].get("fk_order"))

            if isFinished:
                context.update({"remove_errors": True})

                context.update(**order_selection_form_section(user=self.get_user(), group=self.group))
                templates.append("order/bottomSection/form/formOrderItem.html")

                context.update(**order_selection_details_section(disable_remove_button=True))
                templates.append("order/bodySection/detailsSection.html")

                context.update(**order_selection_actions_section())

                self.membersOrders({"message": {"message_type": "membersOrders"}})
            else:
                context.update(EM.FINISH_ORDER)
                context.update(**order_selection_actions_section(order=order, add_order_id=True))

            templates.append("order/bottomSection/actions/finishOrder.html")

        self.response_builder(templates, context)

    @group_message
    def membersOrders(self, event):
        templates, context = [], {}

        context.update(**order_selection_list_section(group=self.group))
        templates.append("order/bodySection/listSection.html")
        self.response_builder(templates, context)

    def OrdersList(self, event):
        templates, context = [], {}

        all_orders = event[self.message].get("all_orders")

        if all_orders:
            context.update(**order_selection_list_section(group=self.group))
            context.update(**order_selection_actions_section())
        else:
            context.update(**order_selection_list_section(user=self.get_user(), group=self.group))
            context.update(**order_selection_actions_section(all_orders=True))

        templates.append("order/bodySection/listSection.html")
        templates.append("order/bottomSection/actions/getOrderList.html")

        self.response_builder(templates, context)

    def deleteOrderItem(self, event):
        templates, context = [], {}

        context.update({"user": self.get_user()})

        orderItemObj = OrderItem.objects.get(pk=event[self.message].get("item_id"))
        if orderItemObj.fk_order.fk_user != self.get_user():
            return

        order_id = orderItemObj.fk_order

        context.update({**order_selection_details_section(order=order_id, add_view=True)})
        templates.append("order/bodySection/detailsSection.html")

        orderItemObj.delete()
        self.response_builder(templates, context)

    def showMemberItemOrders(self, event):
        templates, context = [], {}

        context.update({"user": self.get_user()})

        context.update({**order_selection_details_section(order=event[self.message].get("item_id"), add_view=True, disable_remove_button=True)})
        templates.append("order/bodySection/detailsSection.html")

        self.response_builder(templates, context)

    def groupOrderSummary(self, event):
        templates, context = [], {}

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
        self.response_builder(templates, context)

    def switchView(self, event):
        templates, context = [], {}

        context.update({"user": self.get_user()})

        view_context = get_context(user=self.get_user(), group=self.group, view=event[self.message].get("next_view"))

        context.update(view_context)
        templates.append("base/body.html")

        self.response_builder(templates, context)

    @group_message
    def sendNotification(self, event):
        templates, context = [], {}

        templates.append("base/helpers/notification.html")

        self.response_builder(templates, context)

    def updateUsersConnectedCount(self):
        async_to_sync(self.channel_layer.group_send)(
            ORDER_GROUP_ROOM_GROUP,
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


class RestaurantConsumer(BaseConsumer):
    room_name = RESTAURANT_ROOM_NAME
    room_group_name = RESTAURANT_GROUP_NAME
    view = CV.RESTAURANT
    body_template = "restaurant/body.html"

    def showRestaurantItems(self, event):
        templates, context = [], {}

        context.update({**restaurant_details_section(restaurant=event[self.message].get("item_id"), add_view=True)})
        context.update({"remove_errors": True})

        templates.append("restaurant/bodySection/detailsSection.html")
        templates.append("restaurant/bottomSection/form/formMenuItem.html")

        self.response_builder(templates, context)

    def addRestaurant(self, event):
        templates, context = [], {}

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

        self.response_builder(templates, context)

    def deleteMenuItem(self, event):
        templates, context = [], {}

        MenuItemObj = MenuItem.objects.get(pk=event[self.message].get("item_id"))

        restaurant_id = MenuItemObj.fk_restaurant.id

        context.update({**restaurant_details_section(restaurant=restaurant_id, add_view=True)})

        templates.append("restaurant/bodySection/detailsSection.html")

        MenuItemObj.delete()

        self.response_builder(templates, context)

    def addMenuItem(self, event):
        templates, context = [], {}

        form = MenuItemForm(event[self.message])
        if form.is_valid():
            form.save(True)
            context.update({**restaurant_details_section(restaurant=event[self.message].get("fk_restaurant"), add_view=True)})
            templates.append("restaurant/bodySection/detailsSection.html")
        else:
            context.update({"form": form})

        templates.append("restaurant/bottomSection/form/formMenuItem.html")

        self.response_builder(templates, context)
