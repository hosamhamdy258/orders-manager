from channels_presence.models import Presence, Room
from django.contrib import admin

from orderApp.models import (
    Client,
    GroupRetries,
    MenuItem,
    Order,
    OrderGroup,
    OrderItem,
    OrderRoom,
    OrderRoomUser,
    Restaurant,
)


class MenuItemAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class OrderItemInlineAdmin(admin.TabularInline):
    model = OrderItem
    fields = ["fk_menu_item", "quantity"]
    extra = 0
    autocomplete_fields = ["fk_menu_item"]


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInlineAdmin]
    autocomplete_fields = ["fk_user", "fk_order_room"]


class OrderRoomAdmin(admin.ModelAdmin):
    # filter_horizontal = ["m2m_users"]
    autocomplete_fields = ["m2m_users"]
    search_fields = ["name", "room_number"]


class OrderGroupAdmin(admin.ModelAdmin):
    # filter_horizontal = ["m2m_users"]
    autocomplete_fields = ["fk_owner", "m2m_users"]


admin.site.register(Restaurant)
admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Client)
admin.site.register(OrderRoomUser)
admin.site.register(OrderRoom, OrderRoomAdmin)
admin.site.register(OrderGroup, OrderGroupAdmin)
admin.site.register(GroupRetries)
admin.site.register(Room)
admin.site.register(Presence)
