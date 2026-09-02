"""Cryptographic Telemetry Token Engine.
Handles packing, signing, and decoding of opaque client telemetry tokens (td_tok_...).
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Dict, Any, Tuple, Optional

# Master internal secret for signing tokens (configurable in production)
TOKEN_SECRET = b"trustdna_telemetry_signing_secret_key_v1"


def create_telemetry_token(payload: Dict[str, Any], publishable_key: str = "td_pub_test_default") -> str:
    """
    Packs telemetry payload into an opaque signed token.
    Format: td_tok_<base64_payload>.<signature>
    """
    token_data = {
        "pub": publishable_key,
        "ts": round(time.time(), 3),
        "data": payload
    }
    json_bytes = json.dumps(token_data, separators=(",", ":")).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(json_bytes).decode("utf-8").rstrip("=")
    
    # Generate HMAC-SHA256 signature
    sig = hmac.new(TOKEN_SECRET, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    return f"td_tok_{b64_payload}.{sig}"


def decode_telemetry_token(token_str: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Decodes and validates a telemetry token.
    Returns (is_valid, decoded_payload, error_message).
    """
    if not token_str or not token_str.startswith("td_tok_"):
        return False, None, "Invalid token prefix: must start with td_tok_"

    token_body = token_str[7:]  # Strip 'td_tok_'
    parts = token_body.split(".")
    if len(parts) != 2:
        return False, None, "Malformed token structure"

    b64_payload, signature = parts[0], parts[1]

    # Verify signature
    expected_sig = hmac.new(TOKEN_SECRET, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(signature, expected_sig):
        return False, None, "Token signature verification failed"

    # Decode base64 payload
    padding = "=" * (4 - (len(b64_payload) % 4)) if len(b64_payload) % 4 != 0 else ""
    try:
        raw_json = base64.urlsafe_b64decode(b64_payload + padding).decode("utf-8")
        data = json.loads(raw_json)
        return True, data, ""
    except Exception as ex:
        return False, None, f"Token decode error: {str(ex)}"
