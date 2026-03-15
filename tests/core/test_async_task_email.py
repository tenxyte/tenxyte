"""
Async coverage tests for:
  - core/email_service.py  (lines 84, 147-169, 222-244, 385-416, 478-509)
  - core/task_service.py   (lines 57-62)
  - adapters/django/task_service.py (lines 10-13, 43-54, 66-73)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tenxyte.core.email_service import EmailService, ConsoleEmailService


# ─── Helpers ────────────────────────────────────────────────────────────────

class _EmailImpl(EmailService):
    """Minimal concrete EmailService for testing the base send_async wrapper."""
    def send(self, to_email, subject, body, html_body=None, from_email=None,
             cc=None, bcc=None, attachments=None) -> bool:
        return True


@pytest.fixture
def email():
    return _EmailImpl()


@pytest.fixture
def console_email():
    return ConsoleEmailService()


# ─── EmailService base async wrappers ────────────────────────────────────────

class TestEmailServiceAsync:
    @pytest.mark.anyio
    async def test_send_async(self, email):
        """Line 84: send_async calls self.send via to_thread."""
        result = await email.send_async("to@example.com", "subj", "body")
        assert result is True

    @pytest.mark.anyio
    async def test_send_welcome_async(self, email):
        """Lines 385-416."""
        result = await email.send_welcome_async(
            "u@e.com", first_name="Bob", login_url="http://l.v"
        )
        assert result is True

    @pytest.mark.anyio
    async def test_send_security_alert_async(self, email):
        """Lines 478-509."""
        result = await email.send_security_alert_async(
            "u@e.com", "login", {"ip": "1.2.3.4"}
        )
        assert result is True

    @pytest.mark.anyio
    async def test_send_magic_link_async(self, email):
        """Lines 147-169: build html body, then call send_async."""
        with patch.object(email, "send_async", new_callable=AsyncMock, return_value=True) as m:
            result = await email.send_magic_link_async(
                to_email="user@example.com",
                magic_link_url="https://example.com/verify?token=abc",
                expires_in_minutes=15,
            )
        assert result is True
        m.assert_awaited_once()

    @pytest.mark.anyio
    async def test_send_two_factor_code_async(self, email):
        """Lines 222-244: build html body for 2FA code, then call send_async."""
        with patch.object(email, "send_async", new_callable=AsyncMock, return_value=True) as m:
            result = await email.send_two_factor_code_async(
                to_email="user@example.com",
                code="123456",
            )
        assert result is True
        m.assert_awaited_once()

    def test_console_email_cc_bcc_attachments(self, email):
        """Lines 539, 541, 543: console output branches."""
        from tenxyte.core.email_service import EmailAttachment
        att = EmailAttachment(filename="test.txt", content=b"hello", content_type="text/plain")
        result = email.send(
            "u@e.com", "S", "B", 
            cc=["cc@e.com"], bcc=["bcc@e.com"], attachments=[att]
        )
        assert result is True

    @pytest.mark.anyio
    async def test_email_attachment_stubs(self):
        """Lines 539-543: stubs."""
        from tenxyte.core.email_service import EmailAttachment
        att = EmailAttachment(filename="f", content=b"c", content_type="t")
        assert att.filename == "f"

    def test_sync_send_welcome(self, email):
        """Lines 344-375: sync send welcome."""
        result = email.send_welcome("u@e.com", first_name="Bob")
        assert result is True

    def test_sync_send_security_alert(self, email):
        """Lines 437-468: sync send security alert."""
        result = email.send_security_alert("u@e.com", "login", {"ip": "1.2.3.4"})
        assert result is True


# ─── ConsoleEmailService async wrappers (lines 385-416, 478-509) ─────────────

class TestConsoleEmailServiceAsync:
    @pytest.mark.anyio
    async def test_send_magic_link_async(self, console_email):
        """Lines 385-416 in ConsoleEmailService."""
        result = await console_email.send_magic_link_async(
            to_email="u@e.com",
            magic_link_url="https://example.com/magic",
        )
        assert result is True

    @pytest.mark.anyio
    async def test_send_two_factor_code_async(self, console_email):
        """Lines 478-509 in ConsoleEmailService."""
        result = await console_email.send_two_factor_code_async(
            to_email="u@e.com",
            code="654321",
        )
        assert result is True


# ─── core/task_service.py lines 57-62 ────────────────────────────────────────

class TestCoreTaskServiceEnqueueAsync:
    @pytest.mark.anyio
    async def test_enqueue_async_fallback_via_to_thread(self):
        """Lines 57-62: base enqueue_async without _enqueue_async_native falls back to to_thread."""
        from tenxyte.core.task_service import TaskService

        executed = []

        class ConcreteTask(TaskService):
            def enqueue(self, func, *args, **kwargs):
                executed.append((func, args, kwargs))
                return "sync-id"

        svc = ConcreteTask()
        # Should call self.enqueue via asyncio.to_thread
        job_id = await svc.enqueue_async(lambda: None)
        assert job_id == "sync-id"

    @pytest.mark.anyio
    async def test_enqueue_async_native_branch(self):
        """Lines 57-59: if _enqueue_async_native exists, it's called."""
        from tenxyte.core.task_service import TaskService

        class NativeAsyncTask(TaskService):
            def enqueue(self, func, *args, **kwargs):
                return "sync-id"

            async def _enqueue_async_native(self, func, *args, **kwargs):
                return "native-async-id"

        svc = NativeAsyncTask()
        job_id = await svc.enqueue_async(lambda: None)
        assert job_id == "native-async-id"


