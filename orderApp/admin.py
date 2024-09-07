from django.contrib import admin

from orderApp.models import MenuItem, Order, OrderItem, Restaurant,Clients

# Register your models here.


admin.site.register(Restaurant)
admin.site.register(MenuItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Clients)
