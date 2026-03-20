import pytest
import asyncio
from unittest.mock import MagicMock, patch
from tenxyte.adapters.django.task_service import SyncThreadTaskService, CeleryTaskService, RQTaskService

@pytest.fixture
def task_service():
    return DjangoTaskService()

class TestTaskServiceAdapterExtra:
    def test_run_in_thread_error_path(self):
        """Lines 10-13: _run_in_thread exception handling."""
        from tenxyte.adapters.django.task_service import _run_in_thread
        mock_logger = MagicMock()
        with patch("tenxyte.adapters.django.task_service.logger", mock_logger):
            def failing_func(): raise ValueError("Explosion")
            _run_in_thread(failing_func)
            mock_logger.exception.assert_called_once()

    def test_celery_task_service_delay_path(self):
        """Line 38-40: Celery delay path."""
        svc = CeleryTaskService()
        mock_task = MagicMock()
        mock_task.delay.return_value.id = "delay-id"
        res = svc.enqueue(mock_task)
        assert res == "delay-id"

    def test_celery_task_service_enqueue_generic_wrap(self):
        """Lines 43-54: CeleryTaskService.enqueue (generic wrap)."""
        import sys
        mock_celery = MagicMock()
        with patch.dict(sys.modules, {"celery": mock_celery}):
            svc = CeleryTaskService()
            # Mock the shared_task decorator
            mock_shared_task = MagicMock()
            mock_celery.shared_task = mock_shared_task
            
            # Mock the delay helper
            mock_task = MagicMock()
            mock_shared_task.return_value = lambda f: mock_task
            mock_task.delay.return_value.id = "generic-id"
            
            def some_func(x): return x
            job_id = svc.enqueue(some_func, 10)
            
            # Verify shared_task was called to wrap the function
            mock_shared_task.assert_called()
            assert job_id == "generic-id"
            
    def test_celery_generic_task_body(self):
        """Line 51: internal task body."""
        # We can't easily find the closure, so let's mock more carefully
        import sys
        mock_celery = MagicMock()
        with patch.dict(sys.modules, {"celery": mock_celery}):
            captured_func = None
            def decorator(f):
                nonlocal captured_func
                captured_func = f
                mock_task = MagicMock()
                mock_task.delay.return_value.id = "id"
                return mock_task
            
            mock_celery.shared_task.return_value = decorator
            svc = CeleryTaskService()
            def some_func(v): return v * 2
            svc.enqueue(some_func, 21)
            
            # Now call the captured generic task body
            assert captured_func(21) == 42 # Line 51 hit!

    def test_rq_task_service_import_error(self):
        """Line 69: RQ ImportError."""
        import sys
        with patch.dict(sys.modules, {"django_rq": None}): # Hide it
            svc = RQTaskService()
            with pytest.raises(RuntimeError):
                svc.enqueue(lambda: None)