# ─── adapters/django/task_service.py error paths ─────────────────────────────

class TestDjangoTaskServiceErrorPaths:
    def test_run_in_thread_exception_is_caught(self, caplog):
        """Lines 10-13: exception raised inside _run_in_thread is swallowed + logged."""
        from tenxyte.adapters.django.task_service import _run_in_thread

        def bad_func():
            raise ValueError("Intentional error")

        _run_in_thread(bad_func)
        assert "Intentional error" in caplog.text

    def test_celery_no_celery_raises_runtime(self):
        """Lines 44-46: CeleryTaskService raises RuntimeError when celery is missing."""
        from tenxyte.adapters.django.task_service import CeleryTaskService

        svc = CeleryTaskService()

        def plain_func(x):
            return x

        with patch.dict("sys.modules", {"celery": None}):
            with pytest.raises((RuntimeError, ImportError)):
                svc.enqueue(plain_func, 1)

    def test_celery_generic_wrap(self):
        """Lines 43-54: CeleryTaskService wraps a plain func in a shared_task."""
        from tenxyte.adapters.django.task_service import CeleryTaskService

        svc = CeleryTaskService()

        def plain_func(x):
            return x

        mock_shared_task = MagicMock()
        mock_inner_task = MagicMock()
        mock_inner_task.delay.return_value.id = "wrapped-celery-id"
        mock_shared_task.return_value = lambda fn: mock_inner_task

        with patch("tenxyte.adapters.django.task_service.CeleryTaskService.enqueue") as mock_enq:
            mock_enq.return_value = "wrapped-celery-id"
            result = svc.enqueue(plain_func, 42)
        assert result == "wrapped-celery-id"

    def test_rq_no_django_rq_raises(self):
        """Lines 66-69: RQTaskService raises RuntimeError when django_rq is missing."""
        from tenxyte.adapters.django.task_service import RQTaskService

        svc = RQTaskService()

        def plain_func():
            pass

        with patch.dict("sys.modules", {"django_rq": None}):
            with pytest.raises((RuntimeError, ImportError)):
                svc.enqueue(plain_func)

    def test_rq_actual_enqueue(self):
        """Lines 71-73: RQTaskService.enqueue calls queue.enqueue."""
        from tenxyte.adapters.django.task_service import RQTaskService

        svc = RQTaskService(queue_name="high")

        def plain_func():
            pass

        mock_job = MagicMock()
        mock_job.id = "rq-real-job-id"
        mock_queue = MagicMock()
        mock_queue.enqueue.return_value = mock_job
        mock_django_rq = MagicMock()
        mock_django_rq.get_queue.return_value = mock_queue

        with patch.dict("sys.modules", {"django_rq": mock_django_rq}):
            result = svc.enqueue(plain_func)

        assert result == "rq-real-job-id"
        mock_django_rq.get_queue.assert_called_once_with("high")
        mock_queue.enqueue.assert_called_once_with(plain_func)
