import os
import random
import time
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from orderApp.models import (
    MenuItem,
    Order,
    OrderGroup,
    OrderItem,
    OrderRoom,
    Restaurant,
)

UserModel = get_user_model()
# Create Superuser
if not UserModel.objects.filter(username="admin").exists():
    UserModel.objects.create_superuser("admin", "admin@example.com", "admin")

# Config
NUM_USERS = 4
NUM_GROUPS = 4
NUM_RESTAURANTS = 4
NUM_MENU_ITEMS = 4

users = {f"user{i}" for i in range(1, NUM_USERS + 1)}
# groups = {f"Group {i}" for i in range(1, NUM_GROUPS + 1)}
groups = {_("Backend Team"), _("Frontend Team"), _("AI Team"), _("Testing Team")}
# restaurants = {f"Restaurant {i}" for i in range(1, NUM_RESTAURANTS + 1)}
restaurants = {_("Between the Breads"), _("Baladi Sandwiches"), _("Aish & Foul"), _("Funky Falafel")}
# menu_items = {f"Item {i}" for i in range(1, NUM_MENU_ITEMS + 1)}
menu_items = {_("Falafel"), _("Foul"), _("Eggs"), _("French fries")}

# 1) Create Users
existing_usernames = set(UserModel.objects.values_list("username", flat=True))
for username in users - existing_usernames:
    UserModel.objects.create_user(username=username, email=f"{username}@example.com", password="password")

# Ensure we have at least one user to be the owner for groups
owner_username = sorted(list(users))[0]  # e.g. "user1"
owner = UserModel.objects.get(username=owner_username)

# 2) Create OrderGroups (each group will own one OrderRoom with the same name)
existing_groups = set(OrderGroup.objects.values_list("name", flat=True))
for group_name in groups - existing_groups:
    OrderGroup.objects.create(name=group_name, fk_owner=owner, pin=0)  # pin default set to 0

# 3) Create OrderRooms (each room tied to a group)
existing_rooms = set(OrderRoom.objects.values_list("name", flat=True))
for room_name in groups - existing_rooms:
    # link to the OrderGroup with same name (we created it above)
    fk_order_group = OrderGroup.objects.get(name=room_name)
    OrderRoom.objects.create(name=room_name, room_number=f"g{time.time_ns()}", fk_order_group=fk_order_group)

# 4) Create Restaurants
existing_restaurants = set(Restaurant.objects.values_list("name", flat=True))
for restaurant_name in restaurants - existing_restaurants:
    Restaurant.objects.create(name=restaurant_name)

# 5) Create Menu Items for each restaurant
existing_menu_items = set(MenuItem.objects.values_list("fk_restaurant__name", "name"))
for restaurant_name in restaurants:
    restaurant_obj = Restaurant.objects.get(name=restaurant_name)
    for item_name in menu_items:
        key = (restaurant_name, item_name)
        if key not in existing_menu_items:
            # price is Decimal with 2 decimal places
            cents = random.randint(500, 2000)  # 5.00 .. 20.00
            price = Decimal(cents) / Decimal(100)
            MenuItem.objects.create(fk_restaurant=restaurant_obj, name=item_name, price=price)

# 6) Create Orders
# Adjusted to use fk_order_room (new field)
existing_orders = {(user, room) for user, room in Order.objects.values_list("fk_user__username", "fk_order_room__name")}
desired_orders = {(user, group) for group in groups for user in users}
for user, group in desired_orders - existing_orders:
    Order.objects.create(
        fk_user=UserModel.objects.get(username=user),
        fk_order_room=OrderRoom.objects.get(name=group),
        finished_ordering=True,
    )

# 7) Create OrderItems
existing_order_items = {
    (user, room, restaurant, menu_item)
    for user, room, restaurant, menu_item in OrderItem.objects.values_list(
        "fk_order__fk_user__username",
        "fk_order__fk_order_room__name",
        "fk_menu_item__fk_restaurant__name",
        "fk_menu_item__name",
    )
}
desired_order_items = {(user, group, restaurant, menu_item) for group in groups for user in users for restaurant in restaurants for menu_item in menu_items}

for user, group, restaurant, menu_item in desired_order_items - existing_order_items:
    # get the order and menu item for the relation
    order = Order.objects.get(fk_user__username=user, fk_order_room__name=group)
    menu_item_obj = MenuItem.objects.get(fk_restaurant__name=restaurant, name=menu_item)
    OrderItem.objects.create(fk_order=order, fk_menu_item=menu_item_obj, quantity=random.randint(1, 5))

print("Database population script finished.")
