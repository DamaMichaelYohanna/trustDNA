"""Training Data Ingestion and Feature Extraction Pipeline.
Collects anonymous mathematical behavioral vectors to train subsequent ML models (XGBoost / Isolation Forest).
"""
import time
import threading
from collections import deque
from typing import Dict, Any, List


class TrainingDataPipeline:
    def __init__(self, max_records: int = 50000):
        self._lock = threading.Lock()
        self._records: deque = deque(maxlen=max_records)
        self._total_collected: int = 0

    def record_feature_vector(
        self,
        features: Dict[str, Any],
        decision: str,
        trust_score: int,
        client_id: str = "anonymous"
    ) -> None:
        """
        Appends an anonymous training vector.
        Contains strictly numerical statistics and hashes—zero cleartext PII.
        """
        vector = {
            "timestamp": round(time.time(), 3),
            "client_id": client_id,
            "dwell_mean_ms": features.get("dwell_mean_ms", 0.0),
            "dwell_std_ms": features.get("dwell_std_ms", 0.0),
            "flight_mean_ms": features.get("flight_mean_ms", 0.0),
            "flight_std_ms": features.get("flight_std_ms", 0.0),
            "touch_speed_px_s": features.get("touch_speed_px_s", 0.0),
            "paste_events_count": features.get("paste_events_count", 0),
            "hardware_entropy_hash": features.get("hardware_hash", "none"),
            "webdriver_flag": features.get("webdriver", False),
            "label_decision": decision,
            "label_trust_score": trust_score,
            "is_anomaly": 1 if decision in ("challenge", "block") else 0
        }

        with self._lock:
            self._records.append(vector)
            self._total_collected += 1

    def get_dataset(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._records)[-limit:]

    @property
    def total_records(self) -> int:
        with self._lock:
            return self._total_collected


training_pipeline = TrainingDataPipeline()
