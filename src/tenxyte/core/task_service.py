"""
Task service port for Tenxyte Core.

This module provides the abstract interface for background task execution,
allowing the core to enqueue jobs without coupling to specific implementations
like Celery, RQ, or FastAPI BackgroundTasks.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, TypeVar, Union
import asyncio

T = TypeVar("T")


class TaskService(ABC):
    """
    Abstract base class for background task services.

    Implementations must provide concrete methods for enqueueing tasks
    regardless of the underlying task queue backend (Celery, RQ, asyncio, etc.).
    """

    @abstractmethod
    def enqueue(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """
        Enqueue a synchronous function to run in the background.

        Args:
            func: The synchronous function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            A string representing the task ID.
        """
        pass

    async def enqueue_async(
        self, func: Union[Callable[..., Coroutine[Any, Any, Any]], Callable[..., Any]], *args: Any, **kwargs: Any
    ) -> str:
        """
        Enqueue a function (sync or async) to run in the background non-blockingly.

        This base implementation dynamically delegates to the port's native
        async enqueue method if available, or falls back to running the
        synchronous enqueue method in a separate thread.

        Args:
            func: The function (synchronous or asynchronous) to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            A string representing the task ID.
        """
        native_async = getattr(self, "_enqueue_async_native", None)
        if native_async and callable(native_async):
            return await native_async(func, *args, **kwargs)

        # Fallback for sync adapters (e.g., Celery, RQ)
        return await asyncio.to_thread(self.enqueue, func, *args, **kwargs)
