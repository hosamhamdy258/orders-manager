import os
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# Now this script or any imported module can use any part of Django it needs.
import random

from django.contrib.auth import get_user_model

from orderApp.models import MenuItem, Order, OrderGroup, OrderItem, Restaurant

UserModel = get_user_model()


# Constants
NUM_USERS = 4
NUM_GROUPS = 4
NUM_RESTAURANTS = 4
NUM_MENU_ITEMS = 4
ORDERS = 4

users = {f"user{i}" for i in range(1, NUM_USERS + 1)}
groups = {f"Group {i}" for i in range(1, NUM_GROUPS + 1)}
restaurants = {f"Restaurant {i}" for i in range(1, NUM_RESTAURANTS + 1)}
menu_items = {f"Item {i}" for i in range(1, NUM_MENU_ITEMS + 1)}

# Create Users
all_users = set(UserModel.objects.values_list("username", flat=True))
for user in users - all_users:
    UserModel.objects.create_user(username=user, email=f"{user}@example.com", password="password")

# # Create Groups
all_groups = set(OrderGroup.objects.values_list("name", flat=True))
for group in groups - all_groups:
    OrderGroup.objects.create(name=group, room_number=f"g{time.time_ns()}")

# Create Restaurants
all_restaurants = set(Restaurant.objects.values_list("name", flat=True))
for restaurant in restaurants - all_restaurants:
    Restaurant.objects.create(name=restaurant)

# Create Menu Items success
all_menu_items_with_restaurant = {(restaurant, item) for restaurant, item in MenuItem.objects.values_list("fk_restaurant__name", "name")}
restaurant_menu_items = {(restaurant, menu_item) for menu_item in menu_items for restaurant in restaurants}
for restaurant, menu_item in restaurant_menu_items - all_menu_items_with_restaurant:
    MenuItem.objects.create(fk_restaurant=Restaurant.objects.get(name=restaurant), name=menu_item, price=random.randrange(5, 20))


# Create Orders
all_order_with_users = {(user, group) for user, group in Order.objects.values_list("fk_user__username", "fk_group__name")}
users_orders = {(user, group) for group in groups for user in users}
for user, group in users_orders - all_order_with_users:
    Order.objects.create(fk_user=UserModel.objects.get(username=user), fk_group=OrderGroup.objects.get(name=group), finished_ordering=True)


# Create Order Items
all_orders_with_items = {
    (user, group, restaurant, menu_item)
    for user, group, restaurant, menu_item in OrderItem.objects.values_list(
        "fk_order__fk_user__username", "fk_order__fk_group__name", "fk_menu_item__fk_restaurant__name", "fk_menu_item__name"
    )
}
orders_items = {(user, group, restaurant, menu_item) for group in groups for user in users for restaurant in restaurants for menu_item in menu_items}
for user, group, restaurant, menu_item in orders_items - all_orders_with_items:
    OrderItem.objects.create(
        fk_order=Order.objects.get(fk_user__username=user, fk_group__name=group),
        fk_menu_item=MenuItem.objects.get(fk_restaurant__name=restaurant, name=menu_item),
        quantity=random.randint(1, 5),
    )
