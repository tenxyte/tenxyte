"""
Tests for core email_service - targeting 100% coverage of
src/tenxyte/core/email_service.py

Uses ConsoleEmailService as the concrete impl to test
the abstract EmailService's template methods.
"""
import pytest

from tenxyte.core.email_service import (
    ConsoleEmailService,
    EmailAttachment,
    EmailTemplate,
)


@pytest.fixture
def svc():
    return ConsoleEmailService(prefix="[TEST]")


# ═══════════════════════════════════════════════════════════════════════════════
# ConsoleEmailService.send  (lines 309, 323-339)
# ═══════════════════════════════════════════════════════════════════════════════

def test_send_plain(svc, capsys):
    """Lines 323-339: basic send prints to stdout."""
    assert svc.send("to@x.com", "Subject", "Body") is True
    out = capsys.readouterr().out
    assert "[TEST] TO: to@x.com" in out
    assert "[TEST] SUBJECT: Subject" in out


def test_send_with_cc_bcc(svc, capsys):
    """Lines 327-330: cc and bcc printed."""
    svc.send("to@x.com", "S", "B", cc=["cc@x.com"], bcc=["bcc@x.com"])
    out = capsys.readouterr().out
    assert "CC: cc@x.com" in out
    assert "BCC: bcc@x.com" in out


def test_send_with_attachments(svc, capsys):
    """Lines 331-332: attachments printed."""
    att = EmailAttachment(filename="f.txt", content=b"data", content_type="text/plain")
    svc.send("to@x.com", "S", "B", attachments=[att])
    out = capsys.readouterr().out
    assert "ATTACHMENTS:" in out
    assert "f.txt" in out


def test_send_with_html(svc, capsys):
    """Lines 335-337: HTML version printed."""
    svc.send("to@x.com", "S", "B", html_body="<b>Hi</b>")
    out = capsys.readouterr().out
    assert "HTML VERSION:" in out
    assert "<b>Hi</b>" in out


def test_send_no_html(svc, capsys):
    """Line 335: no html_body → no HTML section."""
    svc.send("to@x.com", "S", "B")
    out = capsys.readouterr().out
    assert "HTML VERSION" not in out


# ═══════════════════════════════════════════════════════════════════════════════
# EmailService template methods  (lines 88-298)
# ═══════════════════════════════════════════════════════════════════════════════

def test_send_magic_link(svc):
    """Lines 88-110."""
    assert svc.send_magic_link("to@x.com", "https://example.com/magic") is True


def test_send_two_factor_code(svc):
    """Lines 131-153."""
    assert svc.send_two_factor_code("to@x.com", "123456") is True


def test_send_welcome_with_name_and_url(svc):
    """Lines 219-246: first_name + login_url provided."""
    assert svc.send_welcome("to@x.com", first_name="Alice", login_url="https://my.app/login") is True


def test_send_welcome_no_name_no_url(svc):
    """Lines 219, 222: first_name=None, login_url=None."""
    assert svc.send_welcome("to@x.com") is True


def test_send_security_alert(svc):
    """Lines 267-298."""
    assert svc.send_security_alert(
        "to@x.com", "new_login",
        {"ip": "1.2.3.4", "browser": "Chrome"}
    ) is True


# ═══════════════════════════════════════════════════════════════════════════════
# EmailTemplate enum
# ═══════════════════════════════════════════════════════════════════════════════

def test_email_template_values():
    assert EmailTemplate.MAGIC_LINK == "magic_link"
    assert EmailTemplate.SECURITY_ALERT == "security_alert"
