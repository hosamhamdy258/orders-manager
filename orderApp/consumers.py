from functools import wraps

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.db.models import DecimalField, F, Sum
from django.urls import reverse
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
from orderApp.models import (
    GroupRetries,
    MenuItem,
    OrderGroup,
    OrderItem,
    OrderRoom,
    Restaurant,
)
from orderApp.orderGroupContext import OrderGroupContext
from orderApp.orderRoomContext import OrderRoomContext
from orderApp.orderSelectionContext import (
    OrderSelectionContext,
    create_order_checks,
    finish_order,
    get_last_order,
    get_order,
)
from orderApp.restaurantContext import RestaurantContext
from orderApp.utils import calculate_totals, group_nested_data, templates_builder
from orderApp.views import get_context

UserModel = get_user_model()
ORDER_GROUP_CHANNEL = "orderGroup"
ORDER_GROUP_CHANNEL_GROUP = f"GROUP_{ORDER_GROUP_CHANNEL}"

ORDER_ROOM_CHANNEL = "orderRoom"
ORDER_ROOM_CHANNEL_GROUP = f"GROUP_{ORDER_ROOM_CHANNEL}"

ORDER_SELECTION_CHANNEL = "orderSelection"
ORDER_SELECTION_CHANNEL_GROUP = f"GROUP_{ORDER_SELECTION_CHANNEL}"

RESTAURANT_ROOM_CHANNEL = "restaurantRoom"
RESTAURANT_ROOM_CHANNEL_GROUP = f"GROUP_{RESTAURANT_ROOM_CHANNEL}"


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
    channel_name = None
    channel_group_name = None
    user = None
    view = None
    group = None
    body_template = None
    context_class = None
    context_builder = None

    def get_user(self):
        if self.user is None:
            self.user = self.scope["user"]
        return self.user

    def connect(self):
        self.get_user()
        async_to_sync(self.channel_layer.group_add)(self.get_channel_group_name(), self.get_channel_name())
        self.accept()
        self.after_connect()

    def after_connect(self):
        self.get_context_builder()
        self.updatePageBody()

    def after_disconnect(self):
        pass

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.get_channel_group_name(), self.get_channel_name())
        self.after_disconnect()

    def get_channel_name(self):
        if self.channel_name is None:
            raise NotImplementedError("Subclasses must define channel_name or implement get_channel_name()")
        return self.channel_name

    def get_channel_group_name(self):
        if self.channel_group_name is None:
            raise NotImplementedError("Subclasses must define channel_group_name or implement get_channel_group_name()")
        return self.channel_group_name

    def get_context_class(self):
        if self.context_class is None:
            raise NotImplementedError("Subclasses must define context_class or implement get_context_class()")
        return self.context_class

    def get_context_builder(self):
        if self.context_builder is None:
            self.context_builder = self.get_context_class()(**self.get_context_builder_kwargs())
        return self.context_builder

    def get_context_builder_kwargs(self):
        return {"user": self.get_user()}

    def receive_json(self, content, **kwargs):
        event_type = content.get(self.message_type, "")
        message = dict(message=content)
        handler = getattr(self, event_type, self.default_handler)
        try:
            handler(message)
        except Exception as e:
            print(e)

    def default_handler(self, message):
        print(f"Unknown event type received: {message}")

    def self_dispatch(self, event):
        # ! add handle for this 2 cases
        # ! from regular dispatch inside consumer
        #  ?{"message": {"message_type": "membersOrders"}}
        # ! from outside consumers
        # ?{"type": "sendNotification", "message": {"message_type": "sendNotification"}}
        try:
            async_to_sync(self.channel_layer.group_send)(
                self.get_channel_group_name(), {"type": event[self.message][self.message_type], self.message: event[self.message], "group": False}
            )
        except Exception as e:
            print(e)

    def updatePageBody(self):
        templates, context = [], {}
        # TODO fix this as we build context already in build context
        context.update(**self.get_context_builder().get_full_context())
        templates.append(self.body_template)
        self.response_builder(templates, context)

    def response_builder(self, templates, context):
        response = templates_builder(context, templates)
        for part in response:
            self.send(text_data=part)


