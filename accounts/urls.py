from django.contrib.auth.views import LogoutView, PasswordChangeDoneView
from django.urls import path

from .views import CustomLoginView, CustomPasswordChangeView, CustomSignUpView

urlpatterns = [
    path("signup/", CustomSignUpView.as_view(), name="signup"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("password_change/", CustomPasswordChangeView.as_view(), name="password_change"),
    path(
        "password_change/done/", PasswordChangeDoneView.as_view(template_name="registration/password_change_done.html"), name="password_change_done"
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
]
