from django.urls import path

from . import views


urlpatterns = [
    # path("", views.index, name="index"),
    path("group/<str:group_name>/", views.GroupView.as_view()),
    path("menuitems/", views.menuitems),
    path("test/", views.announcement),
]
