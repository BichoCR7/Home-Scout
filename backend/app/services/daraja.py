"""Backend-only Daraja OAuth, STK Push, and STK Query client."""

from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import Settings

DARAJA_SANDBOX_HOST = "https://sandbox.safaricom.co.ke"
DARAJA_PRODUCTION_HOST = "https://api.safaricom.co.ke"


class DarajaError(Exception):
    """Sanitized provider error; never carries credentials or response bodies."""

    def __init__(self, code: str, *, submission_unknown: bool = False) -> None:
        self.code = code
        self.submission_unknown = submission_unknown
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class StkPushResult:
    response_code: str
    checkout_request_id: str | None
    merchant_request_id: str | None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class StkQueryResult:
    response_code: str | None
    result_code: str | None
    checkout_request_id: str | None
    transaction_status: str | None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class DarajaClient:
    """Small sync client for Daraja; credentials never leave this backend process."""

    def __init__(self, settings: Settings, opener: Any | None = None) -> None:
        self.settings = settings
        self.host = (
            DARAJA_PRODUCTION_HOST
            if settings.mpesa_environment == "production"
            else DARAJA_SANDBOX_HOST
        )
        self.opener = opener or urllib.request.build_opener(_NoRedirect())
        self._token: str | None = None
        self._token_expires_at = datetime.min
        self._token_lock = threading.Lock()

    def start_stk_push(
        self,
        *,
        amount_kes: Decimal,
        phone_number: str,
        service_order_id: str,
        callback_url: str,
    ) -> StkPushResult:
        access_token = self._access_token()
        now = datetime.now(ZoneInfo("Africa/Nairobi"))
        timestamp = now.strftime("%Y%m%d%H%M%S")
        shortcode = self._setting(self.settings.mpesa_business_shortcode)
        passkey = self._setting(self.settings.mpesa_passkey)
        password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()
        reference = f"HS{service_order_id.replace('-', '')[:10]}"
        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": self.settings.mpesa_transaction_type,
            "Amount": int(amount_kes),
            "PartyA": phone_number,
            "PartyB": shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": reference,
            "TransactionDesc": f"HomeScout service {service_order_id.replace('-', '')[:8]}",
        }
        response = self._request_json(
            "POST", "/mpesa/stkpush/v1/processrequest", payload, access_token
        )
        response_code = str(response.get("ResponseCode", ""))
        if response_code != "0":
            return StkPushResult(
                response_code=response_code or "rejected",
                checkout_request_id=None,
                merchant_request_id=None,
                error_code="provider_rejected_request",
            )
        checkout_id = response.get("CheckoutRequestID")
        merchant_id = response.get("MerchantRequestID")
        if (
            not isinstance(checkout_id, str)
            or not checkout_id
            or not isinstance(merchant_id, str)
            or not merchant_id
        ):
            raise DarajaError("provider_response_incomplete", submission_unknown=True)
        return StkPushResult(
            response_code=response_code,
            checkout_request_id=checkout_id[:128],
            merchant_request_id=merchant_id[:128],
        )

    def query_stk(self, *, checkout_request_id: str) -> StkQueryResult:
        access_token = self._access_token()
        timestamp = datetime.now(ZoneInfo("Africa/Nairobi")).strftime("%Y%m%d%H%M%S")
        shortcode = self._setting(self.settings.mpesa_business_shortcode)
        passkey = self._setting(self.settings.mpesa_passkey)
        password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()
        try:
            response = self._request_json(
                "POST",
                "/mpesa/stkpushquery/v1/query",
                {
                    "BusinessShortCode": shortcode,
                    "Password": password,
                    "Timestamp": timestamp,
                    "CheckoutRequestID": checkout_request_id,
                },
                access_token,
            )
        except DarajaError as error:
            raise DarajaError(error.code) from error
        returned_checkout = response.get("CheckoutRequestID")
        return StkQueryResult(
            response_code=_as_string(response.get("ResponseCode")),
            result_code=_as_string(response.get("ResultCode")),
            checkout_request_id=(
                returned_checkout[:128] if isinstance(returned_checkout, str) else None
            ),
            transaction_status=_as_string(response.get("TransactionStatus")),
        )

    def _access_token(self) -> str:
        now = datetime.now()
        with self._token_lock:
            if self._token and now < self._token_expires_at:
                return self._token
            key = self._setting(self.settings.mpesa_consumer_key)
            secret = self._setting(self.settings.mpesa_consumer_secret)
            authorization = base64.b64encode(f"{key}:{secret}".encode()).decode()
            try:
                response = self._request_json(
                    "GET",
                    "/oauth/v1/generate?grant_type=client_credentials",
                    None,
                    authorization_header=f"Basic {authorization}",
                )
            except DarajaError as error:
                raise DarajaError("daraja_authentication_unavailable") from error
            token = response.get("access_token")
            expires = response.get("expires_in", 300)
            if not isinstance(token, str) or not token:
                raise DarajaError("daraja_authentication_response_invalid")
            try:
                ttl = max(1, int(expires))
            except (TypeError, ValueError):
                ttl = 300
            self._token = token
            self._token_expires_at = now + timedelta(seconds=max(1, ttl - 30))
            return token

    def _request_json(
        self,
        method: str,
        path: str,
        body: dict[str, object] | None,
        access_token: str | None = None,
        authorization_header: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if authorization_header:
            headers["Authorization"] = authorization_header
        elif access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        data = json.dumps(body, separators=(",", ":")).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self.host}{path}", data=data, headers=headers, method=method
        )
        try:
            with self.opener.open(
                request, timeout=self.settings.mpesa_request_timeout_seconds
            ) as response:
                if not 200 <= response.status < 300:
                    raise DarajaError("provider_http_error", submission_unknown=method == "POST")
                parsed = json.loads(response.read(64 * 1024 + 1))
        except urllib.error.HTTPError as error:
            # Do not read or log provider error bodies; they can contain sensitive request context.
            unknown = method == "POST" and error.code >= 500
            raise DarajaError(
                "provider_request_uncertain" if unknown else "provider_http_error",
                submission_unknown=unknown,
            ) from None
        except (TimeoutError, urllib.error.URLError, OSError):
            raise DarajaError(
                "provider_timeout_or_network_error", submission_unknown=method == "POST"
            ) from None
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            raise DarajaError(
                "provider_response_invalid", submission_unknown=method == "POST"
            ) from None
        if not isinstance(parsed, dict):
            raise DarajaError("provider_response_invalid", submission_unknown=method == "POST")
        return parsed

    @staticmethod
    def _setting(value: object | None) -> str:
        if value is None:
            raise DarajaError("payment_integration_not_configured")
        getter = getattr(value, "get_secret_value", None)
        resolved = getter() if callable(getter) else value
        if not isinstance(resolved, str) or not resolved:
            raise DarajaError("payment_integration_not_configured")
        return resolved


def _as_string(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int)):
        return str(value)
    return None
