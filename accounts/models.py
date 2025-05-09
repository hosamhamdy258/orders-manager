from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel


class User(AbstractUser):
    email = models.EmailField(verbose_name=_("email address"), unique=True)


class Configuration(SingletonModel):
    site_name = models.CharField(max_length=255, default="Site Name")
    maintenance_mode = models.BooleanField(default=False)
    order_limit = models.IntegerField(_("Order Limit"), default=1)
    order_archive_delay = models.IntegerField(_("Order Archive Delay Hours"), default=1)
    order_time_limit = models.IntegerField(_("Order Time Limit"), default=15)

    def __str__(self):
        return "Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"


def configuration():
    return Configuration.get_solo()
