from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("group/<str:group_name>/", views.group),
    path("menuitems/", views.menuitems),
]
