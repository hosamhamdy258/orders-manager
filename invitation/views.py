from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from invitations.app_settings import app_settings
from invitations.utils import get_invitation_model
from invitations.views import AcceptInvite

from invitation.models import WaitingRegister

Invitation = get_invitation_model()


class CustomAcceptInvite(AcceptInvite):
    def post(self, *args, **kwargs):
        self.object = invitation = self.get_object()

        if app_settings.GONE_ON_ACCEPT_ERROR and (not invitation or (invitation and (invitation.accepted or invitation.key_expired()))):
            return HttpResponse(status=410)

        if not invitation:
            messages.error(self.request, {"code": 403, "message": _(f"An invalid invitation key was submitted.")})
            return redirect("redirect")

        if invitation.accepted:
            messages.error(self.request, {"code": 403, "message": _(f"The invitation for {invitation.email} was already accepted.")})
            return redirect("redirect")

        if invitation.key_expired():
            messages.error(self.request, {"code": 403, "message": _(f"The invitation for {invitation.email} has expired.")})
            return redirect("redirect")

        invitation.accepted = True
        invitation.save()

        WaitingRegister.objects.create(email=invitation.email, fk_order_group=invitation.fk_order_group)
        WaitingRegister.register_user_to_order_group(invitation.email)

        return redirect(self.get_signup_redirect())