class OrderGroupConsumer(BaseConsumer):
    channel_name = ORDER_GROUP_CHANNEL
    channel_group_name = ORDER_GROUP_CHANNEL_GROUP
    view = CV.ORDER_GROUP
    body_template = "orderGroup/body.html"
    context_class = OrderGroupContext

    @group_message
    def sendUpdateGroupsList(self, event):
        self.updateGroupsListBuilder(event)

    def updateGroupsList(self, event):
        self.updateGroupsListBuilder(event)

    def updateGroupsListBuilder(self, event):
        templates, context = [], {}
        instance = event[self.message].get("instance")
        if instance:
            kwargs = {"instance": instance}
            context.update({"swap_method": "afterbegin"})
            templates.append("orderGroup/bodySection/listSectionBodyTable.html")
        else:
            kwargs = {}
            templates.append("orderGroup/bodySection/listSectionBody.html")
        context.update(**self.get_context_builder().get_list_context(**kwargs))
        self.response_builder(templates, context)

    def showGroupMembers(self, event):
        templates, context = [], {}
        order_group = OrderGroup.objects.get(pk=event[self.message].get("item_id"))
        if self.get_user() != order_group.fk_owner:
            return
        context.update({**self.get_context_builder().get_details_context(instance=event[self.message].get("item_id"))})
        context.update({"remove_errors": True})
        templates.append("orderGroup/bodySection/detailsSectionBodyTable.html")
        context.update({"swap_method": "innerHTML"})
        self.response_builder(templates, context)

    def addGroup(self, event):
        templates, context = [], {}
        event[self.message].update({"fk_owner": self.get_user()})
        form = OrderGroupForm(event[self.message])
        if form.is_valid():
            instance = form.save(True)
            instance.add_user_to_group(user=self.get_user())
            self.sendUpdateGroupsList({"message": {"message_type": "sendUpdateGroupsList", "instance": instance}})
        else:
            context.update({"form": form})
        templates.append("orderGroup/bottomSection/form/formGroupItem.html")
        self.response_builder(templates, context)

    def enterGroup(self, event):
        templates, context = [], {}
        user = self.get_user()

        order_group = OrderGroup.objects.get(pk=event[self.message].get("item_id"))
        pin = event[self.message].get("pin")
        valid_pin = pin.isdigit()
        if not valid_pin:
            # self.send_join_form(templates, context, order_group, error_msg="PIN must contain numbers")
            return
        retry_instance, created = GroupRetries.objects.get_or_create(fk_user=user, fk_order_group=order_group)
        block_msg = lambda: f"You're Blocked Try Again after {retry_instance.get_lock_time_left()} Min"
        if not retry_instance.can_retry():
            self.send_join_form(templates, context, order_group, error_msg=block_msg())
        else:
            if order_group.pin == int(pin):
                context.update({"url": reverse("order_room", args=[order_group.group_number])})
                templates.append("base/helpers/redirector.html")
                order_group.add_user_to_group(self.get_user())
                self.updateConnectedUsers({"message": {"message_type": "updateConnectedUsers", "instance": order_group}})
            else:
                retry_instance.failed_retry()
                if retry_instance.can_retry():
                    self.send_join_form(templates, context, order_group, error_msg=f"Invalid Pin Retries left {retry_instance.retry}")
                else:
                    self.send_join_form(templates, context, order_group, error_msg=block_msg())

        self.response_builder(templates, context)

    def send_join_form(self, templates, context, order_group, error_msg=""):
        context.update(**self.get_context_builder().get_list_context(instance=order_group))
        context.update({"item": order_group})
        context.update({"join_form_error": _(error_msg)})
        templates.append("orderGroup/bodySection/joinForm.html")

    @group_message
    def updateConnectedUsers(self, event):
        templates, context = [], {}
        context.update({"item": event[self.message]["instance"]})
        templates.append("orderGroup/bodySection/connectedUsers.html")
        self.response_builder(templates, context)


