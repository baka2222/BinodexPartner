from decimal import Decimal
import os
import requests
from django.utils import timezone
from .broker import BrokerApi, BrokerError
from .crypto import decrypt
from .models import AccountStatus, SessionStatus, Trade, TradingSession

def _notify(account, text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":account.telegram_chat_id,"text":text}, timeout=10)

def _signal(candles):
    """A transparent baseline signal: price vs. short/long moving averages.
    It is deliberately deterministic; this is not a promise of profitability."""
    closes = [Decimal(str(row[4])) for row in candles if len(row) >= 5]
    if len(closes) < 30: return "up"
    fast = sum(closes[-10:]) / 10; slow = sum(closes[-30:]) / 30
    return "up" if fast >= slow else "down"

def _token(account):
    if not account.access_token_encrypted: raise BrokerError("Binodex authorization is missing")
    if account.token_expires_at and account.token_expires_at <= timezone.now():
        account.status = AccountStatus.REAUTH; account.save(update_fields=["status"])
        raise BrokerError("Binodex authorization expired; user must reconnect")
    return decrypt(account.access_token_encrypted)

def _finish_or_scale(trade, remote):
    trade.status = "closed"; trade.profit = Decimal(str(remote.get("profit", 0))); trade.closed_at = timezone.now(); trade.save(update_fields=["status","profit","closed_at"])
    session, strategy = trade.session, trade.session.strategy
    if trade.profit > 0 or trade.step_number >= strategy.max_steps:
        session.current_primary += 1; session.current_step = 1
    else:
        session.current_step += 1
    if session.current_primary > strategy.primary_trades:
        session.status = SessionStatus.COMPLETE; session.ended_at = timezone.now()
        session.account.status = AccountStatus.READY; session.account.save(update_fields=["status"])
    session.save()
    icon = "🟢" if trade.profit > 0 else "🔴"
    _notify(session.account, f"⚡ Сделка {trade.primary_number} | Шаг {trade.step_number}\n{icon} {trade.symbol or trade.asset_id}: ${trade.amount} → ${trade.profit}")

def run_once():
    api = BrokerApi()
    for session in TradingSession.objects.select_related("account", "strategy").filter(status=SessionStatus.ACTIVE):
        try:
            token = _token(session.account)
            open_local = session.trades.filter(status="open").first()
            closed = {item["id"]: item for item in api.trades(token, status="closed", limit=100).get("trades", [])}
            if open_local:
                if open_local.remote_id in closed: _finish_or_scale(open_local, closed[open_local.remote_id])
                continue
            pairs = [p for p in api.pairs() if p.get("scheduled_until", 1) == 0 and Decimal(str(p.get("payout", 0))) >= session.strategy.payout_floor]
            if not pairs: continue
            pair = max(pairs, key=lambda p: p.get("payout", 0))
            candles = api.chart(pair["id"], "1m", 60)
            step_stake = session.stake * (session.strategy.scaling_multiplier ** (session.current_step - 1))
            remote = api.open_trade(token, {"asset_id": pair["id"], "amount": float(step_stake), "action": _signal(candles), "duration": session.duration})
            Trade.objects.get_or_create(remote_id=remote["id"], defaults={"session":session,"asset_id":pair["id"],"symbol":pair.get("symbol", ""),"action":remote["action"],"amount":step_stake,"payout":Decimal(str(remote.get("payout",0))),"primary_number":session.current_primary,"step_number":session.current_step})
            _notify(session.account, f"📈 Сигнал: {pair.get('symbol', pair['id'])}\nНаправление: {remote['action'].upper()}\nСделка {session.current_primary}, шаг {session.current_step}\nСумма: ${step_stake} · payout: {pair.get('payout')}%")
        except BrokerError as exc:
            session.note = str(exc); session.status = SessionStatus.ERROR; session.save(update_fields=["note","status"])
