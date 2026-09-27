import time
from django.core.management.base import BaseCommand
from trader.engine import run_once

class Command(BaseCommand):
    help = "Run the automatic trading worker"
    def handle(self, *args, **kwargs):
        while True:
            run_once(); time.sleep(5)

