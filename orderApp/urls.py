from django.urls import path

from orderApp.views import (
    IndexView,
    OrderSelectionView,
    RestaurantView,
    announcement,
    menuitems,
)

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("order/<str:group_name>/", OrderSelectionView.as_view(), name="order"),
    path("restaurant/", RestaurantView.as_view(), name="restaurant"),
    path("menuitems/", menuitems, name="get_menu_items"),
    path("test/", announcement),
]
