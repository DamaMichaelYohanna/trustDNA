"""Enterprise-Grade Sliding-Window Velocity Engine.
Features:
- Abstract BaseVelocityStore interface.
- Bounded InMemoryVelocityStore with auto-eviction and memory leak prevention.
- Optional distributed RedisVelocityStore using atomic sorted sets for multi-worker scaling.
"""
import time
import logging
import threading
from abc import ABC, abstractmethod
from collections import deque
from typing import Dict, Deque, Optional

logger = logging.getLogger("trustdna.velocity")


class BaseVelocityStore(ABC):
    @abstractmethod
    def record_attempt(self, entity_id: str, timestamp: Optional[float] = None) -> None:
        """Record an action attempt timestamp for an entity (user, card, or IP)."""
        pass

    @abstractmethod
    def get_velocity_count(self, entity_id: str, window_seconds: float = 60.0, current_time: Optional[float] = None) -> int:
        """Return the count of attempts in the sliding window."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear state (used in testing)."""
        pass


class InMemoryVelocityStore(BaseVelocityStore):
    """
    High-performance thread-safe in-memory store.
    Includes active key cleanup and capacity caps to prevent unbounded RAM growth.
    """
    def __init__(self, max_entities: int = 50000):
        self._lock = threading.Lock()
        self._windows: Dict[str, Deque[float]] = {}
        self._max_entities = max_entities

    def record_attempt(self, entity_id: str, timestamp: Optional[float] = None) -> None:
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            # Memory ceiling protection: if dictionary exceeds capacity, evict oldest items
            if len(self._windows) >= self._max_entities and entity_id not in self._windows:
                # Evict first 10% of keys
                keys_to_evict = list(self._windows.keys())[:max(1, self._max_entities // 10)]
                for k in keys_to_evict:
                    del self._windows[k]

            if entity_id not in self._windows:
                self._windows[entity_id] = deque()
            self._windows[entity_id].append(timestamp)

    def get_velocity_count(self, entity_id: str, window_seconds: float = 60.0, current_time: Optional[float] = None) -> int:
        if current_time is None:
            current_time = time.time()
        cutoff = current_time - window_seconds

        with self._lock:
            q = self._windows.get(entity_id)
            if not q:
                return 0

            while q and q[0] < cutoff:
                q.popleft()

            count = len(q)
            # Memory hygiene: delete empty deques so keys don't linger indefinitely
            if count == 0:
                del self._windows[entity_id]

            return count

    def clear(self) -> None:
        with self._lock:
            self._windows.clear()

    @property
    def active_entities_count(self) -> int:
        with self._lock:
            return len(self._windows)


class RedisVelocityStore(BaseVelocityStore):
    """
    Distributed Redis sliding-window implementation using atomic Sorted Sets.
    Guarantees zero database bottlenecks across horizontally scaled clusters.
    """
    def __init__(self, redis_client):
        self._redis = redis_client
        self._key_prefix = "trustdna:velocity:"

    def record_attempt(self, entity_id: str, timestamp: Optional[float] = None) -> None:
        if timestamp is None:
            timestamp = time.time()
        key = f"{self._key_prefix}{entity_id}"
        # Store timestamp with microsecond resolution to ensure unique member in sorted set
        member = f"{timestamp}_{time.perf_counter()}"
        
        pipeline = self._redis.pipeline(transaction=True)
        pipeline.zadd(key, {member: timestamp})
        pipeline.expire(key, 3600)  # Auto-expire idle keys in 1 hour
        pipeline.execute()

    def get_velocity_count(self, entity_id: str, window_seconds: float = 60.0, current_time: Optional[float] = None) -> int:
        if current_time is None:
            current_time = time.time()
        cutoff = current_time - window_seconds
        key = f"{self._key_prefix}{entity_id}"

        pipeline = self._redis.pipeline(transaction=True)
        pipeline.zremrangebyscore(key, "-inf", cutoff)
        pipeline.zcard(key)
        results = pipeline.execute()
        return int(results[1])

    def clear(self) -> None:
        # In test environments, delete keys matching prefix
        keys = self._redis.keys(f"{self._key_prefix}*")
        if keys:
            self._redis.delete(*keys)


def create_velocity_store(redis_url: Optional[str] = None, max_entities: int = 50000) -> BaseVelocityStore:
    """Factory creating appropriate velocity store with automatic fallback."""
    if redis_url:
        try:
            import redis
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("Connected to Redis for distributed velocity tracking.")
            return RedisVelocityStore(client)
        except Exception as ex:
            logger.warning(f"Redis unavailable ({ex}). Falling back to bounded InMemoryVelocityStore.")

    return InMemoryVelocityStore(max_entities=max_entities)


# Global singleton instance configured via settings
from ..config import settings
velocity_tracker = create_velocity_store(
    redis_url=settings.redis_url,
    max_entities=settings.max_in_memory_entities
)
# Retain VelocityTracker alias for backwards test compatibility
VelocityTracker = InMemoryVelocityStore
