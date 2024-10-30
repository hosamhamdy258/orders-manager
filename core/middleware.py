import time

from django.utils.deprecation import MiddlewareMixin
from django.utils.http import http_date


class ServerClock(MiddlewareMixin):
    def process_response(self, request, response):
        response["Date"] = http_date(time.time())
        return response
