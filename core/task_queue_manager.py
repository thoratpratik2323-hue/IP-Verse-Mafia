"""
core/task_queue_manager.py — Background job queue for IP Prime OS.
Queues long-running tasks (research, code gen, file ops) and runs them
in background threads, reporting results via callback.
"""

from __future__ import annotations
import threading
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any, Literal
from enum import Enum

logger = logging.getLogger("task_queue")


class JobStatus(str, Enum):
    QUEUED   = "queued"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    job_id: str
    name: str
    fn: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: JobStatus = JobStatus.QUEUED
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    on_complete: Callable[["Job"], None] | None = None

    def to_dict(self) -> dict:
        return {
            "id":         self.job_id,
            "name":       self.name,
            "status":     self.status.value,
            "result":     str(self.result)[:200] if self.result else None,
            "error":      self.error,
            "created":    self.created_at,
            "started":    self.started_at,
            "finished":   self.finished_at,
        }


class TaskQueueManager:
    """Thread-safe background job queue with status tracking."""

    def __init__(self, max_concurrent: int = 3):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_concurrent)
        self._on_status_change: list[Callable[[Job], None]] = []

    def submit(
        self,
        name: str,
        fn: Callable,
        *args,
        on_complete: Callable[[Job], None] | None = None,
        **kwargs
    ) -> str:
        """Submit a job to the queue. Returns job_id."""
        job_id = str(uuid.uuid4())[:8]
        job = Job(
            job_id=job_id, name=name, fn=fn,
            args=args, kwargs=kwargs, on_complete=on_complete
        )
        with self._lock:
            self._jobs[job_id] = job
        t = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        t.start()
        logger.info(f"[TaskQueue] Queued: {name} ({job_id})")
        return job_id

    def _run_job(self, job: Job):
        self._semaphore.acquire()
        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now().isoformat()
            self._notify(job)
            job.result = job.fn(*job.args, **job.kwargs)
            job.status = JobStatus.DONE
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            logger.error(f"[TaskQueue] Job '{job.name}' failed: {e}")
        finally:
            job.finished_at = datetime.now().isoformat()
            self._semaphore.release()
            self._notify(job)
            if job.on_complete:
                try:
                    job.on_complete(job)
                except Exception as e:
                    logger.debug(f"[TaskQueue] on_complete error: {e}")

    def _notify(self, job: Job):
        for cb in self._on_status_change:
            try:
                cb(job)
            except Exception:
                pass

    def on_status_change(self, callback: Callable[[Job], None]):
        """Register a callback fired on every job status change."""
        self._on_status_change.append(callback)

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                return True
        return False

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def all_jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def active_jobs(self) -> list[Job]:
        return [j for j in self.all_jobs() if j.status in (JobStatus.QUEUED, JobStatus.RUNNING)]

    def clear_done(self):
        with self._lock:
            self._jobs = {k: v for k, v in self._jobs.items()
                         if v.status not in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED)}

    def summary(self) -> str:
        jobs = self.all_jobs()
        active = [j for j in jobs if j.status == JobStatus.RUNNING]
        queued = [j for j in jobs if j.status == JobStatus.QUEUED]
        done = [j for j in jobs if j.status == JobStatus.DONE]
        failed = [j for j in jobs if j.status == JobStatus.FAILED]
        return (
            f"🔄 Running: {len(active)} | ⏳ Queued: {len(queued)} | "
            f"✅ Done: {len(done)} | ❌ Failed: {len(failed)}"
        )


# Singleton
TaskQueue = TaskQueueManager()
