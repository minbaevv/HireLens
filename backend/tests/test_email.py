"""Тесты Email сервиса."""
from unittest.mock import MagicMock, patch


def test_send_email_no_smtp_config():
    """Без SMTP настроек — возвращает False."""
    from app.services.email import _send_email
    from app.core.config import settings
    original = settings.SMTP_USER
    settings.SMTP_USER = ""
    try:
        assert _send_email("t@t.com", "Subj", "<p>Body</p>") is False
    finally:
        settings.SMTP_USER = original


@patch("app.services.email.smtplib.SMTP")
def test_send_email_success(mock_smtp):
    """Успешная отправка."""
    from app.services.email import _send_email
    from app.core.config import settings
    settings.SMTP_USER = "u@g.com"
    settings.SMTP_PASSWORD = "pass"
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    assert _send_email("hr@c.com", "Test", "<p>Hi</p>") is True
    mock_server.sendmail.assert_called_once()


@patch("app.services.email.smtplib.SMTP")
def test_send_email_smtp_error(mock_smtp):
    """SMTP ошибка — возвращает False."""
    from app.services.email import _send_email
    from app.core.config import settings
    settings.SMTP_USER = "u@g.com"
    settings.SMTP_PASSWORD = "pass"
    mock_smtp.side_effect = Exception("Нет связи")
    assert _send_email("hr@c.com", "Test", "<p>Hi</p>") is False


@patch("app.services.email._send_email", return_value=True)
def test_notify_candidate_received(mock_send):
    from app.services.email import notify_candidate_received
    result = notify_candidate_received("Алекс", "a@t.com", "Python Dev", "hr@c.com")
    assert result is True
    assert "Алекс" in mock_send.call_args[0][2]


@patch("app.services.email._send_email", return_value=True)
def test_notify_interview_result(mock_send):
    from app.services.email import notify_interview_result
    result = notify_interview_result("Борис", "b@t.com", "QA", 85.0, "hire", "Отлично", "hr@c.com")
    assert result is True
    assert "85" in mock_send.call_args[0][1]


@patch("app.services.email._send_email", return_value=True)
def test_notify_candidate_hired(mock_send):
    from app.services.email import notify_candidate_status
    assert notify_candidate_status("Анна", "a@t.com", "Designer", "hired") is True


@patch("app.services.email._send_email", return_value=True)
def test_notify_candidate_rejected(mock_send):
    from app.services.email import notify_candidate_status
    assert notify_candidate_status("Иван", "i@t.com", "Manager", "rejected") is True


def test_notify_candidate_unknown_status():
    from app.services.email import notify_candidate_status
    assert notify_candidate_status("Тест", "t@t.com", "Dev", "unknown") is False
