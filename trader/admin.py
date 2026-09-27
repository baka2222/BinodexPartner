from django.contrib import admin
from .models import OAuthState, Strategy, Trade, TraderAccount, TradingSession

@admin.register(TraderAccount)
class TraderAccountAdmin(admin.ModelAdmin):
    list_display = ("telegram_user_id", "binodex_user_id", "status", "is_partner_client", "real_balance", "updated_at")
    list_filter = ("status", "is_partner_client")
    search_fields = ("telegram_user_id", "binodex_user_id", "email")
    readonly_fields = ("access_token_encrypted", "refresh_token_encrypted")

@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ("name", "min_balance", "primary_trades", "max_steps", "scaling_multiplier", "payout_floor", "enabled")

@admin.register(TradingSession)
class TradingSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "account", "strategy", "stake", "duration", "current_primary", "current_step", "status", "created_at")
    list_filter = ("status", "strategy")

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ("remote_id", "session", "symbol", "action", "amount", "primary_number", "step_number", "status", "profit")
    list_filter = ("status", "action")

admin.site.register(OAuthState)

