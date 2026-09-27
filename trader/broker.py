import os
import requests

class BrokerError(RuntimeError): pass

class BrokerApi:
    def __init__(self): self.base = os.environ.get("BROKER_API_URL", "https://api.binodex.app/v1").rstrip("/")
    def request(self, method, path, token=None, **kwargs):
        headers = {"Accept": "application/json"}
        if token: headers["Authorization"] = f"Bearer {token}"
        response = requests.request(method, self.base + path, headers=headers, timeout=20, **kwargs)
        try: data = response.json()
        except ValueError: data = {"raw": response.text}
        if not response.ok: raise BrokerError(data.get("error", {}).get("message", f"Broker API {response.status_code}"))
        return data
    def exchange_code(self, code):
        return self.request("POST", "/broker/oauth/token", json={"grant_type":"authorization_code", "code":code, "client_id":os.environ["BROKER_CLIENT_ID"], "client_secret":os.environ["BROKER_CLIENT_SECRET"], "redirect_uri":os.environ["PUBLIC_BASE_URL"].rstrip("/")+"/oauth/callback"})
    def user(self, token): return self.request("GET", "/broker/user", token)
    def profile(self, token): return self.request("GET", "/broker/user/profile", token)
    def pairs(self): return self.request("GET", "/broker/pairs/binary")
    def chart(self, asset_id, interval="1m", limit=200): return self.request("GET", f"/broker/chart?asset_id={asset_id}&interval={interval}&limit={limit}")
    def trades(self, token, **params): return self.request("GET", "/broker/user/trades", token, params=params)
    def open_trade(self, token, payload): return self.request("POST", "/broker/user/trades", token, json=payload)
    def widget_session(self, token, origin, mode="deposit"): return self.request("POST", "/broker/widget-sessions", token, json={"origin":origin, "mode":mode})

