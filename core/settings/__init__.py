# flake8:noqa

import os

from dotenv import load_dotenv

load_dotenv()

from .base import *

if os.environ["DJANGO_DEVELOPMENT"] == "True":
    from .development import *
else:
    from .production import *