class OrderRoomConsumer(BaseConsumer):
    channel_name = ORDER_ROOM_CHANNEL
    channel_group_name = ORDER_ROOM_CHANNEL_GROUP
    view = CV.ORDER_ROOM
    body_template = "orderRoom/body.html"
    context_class = OrderRoomContext

    @group_message
    def updateRoomsList(self, event):
        templates, context = [], {}
        context.update(**self.get_context_builder().get_list_context(instance=event["message"].get("instance")))
        templates.append("orderRoom/bodySection/listSectionBodyTable.html")
        self.response_builder(templates, context)

    def showRoomMembers(self, event):
        templates, context = [], {}
        context.update({**self.get_context_builder().get_details_context(instance=event[self.message].get("item_id"))})
        context.update({"remove_errors": True})
        templates.append("orderRoom/bodySection/detailsSectionBodyTable.html")
        context.update({"swap_method": "innerHTML"})
        self.response_builder(templates, context)

    def addGroup(self, event):
        templates, context = [], {}
        event[self.message].update({"fk_order_group": self.get_order_group()})
        form = OrderRoomForm(event[self.message])
        if form.is_valid():
            instance = form.save(True)
            self.updateRoomsList({"message": {"message_type": "updateRoomsList", "instance": instance}})
        else:
            context.update({"form": form})
        templates.append("orderRoom/bottomSection/form/formGroupItem.html")
        self.response_builder(templates, context)

    def get_order_group(self):
        # TODO user has attr for check instead of None
        self.order_group = OrderGroup.objects.get(group_number=self.scope["url_route"]["kwargs"]["group_name"])
        return self.order_group

    def get_context_builder_kwargs(self):
        kwargs = super().get_context_builder_kwargs()
        kwargs.update({"order_group": self.get_order_group()})
        return kwargs

    @group_message
    def updateConnectedUsers(self, event):
        templates, context = [], {}
        context.update({"item": event[self.message]["instance"]})
        templates.append("orderRoom/bodySection/connectedUsers.html")
        self.response_builder(templates, context)


