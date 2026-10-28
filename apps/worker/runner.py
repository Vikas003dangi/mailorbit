import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from apps.worker.interface import Job, JobQueue

logger = logging.getLogger("mailorbit.worker")


class WorkerRunner:
    """
    In-process worker executor that claims jobs from a JobQueue and dispatches
    them to registered handler functions.
    Can be ticked synchronously via API endpoint (/api/v1/tick) or run continuously
    in an embedded background thread.
    """

    def __init__(self, queue: JobQueue):
        self.queue = queue
        self.handlers: Dict[str, Callable[[Job], Any]] = {}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def register_handler(self, job_type: str, handler: Callable[[Job], Any]) -> None:
        """Register a handler callback for a specific job_type."""
        self.handlers[job_type] = handler

    def process_one(self, job: Job) -> bool:
        """Process a single claimed job."""
        handler = self.handlers.get(job.job_type)
        if not handler:
            logger.warning("No handler registered for job type: %s", job.job_type)
            self.queue.fail(job.id, f"No handler registered for {job.job_type}", retry=False)
            return False

        try:
            result = handler(job)
            self.queue.complete(job.id, result=result if isinstance(result, dict) else None)
            return True
        except Exception as e:
            logger.exception("Error executing job %s (%s): %s", job.id, job.job_type, str(e))
            self.queue.fail(job.id, str(e), retry=True)
            return False

    def tick(self, batch_size: int = 10, lease_seconds: int = 60) -> int:
        """
        Single tick: claim ready jobs and execute them.
        Returns the number of jobs processed.
        """
        jobs = self.queue.claim_batch(batch_size=batch_size, lease_seconds=lease_seconds)
        processed = 0
        for job in jobs:
            if self.process_one(job):
                processed += 1
        return processed

    def start_background(self, poll_interval_seconds: float = 5.0) -> None:
        """Start worker loop in an in-process daemon thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()

        def _loop():
            logger.info("MailOrbit in-process worker thread started")
            while not self._stop_event.is_set():
                try:
                    self.tick()
                except Exception as e:
                    logger.exception("Worker loop exception: %s", e)
                self._stop_event.wait(poll_interval_seconds)
            logger.info("MailOrbit in-process worker thread stopped")

        self._thread = threading.Thread(target=_loop, daemon=True, name="MailOrbitWorker")
        self._thread.start()

    def stop_background(self) -> None:
        """Stop background worker loop gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)

