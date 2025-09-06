from django.urls import path, re_path

from invitation.views import CustomAcceptInvite

app_name = "invitation"

urlpatterns = [
    re_path(r"^accept-invite/(?P<key>\w+)/?$", CustomAcceptInvite.as_view(), name="accept-invite"),
]
