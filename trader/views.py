import os
from datetime import timedelta
from django.core import signing
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET
from .broker import BrokerApi, BrokerError
from .crypto import encrypt
from .models import AccountStatus, OAuthState, TraderAccount

@require_GET
def healthz(request): return JsonResponse({"ok": True})

@require_GET
def oauth_callback(request):
    code, state = request.GET.get("code"), request.GET.get("state")
    if not code or not state: return HttpResponseBadRequest("Missing OAuth code or state")
    state_row = OAuthState.objects.filter(value=state, used_at__isnull=True, expires_at__gt=timezone.now()).select_related("account").first()
    if not state_row: return HttpResponseBadRequest("The authorization link is expired. Return to Telegram and start again.")
    try:
        payload = BrokerApi().exchange_code(code)
    except (BrokerError, KeyError) as exc:
        return HttpResponseBadRequest(f"Binodex authorization failed: {exc}")
    user, account = payload["user"], state_row.account
    account.binodex_user_id = user["id"]
    account.email = user.get("email", "")
    account.is_partner_client = bool(user.get("is_partner_client"))
    account.access_token_encrypted = encrypt(payload["access_token"])
    account.refresh_token_encrypted = encrypt(payload["refresh_token"])
    account.token_expires_at = timezone.now() + timedelta(seconds=payload.get("expires_in", 0))
    account.status = AccountStatus.CONFIRMED if account.is_partner_client else AccountStatus.NEW
    account.save()
    state_row.used_at = timezone.now(); state_row.save(update_fields=["used_at"])
    return render(request, "oauth_done.html", {"ok": account.is_partner_client, "bot_name": os.environ.get("BOT_NAME", "Binodex Partner Bot")})

@require_GET
def payment_page(request, token):
    try: account_id = signing.loads(token, salt="payment", max_age=900)
    except signing.BadSignature: return HttpResponseBadRequest("Payment link expired. Return to Telegram.")
    account = get_object_or_404(TraderAccount, pk=account_id)
    if not account.access_token_encrypted: return HttpResponseBadRequest("Authorize Binodex first.")
    from .crypto import decrypt
    try:
        session = BrokerApi().widget_session(decrypt(account.access_token_encrypted), os.environ["PUBLIC_BASE_URL"].rstrip("/"))
    except (BrokerError, KeyError) as exc: return HttpResponseBadRequest(f"Could not open payment widget: {exc}")
    return render(request, "payment.html", {"session": session["session"], "client_id": os.environ.get("BROKER_CLIENT_ID", ""), "platform": os.environ.get("BROKER_PLATFORM_URL", "https://binodex.app")})

