from datetime import datetime, timedelta
import time
from apps.worker.interface import Job
from apps.worker.queue import InMemoryJobQueue
from apps.worker.runner import WorkerRunner


def test_in_memory_queue_lifecycle():
    queue = InMemoryJobQueue()
    job = queue.enqueue("send_email", {"to": "test@example.com", "subject": "Hello"})
    assert job.status == "PENDING"
    assert job.job_type == "send_email"

    # Claim
    claimed = queue.claim_batch(batch_size=5, lease_seconds=10)
    assert len(claimed) == 1
    assert claimed[0].id == job.id
    assert claimed[0].status == "RUNNING"
    assert claimed[0].lease_id is not None

    # Complete
    queue.complete(job.id, result={"status": "sent"})
    assert queue._jobs[job.id].status == "COMPLETED"


def test_worker_runner_dispatch():
    queue = InMemoryJobQueue()
    runner = WorkerRunner(queue=queue)

    processed_jobs = []

    def handle_mock_email(job: Job):
        processed_jobs.append(job.payload["to"])
        return {"status": "ok"}

    runner.register_handler("send_email", handle_mock_email)

    queue.enqueue("send_email", {"to": "alice@example.com"})
    queue.enqueue("send_email", {"to": "bob@example.com"})

    count = runner.tick(batch_size=10)
    assert count == 2
    assert "alice@example.com" in processed_jobs
    assert "bob@example.com" in processed_jobs
