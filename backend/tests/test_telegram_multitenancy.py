"""Тесты мультитенантности Telegram HR-уведомлений (per-company)."""
from unittest.mock import patch

from app.models.models import Company
from app.services import telegram as tg
from app.services.telegram_bot import _handle_start
from tests.conftest import TestingSessionLocal


class _Company:
    def __init__(self, chat_id=None):
        self.telegram_chat_id = chat_id


def test_notify_goes_to_company_chat():
    company_a = _Company(chat_id="1111")
    with patch.object(tg, "_send") as mock_send:
        tg.notify_new_candidate("Иван", "ivan@test.com", "Backend", company=company_a)
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "1111"


def test_notify_not_cross_company():
    company_b = _Company(chat_id="2222")
    with patch.object(tg, "_send") as mock_send:
        tg.notify_new_candidate("Петр", "petr@test.com", "Backend", company=company_b)
        assert mock_send.call_args[0][0] == "2222"


def test_notify_no_chat_skips():
    company = _Company(chat_id=None)
    with patch.object(tg, "_send") as mock_send:
        tg.notify_new_candidate("Аноним", "anon@test.com", "Backend", company=company)
        mock_send.assert_not_called()


def test_notify_interview_complete_uses_company():
    company = _Company(chat_id="3333")
    with patch.object(tg, "_send") as mock_send:
        tg.notify_interview_complete(
            candidate_name="Анна", job_title="QA", score=80.0,
            recommendation="hire", summary="ok", frontend_url="http://x",
            candidate_id=5, company=company,
        )
        mock_send.assert_called_once()
        assert mock_send.call_args[0][0] == "3333"


def _seed_company(link_code, name="LinkCo"):
    _db = TestingSessionLocal()
    c = Company(email=link_code + "@t.com", hashed_password="x", name=name, telegram_link_code=link_code)
    _db.add(c)
    _db.commit()
    cid = c.id
    _db.close()
    return cid


def test_bot_start_links_company_chat():
    cid = _seed_company("LINKCODE1")
    sent = []
    _db = TestingSessionLocal()
    _data = {"language": "ru"}
    session = {"state": "idle", "data": _data}
    with patch("app.services.telegram_bot.send_message", lambda chat_id, text, **kw: sent.append((chat_id, text))):
        _handle_start(chat_id=999, token="LINKCODE1", session=session, db=_db)
    c = _db.query(Company).filter(Company.id == cid).first()
    assert c.telegram_chat_id == "999"
    assert c.telegram_link_code is None
    _db.close()
    assert len(sent) == 1


def test_bot_start_invalid_code_does_not_link():
    cid = _seed_company("LINKCODE2")
    sent = []
    _db = TestingSessionLocal()
    _data = {"language": "ru"}
    session = {"state": "idle", "data": _data}
    with patch("app.services.telegram_bot.send_message", lambda chat_id, text, **kw: sent.append((chat_id, text))):
        _handle_start(chat_id=777, token="WRONGCODE", session=session, db=_db)
    c = _db.query(Company).filter(Company.id == cid).first()
    assert c.telegram_chat_id is None
    assert c.telegram_link_code == "LINKCODE2"
    _db.close()


def test_bot_start_used_code_not_reused():
    cid = _seed_company("LINKCODE3")
    _db = TestingSessionLocal()
    _data = {"language": "ru"}
    session = {"state": "idle", "data": _data}
    with patch("app.services.telegram_bot.send_message", lambda chat_id, text, **kw: None):
        _handle_start(chat_id=100, token="LINKCODE3", session=session, db=_db)
        _handle_start(chat_id=200, token="LINKCODE3", session=session, db=_db)
    c = _db.query(Company).filter(Company.id == cid).first()
    assert c.telegram_chat_id == "100"
    _db.close()
