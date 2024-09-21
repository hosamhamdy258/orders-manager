from django.utils.translation import gettext as _


from orderApp.enums import ViewContextKeys as VC, CurrentViews as CV


def get_current_view(view):
    views = {
        CV.ORDER_VIEW: {VC.CURRENT_VIEW: CV.ORDER_VIEW},
        CV.RESTAURANT_VIEW: {VC.CURRENT_VIEW: CV.RESTAURANT_VIEW},
        CV.GROUP_VIEW: {VC.CURRENT_VIEW: CV.GROUP_VIEW},
    }
    return views.get(view)
