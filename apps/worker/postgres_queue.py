from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
import uuid

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from apps.worker.interface import Job, JobQueue
from packages.shared.schema import JobModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PostgresJobQueue(JobQueue):
    """
    PostgreSQL-backed job queue implementing row-level leasing with FOR UPDATE SKIP LOCKED.
    Provides crash-resilient, transactional background job processing with lease timeouts.
    """

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        run_at: Optional[datetime] = None,
        max_attempts: int = 3,
    ) -> Job:
        now = utc_now()
        effective_run_at = run_at or now

        with self.session_factory() as session:
            job_record = JobModel(
                id=uuid.uuid4(),
                job_type=job_type,
                payload=payload,
                status="PENDING",
                run_at=effective_run_at,
                max_attempts=max_attempts,
                created_at=now,
                updated_at=now,
            )
            session.add(job_record)
            session.commit()
            session.refresh(job_record)

            return Job(
                id=str(job_record.id),
                job_type=job_record.job_type,
                payload=job_record.payload,
                status=job_record.status,
                attempts=job_record.attempts,
                max_attempts=job_record.max_attempts,
                run_at=job_record.run_at,
                lease_id=job_record.lease_id,
                lease_expires_at=job_record.lease_expires_at,
                last_error=job_record.last_error,
                created_at=job_record.created_at,
                updated_at=job_record.updated_at,
            )

    def claim_batch(
        self,
        batch_size: int = 10,
        lease_seconds: int = 60,
    ) -> List[Job]:
        now = utc_now()
        expires_at = now + timedelta(seconds=lease_seconds)
        claimed_jobs: List[Job] = []

        with self.session_factory() as session:
            # Query eligible jobs with row-level lock skipping locked rows
            stmt = (
                select(JobModel)
                .where(
                    or_(
                        and_(JobModel.status == "PENDING", JobModel.run_at <= now),
                        and_(
                            JobModel.status == "RUNNING",
                            JobModel.lease_expires_at <= now,
                            JobModel.attempts < JobModel.max_attempts,
                        ),
                    )
                )
                .order_by(JobModel.run_at.asc())
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )

            job_records = session.execute(stmt).scalars().all()

            for record in job_records:
                record.status = "RUNNING"
                record.attempts += 1
                record.lease_id = str(uuid.uuid4())
                record.lease_expires_at = expires_at
                record.updated_at = now

                claimed_jobs.append(
                    Job(
                        id=str(record.id),
                        job_type=record.job_type,
                        payload=record.payload,
                        status=record.status,
                        attempts=record.attempts,
                        max_attempts=record.max_attempts,
                        run_at=record.run_at,
                        lease_id=record.lease_id,
                        lease_expires_at=record.lease_expires_at,
                        last_error=record.last_error,
                        created_at=record.created_at,
                        updated_at=record.updated_at,
                    )
                )

            session.commit()

        return claimed_jobs

    def complete(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        now = utc_now()
        with self.session_factory() as session:
            record = session.get(JobModel, uuid.UUID(job_id))
            if record:
                record.status = "COMPLETED"
                record.lease_id = None
                record.lease_expires_at = None
                record.updated_at = now
                session.commit()

    def fail(self, job_id: str, error: str, retry: bool = True) -> None:
        now = utc_now()
        with self.session_factory() as session:
            record = session.get(JobModel, uuid.UUID(job_id))
            if record:
                record.last_error = error
                record.lease_id = None
                record.lease_expires_at = None
                record.updated_at = now

                if retry and record.attempts < record.max_attempts:
                    backoff_seconds = min(300, (2 ** record.attempts) * 5)
                    record.status = "PENDING"
                    record.run_at = now + timedelta(seconds=backoff_seconds)
                else:
                    record.status = "FAILED"

                session.commit()

    def heartbeat(self, job_id: str, lease_id: str, extension_seconds: int = 60) -> bool:
        now = utc_now()
        with self.session_factory() as session:
            record = session.get(JobModel, uuid.UUID(job_id))
            if record and record.status == "RUNNING" and record.lease_id == lease_id:
                record.lease_expires_at = now + timedelta(seconds=extension_seconds)
                record.updated_at = now
                session.commit()
                return True
            return False
