from django.db import models

class AccountStatus(models.TextChoices):
    NEW = "new", "New"
    OAUTH_PENDING = "oauth_pending", "OAuth pending"
    CONFIRMED = "confirmed", "Partner confirmed"
    WAITING_DEPOSIT = "waiting_deposit", "Waiting for deposit"
    READY = "ready", "Ready"
    TRADING = "trading", "Trading"
    REAUTH = "reauth", "Reauthorization required"
    BLOCKED = "blocked", "Blocked"

class TraderAccount(models.Model):
    telegram_user_id = models.BigIntegerField(unique=True)
    telegram_chat_id = models.BigIntegerField()
    binodex_user_id = models.BigIntegerField(null=True, blank=True, unique=True)
    email = models.EmailField(blank=True)
    is_partner_client = models.BooleanField(default=False)
    status = models.CharField(max_length=32, choices=AccountStatus.choices, default=AccountStatus.NEW)
    access_token_encrypted = models.TextField(blank=True)
    refresh_token_encrypted = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    real_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    last_balance_check_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return f"TG {self.telegram_user_id} / Bino {self.binodex_user_id or '—'}"

class OAuthState(models.Model):
    value = models.CharField(max_length=96, unique=True)
    account = models.ForeignKey(TraderAccount, on_delete=models.CASCADE, related_name="oauth_states")
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Strategy(models.Model):
    name = models.CharField(max_length=64, unique=True)
    min_balance = models.DecimalField(max_digits=12, decimal_places=2)
    primary_trades = models.PositiveSmallIntegerField(default=3)
    max_steps = models.PositiveSmallIntegerField(default=5)
    scaling_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=2.30)
    payout_floor = models.DecimalField(max_digits=5, decimal_places=2, default=72)
    enabled = models.BooleanField(default=True)

    class Meta: verbose_name_plural = "Strategies"
    def __str__(self): return self.name

class SessionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETE = "complete", "Complete"
    STOPPED = "stopped", "Stopped"
    ERROR = "error", "Error"

class TradingSession(models.Model):
    account = models.ForeignKey(TraderAccount, on_delete=models.CASCADE, related_name="sessions")
    strategy = models.ForeignKey(Strategy, on_delete=models.PROTECT)
    stake = models.DecimalField(max_digits=12, decimal_places=2)
    duration = models.PositiveIntegerField(help_text="seconds")
    selected_asset_id = models.IntegerField(null=True, blank=True)
    current_primary = models.PositiveSmallIntegerField(default=1)
    current_step = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=SessionStatus.choices, default=SessionStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    def __str__(self): return f"#{self.pk} {self.account} {self.status}"

class Trade(models.Model):
    session = models.ForeignKey(TradingSession, on_delete=models.CASCADE, related_name="trades")
    remote_id = models.BigIntegerField(unique=True)
    asset_id = models.IntegerField()
    symbol = models.CharField(max_length=40, blank=True)
    action = models.CharField(max_length=4)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payout = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    primary_number = models.PositiveSmallIntegerField()
    step_number = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, default="open")
    profit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self): return f"#{self.remote_id} {self.status}"

