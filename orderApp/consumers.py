from datetime import datetime
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from django.db.models import F, Sum, DecimalField
from django.utils.translation import gettext as _


from orderApp.utils import calculate_totals, group_nested_data


from orderApp.models import Clients, MenuItem, OrderItem, Restaurant
from orderApp.forms import MenuItemForm, OrderItemForm, RestaurantForm

from orderApp.utils import templates_joiner
from orderApp.orderContext import (
    create_order_updated,
    finish_order,
    get_all_orders,
    order_actions_section,
    order_details_section,
    order_form_id,
    order_form_section,
    order_list_section,
)
from orderApp.restaurantContext import restaurant_context, restaurant_details_section, restaurant_list_section
from orderApp.views import get_context

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
        Clients.objects.create(channel_name=self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)
        Clients.objects.filter(channel_name=self.channel_name).delete()

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
            context = {"user": user}

            if not event[self.message].get("fk_order"):
                event[self.message]["fk_order"] = create_order_updated(user)

            form = OrderItemForm(event[self.message])
            if form.is_valid():
                form.save(True)

                form = OrderItemForm(initial={**form.cleaned_data, "fk_menu_item": None, "quantity": None})
                context.update({"form": form})
                context.update({"remove_errors": True})

                context.update(**order_details_section(order=event[self.message]["fk_order"], add_view=True))
                templates.append("base/bodySection/detailsSection.html")

                context.update(**order_actions_section())
                templates.append("order/bottomSection/actions/finish_order_id.html")
            else:
                context.update({"form": form})

            templates.append("order/bottomSection/form/formOrderItem.html")
            context.update(**order_form_section(user=user, restaurant=event[self.message].get("fk_restaurant")))

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

            isFinished, finish_order_error, order = finish_order(event[self.message].get("fk_order"))
            if isFinished:
                context.update({"remove_errors": True})

                context.update(**order_form_id())
                templates.append("order/bottomSection/form/form_order_id.html")

                context.update(**order_details_section())
                templates.append("base/bodySection/detailsSection.html")

                context.update(**order_actions_section())

                # ! to be announcements
                self.membersOrders({"message": {"message_type": "membersOrders"}})
            else:
                context.update({"finish_order_error": finish_order_error})
                context.update(**order_actions_section(order=order, add_order_id=True))

            templates.append("order/bottomSection/actions/finishOrder.html")

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

            context.update(**order_list_section())
            templates.append("base/bodySection/listSection.html")
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

            context.update(**order_list_section(user))
            templates.append("base/bodySection/listSection.html")

            context.update(**order_details_section())
            templates.append("base/bodySection/detailsSection.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def deleteOrderItem(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]
            context.update({"user": user})

            orderItemObj = OrderItem.objects.get(pk=event[self.message].get("item_id"))
            if orderItemObj.fk_order.fk_user != user:
                return

            order_id = orderItemObj.fk_order

            context.update({**order_details_section(order=order_id, add_view=True)})
            templates.append("base/bodySection/detailsSection.html")

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

            context.update({**order_details_section(order=event[self.message].get("item_id"), add_view=True)})
            templates.append("base/bodySection/detailsSection.html")

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
                templates.append("order/bottomSection/actions/orderSummary.html")
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
                    }
                )

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def switchView(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]
            context.update({"user": user})

            view_context = get_context(user=user, view=event[self.message].get("next_view"))

            context.update(view_context)
            templates.append("base/body.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def showRestaurantItems(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]
            context.update({"user": user})

            context.update({**restaurant_details_section(restaurant=event[self.message].get("item_id"), add_view=True)})
            context.update({"remove_errors": True})

            templates.append("base/bodySection/detailsSection.html")
            templates.append("restaurant/bottomSection/form/formMenuItem.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def addRestaurant(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]
            context.update({"user": user})

            form = RestaurantForm(event[self.message])
            if form.is_valid():
                instance = form.save(True)
                context.update(**restaurant_list_section())
                context.update(**restaurant_context(restaurant=instance.id))
                templates.append("base/bodySection/listSection.html")
                templates.append("base/bodySection/detailsSection.html")
                templates.append("restaurant/bottomSection/form/formMenuItem.html")
            else:
                context.update({"form": form})

            templates.append("restaurant/bottomSection/form/formRestaurant.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def deleteMenuItem(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]
            context.update({"user": user})

            MenuItemObj = MenuItem.objects.get(pk=event[self.message].get("item_id"))

            restaurant_id = MenuItemObj.fk_restaurant.id

            context.update({**restaurant_details_section(restaurant=restaurant_id, add_view=True)})

            templates.append("base/bodySection/detailsSection.html")

            MenuItemObj.delete()

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass

    def addMenuItem(self, event):
        group = event.get("group", False)
        if group:  # to recursive call dispatch method
            self.self_dispatch(event)
        else:
            templates = []
            context = {}
            user = self.scope["user"]
            context.update({"user": user})

            form = MenuItemForm(event[self.message])
            if form.is_valid():
                form.save(True)
                context.update({**restaurant_details_section(restaurant=event[self.message].get("fk_restaurant"), add_view=True)})
                templates.append("base/bodySection/detailsSection.html")
            else:
                context.update({"form": form})

            templates.append("restaurant/bottomSection/form/formMenuItem.html")

            response = templates_joiner(context, templates)

            self.send(text_data=response)
            pass
