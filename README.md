# Binodex partner trading bot

Universal Telegram bot with a Django admin panel, Binodex OAuth, official payment iframe, PostgreSQL, an automatic trading worker and Docker deployment.

## Before the first live run

1. Copy `.env.example` to `.env` and fill every secret locally.
2. In BinoPartner → **Broker API**, create an OAuth client.
3. Add `https://YOUR_DOMAIN/oauth/callback` to its redirect URIs and `https://YOUR_DOMAIN` to origins.
4. Ask Binodex support to enable trade opening for that client.
5. Create an admin: `docker compose run --rm web python manage.py createsuperuser`.
6. Create starter strategies: `docker compose run --rm web python manage.py bootstrap_strategies`, then adjust them in `/admin/`.
7. Start: `docker compose up -d --build`.

For TLS, place the Docker stack behind a managed HTTPS proxy (recommended) or replace `nginx/default.conf` with the certificate-enabled configuration. The public URL must be HTTPS in production for OAuth and the payment iframe.

## Verified Binodex calls

The implementation uses the methods confirmed by the official `binodex/broker-web` terminal: `/broker/user`, `/broker/pairs/binary`, `/broker/chart`, `/broker/user/trades`, OAuth token exchange and widget sessions. Actual trade opening remains unavailable until Binodex enables it on the created client.

## Safety defaults

- OAuth tokens are encrypted at rest with `TOKEN_ENCRYPTION_SECRET`.
- The bot does not collect Binodex passwords.
- An expired OAuth token stops the session and requests reauthorization.
- Every active session can be stopped from Telegram or Django admin.
- The rule engine is deterministic and must not be presented as a profit guarantee.
