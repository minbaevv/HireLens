"""Обработка видео: извлечение аудио, анализ."""
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_audio_from_video(video_path: str) -> Optional[bytes]:
    """Извлекает аудиодорожку из видео в формат wav.

    Args:
        video_path: Путь к видеофайлу.

    Returns:
        Байты аудио в формате wav или None при ошибке.

    Raises:
        RuntimeError: Если ffmpeg недоступен или извлечение не удалось.
    """
    output_path = video_path.replace(Path(video_path).suffix, ".wav")

    try:
        # Проверяем что ffmpeg доступен
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=5
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(
            f"ffmpeg не установлен или недоступен. "
            f"Установите: apt-get install ffmpeg (Linux) или brew install ffmpeg (Mac). "
            f"Ошибка: {e}"
        )

    try:
        # Извлекаем аудио: -vn (без видео), -acodec pcm_s16le (WAV формат)
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", video_path,
                "-vn",  # без видео
                "-acodec", "pcm_s16le",  # WAV PCM 16-bit
                "-ar", "16000",  # 16kHz sample rate (оптимально для Whisper)
                "-ac", "1",  # моно
                "-y",  # перезаписать если существует
                output_path
            ],
            capture_output=True,
            check=True,
            timeout=30
        )

        if not os.path.exists(output_path):
            raise RuntimeError(f"ffmpeg не создал аудио файл: {output_path}")

        with open(output_path, "rb") as f:
            audio_bytes = f.read()

        # Удаляем временный WAV файл
        os.remove(output_path)

        logger.info(f"Аудио извлечено из {video_path}: {len(audio_bytes)} байт")
        return audio_bytes

    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg ошибка: {e.stderr.decode() if e.stderr else e}")
        raise RuntimeError(f"Не удалось извлечь аудио из видео: {e}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Извлечение аудио превысило таймаут 30s")
    finally:
        # Очистка временного файла если остался
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass


def get_video_duration(video_path: str) -> float:
    """Получает длительность видео в секундах через ffprobe.

    Args:
        video_path: Путь к видеофайлу.

    Returns:
        Длительность в секундах.

    Raises:
        RuntimeError: Если ffprobe недоступен или видео повреждено.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            capture_output=True,
            check=True,
            timeout=10,
            text=True
        )
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, subprocess.TimeoutExpired) as e:
        logger.warning(f"Не удалось определить длительность видео: {e}")
        return 0.0
