from django.db import models
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel


# Create your models here.
class Configuration(SingletonModel):
    order_limit = models.IntegerField(_("Order Limit Per Day"), default=1)
    order_archive_delay = models.IntegerField(_("Order Archive Delay (Hours)"), default=6)
    order_time_limit = models.IntegerField(_("Order Time Limit (Mins) Per User"), default=15)
    total_order_time_limit = models.IntegerField(_("Order Time Limit (Mins) Per Room"), default=60)
    order_room_lock_limit = models.IntegerField(_("Order Room Lock Limit (Mins) (No Entry)"), default=1)
    lock_time_limit = models.IntegerField(_("Lock Time Limit (Mins) for Pin Retries (Deprecated)"), default=60)
    join_retry_limit = models.IntegerField(_("Group Join Retry Limit for Pin Retries (Deprecated)"), default=3)

    def __str__(self):
        return "Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"


def configuration():
    return Configuration.get_solo()


def join_retry_limit():
    return Configuration.get_solo().join_retry_limit
