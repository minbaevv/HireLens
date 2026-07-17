"""SEO: robots.txt и sitemap.xml для публичного лендинга (Roadmap D3).

Сайтмап включает hreflang-альтернативы для RU/KY/EN. Базовый URL — FRONTEND_URL.
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response

from app.core.config import settings

router = APIRouter(tags=["seo"])

_LANGS = ("ru", "ky", "en")
_PUBLIC_PATHS = ("/landing", "/login", "/register")


def _base_url() -> str:
    return (settings.FRONTEND_URL or "http://localhost:3000").rstrip("/")


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots_txt() -> str:
    base = _base_url()
    return (
        "User-agent: *\n"
        "Allow: /landing\n"
        "Allow: /login\n"
        "Allow: /register\n"
        "Disallow: /api/\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml() -> Response:
    base = _base_url()
    urls = []
    for path in _PUBLIC_PATHS:
        loc = f"{base}{path}"
        alternates = "".join(
            f'<xhtml:link rel="alternate" hreflang="{lang}" href="{loc}?lang={lang}"/>'
            for lang in _LANGS
        )
        urls.append(
            f"<url><loc>{loc}</loc>{alternates}"
            "<changefreq>weekly</changefreq><priority>0.8</priority></url>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        + "".join(urls)
        + "</urlset>"
    )
    return Response(content=body, media_type="application/xml")