class OrderSelectionConsumer(BaseConsumer):
    channel_name = ORDER_SELECTION_CHANNEL
    channel_group_name = ORDER_SELECTION_CHANNEL_GROUP
    view = CV.ORDER_SELECTION
    body_template = "orderSelection/body.html"
    context_class = OrderSelectionContext

    def after_connect(self):
        self.add_user_to_room()
        self.updateUsersConnectedCount()
        super().after_connect()

    def get_context_builder_kwargs(self):
        kwargs = super().get_context_builder_kwargs()
        kwargs.update({"order_group": self.get_order_group(), "order_room": self.get_order_room()})
        return kwargs

    def get_order_group(self):
        # TODO use has attr for check instead of None
        self.order_group = OrderGroup.objects.get(group_number=self.scope["url_route"]["kwargs"]["group_name"])
        return self.order_group

    def get_order_room(self):
        # TODO use has attr for check instead of None
        self.order_room = OrderRoom.objects.get(room_number=self.scope["url_route"]["kwargs"]["room_name"])
        return self.order_room

    def add_user_to_room(self):
        self.get_order_room().add_user_to_room(self.get_user())

    def remove_user_from_room(self):
        self.get_order_room().remove_user_from_room(self.get_user())

    def after_disconnect(self):
        super().after_disconnect()
        self.remove_user_from_room()
        self.updateUsersConnectedCount()

    def addOrderItem(self, event):
        templates, context = [], {}

        # TODO check order id is belong to this user and last order in room

        state = get_order(user=self.get_user(), order_room=self.get_order_room())

        # TODO improve error msgs handling
        if state.get("disabled") and state["reason"] == "time_out":
            context.update(EM.TIME_UP)
            templates.append("orderSelection/bottomSection/error_time_expired.html")
        elif state.get("disabled") and state["reason"] == "order_limit":
            context.update(EM.CREATE_ORDER)

        if state.get("created", False):
            event[self.message].update({"fk_order": state.get("order")})
            if not event[self.message].get("fk_order"):
                raise ValueError("fk_order")
            # TODO use form in template instead of manually render fields
            form = OrderItemForm(event[self.message])
            if form.is_valid():
                instance = form.save(True)
                form = OrderItemForm(initial={**form.cleaned_data, "fk_menu_item": None, "quantity": None})
                context.update({"form": form})
                context.update({"remove_errors": True})

                context.update(**self.get_context_builder().get_details_context(instance=instance))
                # TODO refactor body tables sections as they're so similar
                templates.append("orderSelection/bodySection/detailsSectionBodyTable.html")

            else:
                context.update({"form": form})

        templates.append("orderSelection/bottomSection/form/formOrderItem.html")
        context.update(**self.get_context_builder().get_form_context(restaurant_instance=event[self.message].get("fk_restaurant")))

        self.response_builder(templates, context)

    def finishOrder(self, event):
        templates, context = [], {}

        order = get_last_order(user=self.get_user(), order_room=self.get_order_room())
        if order:
            event[self.message].update({"fk_order": order.pk})

        state = create_order_checks(user=self.get_user(), order_room=self.get_order_room())
        if state.get("disabled") and state["reason"] == "time_out":
            context.update(EM.TIME_UP)
            templates.append("orderSelection/bottomSection/error_time_expired.html")
        else:
            finished_state = finish_order(event[self.message].get("fk_order"))

            if finished_state["finished"]:
                context.update({"remove_errors": True})

                context.update(**self.get_context_builder().get_form_context())
                templates.append("orderSelection/bottomSection/form/formOrderItem.html")

                context.update(**self.get_context_builder().get_details_context())
                templates.append("orderSelection/bodySection/detailsSection.html")

                self.membersOrders({"message": {"message_type": "membersOrders", "instance": order}})

            else:
                context.update(EM.FINISH_ORDER)

            templates.append("orderSelection/bottomSection/actions/finishOrder.html")

        self.response_builder(templates, context)

    @group_message
    def membersOrders(self, event):
        templates, context = [], {}
        context.update(**self.get_context_builder().get_list_context(instance=event["message"].get("instance")))
        templates.append("orderSelection/bodySection/listSectionBodyTable.html")
        self.response_builder(templates, context)

    def OrdersList(self, event):
        templates, context = [], {}

        all_orders = bool(event[self.message].get("all_orders"))

        if all_orders:
            context.update(**self.get_context_builder().get_list_context(all_orders=all_orders))
            context.update(**self.get_context_builder().get_extra_context(all_orders=all_orders))
        else:
            order = get_last_order(user=self.get_user(), order_room=self.get_order_room(), finished=True)
            context.update(**self.get_context_builder().get_list_context(instance=order, all_orders=all_orders))
            context.update(**self.get_context_builder().get_extra_context(all_orders=all_orders))

        # TODO make the update only on inner table
        templates.append("orderSelection/bodySection/listSectionBody.html")
        templates.append("orderSelection/bottomSection/actions/getOrderList.html")

        self.response_builder(templates, context)

    def deleteOrderItem(self, event):
        templates, context = [], {}

        orderItemObj = OrderItem.objects.get(pk=event[self.message].get("item_id"))

        if orderItemObj.fk_order.fk_user != self.get_user():
            return
        # TODO validation for delete is on right order and can delete [finished orders]
        orderItemObj.delete()
        context.update({"item_id": event[self.message].get("item_id")})
        templates.append("orderSelection/bodySection/row_remove.html")

        self.response_builder(templates, context)

    def showMemberItemOrders(self, event):
        templates, context = [], {}
        # TODO validate order_id in same room

        context.update(
            {**self.get_context_builder().get_details_context(order_instance=event[self.message].get("item_id"), disable_remove_button=True)}
        )
        templates.append("orderSelection/bodySection/order_items_modal.html")

        self.response_builder(templates, context)

    # ! did check this function yet
    def groupOrderSummary(self, event):
        templates, context = [], {}

        UserModel = get_user_model()

        if self.get_context_builder().get_all_orders(order_room=self.get_order_room()).count() == 0:
            templates.append("orderSelection/bottomSection/actions/orderSummary.html")
            context.update(EM.ORDER_SUMMARY)
        else:
            orderTotalSummary = (
                Restaurant.objects.filter(
                    menuitem__orderitem__fk_order__created__date=timezone.now(), menuitem__orderitem__fk_order__fk_order_room=self.get_order_room()
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
                    menuitem__orderitem__fk_order__created__date=timezone.now(), menuitem__orderitem__fk_order__fk_order_room=self.get_order_room()
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
                UserModel.objects.filter(
                    order__created__date=timezone.now(), order__finished_ordering=True, order__fk_order_room=self.get_order_room()
                )
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

            templates.append("orderSelection/bottomSection/actions/summaryTables.html")

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

    def updateUsersConnectedCount(self):
        async_to_sync(self.channel_layer.group_send)(
            ORDER_ROOM_CHANNEL_GROUP,
            {
                "type": "updateConnectedUsers",
                "message": {"message_type": "updateConnectedUsers", "instance": self.get_order_room()},
            },
        )


class RestaurantConsumer(BaseConsumer):
    channel_name = RESTAURANT_ROOM_CHANNEL
    channel_group_name = RESTAURANT_ROOM_CHANNEL_GROUP
    view = CV.RESTAURANT
    body_template = "restaurant/body.html"
    context_class = RestaurantContext

    def showRestaurantItems(self, event):
        templates, context = [], {}

        context.update({**self.get_context_builder().get_details_context(instance=event[self.message].get("item_id"))})
        context.update({"remove_errors": True})

        templates.append("restaurant/bodySection/detailsSectionBodyTable.html")
        context.update({"swap_method": "innerHTML"})
        templates.append("restaurant/bottomSection/form/formMenuItem.html")

        self.response_builder(templates, context)

    def addRestaurant(self, event):
        templates, context = [], {}
        #  TODO Make restaurant linked to group for approvement later
        form = RestaurantForm(event[self.message])
        if form.is_valid():
            instance = form.save(True)
            context.update(**self.get_context_builder().get_list_context(instance=instance))
            templates.append("restaurant/bodySection/listSectionBodyTable.html")

            templates.append("restaurant/bodySection/detailsSection.html")
            templates.append("restaurant/bottomSection/form/formMenuItem.html")
        else:
            context.update({"form": form})

        templates.append("restaurant/bottomSection/form/formRestaurant.html")

        self.response_builder(templates, context)

    def deleteMenuItem(self, event):
        templates, context = [], {}
        MenuItemObj = MenuItem.objects.get(pk=event[self.message].get("item_id"))
        # TODO do checks for item belong to current user
        # TODO change to soft delete
        MenuItemObj.delete()

        context.update({"item_id": event[self.message].get("item_id")})
        templates.append("restaurant/bodySection/row_remove.html")

        self.response_builder(templates, context)

    def addMenuItem(self, event):
        templates, context = [], {}
        form = MenuItemForm(event[self.message])
        if form.is_valid():
            instance = form.save(True)
            context.update({**self.get_context_builder().get_details_context(menu_item=instance)})
            context.update({"swap_method": "afterbegin"})
            templates.append("restaurant/bodySection/detailsSectionBodyTable.html")
            form = MenuItemForm(initial={"fk_restaurant": event[self.message].get("fk_restaurant")})

        context.update({"form": form})
        templates.append("restaurant/bottomSection/form/formMenuItem.html")
        self.response_builder(templates, context)
