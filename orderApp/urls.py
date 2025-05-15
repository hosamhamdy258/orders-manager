from django.urls import path

from orderApp.enums import GeneralContextKeys as GC
from orderApp.views import (
    IndexView,
    OrderRoomView,
    OrderSelectionView,
    RestaurantView,
    announcement,
    menuitems,
    redirect_page,
)

urlpatterns = [
    path("", IndexView.as_view(), name="order_groups"),
    path(f"order/<str:{GC.GROUP_NUMBER}>/", OrderRoomView.as_view(), name="order_room"),
    path(f"order_selection/<str:{GC.GROUP_NUMBER}>/<str:{GC.ROOM_NUMBER}>/", OrderSelectionView.as_view(), name="order_selection"),
    path("restaurant/", RestaurantView.as_view(), name="restaurants"),
    path("menuitems/", menuitems, name="get_menu_items"),
    path("test/", announcement),
    path("redirect/", redirect_page, name="redirect"),
]
