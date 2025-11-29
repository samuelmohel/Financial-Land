import time
from typing import Dict

class CircuitBreaker:
    """Simple per-key in-memory circuit breaker.

    Usage:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=60)
        if cb.is_open('get_exchange_rate'):
            raise RuntimeError('Circuit open')
        try:
            ...call tool...
            cb.record_success('get_exchange_rate')
        except Exception:
            cb.record_failure('get_exchange_rate')
            raise
    """

    def __init__(self, failure_threshold: int = 3, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._state: Dict[str, Dict[str, float]] = {}

    def is_open(self, key: str) -> bool:
        entry = self._state.get(key)
        if not entry:
            return False
        if entry['failures'] < self.failure_threshold:
            return False
        # check reset timeout
        if time.time() - entry['last_failure'] >= self.reset_timeout:
            # reset
            self._state.pop(key, None)
            return False
        return True

    def record_failure(self, key: str):
        now = time.time()
        entry = self._state.setdefault(key, {'failures': 0, 'last_failure': now})
        entry['failures'] += 1
        entry['last_failure'] = now

    def record_success(self, key: str):
        self._state.pop(key, None)
