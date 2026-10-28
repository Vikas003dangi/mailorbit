from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass
class Job:
    id: str
    job_type: str
    payload: Dict[str, Any]
    status: str = "PENDING"
    attempts: int = 0
    max_attempts: int = 3
    run_at: datetime = field(default_factory=utc_now)
    lease_id: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


class JobQueue(ABC):
    """
    Abstract interface for MailOrbit job queues.
    Decouples the worker runner from the backing storage (Memory in M0/tests,
    PostgreSQL FOR UPDATE SKIP LOCKED in M1+).
    """

    @abstractmethod
    def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        run_at: Optional[datetime] = None,
        max_attempts: int = 3,
    ) -> Job:
        """Enqueue a new background job."""
        pass

    @abstractmethod
    def claim_batch(
        self,
        batch_size: int = 10,
        lease_seconds: int = 60,
    ) -> List[Job]:
        """Claim a batch of runnable pending/expired jobs with a leased lock."""
        pass

    @abstractmethod
    def complete(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark a claimed job as completed."""
        pass

    @abstractmethod
    def fail(self, job_id: str, error: str, retry: bool = True) -> None:
        """Mark a claimed job as failed or retryable."""
        pass

    @abstractmethod
    def heartbeat(self, job_id: str, lease_id: str, extension_seconds: int = 60) -> bool:
        """Extend lease of a currently running job."""
        pass

