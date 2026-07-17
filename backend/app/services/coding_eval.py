"""GAP-5 — key-free эвристическая оценка кода без исполнения.

Не запускает код кандидата (безопасно): для Python только ast.parse (проверка
синтаксиса, без выполнения). Даёт предварительный балл и всегда требует
ручной проверки HR (requires_manual_review=True).
"""
import ast
from typing import List, Optional


def evaluate_submission(
    code: str,
    language: Optional[str],
    required_keywords: Optional[List[str]] = None,
    max_score: int = 100,
) -> dict:
    code = code or ""
    stripped = code.strip()
    lang = (language or "python").lower()
    keywords = required_keywords or []
    checks = []
    pct = 0.0

    non_empty = len(stripped) >= 10
    checks.append({"name": "non_empty", "passed": non_empty})
    if non_empty:
        pct += 0.20

    is_python = lang in ("python", "py")
    syntax_ok = None
    struct_count = 0
    if is_python:
        try:
            tree = ast.parse(code)
            syntax_ok = True
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    struct_count += 1
        except SyntaxError:
            syntax_ok = False
        checks.append({"name": "python_syntax_valid", "passed": bool(syntax_ok)})
        if syntax_ok:
            pct += 0.30
        checks.append({"name": "defines_function_or_class", "passed": struct_count > 0})
        if struct_count > 0:
            pct += 0.20
    else:
        checks.append(
            {"name": "python_syntax_valid", "passed": None, "detail": "проверка только для Python"}
        )
        multiline = stripped.count("\n") >= 2
        checks.append({"name": "multiline_code", "passed": multiline})
        if multiline:
            pct += 0.30
        has_structure = any(t in code for t in ("{", "def ", "function", "func ", "class "))
        checks.append({"name": "has_code_structure", "passed": has_structure})
        if has_structure:
            pct += 0.20

    if keywords:
        hits = [k for k in keywords if k.lower() in code.lower()]
        frac = len(hits) / len(keywords)
        pct += 0.30 * frac
        checks.append(
            {
                "name": "required_keywords",
                "passed": len(hits) == len(keywords),
                "detail": str(len(hits)) + "/" + str(len(keywords)),
                "matched": hits,
            }
        )
    else:
        pct += 0.30
        checks.append({"name": "required_keywords", "passed": True, "detail": "не заданы"})

    auto_score = round(pct * float(max_score), 1)
    feedback = {
        "auto_score": auto_score,
        "max_score": max_score,
        "language": lang,
        "syntax_ok": syntax_ok,
        "checks": checks,
        "note": "Эвристическая предварительная оценка без исполнения кода. Требуется ручная проверка HR.",
    }
    return {"auto_score": auto_score, "requires_manual_review": True, "feedback": feedback}
