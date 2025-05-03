from orderApp.enums import CurrentViews as CV
from orderApp.enums import ViewContextKeys as VC


def get_current_view(view):
    if view == CV.ORDER_VIEW:
        return {VC.CURRENT_VIEW: CV.ORDER_VIEW}
    if view == CV.RESTAURANT_VIEW:
        return {VC.CURRENT_VIEW: CV.RESTAURANT_VIEW}
    if view == CV.GROUP_VIEW:
        return {VC.CURRENT_VIEW: CV.GROUP_VIEW}
    return view
