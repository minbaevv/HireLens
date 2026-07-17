"""Сервис экспорта: CSV список кандидатов + PDF отчёт кандидата."""
import csv
import io
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Optional

logger = logging.getLogger(__name__)

from app.core.config import settings as _settings


def _local_dt(dt):
    """UTC-наивный/aware datetime → локальное время SCHEDULING_TIMEZONE (Бишкек)."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        return dt.astimezone(ZoneInfo(_settings.SCHEDULING_TIMEZONE))
    except Exception:
        return dt


def generate_candidates_csv(candidates: list) -> bytes:
    """Генерирует CSV со списком кандидатов."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Заголовок
    writer.writerow([
        "ID", "Имя", "Email", "Статус",
        "Оценка", "Рекомендация", "Вакансия ID", "Дата подачи",
    ])

    for c in candidates:
        writer.writerow([
            c.id,
            c.name,
            c.email,
            c.status.value,
            f"{c.score:.1f}" if c.score is not None else "",
            c.recommendation or "",
            c.job_id,
            _local_dt(c.created_at).strftime("%Y-%m-%d %H:%M") if c.created_at else "",
        ])

    return output.getvalue().encode("utf-8-sig")  # utf-8-sig для Excel


def _register_cyrillic_font():
    """Регистрирует шрифт с поддержкой кириллицы."""
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Пути к DejaVuSans на разных ОС
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",       # Linux (Debian/Ubuntu)
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",                 # Linux (Alpine)
        "/usr/share/fonts/TTF/DejaVuSans.ttf",                    # Arch Linux
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",   # macOS
        "C:/Windows/Fonts/arial.ttf",                             # Windows
    ]

    for path in font_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("CyrillicFont", path))
            pdfmetrics.registerFont(TTFont("CyrillicFont-Bold", path))
            return "CyrillicFont"

    # Fallback: скачиваем DejaVuSans если нет локально
    try:
        import urllib.request
        import tempfile
        url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
        tmp = tempfile.mktemp(suffix=".ttf")
        urllib.request.urlretrieve(url, tmp)
        pdfmetrics.registerFont(TTFont("CyrillicFont", tmp))
        pdfmetrics.registerFont(TTFont("CyrillicFont-Bold", tmp))
        return "CyrillicFont"
    except Exception:
        pass

    return None  # шрифт не найден, используем Helvetica (без кириллицы)


def generate_candidate_pdf(candidate, job_title: str, messages: list = None) -> bytes:
    """Генерирует PDF отчёт по кандидату."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError:
        raise RuntimeError("Библиотека reportlab не установлена. Запусти: pip install reportlab")

    # Регистрируем кириллический шрифт
    font_name = _register_cyrillic_font() or "Helvetica"
    font_bold = font_name if font_name != "Helvetica" else "Helvetica-Bold"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    # Стили с поддержкой кириллицы
    title_style = ParagraphStyle(
        "CyrTitle", parent=styles["Title"],
        fontSize=18, spaceAfter=12, textColor=colors.HexColor("#4F46E5"),
        fontName=font_name,
    )
    heading_style = ParagraphStyle(
        "CyrHeading", parent=styles["Heading2"],
        fontSize=13, spaceBefore=16, spaceAfter=6, textColor=colors.HexColor("#1F2937"),
        fontName=font_bold,
    )
    normal_style = ParagraphStyle(
        "CyrNormal", parent=styles["Normal"],
        fontSize=10, spaceAfter=4, leading=14,
        fontName=font_name,
    )
    label_style = ParagraphStyle(
        "CyrLabel", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#6B7280"),
        fontName=font_name,
    )

    # Цвет рекомендации
    rec_colors = {
        "hire": colors.HexColor("#10B981"),
        "maybe": colors.HexColor("#F59E0B"),
        "reject": colors.HexColor("#EF4444"),
    }
    rec_labels = {"hire": "HIRE", "maybe": "MAYBE", "reject": "REJECT"}
    rec = candidate.recommendation or "maybe"
    rec_color = rec_colors.get(rec, colors.gray)
    rec_label = rec_labels.get(rec, rec.upper())

    story = []

    # Заголовок
    story.append(Paragraph("HireLens — Отчёт кандидата", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB")))
    story.append(Spacer(1, 0.4 * cm))

    # Основная инфо
    info_data = [
        ["Кандидат:", candidate.name],
        ["Email:", candidate.email],
        ["Вакансия:", job_title],
        ["Статус:", candidate.status.value.upper()],
        ["Дата:", _local_dt(candidate.created_at).strftime("%d.%m.%Y") if candidate.created_at else "—"],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, 13 * cm])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6B7280")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTNAME", (1, 0), (1, -1), font_bold),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4 * cm))

    # Скоринг + рекомендация
    if candidate.score is not None:
        story.append(Paragraph("📊 Результат AI-интервью", heading_style))
        score_data = [
            ["Оценка:", f"{candidate.score:.0f} / 100"],
            ["Рекомендация:", rec_label],
        ]
        score_table = Table(score_data, colWidths=[4 * cm, 13 * cm])
        score_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6B7280")),
            ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#4F46E5")),
            ("TEXTCOLOR", (1, 1), (1, 1), rec_color),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTNAME", (1, 0), (1, -1), font_bold),
            ("FONTSIZE", (1, 0), (1, 0), 20),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(score_table)

    # Резюме
    if candidate.summary:
        story.append(Paragraph("📝 Резюме AI", heading_style))
        story.append(Paragraph(candidate.summary, normal_style))

    # Резюме кандидата
    if candidate.resume_text:
        story.append(Paragraph("📄 Резюме кандидата", heading_style))
        # Ограничиваем длину резюме в PDF
        resume_text = candidate.resume_text[:2000]
        if len(candidate.resume_text) > 2000:
            resume_text += "..."
        story.append(Paragraph(resume_text.replace("\n", "<br/>"), normal_style))

    # Транскрипт интервью
    if messages:
        story.append(Paragraph("🎤 Транскрипт интервью", heading_style))
        for msg in messages:
            role = "AI" if msg.role.value == "ai" else "Кандидат"
            color = "#4F46E5" if msg.role.value == "ai" else "#111827"
            story.append(Paragraph(
                f'<font color="{color}"><b>{role}:</b></font> {msg.content[:500]}',
                normal_style,
            ))
            story.append(Spacer(1, 0.2 * cm))

    # Футер
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB")))
    story.append(Paragraph(
        f"Сгенерировано: {_local_dt(datetime.now(timezone.utc)).strftime('%d.%m.%Y %H:%M')} | HireLens",
        ParagraphStyle("CyrFooter", parent=styles["Normal"], fontSize=8,
                       textColor=colors.HexColor("#9CA3AF"), spaceBefore=6,
                       fontName=font_name),
    ))

    doc.build(story)
    return buffer.getvalue()
