"""
Database-Backed Persistent & In-Memory Sliding-Window Rate Limiter.

Enforces per-IP and per-account (email) limits:
- Login: 5 attempts per 60s
- Signup: 5 attempts per 3600s
- OTP Requests: 5 attempts per 300s
- Key test: 10 attempts per 60s
- Upload: 10 attempts per 60s

Persistent Database Storage:
- Backed by the `rate_limits` table (`RateLimitRecord`) so limits and lockouts survive container recycles and deploys.
- Gracefully falls back to in-memory tracking if database is temporarily unavailable.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from packages.shared.schema import RateLimitRecord

logger = logging.getLogger("mailorbit.rate_limiter")


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware UTC, normalizing SQLite naive datetimes."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SlidingWindowLimiter:
    def __init__(self):
        # In-memory fallback history: (action, scope_identifier) -> list of timestamp floats
        self._history: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def get_client_ip(self, request: Request) -> str:
        """
        Extracts trusted client IP handling reverse proxy hops.
        Prevents client header spoofing by reading the IP appended by the trusted proxy chain
        instead of trusting the client-supplied first X-Forwarded-For entry.
        CF-Connecting-IP is ignored unless IS_BEHIND_CLOUDFLARE is explicitly True.
        """
        from apps.api.config import settings

        if getattr(settings, "IS_BEHIND_CLOUDFLARE", False):
            cf_ip = request.headers.get("CF-Connecting-IP")
            if cf_ip:
                return cf_ip.strip()

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ips = [x.strip() for x in forwarded.split(",") if x.strip()]
            if ips:
                proxy_count = max(1, getattr(settings, "TRUSTED_PROXY_COUNT", 1))
                idx = -proxy_count if len(ips) >= proxy_count else 0
                return ips[idx]

        return request.client.host if request.client else "unknown"

    def _check_db_limit(
        self,
        db: Session,
        key: str,
        max_requests: int,
        window_seconds: int,
        error_message: str,
    ) -> None:
        """Evaluates and persists rate limits to the database."""
        now = datetime.now(timezone.utc)
        record = db.query(RateLimitRecord).filter(RateLimitRecord.key == key).first()

        # Check existing lockout
        if record and record.locked_until:
            locked_until = ensure_utc(record.locked_until)
            if locked_until and locked_until > now:
                retry_after = max(1, int((locked_until - now).total_seconds()))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"{error_message} Locked out. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

        window_start = ensure_utc(record.window_start) if record else None
        window_expiry = (window_start + timedelta(seconds=window_seconds)) if window_start else now
        if not record or now > window_expiry:
            # First request in new window
            if not record:
                record = RateLimitRecord(
                    key=key,
                    attempts=1,
                    window_start=now,
                )
                db.add(record)
            else:
                record.attempts = 1
                record.window_start = now
                record.locked_until = None
            db.commit()
            return

        # Within active window
        record.attempts += 1
        if record.attempts > max_requests:
            # Lockout for the window duration
            record.locked_until = now + timedelta(seconds=window_seconds)
            db.commit()
            retry_after = window_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"{error_message} Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        db.commit()

    def check_otp_abuse(
        self,
        request: Request,
        email: str,
        db: Optional[Session] = None,
    ) -> None:
        """
        Database-backed OTP abuse prevention:
        1. 60-second cooldown per target email (counted on ATTEMPTS).
        2. Hourly limit of 5 OTP requests per target email (counted on ATTEMPTS).
        3. Daily limit of 15 OTP requests per target email (counted on ATTEMPTS).
        4. Hourly limit of 20 OTP requests per client IP (counted on ATTEMPTS).
        """
        norm_email = email.strip().lower()
        ip = self.get_client_ip(request)

        if db is not None:
            # 1. 60s cooldown per email
            self._check_db_limit(
                db=db,
                key=f"otp_cooldown:id:{norm_email}",
                max_requests=1,
                window_seconds=60,
                error_message="Please wait 60 seconds before requesting another code.",
            )
            # 2. Hourly limit per email
            self._check_db_limit(
                db=db,
                key=f"otp_hourly:id:{norm_email}",
                max_requests=5,
                window_seconds=3600,
                error_message="Too many verification code requests for this email address. Please try again in an hour.",
            )
            # 3. Daily limit per email
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self._check_db_limit(
                db=db,
                key=f"otp_daily:id:{norm_email}:{today_str}",
                max_requests=15,
                window_seconds=86400,
                error_message="Daily verification limit reached for this email address. Please try again tomorrow.",
            )
            # 4. Hourly limit per IP
            self._check_db_limit(
                db=db,
                key=f"otp_ip_hourly:ip:{ip}",
                max_requests=20,
                window_seconds=3600,
                error_message="Too many verification requests from your network. Please try again later.",
            )
        else:
            self.check(request, "otp_cooldown", max_requests=1, window_seconds=60, identifier=norm_email)
            self.check(request, "otp_hourly", max_requests=5, window_seconds=3600, identifier=norm_email)

    def check(
        self,
        request: Request,
        action: str,
        max_requests: int,
        window_seconds: int,
        identifier: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> None:
        """
        Enforces rate limiting keyed on:
        1. Real client IP
        2. Account identifier (e.g. email) if provided
        Uses database persistence if db session is provided; falls back to in-memory history.
        """
        ip = self.get_client_ip(request)

        # 1. Database-backed execution if db session is provided
        if db is not None:
            try:
                # Check IP limit in DB
                self._check_db_limit(
                    db=db,
                    key=f"{action}:ip:{ip}",
                    max_requests=max_requests,
                    window_seconds=window_seconds,
                    error_message=f"Rate limit exceeded for {action}.",
                )
                # Check identifier (email) limit in DB
                if identifier:
                    norm_id = identifier.lower().strip()
                    self._check_db_limit(
                        db=db,
                        key=f"{action}:id:{norm_id}",
                        max_requests=max_requests,
                        window_seconds=window_seconds,
                        error_message="Too many attempts for this account.",
                    )
                return
            except HTTPException:
                raise
            except Exception as e:
                logger.warning("Database rate limiting check failed (%s); falling back to in-memory: %s", action, e)
                try:
                    db.rollback()
                except Exception:
                    pass

        # 2. In-Memory Fallback
        now = time.time()
        cutoff = now - window_seconds

        # Enforce IP-based limit
        ip_key = (action, f"ip:{ip}")
        ip_history = [t for t in self._history[ip_key] if t > cutoff]

        if len(ip_history) >= max_requests:
            retry_after = int(window_seconds - (now - ip_history[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {action}. Please try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        # Enforce Account/Email-based limit if identifier is provided
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
        """Clears in-memory sliding window history."""
        self._history.clear()


rate_limiter = SlidingWindowLimiter()
