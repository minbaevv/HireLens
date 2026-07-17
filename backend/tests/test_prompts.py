"""Тесты Prompt Versioning (Roadmap 6.2)."""
from app.ai import prompt_service

# Минимальный валидный контент для scoring_system (все обязательные placeholders).
VALID_SCORING = (
    "TEST SCORING {data_handling_rule} {job_title} {job_requirements} "
    "{transcript} {interview_language} {schema}"
)


# --- Сервис-уровень (резолвер + валидация) ---

def test_resolve_fallback_to_default(db):
    """Без записей в БД резолвер возвращает code-default."""
    result = prompt_service.resolve_prompt(db, 999, "scoring_system")
    assert result == prompt_service.default_content("scoring_system")


def test_resolve_active_version(db):
    """После создания+активации резолвер возвращает кастомный текст."""
    prompt_service.create_version(db, 777, "scoring_system", VALID_SCORING, activate=True)
    result = prompt_service.resolve_prompt(db, 777, "scoring_system")
    assert result == VALID_SCORING


def test_validate_missing_placeholder():
    ok, _ = prompt_service.validate_content("scoring_system", "нет подстановок")
    assert ok is False


def test_validate_unknown_placeholder():
    bad = VALID_SCORING + " {unexpected}"
    ok, _ = prompt_service.validate_content("scoring_system", bad)
    assert ok is False


def test_validate_ok():
    ok, msg = prompt_service.validate_content("scoring_system", VALID_SCORING)
    assert ok is True


def test_create_version_rejects_invalid(db):
    import pytest
    with pytest.raises(ValueError):
        prompt_service.create_version(db, 555, "scoring_system", "плохой")


def test_ab_weighted_selection(db):
    """При нескольких активных версиях резолвер выбирает только активные."""
    v1 = prompt_service.create_version(db, 111, "scoring_system", VALID_SCORING, name="A")
    v2 = prompt_service.create_version(db, 111, "scoring_system", VALID_SCORING + " ", name="B")
    prompt_service.set_ab_weights(db, 111, "scoring_system", {v1.id: 1, v2.id: 3})
    versions = {pt.id: pt for pt in prompt_service.list_versions(db, 111, "scoring_system")}
    assert versions[v1.id].is_active and versions[v2.id].is_active
    assert versions[v2.id].ab_weight == 3
    # выбор всегда из активных
    chosen = {prompt_service.resolve_prompt(db, 111, "scoring_system") for _ in range(20)}
    assert chosen <= {VALID_SCORING, VALID_SCORING + " "}


# --- API-уровень ---

def test_list_keys_api(client, auth_headers):
    r = client.get("/prompts/keys", headers=auth_headers)
    assert r.status_code == 200
    keys = {item["key"] for item in r.json()}
    assert {"interview_system", "scoring_system", "prescreen"} <= keys
    for item in r.json():
        assert item["default_content"]


def test_create_activate_api(client, auth_headers):
    r = client.post(
        "/prompts/scoring_system",
        headers=auth_headers,
        json={"content": VALID_SCORING, "name": "v1", "activate": True},
    )
    assert r.status_code == 201, r.text
    assert r.json()["is_active"] is True
    lst = client.get("/prompts/scoring_system", headers=auth_headers)
    assert lst.status_code == 200
    assert any(v["is_active"] for v in lst.json())


def test_create_invalid_api(client, auth_headers):
    r = client.post(
        "/prompts/scoring_system",
        headers=auth_headers,
        json={"content": "нет подстановок", "activate": False},
    )
    assert r.status_code == 400


def test_unknown_key_api(client, auth_headers):
    r = client.get("/prompts/does_not_exist", headers=auth_headers)
    assert r.status_code == 404


def test_requires_auth(client):
    r = client.get("/prompts/keys")
    assert r.status_code == 401
