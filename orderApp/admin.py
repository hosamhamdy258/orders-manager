from django.contrib import admin

from orderApp.models import Client, Group, MenuItem, Order, OrderItem, Restaurant


class OrderItemInlineAdmin(admin.TabularInline):
    model = OrderItem
    fields = ["fk_menu_item", "quantity"]
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInlineAdmin]


class GroupAdmin(admin.ModelAdmin):
    filter_horizontal = ["m2m_users"]


admin.site.register(Restaurant)
admin.site.register(MenuItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Client)
admin.site.register(Group, GroupAdmin)
