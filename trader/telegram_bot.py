import os, secrets
from datetime import timedelta
from django.core import signing
from django.utils import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
from .models import AccountStatus, OAuthState, Strategy, TraderAccount, TradingSession

def cfg(name): return os.environ.get(name, "")
def configured(): return bool(cfg("TELEGRAM_BOT_TOKEN") and cfg("BROKER_CLIENT_ID") and cfg("PUBLIC_BASE_URL"))

def registration_url(account):
    state = secrets.token_urlsafe(32)
    OAuthState.objects.create(value=state, account=account, expires_at=timezone.now()+timedelta(minutes=10))
    q = {"client_id":cfg("BROKER_CLIENT_ID"), "redirect_uri":cfg("PUBLIC_BASE_URL").rstrip("/")+"/oauth/callback", "state":state, "ref":cfg("PARTNER_REF_CODE")}
    from urllib.parse import urlencode
    return cfg("BROKER_PLATFORM_URL") .rstrip("/") + "/oauth/authorize?" + urlencode(q)

def account_for(update):
    user, chat = update.effective_user, update.effective_chat
    return TraderAccount.objects.get_or_create(telegram_user_id=user.id, defaults={"telegram_chat_id":chat.id})[0]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    account = account_for(update)
    if account.status in (AccountStatus.CONFIRMED, AccountStatus.WAITING_DEPOSIT, AccountStatus.READY, AccountStatus.TRADING):
        buttons = [[InlineKeyboardButton("Пополнить баланс", callback_data="deposit"), InlineKeyboardButton("Проверить статус", callback_data="status")], [InlineKeyboardButton("Автоторговля", callback_data="strategies"), InlineKeyboardButton("Стоп", callback_data="stop")], [InlineKeyboardButton("Нужна помощь", url=cfg("SUPPORT_URL"))]]
        await update.message.reply_text("Аккаунт подтверждён. Выберите действие.", reply_markup=InlineKeyboardMarkup(buttons))
        return
    url = registration_url(account)
    await update.message.reply_text("Добро пожаловать. Чтобы подтвердить аккаунт и получить доступ, зарегистрируйтесь или войдите через Binodex по партнёрской ссылке.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Регистрация", url=url)], [InlineKeyboardButton("Нужна помощь", url=cfg("SUPPORT_URL"))]]))
    account.status = AccountStatus.OAUTH_PENDING; account.save(update_fields=["status"])

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); account = account_for(update)
    if q.data == "status":
        from .broker import BrokerApi, BrokerError
        from .crypto import decrypt
        try:
            data = BrokerApi().user(decrypt(account.access_token_encrypted))
            account.real_balance = data["real"]["available"]
            account.last_balance_check_at = timezone.now()
            if account.real_balance > 0 and account.status in (AccountStatus.CONFIRMED, AccountStatus.WAITING_DEPOSIT): account.status = AccountStatus.READY
            elif account.real_balance <= 0 and account.status == AccountStatus.CONFIRMED: account.status = AccountStatus.WAITING_DEPOSIT
            account.save(update_fields=["real_balance", "last_balance_check_at", "status"])
        except (BrokerError, ValueError, KeyError):
            await q.message.reply_text("Не удалось обновить баланс. Если сессия Binodex истекла, пройдите регистрацию заново."); return
        await q.message.reply_text(f"Статус: {account.get_status_display()}\nБаланс: ${account.real_balance}"); return
    if q.data == "deposit":
        if not account.access_token_encrypted: await q.message.reply_text("Сначала пройдите регистрацию."); return
        token = signing.dumps(account.pk, salt="payment")
        await q.message.reply_text("Откройте официальный виджет Binodex для пополнения:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Пополнить баланс", url=cfg("PUBLIC_BASE_URL").rstrip("/")+f"/pay/{token}/")]])); return
    if q.data == "strategies":
        rows = [[InlineKeyboardButton(f"{s.name} — от ${s.min_balance}", callback_data=f"strategy:{s.pk}")] for s in Strategy.objects.filter(enabled=True)]
        await q.message.reply_text("Выберите стратегию:", reply_markup=InlineKeyboardMarkup(rows)); return
    if q.data.startswith("strategy:"):
        context.user_data["strategy"] = int(q.data.split(":")[1])
        await q.message.reply_text("Выберите время сделки:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"{x} сек", callback_data=f"duration:{x}") for x in (15,30,60)]])); return
    if q.data.startswith("duration:"):
        context.user_data["duration"] = int(q.data.split(":")[1])
        await q.message.reply_text("Выберите сумму сделки:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("$1", callback_data="stake:1"), InlineKeyboardButton("$3", callback_data="stake:3"), InlineKeyboardButton("$5", callback_data="stake:5")], [InlineKeyboardButton("$10 RISK", callback_data="stake:10"), InlineKeyboardButton("$20 RISK", callback_data="stake:20")]])); return
    if q.data.startswith("stake:"):
        strategy = Strategy.objects.get(pk=context.user_data.get("strategy")); stake=float(q.data.split(":")[1]); duration=context.user_data.get("duration",60)
        if account.real_balance < strategy.min_balance: await q.message.reply_text(f"Для «{strategy.name}» нужен баланс от ${strategy.min_balance}."); return
        TradingSession.objects.filter(account=account, status="active").update(status="stopped", note="Replaced by user")
        TradingSession.objects.create(account=account, strategy=strategy, stake=stake, duration=duration)
        account.status=AccountStatus.TRADING; account.save(update_fields=["status"])
        await q.message.reply_text("Торговая сессия запущена. Бот выберет актив с подходящим payout и будет отправлять результат каждой сделки."); return
    if q.data == "stop":
        TradingSession.objects.filter(account=account, status="active").update(status="stopped", note="Stopped by user")
        account.status=AccountStatus.READY; account.save(update_fields=["status"])
        await q.message.reply_text("Автоторговля остановлена.")

async def post_init(app):
    await app.bot.set_my_commands([("start", "Начать"), ("status", "Статус")])

def run():
    if not configured(): raise RuntimeError("Set TELEGRAM_BOT_TOKEN, BROKER_CLIENT_ID and PUBLIC_BASE_URL in .env")
    app = ApplicationBuilder().token(cfg("TELEGRAM_BOT_TOKEN")).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start)); app.add_handler(CallbackQueryHandler(menu))
    app.run_polling(allowed_updates=Update.ALL_TYPES)
