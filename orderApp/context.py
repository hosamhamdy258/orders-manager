from django.utils.translation import gettext as _


from orderApp.enums import ViewContextKeys, CurrentViews


def get_current_view(view):
    views = {
        CurrentViews.ORDER_VIEW: {ViewContextKeys.CURRENT_VIEW: CurrentViews.ORDER_VIEW},
        CurrentViews.RESTAURANT_VIEW: {ViewContextKeys.CURRENT_VIEW: CurrentViews.RESTAURANT_VIEW},
    }
    return views.get(view)
