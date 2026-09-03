"""Composite Risk Scoring Engine for TrustDNA.
Combines device, network, travel, behavioral, and transaction telemetry into actionable decisions.
"""
import time
from typing import List, Dict, Any
from ..config import settings
from ..models.request import RiskEvaluationRequest
from ..models.response import RiskEvaluationResponse, ModuleScores, ReasonTag
from .network import evaluate_network
from .travel import calculate_haversine_distance, calculate_travel_velocity
from .velocity import velocity_tracker
from .tokens import decode_telemetry_token
from .training import training_pipeline


def evaluate_risk(request: RiskEvaluationRequest) -> RiskEvaluationResponse:
    start_time = time.perf_counter()

    reasons: List[ReasonTag] = []
    token_features: Dict[str, Any] = {}

    # Decode client telemetry token if provided
    if request.telemetry_token:
        valid, decoded_data, err_msg = decode_telemetry_token(request.telemetry_token)
        if valid and decoded_data and "data" in decoded_data:
            token_features = decoded_data["data"]
            reasons.append(ReasonTag(text="valid_telemetry_token_verified", type="success"))
        else:
            reasons.append(ReasonTag(text="invalid_or_expired_telemetry_token", type="warning"))

    # 1. Device Evaluation
    device_profile = request.device.profile
    if token_features.get("webdriver", False):
        device_score = 10
        reasons.append(ReasonTag(text="headless_browser_automation_detected", type="danger"))
    elif device_profile == "known_trusted":
        device_score = 96
        reasons.append(ReasonTag(text="known_device_profile", type="success"))
    elif device_profile == "new_fingerprint":
        device_score = 60
        reasons.append(ReasonTag(text="new_device_fingerprint", type="warning"))
    elif device_profile == "emulated_rooted" or request.device.is_rooted_or_jailbroken:
        device_score = 15
        reasons.append(ReasonTag(text="emulated_or_rooted_environment", type="danger"))
    else:
        device_score = 70
        reasons.append(ReasonTag(text="unverified_device_entropy", type="warning"))

    # 2. Network Evaluation
    network_score, net_reasons = evaluate_network(
        request.network.type,
        request.network.ip_address
    )
    reasons.extend(net_reasons)

    # 3. Impossible Travel Evaluation
    travel_km = request.travel.distance_km
    time_delta = request.travel.time_delta_hours or 1.0

    # If explicit coordinates are provided, recalculate distance
    if request.travel.previous_location and request.travel.current_location:
        travel_km = calculate_haversine_distance(
            request.travel.previous_location.latitude,
            request.travel.previous_location.longitude,
            request.travel.current_location.latitude,
            request.travel.current_location.longitude
        )
        time_elapsed_sec = max(
            1.0,
            request.travel.current_location.timestamp_epoch_sec - request.travel.previous_location.timestamp_epoch_sec
        )
        time_delta = time_elapsed_sec / 3600.0

    velocity_kmh, is_impossible = calculate_travel_velocity(travel_km, time_delta)

    if is_impossible or travel_km > settings.max_realistic_travel_speed_kmh:
        network_score = min(network_score, 20)
        reasons.append(ReasonTag(
            text=f"impossible_travel_delta_{int(travel_km)}km",
            type="danger"
        ))

    # 4. Behavioral Biometrics Evaluation
    behavior_profile = request.behavior.typing_profile

    # If client token has real collected keystroke cadence, evaluate mathematical variance
    if "flight_std_ms" in token_features:
        flight_std = float(token_features["flight_std_ms"])
        if flight_std < 5.0:
            behavior_score = 10
            reasons.append(ReasonTag(text="bot_automated_zero_cadence_variance", type="danger"))
        elif flight_std > 65.0:
            behavior_score = 55
            reasons.append(ReasonTag(text="behavioral_flight_time_variance", type="warning"))
        else:
            behavior_score = 94
            reasons.append(ReasonTag(text="consistent_human_typing_cadence", type="success"))
        
        if token_features.get("paste_events_count", 0) > 0:
            behavior_score = min(behavior_score, 60)
            reasons.append(ReasonTag(text="clipboard_paste_event_flagged", type="warning"))
    elif behavior_profile == "natural":
        behavior_score = 92
        reasons.append(ReasonTag(text="consistent_typing_cadence", type="success"))
    elif behavior_profile == "deviated":
        behavior_score = 55
        reasons.append(ReasonTag(text="behavioral_flight_time_variance", type="warning"))
    elif behavior_profile == "robotic_paste":
        behavior_score = 12
        reasons.append(ReasonTag(text="bot_automated_keystroke_cadence", type="danger"))
    else:
        behavior_score = 75
        reasons.append(ReasonTag(text="baseline_behavioral_telemetry", type="success"))

    # 5. Transaction & Velocity Evaluation
    amount = request.transaction.amount
    account_id = request.transaction.account_id or request.user_id or "default_user"
    
    # Track velocity in sliding window
    velocity_tracker.record_attempt(account_id)
    attempt_count = velocity_tracker.get_velocity_count(account_id, window_seconds=60.0)

    if amount <= 100000:
        tx_score = 95
        reasons.append(ReasonTag(text="within_normal_spending_baseline", type="success"))
    elif amount <= 1000000:
        tx_score = 65
        reasons.append(ReasonTag(text="moderate_spend_deviation", type="warning"))
    else:
        tx_score = 25
        reasons.append(ReasonTag(text="high_value_transaction_spike", type="danger"))

    # Velocity penalty
    if attempt_count > 5:
        tx_score = max(10, tx_score - 30)
        reasons.append(ReasonTag(text=f"rapid_velocity_spike_{attempt_count}_attempts", type="danger"))

    # 6. Composite Weighted Calculation
    w = settings.weights
    composite_raw = (
        (device_score * w.device) +
        (network_score * w.network) +
        (behavior_score * w.behavior) +
        (tx_score * w.transaction)
    )
    composite_score = round(composite_raw)

    # 7. Hard Override Security Constraints
    hard_override_triggered = False
    if (
        request.network.type == "tor_exit"
        or (device_profile == "emulated_rooted" and amount > 500000)
        or travel_km > 2000
        or attempt_count > 10
    ):
        composite_score = min(composite_score, 22)
        hard_override_triggered = True

    # Clamp composite score between 5 and 99
    composite_score = max(5, min(99, composite_score))

    # 8. Decision Categorization
    thresholds = settings.thresholds
    if composite_score >= thresholds.allow_min:
        decision = "allow"
        risk_level = "low"
        recommended_action = "proceed"
    elif composite_score >= thresholds.challenge_min:
        decision = "challenge"
        risk_level = "medium"
        recommended_action = "require_totp_mfa"
    else:
        decision = "block"
        risk_level = "high"
        recommended_action = "block_and_terminate_session"

    # Execution Latency calculation
    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    uid = request.customer_id or request.user_id or "usr_anonymous"

    # 9. Asynchronously queue feature vector for ML Model Training
    if token_features:
        training_pipeline.record_feature_vector(
            features=token_features,
            decision=decision,
            trust_score=composite_score,
            client_id=uid
        )

    return RiskEvaluationResponse(
        trust_score=composite_score,
        decision=decision,
        risk_level=risk_level,
        latency_ms=elapsed_ms,
        customer_id=uid,
        reasons=[r.text for r in reasons],

        reason_details=reasons,
        module_scores=ModuleScores(
            device=device_score,
            network=network_score,
            behavior=behavior_score,
            transaction=tx_score
        ),
        recommended_action=recommended_action
    )
