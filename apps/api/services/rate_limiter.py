"""
Lightweight In-Memory Sliding-Window Rate Limiter.

Zero external dependencies. Enforces per-IP and per-action limits:
- Login: 5 attempts per 60s
- Signup: 5 attempts per 3600s
- Key test: 10 attempts per 60s
- Upload: 10 attempts per 60s
"""

from collections import defaultdict
import time
from typing import Dict, List, Tuple
from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self):
        # Key: (action, ip) -> list of timestamp floats
        self._history: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def check(self, request: Request, action: str, max_requests: int, window_seconds: int) -> None:
        """
        Enforces sliding-window rate limit. Raises HTTP 429 if exceeded.
        """
        ip = request.client.host if request.client else "unknown"
        # Extract real client IP if forwarded by proxy (Render)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()

        key = (action, ip)
        now = time.time()
        cutoff = now - window_seconds

        # Filter out timestamps older than the window
        timestamps = [t for t in self._history[key] if t > cutoff]

        if len(timestamps) >= max_requests:
            retry_after = int(window_seconds - (now - timestamps[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {action}. Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        self._history[key] = timestamps


rate_limiter = SlidingWindowLimiter()
