"""Тесты ручной загрузки чеков об оплате и их проверки суперадмином."""
from app.core.config import settings


def _png_bytes():
    return b"\x89PNG\r\n\x1a\n" + b"0" * 64


def test_upload_and_list_receipt(client, auth_headers):
    resp = client.post(
        "/billing/receipt",
        data={"plan": "starter"},
        files={"file": ("check.png", _png_bytes(), "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["plan_requested"] == "starter"

    mine = client.get("/billing/receipts", headers=auth_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1


def test_upload_rejects_bad_extension(client, auth_headers):
    resp = client.post(
        "/billing/receipt",
        data={"plan": "pro"},
        files={"file": ("bad.exe", b"MZ junk", "application/octet-stream")},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_upload_rejects_unknown_plan(client, auth_headers):
    resp = client.post(
        "/billing/receipt",
        data={"plan": "enterprise"},
        files={"file": ("check.png", _png_bytes(), "image/png")},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_admin_receipts_requires_superadmin(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", "")
    resp = client.get("/admin/receipts", headers=auth_headers)
    assert resp.status_code == 403


def test_admin_review_and_download_receipt(client, auth_headers, monkeypatch):
    up = client.post(
        "/billing/receipt",
        data={"plan": "starter"},
        files={"file": ("check.png", _png_bytes(), "image/png")},
        headers=auth_headers,
    )
    rid = up.json()["id"]

    monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", "jobs@test.com")
    listed = client.get("/admin/receipts", headers=auth_headers)
    assert listed.status_code == 200
    assert any(r["id"] == rid for r in listed.json())

    review = client.post(
        f"/admin/receipts/{rid}/review",
        json={"status": "approved", "note": "ok"},
        headers=auth_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "approved"

    downloaded = client.get(f"/admin/receipts/{rid}/file", headers=auth_headers)
    assert downloaded.status_code == 200
