from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import CreateView

UserModel = get_user_model()


def add_custom_class(self):
    for field in self.fields.values():
        field.widget.attrs.update({"class": "form-control"})


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = UserModel
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_custom_class(self)


class CustomSignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/sign_up.html"


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_custom_class(self)


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_custom_class(self)


class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = "registration/change_password.html"
    success_url = reverse_lazy("password_change_done")
