from orderApp.enums import CurrentViews as CV
from orderApp.enums import ViewContextKeys as VC


def get_current_view(view):
    if view == CV.ORDER_SELECTION:
        return {VC.CURRENT: CV.ORDER_SELECTION}
    if view == CV.RESTAURANT:
        return {VC.CURRENT: CV.RESTAURANT}
    if view == CV.ORDER_ROOM:
        return {VC.CURRENT: CV.ORDER_ROOM}
    if view == CV.ORDER_GROUP:
        return {VC.CURRENT: CV.ORDER_GROUP}
    return view
