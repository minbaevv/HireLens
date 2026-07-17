"""B5-lite — тесты enforcement лимитов тарифов.

Проверяем, что лимиты из landing.py реально применяются:
    Free:    1 активная вакансия,   5 кандидатов/месяц
    Starter: 3 активные вакансии
"""
from app.models.models import Company


def _company(db, email="jobs@test.com"):
    return db.query(Company).filter(Company.email == email).first()


def _create_job(client, headers, title="T"):
    return client.post(
        "/jobs",
        headers=headers,
        json={"title": title, "description": "D", "requirements": "R", "language": "ru"},
    )


def _reset_free(db):
    c = _company(db)
    c.plan = "free"
    c.plan_expires_at = None
    db.commit()


def test_free_plan_allows_only_one_active_job(client, auth_headers, db):
    r1 = _create_job(client, auth_headers, "Job 1")
    assert r1.status_code == 201, r1.text
    r2 = _create_job(client, auth_headers, "Job 2")
    assert r2.status_code == 402, r2.text


def test_starter_plan_allows_three_jobs(client, auth_headers, db):
    c = _company(db)
    c.plan = "starter"
    c.plan_expires_at = None  # бессрочный доступ
    db.commit()
    assert _create_job(client, auth_headers, "J1").status_code == 201
    assert _create_job(client, auth_headers, "J2").status_code == 201
    assert _create_job(client, auth_headers, "J3").status_code == 201
    assert _create_job(client, auth_headers, "J4").status_code == 402
    _reset_free(db)


def test_deactivating_job_frees_a_slot(client, auth_headers, db):
    r1 = _create_job(client, auth_headers, "Job 1")
    assert r1.status_code == 201, r1.text
    job_id = r1.json()["id"]
    # вторая — блокируется
    assert _create_job(client, auth_headers, "Job 2").status_code == 402
    # деактивируем первую — слот освобождается
    upd = client.patch(f"/jobs/{job_id}", headers=auth_headers, json={"is_active": False})
    assert upd.status_code == 200, upd.text
    assert _create_job(client, auth_headers, "Job 3").status_code == 201


def test_free_plan_caps_five_candidates_per_month(client, auth_headers, db):
    r = _create_job(client, auth_headers, "Vac")
    assert r.status_code == 201, r.text
    token = r.json()["apply_token"]
    for i in range(5):
        resp = client.post(
            f"/apply/{token}",
            data={"name": f"Cand {i}", "email": f"c{i}@example.com"},
        )
        assert resp.status_code == 201, resp.text
    # 6-й кандидат — заблокирован (лимит free = 5/мес)
    resp = client.post(
        f"/apply/{token}",
        data={"name": "Cand 6", "email": "c6@example.com"},
    )
    assert resp.status_code == 403, resp.text
