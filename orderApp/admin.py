from django.contrib import admin

from orderApp.models import MenuItem, Order, OrderItem, Restaurant, Clients

# Register your models here.


class OrderItemInlineAdmin(admin.TabularInline):
    model = OrderItem
    fields = ["fk_menu_item", "quantity"]
    max_num = 0


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInlineAdmin]


admin.site.register(Restaurant)
admin.site.register(MenuItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Clients)
