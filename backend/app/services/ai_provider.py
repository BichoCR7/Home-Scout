"""Configurable, server-only text completion client for OpenAI-compatible endpoints."""

from __future__ import annotations

import json
import logging
import ssl
from collections.abc import Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from app.core.config import Settings

logger = logging.getLogger("homescout.ai.provider")
MAX_RESPONSE_BYTES = 524_288


class AiProviderUnavailable(Exception):
    """Provider call failed without exposing secrets or raw provider content."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class AiProviderClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def complete(self, instructions: str, messages: Sequence[dict[str, str]]) -> str:
        if not self.settings.ai_enabled:
            raise AiProviderUnavailable
        api_key = self.settings.ai_api_key.get_secret_value() if self.settings.ai_api_key else ""
        if not api_key or not self.settings.ai_api_base_url or not self.settings.ai_model:
            raise AiProviderUnavailable
        endpoint = self._endpoint()
        if self.settings.ai_api_protocol == "responses":
            payload: dict[str, Any] = {
                "model": self.settings.ai_model,
                "instructions": instructions,
                "input": list(messages),
                "store": False,
                "max_output_tokens": 900,
            }
        else:
            payload = {
                "model": self.settings.ai_model,
                "messages": [{"role": "system", "content": instructions}, *messages],
                "max_tokens": 900,
            }
        request = Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        opener = build_opener(
            _RejectRedirects(), HTTPSHandler(context=ssl.create_default_context())
        )
        try:
            with opener.open(request, timeout=self.settings.ai_request_timeout_seconds) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise AiProviderUnavailable
                result = json.loads(body)
        except HTTPError as error:
            logger.warning("provider_request_rejected status=%s", error.code)
            raise AiProviderUnavailable from None
        except (TimeoutError, URLError, OSError, ValueError, json.JSONDecodeError) as error:
            logger.warning("provider_request_failed error_type=%s", type(error).__name__)
            raise AiProviderUnavailable from None
        except Exception as error:
            logger.warning("provider_response_failed error_type=%s", type(error).__name__)
            raise AiProviderUnavailable from None
        try:
            text = self._extract_text(result)
        except (AttributeError, KeyError, IndexError, TypeError, ValueError):
            logger.warning("provider_response_invalid")
            raise AiProviderUnavailable from None
        clean = text.strip()
        if not clean or len(clean) > 12_000:
            raise AiProviderUnavailable
        return clean

    def _endpoint(self) -> str:
        base = (self.settings.ai_api_base_url or "").rstrip("/")
        suffix = "responses" if self.settings.ai_api_protocol == "responses" else "chat/completions"
        if base.endswith("/v1"):
            return f"{base}/{suffix}"
        return f"{base}/v1/{suffix}"

    def _extract_text(self, result: object) -> str:
        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object.")
        if self.settings.ai_api_protocol == "chat_completions":
            choices = result["choices"]
            message = choices[0]["message"]
            content = message["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join(
                    block["text"]
                    for block in content
                    if isinstance(block, dict) and isinstance(block.get("text"), str)
                )
            raise ValueError("Expected message content.")
        if isinstance(result.get("output_text"), str):
            return result["output_text"]
        output = result["output"]
        pieces = []
        for item in output:
            if item.get("type") != "message":
                continue
            for block in item.get("content", []):
                if block.get("type") == "output_text" and isinstance(block.get("text"), str):
                    pieces.append(block["text"])
        if not pieces:
            raise ValueError("Expected output text.")
        return "\n".join(pieces)
