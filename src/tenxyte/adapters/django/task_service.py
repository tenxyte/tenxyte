import logging
import threading
from typing import Any, Callable
from tenxyte.core.task_service import TaskService

logger = logging.getLogger(__name__)


def _run_in_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    try:
        func(*args, **kwargs)
    except Exception as e:
        logger.exception("Error executing background task in SyncThreadTaskService: %s", str(e))


class SyncThreadTaskService(TaskService):
    """
    A simple zero-dependency backend that runs tasks in a background thread.
    Useful for local development or when neither Celery nor RQ are available.
    """

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        thread = threading.Thread(target=_run_in_thread, args=(func,) + args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread.name


class CeleryTaskService(TaskService):
    """
    Backend that delegates to Celery.
    If the function is a Celery `@shared_task`, it calls `.delay()`.
    Otherwise, it wraps standard functions in a generic Celery task.
    """

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        # Check if it's already a Celery task
        if hasattr(func, "delay"):
            result = func.delay(*args, **kwargs)
            return result.id

        # Wrap in generic Celery task
        try:
            from celery import shared_task
        except ImportError:
            raise RuntimeError("Celery is not installed or configured.")

        # Create a dynamic task wrapper
        @shared_task(name=f"tenxyte.generic_task.{func.__name__}")
        def _generic_celery_task(*task_args, **task_kwargs):
            return func(*task_args, **task_kwargs)

        result = _generic_celery_task.delay(*args, **kwargs)
        return result.id


class RQTaskService(TaskService):
    """
    Backend that delegates to Django-RQ.
    """

    def __init__(self, queue_name: str = "default"):
        self.queue_name = queue_name

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        try:
            import django_rq
        except ImportError:
            raise RuntimeError("django_rq is not installed or configured.")

        queue = django_rq.get_queue(self.queue_name)
        job = queue.enqueue(func, *args, **kwargs)
        return job.id
