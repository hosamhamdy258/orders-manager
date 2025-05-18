from apscheduler.schedulers.background import BackgroundScheduler
from django.db.utils import OperationalError
from django.utils import timezone

from accounts.models import configuration
from orderApp.models import Order

scheduler = BackgroundScheduler()
scheduler.start()


def archive_orders():
    try:
        Order.objects.filter(delete_timer__lte=timezone.now()).update(order_archived=True)
    except OperationalError as e:
        print(e)


def cleaner():
    try:
        scheduler.add_job(func=archive_orders)
        scheduler.add_job(func=archive_orders, trigger="interval", minutes=configuration().order_archive_delay)
    except OperationalError as e:
        print(e)
