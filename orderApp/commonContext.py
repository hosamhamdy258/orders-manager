from django.utils.translation import gettext_lazy as _

from orderApp.enums import CurrentViews as CV
from orderApp.enums import GeneralContextKeys as GC
from orderApp.enums import ViewContextKeys as VC

NAVIGATION_BUTTONS = [
    {"view": CV.ORDER_GROUP, "url": "order_groups", "display": _("Groups")},
    {"view": CV.RESTAURANT, "url": "restaurants", "display": _("Restaurants")},
]
