from django.core.validators import BaseValidator
from django.utils.translation import gettext_lazy as _



class PositiveValueValidator(BaseValidator):
    message = _("Ensure this value is greater than %(limit_value)s.")
    code = "positive_value"

    def compare(self, a, b):
        return a > 0
