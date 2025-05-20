from collections import defaultdict
from decimal import Decimal
from itertools import groupby
from operator import itemgetter

from django.core.validators import BaseValidator
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _


class PositiveValueValidator(BaseValidator):
    message = _("Ensure this value is greater than %(limit_value)s.")
    code = "positive_value"

    def compare(self, a, b):
        return a <= b


def templates_builder(context, templates, chunks=True):
    rendered_templates = [render_to_string(template, context=context) for template in templates]
    if chunks:
        return rendered_templates
    else:
        return ["".join(rendered_templates)]


def group_nested_data(data, group_keys):
    """
    Groups a list of dictionaries by the specified keys.

    :param data: List of dictionaries to be grouped.
    :param group_keys: List of keys to group by, in order of grouping.
    :return: Nested dictionary with grouped data.
    """
    if not group_keys:
        return data

    # Sort data by the current group key
    data = sorted(data, key=itemgetter(group_keys[0]))
    # To avoid extra list wraps in nested groups
    if len(group_keys) > 1:
        grouped_data = defaultdict(dict)
    else:
        grouped_data = defaultdict(list)

    # Group by the first key in the group_keys list
    for key, group in groupby(data, key=itemgetter(group_keys[0])):
        # If there are more keys to group by, call the function recursively
        if len(group_keys) > 1:
            # Group the remaining data by the next key(s)
            grouped_data[key].update(group_nested_data(list(group), group_keys[1:]))
        else:
            # If this is the last key, append the group as is
            grouped_data[key].extend(list(group))

    # Convert defaultdict to a regular dict for the final output
    return dict(grouped_data)


def calculate_totals(data, keys):
    """
    Calculate the total for specified keys across a list of dictionaries.

    :param data: List of dictionaries containing data to sum.
    :param keys: List of keys to sum up in the dictionaries.
    :return: Dictionary with the total sums for each specified key.
    """
    if not keys:
        return data

    totals = {key: 0 for key in keys}

    for item in data:
        for key in keys:
            value = item.get(key, 0)
            if isinstance(value, (int, float, Decimal)):
                totals[key] += value

    return totals
