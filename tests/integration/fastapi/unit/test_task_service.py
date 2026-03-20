import asyncio
import pytest
from unittest.mock import MagicMock, patch

from tenxyte.adapters.fastapi.task_service import AsyncIOTaskService


# Basic Sync and Async targets for the tests
def sample_sync_task(x, y):
    return x + y


async def sample_async_task(x, y):
    await asyncio.sleep(0.01)
    return x * y


@pytest.fixture
def service():
    return AsyncIOTaskService()


class TestAsyncIOTaskService:
    @pytest.mark.anyio
    @patch("tenxyte.adapters.fastapi.task_service.asyncio.get_running_loop")
    async def test_enqueue_sync_with_loop(self, mock_get_running_loop, service):
        """When enqueue hits a running loop, it runs in the executor."""
        # Mock loop
        mock_loop = MagicMock()
        mock_task = MagicMock()
        mock_loop.run_in_executor.return_value = mock_task
        mock_get_running_loop.return_value = mock_loop

        job_id = service.enqueue(sample_sync_task, 3, 4)

        assert job_id.startswith("asyncio-thread-")
        mock_loop.run_in_executor.assert_called_once()
        # Verify the callable inside was roughly correct (it's a lambda for thread execution)
        args, kwargs = mock_loop.run_in_executor.call_args
        assert args[0] is None  # Defaults to default executor
        assert callable(args[1]) # The lambda wrapping _execute_sync_task

    @patch("tenxyte.adapters.fastapi.task_service.asyncio.get_running_loop")
    def test_enqueue_sync_no_loop(self, mock_get_running_loop, service):
        """When no loop exists, execute sync function synchronously as fallback."""
        # Raise RuntimeError for no running loop
        mock_get_running_loop.side_effect = RuntimeError("No running event loop")
        
        # Test executing it synchronous fallback
        with patch.object(service, "_execute_sync_task") as mock_execute:
            job_id = service.enqueue(sample_sync_task, 3, 4)

            assert job_id == "sync-execution"
            mock_execute.assert_called_once_with(sample_sync_task, 3, 4)

    @pytest.mark.anyio
    async def test_enqueue_async_coro_func(self, service):
        """Test scheduling a standard coroutine function."""
        with patch("tenxyte.adapters.fastapi.task_service.asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task
            
            job_id = await service.enqueue_async(sample_async_task, 5, 2)
            
            assert job_id.startswith("asyncio-task-")
            mock_create_task.assert_called_once()

    @pytest.mark.anyio
    async def test_enqueue_async_sync_func_fallback(self, service):
        """Test that if we enqueue_async a sync function, it routes gracefully back to enqueue."""
        with patch.object(service, "enqueue") as mock_enqueue:
            mock_enqueue.return_value = "routed-sync-id"
            
            job_id = await service.enqueue_async(sample_sync_task, 1, 1)
            
            assert job_id == "routed-sync-id"
            mock_enqueue.assert_called_once_with(sample_sync_task, 1, 1)

    def test_execute_sync_task_catches_exception(self, service, caplog):
        """Errors in background task shouldn't blow up the app lifecycle."""
        def bad_sync_task():
            raise ValueError("Intentional Error")
        
        service._execute_sync_task(bad_sync_task)
        assert "Intentional Error" in caplog.text

    @pytest.mark.anyio
    async def test_execute_async_task_catches_exception(self, service, caplog):
        """Errors in async background task shouldn't panic."""
        async def bad_async_task():
            raise ValueError("Async Intentional Error")
        
        await service._execute_async_task(bad_async_task())
        assert "Async Intentional Error" in caplog.text
