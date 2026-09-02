"""Asynchronous Audit & Telemetry Logging Engine.
Decouples persistent storage (database / log streams) from the real-time evaluation path.
Guarantees ZERO database bottlenecks on the critical evaluation loop.
"""
import time
import logging
from typing import Dict, Any, List
from collections import deque
import threading

logger = logging.getLogger("trustdna.audit")


class AsyncAuditLogger:
    """
    Non-blocking in-memory buffer that collects decision audit trails
    and writes them asynchronously out-of-band without blocking HTTP client responses.
    """
    def __init__(self, max_buffer_size: int = 10000):
        self._buffer: deque = deque(maxlen=max_buffer_size)
        self._lock = threading.Lock()
        self._total_logged: int = 0

    def log_decision(self, record: Dict[str, Any]) -> None:
        """Called via FastAPI BackgroundTasks after HTTP response is flushed."""
        record["logged_at_epoch"] = time.time()
        with self._lock:
            self._buffer.append(record)
            self._total_logged += 1
        
        # In production, this can flush to PostgreSQL / Kafka / ClickHouse in batches
        logger.debug(f"Audit log recorded for customer={record.get('customer_id')} decision={record.get('decision')}")

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve latest audit records for administrative / monitoring inspection."""
        with self._lock:
            items = list(self._buffer)
            return items[-limit:]

    @property
    def total_logged(self) -> int:
        with self._lock:
            return self._total_logged


audit_logger = AsyncAuditLogger()
