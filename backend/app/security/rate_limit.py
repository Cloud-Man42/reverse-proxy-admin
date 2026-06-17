import secrets
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        bucket = self._attempts[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_attempts:
            return False
        bucket.append(now)
        return True

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
