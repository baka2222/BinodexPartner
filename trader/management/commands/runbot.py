from django.core.management.base import BaseCommand
from trader.telegram_bot import run

class Command(BaseCommand):
    help = "Run the Telegram long-polling worker"
    def handle(self, *args, **kwargs): run()

