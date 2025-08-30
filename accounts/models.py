from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel


class User(AbstractUser):
    email = models.EmailField(verbose_name=_("email address"), unique=True)


class Configuration(SingletonModel):
    site_name = models.CharField(max_length=255, default="Site Name")
    order_limit = models.IntegerField(_("Order Limit"), default=1)
    order_archive_delay = models.IntegerField(_("Order Archive Delay (Hours)"), default=1)
    order_time_limit = models.IntegerField(_("Order Time Limit (Mins)"), default=15)
    lock_time_limit = models.IntegerField(_("Lock Time Limit (Mins)"), default=60)
    join_retry_limit = models.IntegerField(_("Group Join Retry Limit"), default=3)

    def __str__(self):
        return "Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"


def configuration():
    return Configuration.get_solo()


def join_retry_limit():
    return Configuration.get_solo().join_retry_limit
