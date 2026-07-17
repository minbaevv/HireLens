"""Тесты локализованного лендинга и SEO (Roadmap D3)."""


def test_landing_default_ru(client):
    r = client.get("/landing")
    assert r.status_code == 200
    data = r.json()
    assert data["lang"] == "ru"
    assert data["tagline"]
    assert len(data["features"]) == 6
    assert len(data["pricing"]) == 3
    assert len(data["cases"]) >= 1


def test_landing_english(client):
    data = client.get("/landing?lang=en").json()
    assert data["lang"] == "en"
    assert "faster" in data["tagline"].lower()


def test_landing_kyrgyz(client):
    data = client.get("/landing?lang=ky").json()
    assert data["lang"] == "ky"
    assert data["features"]


def test_landing_unknown_lang_falls_back_to_ru(client):
    data = client.get("/landing?lang=zz").json()
    assert data["lang"] == "ru"


def test_robots_and_sitemap(client):
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "sitemap" in robots.text.lower()
    sm = client.get("/sitemap.xml")
    assert sm.status_code == 200
    assert "<urlset" in sm.text
    assert "hreflang" in sm.text
