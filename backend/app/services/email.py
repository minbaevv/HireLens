"""Сервис Email уведомлений (SMTP)."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
import re
from typing import Optional

from app.core.config import settings
from app.services.i18n_texts import (
    CANDIDATE_STATUS_EMAIL,
    EMAIL_GREETING,
    EMAIL_JOB_LABEL,
    normalize_language,
)

logger = logging.getLogger(__name__)


def _html_to_text(html: str) -> str:
    """Text-версия из HTML для multipart/alternative (важно для доставляемости)."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|h[1-6]|table)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Отправляет email через SMTP. Возвращает True при успехе."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP не настроен (SMTP_USER/SMTP_PASSWORD пустые)")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"HireLens <{settings.SMTP_FROM}>"
        msg["To"] = to
        msg["Reply-To"] = settings.SMTP_FROM
        msg["Message-ID"] = make_msgid(domain=settings.SMTP_FROM.split("@")[-1])
        msg["Date"] = formatdate(localtime=True)
        msg.attach(MIMEText(_html_to_text(html_body), "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to, msg.as_string())

        logger.info(f"Email отправлен: {to} | {subject}")
        return True
    except Exception as e:
        logger.error(f"Email ошибка ({to}): {e}")
        return False


def notify_candidate_received(candidate_name: str, candidate_email: str, job_title: str, hr_email: str) -> bool:
    """Уведомляет HR о новом кандидате."""
    subject = f"📩 Новый кандидат: {candidate_name}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #4F46E5;">📩 Новый кандидат</h2>
        <p>На вакансию <strong>{job_title}</strong> подал заявку новый кандидат:</p>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; color: #6B7280;">Имя:</td>
                <td style="padding: 8px;"><strong>{candidate_name}</strong></td></tr>
            <tr><td style="padding: 8px; color: #6B7280;">Email:</td>
                <td style="padding: 8px;">{candidate_email}</td></tr>
            <tr><td style="padding: 8px; color: #6B7280;">Вакансия:</td>
                <td style="padding: 8px;">{job_title}</td></tr>
        </table>
        <p style="margin-top: 20px;">
            <a href="{settings.FRONTEND_URL}/candidates"
               style="background: #4F46E5; color: white; padding: 10px 20px;
                      text-decoration: none; border-radius: 6px;">
                Открыть дашборд
            </a>
        </p>
        <p style="color: #9CA3AF; font-size: 12px; margin-top: 30px;">HireLens</p>
    </div>
    """
    return _send_email(hr_email, subject, html)


def notify_interview_result(candidate_name: str, candidate_email: str,
                            job_title: str, score: float,
                            recommendation: str, summary: str,
                            hr_email: str, candidate_id: int | None = None) -> bool:
    """Уведомляет HR о результате AI-интервью."""
    rec_map = {"hire": ("🎉 Нанять", "#10B981"),
               "maybe": ("🤔 Подумать", "#F59E0B"),
               "reject": ("❌ Отказать", "#EF4444")}
    rec_label, rec_color = rec_map.get(recommendation, ("❓ Неизвестно", "#6B7280"))

    profile_path = f"/candidates/{candidate_id}" if candidate_id else "/candidates"
    subject = f"✅ Интервью завершено: {candidate_name} — {score:.0f}/100"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #4F46E5;">✅ Результат AI-интервью</h2>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; color: #6B7280;">Кандидат:</td>
                <td style="padding: 8px;"><strong>{candidate_name}</strong> ({candidate_email})</td></tr>
            <tr><td style="padding: 8px; color: #6B7280;">Вакансия:</td>
                <td style="padding: 8px;">{job_title}</td></tr>
            <tr><td style="padding: 8px; color: #6B7280;">Оценка:</td>
                <td style="padding: 8px; font-size: 24px; font-weight: bold; color: #4F46E5;">{score:.0f}/100</td></tr>
            <tr><td style="padding: 8px; color: #6B7280;">Рекомендация:</td>
                <td style="padding: 8px; font-weight: bold; color: {rec_color};">{rec_label}</td></tr>
        </table>
        <div style="background: #F9FAFB; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="color: #374151; margin: 0;"><strong>Резюме:</strong> {summary}</p>
        </div>
        <p style="margin-top: 20px;">
            <a href="{settings.FRONTEND_URL}{profile_path}"
               style="background: #4F46E5; color: white; padding: 10px 20px;
                      text-decoration: none; border-radius: 6px;">
                Открыть профиль кандидата
            </a>
        </p>
        <p style="color: #9CA3AF; font-size: 12px; margin-top: 30px;">HireLens</p>
    </div>
    """
    return _send_email(hr_email, subject, html)


def notify_candidate_status(candidate_name: str, candidate_email: str,
                             job_title: str, new_status: str,
                             language: str = "ru") -> bool:
    """Уведомляет кандидата об изменении статуса (текст — на языке вакансии)."""
    texts = CANDIDATE_STATUS_EMAIL.get(new_status)
    if not texts:
        return False

    lang = normalize_language(language)
    localized = texts.get(lang, texts["ru"])
    title = localized["title"]
    color = localized["color"]
    message = localized["message"]
    greeting = EMAIL_GREETING.get(lang, EMAIL_GREETING["ru"])
    job_label = EMAIL_JOB_LABEL.get(lang, EMAIL_JOB_LABEL["ru"])

    subject = f"{title} — {job_title}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {color};">{title}</h2>
        <p>{greeting} <strong>{candidate_name}</strong>,</p>
        <p>{message}</p>
        <p style="color: #6B7280;">{job_label}: <strong>{job_title}</strong></p>
        <p style="color: #9CA3AF; font-size: 12px; margin-top: 30px;">HireLens</p>
    </div>
    """
    return _send_email(candidate_email, subject, html)



def notify_interview_invitation(candidate_name: str, candidate_email: str,
                                 job_title: str, date: str, time: str = "",
                                 location: str = "", note: str = "",
                                 company_name: str = "",
                                 language: str = "ru") -> bool:
    """Приглашает кандидата на очное (живое) собеседование.
    Дату/время/адрес вводит HR — они подставляются в письмо."""
    lang = normalize_language(language)
    T = {
        "ru": {
            "title": "Приглашение на собеседование",
            "intro": "Рады сообщить, что мы приглашаем вас на собеседование по вакансии",
            "when": "Дата",
            "time": "Время",
            "where": "Место",
            "outro": "Пожалуйста, подтвердите участие ответным письмом. Будем рады встрече!",
        },
        "ky": {
            "title": "Маегке чакыруу",
            "intro": "Сизди төмөнкү вакансия боюнча маегке чакырабыз",
            "when": "Күнү",
            "time": "Убакыт",
            "where": "Дарек",
            "outro": "Катышууңузду ырастап, жооп кат жазыңыз. Жолугушууну күтөбүз!",
        },
        "en": {
            "title": "Interview invitation",
            "intro": "We are glad to invite you to an interview for the position",
            "when": "Date",
            "time": "Time",
            "where": "Location",
            "outro": "Please confirm your attendance by replying to this email. We look forward to meeting you!",
        },
    }
    tx = T.get(lang, T["ru"])
    greeting = EMAIL_GREETING.get(lang, EMAIL_GREETING["ru"])

    time_row = (
        f'<tr><td style="padding: 8px; color: #6B7280;">{tx["time"]}:</td>'
        f'<td style="padding: 8px;"><strong>{time}</strong></td></tr>'
    ) if time else ""
    note_block = (
        f'<div style="background: #F9FAFB; padding: 16px; border-radius: 8px; '
        f'margin: 16px 0; color: #374151;">{note}</div>'
    ) if note else ""
    sig = f" — {company_name}" if company_name else ""

    subject = f"{tx['title']} — {job_title}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #4F46E5;">{tx['title']}</h2>
        <p>{greeting} <strong>{candidate_name}</strong>,</p>
        <p>{tx['intro']} <strong>{job_title}</strong>.</p>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; color: #6B7280;">{tx['when']}:</td>
                <td style="padding: 8px;"><strong>{date}</strong></td></tr>
            {time_row}
            <tr><td style="padding: 8px; color: #6B7280;">{tx['where']}:</td>
                <td style="padding: 8px;"><strong>{location}</strong></td></tr>
        </table>
        {note_block}
        <p>{tx['outro']}</p>
        <p style="color: #9CA3AF; font-size: 12px; margin-top: 30px;">HireLens{sig}</p>
    </div>
    """
    return _send_email(candidate_email, subject, html)


def send_verification_code(to: str, code: str) -> bool:
    """Отправляет 6-значный код подтверждения email при регистрации (SEC-11)."""
    subject = "Ваш код подтверждения регистрации в HireLens"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #374151;">
        <h2 style="color: #4F46E5;">Подтверждение адреса электронной почты</h2>
        <p>Здравствуйте!</p>
        <p>Вы начали регистрацию в <strong>HireLens</strong> — платформе автоматического AI-скрининга и интервьюирования кандидатов. Чтобы подтвердить, что этот адрес принадлежит вам, введите код подтверждения на странице регистрации:</p>
        <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #4F46E5; margin: 24px 0;">{code}</p>
        <p>Код действует <strong>15 минут</strong>. После подтверждения вы получите доступ к личному кабинету, где сможете создавать вакансии, приглашать кандидатов и получать результаты AI-интервью.</p>
        <p style="color: #6B7280;">Если вы не регистрировались в HireLens — просто проигнорируйте это письмо. Никаких действий не требуется, и ваш адрес не будет использован.</p>
        <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 24px 0;">
        <p style="color: #9CA3AF; font-size: 12px; line-height: 1.6;">
            HireLens — автоматизация найма с помощью искусственного интеллекта.<br>
            Это письмо отправлено автоматически в ответ на регистрацию, отвечать на него не нужно.<br>
            Сайт: https://gethirelens.tech
        </p>
    </div>
    """
    sent = _send_email(to, subject, html)
    if not sent and settings.ENVIRONMENT == "development":
        # DEV-удобство: SMTP не настроен — выводим код в лог, чтобы можно было завершить регистрацию.
        logger.warning(f"[DEV] Код подтверждения для {to}: {code} (SMTP не настроен)")
    return sent


def notify_registration_attempt(to: str) -> bool:
    """Уведомляет владельца существующего аккаунта о попытке повторной регистрации (SEC-11)."""
    subject = "Попытка регистрации — HireLens"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #4F46E5;">Кто-то пытался зарегистрироваться</h2>
        <p>На адрес <strong>{to}</strong> уже есть аккаунт HireLens, и кто-то попытался зарегистрироваться повторно.</p>
        <p>Если это были вы — просто войдите. Если нет — проигнорируйте письмо, ваш аккаунт в безопасности.</p>
        <p style="color: #9CA3AF; font-size: 12px; margin-top: 30px;">HireLens</p>
    </div>
    """
    return _send_email(to, subject, html)
