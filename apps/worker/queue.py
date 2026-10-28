from datetime import datetime, timedelta, timezone
import threading
from typing import Any, Dict, List, Optional
import uuid

from apps.worker.interface import Job, JobQueue

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryJobQueue(JobQueue):
    """
    Thread-safe in-memory job queue conforming to the JobQueue interface.
    Used for local tests, development, and M0 baseline validation.
    """

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        run_at: Optional[datetime] = None,
        max_attempts: int = 3,
    ) -> Job:
        with self._lock:
            job_id = str(uuid.uuid4())
            now = utc_now()
            job = Job(
                id=job_id,
                job_type=job_type,
                payload=payload,
                status="PENDING",
                run_at=run_at or now,
                max_attempts=max_attempts,
                created_at=now,
                updated_at=now,
            )
            self._jobs[job_id] = job
            return job

    def claim_batch(
        self,
        batch_size: int = 10,
        lease_seconds: int = 60,
    ) -> List[Job]:
        with self._lock:
            now = utc_now()
            claimed: List[Job] = []

            for job in self._jobs.values():
                if len(claimed) >= batch_size:
                    break

                is_pending = job.status == "PENDING" and job.run_at <= now
                is_expired_lease = (
                    job.status == "RUNNING"
                    and job.lease_expires_at is not None
                    and job.lease_expires_at <= now
                    and job.attempts < job.max_attempts
                )

                if is_pending or is_expired_lease:
                    job.status = "RUNNING"
                    job.attempts += 1
                    job.lease_id = str(uuid.uuid4())
                    job.lease_expires_at = now + timedelta(seconds=lease_seconds)
                    job.updated_at = now
                    claimed.append(job)

            return claimed

    def complete(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            if job_id in self._jobs:
                now = utc_now()
                self._jobs[job_id].status = "COMPLETED"
                self._jobs[job_id].lease_id = None
                self._jobs[job_id].lease_expires_at = None
                self._jobs[job_id].updated_at = now

    def fail(self, job_id: str, error: str, retry: bool = True) -> None:
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                now = utc_now()
                job.last_error = error
                job.lease_id = None
                job.lease_expires_at = None
                job.updated_at = now

                if retry and job.attempts < job.max_attempts:
                    # Exponential backoff retry
                    backoff_seconds = min(300, 2 ** job.attempts * 5)
                    job.status = "PENDING"
                    job.run_at = now + timedelta(seconds=backoff_seconds)
                else:
                    job.status = "FAILED"

    def heartbeat(self, job_id: str, lease_id: str, extension_seconds: int = 60) -> bool:
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                if job.status == "RUNNING" and job.lease_id == lease_id:
                    now = utc_now()
                    job.lease_expires_at = now + timedelta(seconds=extension_seconds)
                    job.updated_at = now
                    return True
            return False

