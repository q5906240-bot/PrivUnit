from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any

from .models import Candidate, Rect

IDENTITY_RE = re.compile(r"(?<!\d)[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")
PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
ADDRESS_HINTS = ("地址", "住址", "所在地", "通讯地址", "注册地址")
DEPARTMENT_HINTS = ("部门", "学院", "科室", "中心", "办公室")
EMPLOYER_HINTS = ("公司", "大学", "学院", "医院", "研究院", "学校", "单位", "集团", "厂")


def _word_to_rect(word: dict[str, Any]) -> Rect:
    left, top, right, bottom = word["box"]
    page_width = word["page_width"]
    page_height = word["page_height"]
    return Rect(
        x=round(left / page_width, 6),
        y=round(top / page_height, 6),
        width=round((right - left) / page_width, 6),
        height=round((bottom - top) / page_height, 6),
    ).clamped()


def _matched_text_rect(word: dict[str, Any], text: str, matched: str) -> Rect:
    """Approximate a substring box when OCR returns a full-line box."""

    match_index = text.find(matched)
    if match_index < 0 or not text:
        return _word_to_rect(word)
    if text == matched:
        return _word_to_rect(word)

    left, top, right, bottom = word["box"]
    page_width = word["page_width"]
    page_height = word["page_height"]
    full_width = right - left
    text_length = max(len(text), 1)
    match_left = left + full_width * (match_index / text_length)
    match_right = left + full_width * ((match_index + len(matched)) / text_length)
    pad = max(full_width / text_length * 0.15, 1)
    return Rect(
        x=round((match_left - pad) / page_width, 6),
        y=round(top / page_height, 6),
        width=round((match_right - match_left + pad * 2) / page_width, 6),
        height=round((bottom - top) / page_height, 6),
    ).clamped()


def _contains_any(text: str, terms: Sequence[str]) -> bool:
    return any(term and term in text for term in terms)


def detect_sensitive_text(
    words: Iterable[dict[str, Any]],
    *,
    person_name: str | None,
    employer_terms: Sequence[str],
    file_id: str = "file-1",
    page_index: int = 0,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    normalized_name = (person_name or "").strip()
    normalized_employer_terms = [term.strip() for term in employer_terms if term.strip()]

    for word in words:
        text = str(word.get("text", "")).strip()
        if not text:
            continue

        category: str | None = None
        source = "ocr"
        confidence = 0.88
        candidate_rect = _word_to_rect(word)
        candidate_text = text

        if normalized_name and normalized_name in text:
            category = "person_name"
            confidence = 0.96
            candidate_rect = _matched_text_rect(word, text, normalized_name)
            candidate_text = normalized_name
        elif IDENTITY_RE.search(text):
            category = "identity_number"
            confidence = 0.98
        elif PHONE_RE.search(text):
            category = "phone_number"
            confidence = 0.97
        elif _contains_any(text, normalized_employer_terms) or _contains_any(text, EMPLOYER_HINTS):
            category = "employer_name"
            confidence = 0.78
        elif _contains_any(text, ADDRESS_HINTS):
            category = "employer_address"
            confidence = 0.72
        elif _contains_any(text, DEPARTMENT_HINTS):
            category = "department_name"
            confidence = 0.72

        if category:
            candidates.append(
                Candidate(
                    file_id=file_id,
                    page_index=page_index,
                    rect_normalized=candidate_rect,
                    category=category,  # type: ignore[arg-type]
                    source=source,  # type: ignore[arg-type]
                    confidence=confidence,
                    text=candidate_text,
                )
            )

    return candidates
