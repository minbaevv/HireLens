"""Обратная совместимость: модели разнесены по доменным модулям (A5).

Новый код должен импортировать из app.models:
    from app.models import Company, Job, Candidate, Interview, Message
Этот файл оставлен, чтобы не ломать существующие импорты app.models.models.
"""

from app.models.audit_log import AuditLog
from app.models.api_key import ApiKey
from app.models.coding import CodingChallenge, CodingSubmission
from app.models.candidate import Candidate, CandidateStatus
from app.models.candidate_comment import CandidateComment
from app.models.company import Company
from app.models.payment_receipt import PaymentReceipt
from app.models.interview import Interview, InterviewStatus, Message, MessageRole
from app.models.job import Job
from app.models.team_member import TeamMember, TeamRole
from app.models.webhook import Webhook, WebhookDelivery

__all__ = [
    "AuditLog",
    "ApiKey",
    "CodingChallenge",
    "CodingSubmission",
    "Candidate",
    "CandidateStatus",
    "Company",
    "PaymentReceipt",
    "Interview",
    "InterviewStatus",
    "Job",
    "Message",
    "MessageRole",
    "TeamMember",
    "TeamRole",
    "Webhook",
    "WebhookDelivery",
]
