from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    email = models.EmailField(verbose_name=_("email address"), unique=True)

    def clean(self):
        super().clean()
        self.email = self.email.lower()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(force_insert, force_update, using, update_fields)

        from invitation.models import WaitingRegister

        WaitingRegister.register_user_to_order_group(self.email)
