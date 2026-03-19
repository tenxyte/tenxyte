import asyncio
import logging
from typing import Any, Callable, Coroutine, Union

from tenxyte.core.task_service import TaskService

logger = logging.getLogger(__name__)


class AsyncIOTaskService(TaskService):
    """
    Background task service using native asyncio mechanisms.
    Best suited for FastAPI and pure async applications where we don't
    want/need external dependencies like Celery or RQ.
    """

    def _execute_sync_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Helper to run synchronous tasks, catching exceptions."""
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.exception("Error executing background sync task in AsyncIOTaskService: %s", str(e))

    async def _execute_async_task(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Helper to await a coroutine safely, catching exceptions."""
        try:
            await coro
        except Exception as e:
            logger.exception("Error executing background async task in AsyncIOTaskService: %s", str(e))

    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """
        Enqueues a synchronous function to run in the background.
        Uses the event loop's `run_in_executor` to avoid blocking the loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # If there's no running loop, we can't easily schedule an async task.
            # We'll just run it synchronously as a fallback for some testing contexts,
            # but ideally the developer is using BackgroundTasks or similar if no loop exists.
            logger.warning("No running event loop found. Executing task synchronously.")
            self._execute_sync_task(func, *args, **kwargs)
            return "sync-execution"

        # Execute the sync function in a thread pool managed by the event loop
        task = loop.run_in_executor(None, lambda: self._execute_sync_task(func, *args, **kwargs))
        return f"asyncio-thread-{id(task)}"

    async def enqueue_async(
        self, func: Union[Callable[..., Coroutine[Any, Any, Any]], Callable[..., Any]], *args: Any, **kwargs: Any
    ) -> str:
        """
        Enqueues an asynchronous coroutine OR a synchronous function.
        """
        if asyncio.iscoroutinefunction(func):
            # It's an async function, call it and schedule the coroutine
            coro = func(*args, **kwargs)
            task = asyncio.create_task(self._execute_async_task(coro))
            return f"asyncio-task-{id(task)}"
        elif asyncio.iscoroutine(func):
            # It's already a coroutine object.
            task = asyncio.create_task(self._execute_async_task(func))
            return f"asyncio-task-{id(task)}"
        else:
            # It's a synchronous function. Fallback to `enqueue` behavior.
            return self.enqueue(func, *args, **kwargs)
