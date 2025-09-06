import datetime

from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.html import strip_tags
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from invitations import signals
from invitations.app_settings import app_settings
from invitations.base_invitation import AbstractBaseInvitation

from orderApp.models import OrderGroup

UserModel = get_user_model()


def send_invite_email(to_email, context):
    subject = _("You're Invited to Join Orders Manager")
    html_content = render_to_string("invitation/invite.html", {**context})
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject=subject, body=text_content, to=[to_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


class CustomInvitation(AbstractBaseInvitation):
    email = models.EmailField(verbose_name=_("email address"), max_length=app_settings.EMAIL_MAX_LENGTH)
    created = models.DateTimeField(verbose_name=_("created"), default=timezone.now)
    fk_order_group = models.ForeignKey(OrderGroup, verbose_name=_("Group"), on_delete=models.CASCADE)

    @classmethod
    def create(cls, email, group, inviter=None, **kwargs):
        key = get_random_string(64).lower()
        instance = cls._default_manager.create(email=email, key=key, inviter=inviter, fk_order_group=group, **kwargs)
        return instance

    def key_expired(self):
        expiration_date = self.sent + datetime.timedelta(days=app_settings.INVITATION_EXPIRY)
        return expiration_date <= timezone.now()

    def send_invitation(self, host, **kwargs):
        invite_url = host + reverse(app_settings.CONFIRMATION_URL_NAME, args=[self.key])
        ctx = kwargs
        ctx.update(
            {
                "invite_url": invite_url,
                "site_name": host,
                "email": self.email,
                "key": self.key,
                "inviter": self.inviter.username,
                "app_name": _("Orders Manager"),
                "expiration_days": app_settings.INVITATION_EXPIRY,
                "year": now().year,
                "group_name": self.fk_order_group.name,
            },
        )
        send_invite_email(self.email, ctx)
        self.sent = timezone.now()
        self.save()

        signals.invite_url_sent.send(
            sender=self.__class__,
            instance=self,
            invite_url_sent=invite_url,
            inviter=self.inviter,
        )

    def __str__(self):
        return f"Invitation: {self.email} -> {self.fk_order_group.name}"


class WaitingRegister(models.Model):
    fk_order_group = models.ForeignKey(OrderGroup, verbose_name=_("Order Group"), on_delete=models.CASCADE)
    email = models.EmailField(verbose_name=_("email address"), max_length=app_settings.EMAIL_MAX_LENGTH)
    redeemed = models.BooleanField(_("Redeemed"), default=False)

    def __str__(self):
        return f"Invitation waiting for : {self.email} -> {self.fk_order_group.name}"

    @classmethod
    def register_user_to_order_group(cls, email):
        user = UserModel.objects.filter(email=email).first()
        if user:  # * user is registered
            waiting_list = WaitingRegister.objects.filter(email=email, redeemed=False)
            for invitation in waiting_list:
                order_group = OrderGroup.objects.get(pk=invitation.fk_order_group.pk)
                order_group.m2m_users.add(user)
                order_group.save()
                invitation.redeemed = True
                # TODO send event to increase connected user number in channel
