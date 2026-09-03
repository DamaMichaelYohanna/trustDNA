"""Cryptographic Telemetry Token Engine.
Handles packing, signing, decoding, and deterministic developer QA test tokens.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Dict, Any, Tuple, Optional

# Master internal secret for signing tokens (configurable in production)
TOKEN_SECRET = b"trustdna_telemetry_signing_secret_key_v1"

# Deterministic QA Developer Test Token Definitions
DETERMINISTIC_TEST_TOKENS = {
    "td_tok_test_allow": {
        "pub": "td_pub_test_mock",
        "ts": time.time(),
        "data": {
            "device": {"profile": "known_trusted", "is_headless": False, "entropy_score": 98.5},
            "network": {"type": "residential", "ip": "192.168.1.100"},
            "travel": {"distance_km": 0},
            "behavior": {"typing_profile": "natural", "flight_time_variance_ms": 38.4, "touch_curve_velocity": 450.0}
        }
    },
    "td_tok_test_challenge": {
        "pub": "td_pub_test_mock",
        "ts": time.time(),
        "data": {
            "device": {"profile": "new_fingerprint", "is_headless": False, "entropy_score": 62.0},
            "network": {"type": "datacenter_vpn", "ip": "104.28.19.45"},
            "travel": {"distance_km": 450},
            "behavior": {"typing_profile": "deviated", "flight_time_variance_ms": 15.2, "touch_curve_velocity": 210.0}
        }
    },
    "td_tok_test_block": {
        "pub": "td_pub_test_mock",
        "ts": time.time(),
        "data": {
            "device": {"profile": "emulated_rooted", "is_headless": True, "entropy_score": 12.0},
            "network": {"type": "tor_exit", "ip": "185.220.101.5"},
            "travel": {"distance_km": 3500},
            "behavior": {"typing_profile": "robotic_paste", "flight_time_variance_ms": 0.2, "touch_curve_velocity": 0.0}
        }
    }
}


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
    Supports standard cryptographically signed tokens as well as deterministic test tokens.
    Returns (is_valid, decoded_payload, error_message).
    """
    if not token_str or not token_str.startswith("td_tok_"):
        return False, None, "Invalid token prefix: must start with td_tok_"

    # 1. Check for deterministic developer test tokens
    if token_str in DETERMINISTIC_TEST_TOKENS:
        test_payload = DETERMINISTIC_TEST_TOKENS[token_str].copy()
        test_payload["ts"] = time.time()
        return True, test_payload, ""

    token_body = token_str[7:]  # Strip 'td_tok_'
    parts = token_body.split(".")
    if len(parts) != 2:
        return False, None, "Malformed token structure"

    b64_payload, signature = parts[0], parts[1]

    # 2. Verify HMAC signature
    expected_sig = hmac.new(TOKEN_SECRET, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(signature, expected_sig):
        return False, None, "Token signature verification failed"

    # 3. Decode base64 payload
    padding = "=" * (4 - (len(b64_payload) % 4)) if len(b64_payload) % 4 != 0 else ""
    try:
        raw_json = base64.urlsafe_b64decode(b64_payload + padding).decode("utf-8")
        data = json.loads(raw_json)
        return True, data, ""
    except Exception as ex:
        return False, None, f"Token decode error: {str(ex)}"
