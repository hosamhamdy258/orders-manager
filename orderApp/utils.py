from django.core.validators import BaseValidator
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string


class PositiveValueValidator(BaseValidator):
    message = _("Ensure this value is greater than %(limit_value)s.")
    code = "positive_value"

    def compare(self, a, b):
        return a <= b  # Invalid if a is less than or equal to 0


def templates_joiner(context, templates):
    response = "".join([render_to_string(template, context=context) for template in templates])
    return response
