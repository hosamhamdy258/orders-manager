from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from invitations.exceptions import AlreadyAccepted, AlreadyInvited, UserRegisteredEmail
from invitations.utils import get_invitation_model

Invitation = get_invitation_model()


class CustomInviteForm(ModelForm):
    class Meta:
        model = Invitation
        fields = ["email", "fk_order_group"]

    def clean(self):
        cleaned_data = self.cleaned_data
        email = cleaned_data["email"]
        group = cleaned_data["fk_order_group"]

        errors = {
            "already_invited": _(f"This email is already invited to {group.name}"),
            "already_accepted": _(
                "This e-mail address has already" " accepted an invite.",
            ),
            "email_in_use": _("An active user is using this e-mail address"),
        }
        try:
            self.validate_invitation(email, group)
        except AlreadyInvited:
            raise forms.ValidationError({"email": errors["already_invited"]})
        except AlreadyAccepted:
            raise forms.ValidationError({"email": errors["already_accepted"]})
        except UserRegisteredEmail:
            raise forms.ValidationError({"email": errors["email_in_use"]})
        return super().clean()

    def validate_invitation(self, email, group):
        if Invitation.objects.all_valid().filter(email__iexact=email, fk_order_group=group, accepted=False):
            raise AlreadyInvited
        elif Invitation.objects.filter(email__iexact=email, fk_order_group=group, accepted=True):
            raise AlreadyAccepted
        # elif get_user_model().objects.filter(email__iexact=email):
        #     raise UserRegisteredEmail
        else:
            return True
