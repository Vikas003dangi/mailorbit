"""
Lightweight In-Memory Sliding-Window Rate Limiter.

Zero external dependencies. Enforces per-IP and per-account (email) limits:
- Login: 5 attempts per 60s
- Signup: 5 attempts per 3600s
- Key test: 10 attempts per 60s
- Upload: 10 attempts per 60s
"""

from collections import defaultdict
import time
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self):
        # Key: (action, scope_identifier) -> list of timestamp floats
        self._history: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def get_client_ip(self, request: Request) -> str:
        """Extracts trusted client IP handling CDN/proxy headers (Cloudflare, Render reverse-proxy)."""
        for header in ("CF-Connecting-IP", "X-Real-IP"):
            val = request.headers.get(header)
            if val:
                return val.strip()
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(
        self,
        request: Request,
        action: str,
        max_requests: int,
        window_seconds: int,
        identifier: Optional[str] = None,
    ) -> None:
        """
        Enforces sliding-window rate limit keyed on:
        1. Real client IP
        2. Account identifier (e.g. email) if provided
        Raises HTTP 429 if either threshold is breached.
        """
        ip = self.get_client_ip(request)
        now = time.time()
        cutoff = now - window_seconds

        # 1. Enforce IP-based limit
        ip_key = (action, f"ip:{ip}")
        ip_history = [t for t in self._history[ip_key] if t > cutoff]

        if len(ip_history) >= max_requests:
            retry_after = int(window_seconds - (now - ip_history[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {action}. Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        # 2. Enforce Account/Email-based limit if identifier is provided
        if identifier:
            norm_id = identifier.lower().strip()
            id_key = (action, f"id:{norm_id}")
            id_history = [t for t in self._history[id_key] if t > cutoff]

            if len(id_history) >= max_requests:
                retry_after = int(window_seconds - (now - id_history[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts for this account. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            id_history.append(now)
            self._history[id_key] = id_history

        ip_history.append(now)
        self._history[ip_key] = ip_history

    def reset(self) -> None:
        """Clears sliding window history across all actions and identifiers."""
        self._history.clear()


rate_limiter = SlidingWindowLimiter()

