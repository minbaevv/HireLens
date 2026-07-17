"""Тесты локализации email/Telegram уведомлений (A6.3)."""
from unittest.mock import patch


def test_i18n_texts_fallback_to_russian():
    from app.services.i18n_texts import t
    assert t("cancelled", "fr") == t("cancelled", "ru")


def test_i18n_texts_kyrgyz():
    from app.services.i18n_texts import t
    text = t("ask_name", "ky", job_title="Python Dev")
    assert "Python Dev" in text
    assert "Кош келиңиз" in text


def test_is_skip_word_universal_fallback():
    from app.services.i18n_texts import is_skip_word
    assert is_skip_word("skip", "ky") is True
    assert is_skip_word("Пропустить", "ru") is True
    assert is_skip_word("something else", "en") is False


@patch("app.services.email._send_email", return_value=True)
def test_notify_candidate_status_english(mock_send):
    from app.services.email import notify_candidate_status
    assert notify_candidate_status("John", "j@t.com", "Backend Dev", "hired", language="en") is True
    html = mock_send.call_args[0][2]
    assert "Congratulations" in html


@patch("app.services.email._send_email", return_value=True)
def test_notify_candidate_status_kyrgyz(mock_send):
    from app.services.email import notify_candidate_status
    assert notify_candidate_status("Айгуль", "a@t.com", "QA", "rejected", language="ky") is True
    html = mock_send.call_args[0][2]
    assert "Урматтуу" in html


@patch("app.services.email._send_email", return_value=True)
def test_notify_candidate_status_unknown_language_falls_back_to_russian(mock_send):
    from app.services.email import notify_candidate_status
    assert notify_candidate_status("Тест", "t@t.com", "Dev", "hired", language="fr") is True
    html = mock_send.call_args[0][2]
    assert "Поздравляем" in html
