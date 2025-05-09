from django.contrib import admin

from orderApp.models import (
    Client,
    MenuItem,
    Order,
    OrderGroup,
    OrderItem,
    OrderRoom,
    Restaurant,
)


class OrderItemInlineAdmin(admin.TabularInline):
    model = OrderItem
    fields = ["fk_menu_item", "quantity"]
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInlineAdmin]


class OrderRoomAdmin(admin.ModelAdmin):
    filter_horizontal = ["m2m_users"]


class OrderGroupAdmin(admin.ModelAdmin):
    filter_horizontal = ["m2m_users"]


admin.site.register(Restaurant)
admin.site.register(MenuItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Client)
admin.site.register(OrderRoom, OrderRoomAdmin)
admin.site.register(OrderGroup, OrderGroupAdmin)
