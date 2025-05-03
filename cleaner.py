from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone

from accounts.models import configuration
from orderApp.models import Order

scheduler = BackgroundScheduler()
scheduler.start()


def archive_orders():
    Order.objects.filter(delete_timer__lte=timezone.now()).update(order_archived=True)


def cleaner():
    scheduler.add_job(func=archive_orders)
    scheduler.add_job(func=archive_orders, trigger="interval", minutes=configuration().order_archive_delay)
