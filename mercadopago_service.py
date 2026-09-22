"""Minimal Mercado Pago adapter for Bocali.

Secrets stay server-side. Pix is created through the Payments API. Card checkout
uses Checkout Pro and is opened by Android in a Custom Tab, so card number/CVV
never pass through Bocali's WebView or Python server.
"""
from __future__ import annotations
import json
import urllib.error
import urllib.request


class MercadoPagoError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


class MercadoPagoService:
    API = "https://api.mercadopago.com"

    def __init__(self, access_token: str, public_key: str, webhook_secret: str = ""):
        self.access_token = (access_token or "").strip()
        self.public_key = (public_key or "").strip()
        self.webhook_secret = (webhook_secret or "").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.access_token)

    def _request(self, method: str, path: str, payload=None, idempotency_key: str | None = None):
        if not self.access_token:
            raise MercadoPagoError("Mercado Pago ainda não foi configurado no servidor.", 503)
        body = None if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "User-Agent": "Bocali/1.0",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        req = urllib.request.Request(self.API + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read(2 * 1024 * 1024)
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read(512 * 1024).decode("utf-8", "replace"))
                message = data.get("message") or data.get("error") or "Pagamento recusado pelo provedor."
            except Exception:
                message = "Não foi possível processar o pagamento no Mercado Pago."
            raise MercadoPagoError(str(message)[:240], 422 if 400 <= exc.code < 500 else 502) from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise MercadoPagoError("Mercado Pago indisponível no momento. Confira o pedido antes de tentar novamente.", 503) from exc

    @staticmethod
    def _clean_payer(value):
        payer = value if isinstance(value, dict) else {}
        out = {}
        email = payer.get("email")
        if isinstance(email, str) and 3 <= len(email) <= 254:
            out["email"] = email.strip()
        identification = payer.get("identification")
        if isinstance(identification, dict):
            typ = identification.get("type")
            number = identification.get("number")
            if isinstance(typ, str) and isinstance(number, str) and typ and number:
                out["identification"] = {"type": typ[:20], "number": number[:40]}
        for key in ("first_name", "last_name"):
            value = payer.get(key)
            if isinstance(value, str) and value.strip():
                out[key] = value.strip()[:100]
        return out

    def create_payment(self, order: dict, form_data: dict, idempotency_key: str, notification_url: str):
        if not isinstance(form_data, dict):
            raise MercadoPagoError("Dados de pagamento inválidos.", 400)
        payment_method_id = form_data.get("payment_method_id")
        if not isinstance(payment_method_id, str) or not payment_method_id:
            raise MercadoPagoError("Escolha Pix ou cartão para continuar.", 400)
        payload = {
            "transaction_amount": round(int(order["total"]) / 100.0, 2),
            "description": f"Bocali {order['id']} - {order['storeName']}"[:250],
            "payment_method_id": payment_method_id,
            "external_reference": order["id"],
            "notification_url": notification_url,
            "payer": self._clean_payer(form_data.get("payer")),
        }
        token = form_data.get("token")
        if isinstance(token, str) and token:
            payload["token"] = token
        issuer_id = form_data.get("issuer_id")
        if issuer_id not in (None, ""):
            payload["issuer_id"] = str(issuer_id)[:80]
        installments = form_data.get("installments")
        if isinstance(installments, int) and 1 <= installments <= 24:
            payload["installments"] = installments
        # Do not trust the amount/description supplied by the browser; both are overwritten above.
        result = self._request("POST", "/v1/payments", payload, idempotency_key)
        return self.sanitize(result)

    def get_payment(self, payment_id: str):
        if not str(payment_id).isdigit():
            raise MercadoPagoError("Identificador de pagamento inválido.", 400)
        return self.sanitize(self._request("GET", f"/v1/payments/{payment_id}"))

    def create_checkout_preference(self, order: dict, idempotency_key: str, notification_url: str, back_urls: dict):
        """Create a Checkout Pro preference for card payment in an external/Custom Tab flow.

        The total comes exclusively from the server-side order snapshot. The browser/app never
        supplies amount, description or return destinations. Pix is offered separately by Bocali,
        so bank transfer/ticket methods are excluded from this card-oriented preference.
        """
        if not isinstance(back_urls, dict) or not all(isinstance(back_urls.get(k), str) and back_urls.get(k) for k in ("success", "pending", "failure")):
            raise MercadoPagoError("URLs de retorno inválidas.", 500)
        payload = {
            "items": [{
                "id": str(order["id"])[:100],
                "title": f"Pedido {order['id']} - {order['storeName']}"[:250],
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": round(int(order["total"]) / 100.0, 2),
            }],
            "external_reference": str(order["id"]),
            "notification_url": notification_url,
            "back_urls": back_urls,
            "auto_return": "approved",
            "payment_methods": {
                "excluded_payment_methods": [{"id": "pix"}],
                "excluded_payment_types": [
                    {"id": "bank_transfer"},
                    {"id": "ticket"},
                    {"id": "atm"},
                    {"id": "digital_currency"},
                ],
                "installments": 12,
            },
        }
        data = self._request("POST", "/checkout/preferences", payload, idempotency_key)
        return {
            "id": str(data.get("id") or ""),
            "init_point": str(data.get("init_point") or ""),
            "sandbox_init_point": str(data.get("sandbox_init_point") or ""),
            "external_reference": str(data.get("external_reference") or order["id"]),
        }

    def refund_payment(self, payment_id: str, idempotency_key: str):
        if not str(payment_id).isdigit():
            raise MercadoPagoError("Identificador de pagamento inválido.", 400)
        if not isinstance(idempotency_key, str) or len(idempotency_key) < 16:
            raise MercadoPagoError("Identificador de estorno inválido.", 400)
        # Full refund: Mercado Pago specifies an empty JSON object/body without `amount`.
        return self._request("POST", f"/v1/payments/{payment_id}/refunds", {}, idempotency_key)

    @staticmethod
    def sanitize(data: dict):
        tx = ((data.get("point_of_interaction") or {}).get("transaction_data") or {}) if isinstance(data, dict) else {}
        return {
            "id": str(data.get("id") or ""),
            "status": str(data.get("status") or ""),
            "status_detail": str(data.get("status_detail") or ""),
            "payment_method_id": str(data.get("payment_method_id") or ""),
            "external_reference": str(data.get("external_reference") or ""),
            "qr_code": str(tx.get("qr_code") or ""),
            "qr_code_base64": str(tx.get("qr_code_base64") or ""),
            "ticket_url": str(tx.get("ticket_url") or ""),
        }
