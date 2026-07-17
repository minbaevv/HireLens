import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.core.db as db_module
from app.core.db import Base, get_db
from app.core.limiter import limiter
from main import app

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Фоновые задачи (скоринг) открывают собственную сессию через app.core.db.SessionLocal.
# Без этой подмены они бы шли в боевой postgres из .env — в тестах он недоступен,
# скоринг молча падал бы и поля confidence/bias_flags оставались None.
db_module.SessionLocal = TestingSessionLocal

# Отключаем rate limiting в тестах
limiter.enabled = False


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _stub_anticheat_llm():
    """Roadmap 4.1: anti-cheat теперь идёт через отдельный seam _anticheat_llm
    и выполняется ПАРАЛЛЕЛЬНО со скорингом. В тестах глушим его, чтобы:
      1) не ходить в сеть с плейсхолдер-ключом из .env;
      2) параллельный скоринг не конкурировал за общий mock _call_groq.
    Timing-эвристика anti-cheat при этом продолжает работать (она не LLM).

    Тесты самого anti-cheat (test_anticheat.py) передают свой llm_fn — на них это не влияет.
    """
    from unittest import mock
    with mock.patch(
        "app.ai.interview_service._anticheat_llm",
        side_effect=RuntimeError("anti-cheat LLM disabled in tests"),
    ):
        yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    """Фикстура для прямого доступа к БД в тестах."""
    _db = TestingSessionLocal()
    try:
        yield _db
    finally:
        _db.close()


def mark_verified(email: str) -> None:
    """Тест-хелпер: помечает компанию подтверждённой (email-верификация включена)."""
    from app.models.models import Company
    _db = TestingSessionLocal()
    try:
        c = _db.query(Company).filter(Company.email == email).first()
        if c and not c.is_verified:
            c.is_verified = True
            _db.commit()
    finally:
        _db.close()


def grant_plan(email: str, plan: str = "starter") -> None:
    """Тест-хелпер: выдаёт компании тариф с бессрочным доступом.

    Нужен тестам, которые создают >1 активной вакансии: на free-плане лимит
    1 вакансия, поэтому вторая /jobs отдаёт 402. mark_verified ставит только
    is_verified и триал не выдаёт (он вешается на эндпоинт /auth/verify).
    """
    from app.models.models import Company
    _db = TestingSessionLocal()
    try:
        c = _db.query(Company).filter(Company.email == email).first()
        if c:
            c.plan = plan
            c.plan_expires_at = None
            _db.commit()
    finally:
        _db.close()


@pytest.fixture
def auth_headers(client):
    client.post(
        "/auth/register",
        json={"email": "jobs@test.com", "password": "test1234", "company_name": "Jobs LLC"},
    )
    mark_verified("jobs@test.com")
    response = client.post(
        "/auth/login",
        data={"username": "jobs@test.com", "password": "test1234"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
