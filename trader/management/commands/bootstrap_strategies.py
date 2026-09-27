from django.core.management.base import BaseCommand
from trader.models import Strategy

DEFAULTS = [
    {"name":"Balanced", "min_balance":50, "primary_trades":3, "max_steps":5, "scaling_multiplier":2.30, "payout_floor":72},
    {"name":"Precision", "min_balance":150, "primary_trades":4, "max_steps":7, "scaling_multiplier":2.30, "payout_floor":72},
    {"name":"High-Profit", "min_balance":200, "primary_trades":5, "max_steps":5, "scaling_multiplier":2.30, "payout_floor":72},
]

class Command(BaseCommand):
    help = "Create the three starter strategies; values remain editable in Django admin."
    def handle(self, *args, **kwargs):
        for values in DEFAULTS:
            strategy, created = Strategy.objects.get_or_create(name=values["name"], defaults=values)
            self.stdout.write(f"{'Created' if created else 'Kept'} {strategy.name}")
