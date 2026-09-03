"""Outbound Signed Webhook Delivery Engine for TrustDNA.
Dispatches signed event payloads to client-configured HTTP endpoints.
"""
import hashlib
import hmac
import json
import logging
import secrets
import time
import requests
from typing import Dict, Any, Optional
from ..config import settings

logger = logging.getLogger("trustdna.webhooks")


def generate_webhook_signature(payload_str: str, secret: str, timestamp: int) -> str:
    """
    Computes standard enterprise HMAC-SHA256 signature header.
    Format: t=<timestamp>,v1=<signature_hex>
    """
    signature_payload = f"{timestamp}.{payload_str}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signature_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


def dispatch_webhook_event(
    webhook_url: str,
    webhook_secret: Optional[str],
    event_type: str,
    tenant_id: str,
    event_data: Dict[str, Any]
):
    """
    Delivers a signed webhook event asynchronously to third-party endpoints.
    Designed to run in background tasks with strict timeouts and error isolation.
    """
    if not webhook_url or not webhook_url.startswith(("http://", "https://")):
        return

    now = int(time.time())
    event_id = f"evt_{secrets.token_hex(8)}"
    payload_obj = {
        "id": event_id,
        "event": event_type,
        "created_at": now,
        "tenant_id": tenant_id,
        "data": event_data
    }

    payload_json = json.dumps(payload_obj, separators=(",", ":"))
    secret = webhook_secret or "trustdna_default_webhook_secret_key"
    sig_header = generate_webhook_signature(payload_json, secret, now)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "TrustDNA-Webhook-Dispatcher/1.0",
        "X-TrustDNA-Event": event_type,
        "X-TrustDNA-Event-Id": event_id,
        "X-TrustDNA-Signature": sig_header
    }

    try:
        resp = requests.post(
            webhook_url,
            data=payload_json,
            headers=headers,
            timeout=settings.webhook_timeout_seconds
        )
        if resp.status_code >= 400:
            logger.warning(f"[TrustDNA Webhook] Client endpoint returned HTTP {resp.status_code} for {event_id}")
    except Exception as ex:
        logger.warning(f"[TrustDNA Webhook] Failed to deliver {event_id} to {webhook_url}: {str(ex)}")
