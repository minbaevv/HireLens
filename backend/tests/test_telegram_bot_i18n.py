"""Тесты локализации Telegram-бота для кандидатов (A6.3)."""
from unittest.mock import MagicMock, patch


def _mock_job(language="ky", title="Backend Developer", apply_token="tok123", job_id=1):
    job = MagicMock()
    job.id = job_id
    job.title = title
    job.language = language
    job.apply_token = apply_token
    job.is_active = True
    return job


@patch("app.services.telegram_bot.send_message")
def test_start_uses_job_language_for_greeting(mock_send):
    from app.services import telegram_bot

    db = MagicMock()
    job = _mock_job(language="ky")
    db.query.return_value.filter.return_value.first.return_value = job

    telegram_bot._reset_session(555)
    telegram_bot.handle_update(
        {"message": {"chat": {"id": 555}, "text": "/start tok123"}}, db
    )

    sent_text = mock_send.call_args[0][1]
    assert "Кош келиңиз" in sent_text
    assert telegram_bot._sessions[555]["data"]["language"] == "ky"


@patch("app.services.telegram_bot.send_message")
def test_cancel_uses_session_language(mock_send):
    from app.services import telegram_bot

    telegram_bot._sessions[777] = {
        "state": telegram_bot.STATE_WAIT_NAME,
        "data": {"language": "en"},
    }
    telegram_bot.handle_update({"message": {"chat": {"id": 777}, "text": "/cancel"}}, MagicMock())

    sent_text = mock_send.call_args[0][1]
    assert sent_text == "❌ Cancelled. Type /start to begin again."


@patch("app.services.telegram_bot.send_message")
def test_ask_resume_skip_word_in_kyrgyz(mock_send):
    from app.services import telegram_bot

    telegram_bot._sessions[888] = {
        "state": telegram_bot.STATE_WAIT_EMAIL,
        "data": {"language": "ky", "job_id": 1, "job_title": "QA", "name": "Азамат"},
    }
    telegram_bot.handle_update(
        {"message": {"chat": {"id": 888}, "text": "azamat@example.com"}}, MagicMock()
    )

    sent_text = mock_send.call_args[0][1]
    assert "резюме" in sent_text.lower() or "резюмеңизди" in sent_text
