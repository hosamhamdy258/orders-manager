from apscheduler.schedulers.background import BackgroundScheduler
from channels_presence.models import Room
from django.db.utils import OperationalError
from django.utils import timezone

from configuration.models import configuration
from orderApp.models import Order

scheduler = BackgroundScheduler()
scheduler.start()


def archive_orders():
    try:
        Order.objects.filter(delete_timer__lte=timezone.now()).update(order_archived=True)
    except OperationalError as e:
        print(e)


def clean_rooms():
    try:
        Room.objects.prune_rooms()
    except OperationalError as e:
        print(e)


def clean_presences():
    try:
        Room.objects.prune_presences()
    except OperationalError as e:
        print(e)


def cleaner():
    try:
        scheduler.add_job(func=archive_orders)
        scheduler.add_job(func=archive_orders, trigger="interval", minutes=configuration().order_archive_delay)

        scheduler.add_job(func=clean_rooms)
        scheduler.add_job(func=clean_rooms, trigger="interval", minutes=1)

        scheduler.add_job(func=clean_presences)
        scheduler.add_job(func=clean_presences, trigger="interval", minutes=1)
    except OperationalError as e:
        print(e)
