import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _decode(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Долгоживущий refresh-токен (claim type=refresh)."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    payload = _decode(token)
    # refresh-токен нельзя использовать как access для доступа к API
    if payload is not None and payload.get("type") == "refresh":
        return None
    return payload


def decode_refresh_token(token: str) -> Optional[dict]:
    payload = _decode(token)
    if payload is not None and payload.get("type") == "refresh":
        return payload
    return None


# SEC-5: политика паролей — минимум 8 символов + буквы и цифры.
MIN_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> None:
    """Проверяет сложность пароля. Поднимает ValueError с причиной, если пароль слабый."""
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Пароль должен содержать не менее {MIN_PASSWORD_LENGTH} символов")
    if not any(c.isalpha() for c in password):
        raise ValueError("Пароль должен содержать хотя бы одну букву")
    if not any(c.isdigit() for c in password):
        raise ValueError("Пароль должен содержать хотя бы одну цифру")


# ─── D2: ключи публичного API ───
# Ключ выдаётся один раз (вида "hl_<random>"), в БД хранится только SHA-256 хеш.
API_KEY_PREFIX = "hl_"


def hash_api_key(full_key: str) -> str:
    """SHA-256 хеш от полного API-ключа (для хранения и поиска)."""
    return hashlib.sha256((full_key or "").encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Создаёт новый API-ключ.

    Возвращает (full_key, prefix, hashed_key). Полный ключ показывается
    клиенту один раз; в БД сохраняются только prefix и hashed_key.
    """
    full_key = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    prefix = full_key[:12]
    return full_key, prefix, hash_api_key(full_key)
