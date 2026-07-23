import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from app.models.models import CandidateStatus


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    company_name: str = Field(min_length=1)


class RegisterResponse(BaseModel):
    id: int
    email: EmailStr
    company_name: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    plan: str


# Поддерживаемые языки вакансии/интервью: русский, кыргызский, английский
LANGUAGE_PATTERN = "^(ru|ky|en)$"


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    requirements: str = Field(min_length=1)
    language: str = Field(default="ru", pattern=LANGUAGE_PATTERN)
    scoring_weights: Optional[dict] = None  # Priority 2
    # Обязательные вопросы рекрутёра (pilot feedback: Dinara)
    mandatory_questions: Optional[list[str]] = Field(default=None, max_length=20)


class JobUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1)
    requirements: Optional[str] = Field(default=None, min_length=1)
    language: Optional[str] = Field(default=None, pattern=LANGUAGE_PATTERN)
    is_active: Optional[bool] = None
    scoring_weights: Optional[dict] = None
    mandatory_questions: Optional[list[str]] = Field(default=None, max_length=20)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    title: str
    description: str
    requirements: str
    apply_token: str
    language: str = "ru"
    is_active: bool
    created_at: datetime
    apply_link: str = ""
    scoring_weights: Optional[dict] = None
    mandatory_questions: list[str] = []

    @field_validator("scoring_weights", mode="before")
    @classmethod
    def _parse_weights(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return None
        return v

    @field_validator("mandatory_questions", mode="before")
    @classmethod
    def _parse_mandatory_questions(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (ValueError, TypeError):
                return []
        return v or []

    @classmethod
    def from_job(cls, job, frontend_url: str) -> "JobOut":
        out = cls.model_validate(job)
        out.apply_link = f"{frontend_url}/apply/{job.apply_token}"
        return out


# --- Candidate schemas ---

class JobPublicOut(BaseModel):
    """Публичная информация о вакансии для кандидата."""
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    requirements: str
    language: str = "ru"


class CandidateApply(BaseModel):
    """Форма подачи заявки кандидатом."""
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=32)
    resume_text: Optional[str] = Field(default=None, min_length=1)


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_text: Optional[str]
    status: CandidateStatus
    score: Optional[float]
    pre_score: Optional[float]

    # Structured scoring (C5.1)
    technical_score: Optional[int] = None
    soft_skills_score: Optional[int] = None
    experience_score: Optional[int] = None
    motivation_score: Optional[int] = None
    confidence: Optional[float] = None
    scoring_reasoning: Optional[str] = None  # JSON-строка

    # Bias detection (C5.2)
    bias_flags: Optional[str] = None  # JSON-строка или None
    cross_validation: Optional[str] = None  # Priority 2: JSON-строка
    answer_attribution: Optional[str] = None  # Priority 2.2: JSON-строка

    anti_cheat_score: Optional[float] = None
    anti_cheat_flags: Optional[list[str]] = None
    summary: Optional[str]
    recommendation: Optional[str]
    created_at: datetime

    # Ground Truth Tracking (Phase 10/10 - 1.1)
    actual_hire_decision: Optional[str] = None
    ai_feedback: Optional[str] = None
    hr_notes: Optional[str] = None
    requires_manual_review: bool = False
    tags: list[str] = []

    # 1.3 Unified Scale + Confidence Bounds (вычисляемые, не хранятся в БД)
    confidence_level: Optional[str] = None  # "low" | "medium" | "high"
    score_range: Optional[str] = None       # например "75 ±10"

    @model_validator(mode="after")
    def _derive_confidence_bounds(self):
        if self.confidence is not None:
            if self.confidence >= 0.8:
                self.confidence_level, margin = "high", 5
            elif self.confidence >= 0.5:
                self.confidence_level, margin = "medium", 10
            else:
                self.confidence_level, margin = "low", 15
            if self.score is not None:
                self.score_range = f"{round(self.score)} ±{margin}"
        return self

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags_out(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []

    @field_validator("anti_cheat_flags", mode="before")
    @classmethod
    def _parse_anti_cheat_flags(cls, v):
        """anti_cheat_flags хранится в БД как JSON-строка — приводим к списку."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class CandidateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    status: CandidateStatus
    score: Optional[float]
    pre_score: Optional[float]
    recommendation: Optional[str]
    requires_manual_review: bool = False
    tags: list[str] = []
    created_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags_li(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return v or []


# --- Ground Truth Tracking schemas (Phase 10/10 - 1.1) ---

class FinalDecisionRequest(BaseModel):
    """HR отмечает финальное решение по кандидату."""
    actual_hire_decision: str = Field(pattern="^(hired|rejected_final|pending)$")
    ai_feedback: Optional[str] = Field(default=None, pattern="^(correct|incorrect|partial)$")
    hr_notes: Optional[str] = Field(default=None, max_length=1000)


class AIAccuracyStats(BaseModel):
    """Статистика точности AI рекомендаций."""
    total_with_feedback: int
    correct_predictions: int
    incorrect_predictions: int
    partial_predictions: int
    accuracy_rate: float  # 0-100%
    breakdown_by_recommendation: dict[str, dict]  # {"hire": {"correct": 10, "incorrect": 2}, ...}


# --- AI-copilot для HR (C4) ---

class CopilotMessage(BaseModel):
    """Одно сообщение истории диалога с copilot."""
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class CopilotRequest(BaseModel):
    """Запрос HR к AI-copilot по базе кандидатов."""
    message: str = Field(min_length=1, max_length=2000)
    history: Optional[list[CopilotMessage]] = Field(default=None, max_length=20)


class CopilotReferencedCandidate(BaseModel):
    """Кандидат, упомянутый в ответе copilot — для кликабельных чипов во фронте."""
    id: int
    name: str
    score: Optional[float] = None
    recommendation: Optional[str] = None


class CopilotResponse(BaseModel):
    """Ответ AI-copilot."""
    answer: str
    referenced_candidates: list[CopilotReferencedCandidate] = []
    candidates_analyzed: int

