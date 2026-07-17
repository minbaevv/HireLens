"""Парсинг резюме из PDF или plain text."""
import io
import logging

logger = logging.getLogger(__name__)


def parse_resume(file_bytes: bytes, filename: str) -> str:
    """Извлекает текст из PDF или возвращает текст как есть.

    Args:
        file_bytes: байты загруженного файла
        filename: имя файла для определения типа

    Returns:
        Извлечённый текст резюме
    """
    if filename.lower().endswith(".pdf"):
        return _parse_pdf(file_bytes)
    # Для .txt и других текстовых форматов
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("cp1251").strip()
        except Exception as e:
            logger.warning(f"Не удалось декодировать файл {filename}: {e}")
            return ""


def _parse_pdf(file_bytes: bytes) -> str:
    """Извлекает текст из PDF через pdfplumber."""
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())
            result = "\n\n".join(pages_text).strip()
            if not result:
                logger.warning("PDF не содержит извлекаемого текста")
            return result
    except Exception as e:
        logger.error(f"Ошибка парсинга PDF: {e}")
        return ""
