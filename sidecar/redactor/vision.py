from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .models import Candidate, Rect
from .vision_assets import find_face_cascade_path


def detect_visual_candidates(image_path: str | Path, *, file_id: str, page_index: int) -> list[Candidate]:
    image = cv2.imread(str(image_path))
    if image is None:
        return []

    height, width = image.shape[:2]
    candidates: list[Candidate] = []
    candidates.extend(_detect_red_seals(image, width, height, file_id, page_index))
    candidates.extend(_detect_portraits(image, width, height, file_id, page_index))
    candidates.extend(_detect_logo_like_blocks(image, width, height, file_id, page_index))
    return _dedupe(candidates)


def _detect_red_seals(image: np.ndarray, width: int, height: int, file_id: str, page_index: int) -> list[Candidate]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    low_red_a = cv2.inRange(hsv, np.array([0, 60, 60]), np.array([12, 255, 255]))
    low_red_b = cv2.inRange(hsv, np.array([165, 60, 60]), np.array([180, 255, 255]))
    mask = cv2.morphologyEx(cv2.bitwise_or(low_red_a, low_red_b), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[Candidate] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < max(40, width * height * 0.002):
            continue
        x, y, w, h = cv2.boundingRect(contour)
        candidates.append(
            Candidate(
                file_id=file_id,
                page_index=page_index,
                rect_normalized=_rect_from_pixels(x, y, w, h, width, height),
                category="seal",
                source="vision",
                confidence=0.82,
                color="#dc2626",
            )
        )
    return candidates


def _detect_portraits(image: np.ndarray, width: int, height: int, file_id: str, page_index: int) -> list[Candidate]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    try:
        cascade_path = str(find_face_cascade_path())
    except FileNotFoundError:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    classifier = cv2.CascadeClassifier(cascade_path)
    if classifier.empty():
        return []

    faces = classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24))
    return [
        Candidate(
            file_id=file_id,
            page_index=page_index,
            rect_normalized=_rect_from_pixels(x, y, w, h, width, height),
            category="portrait",
            source="vision",
            confidence=0.76,
            color="#7c3aed",
        )
        for (x, y, w, h) in faces
    ]


def _detect_logo_like_blocks(image: np.ndarray, width: int, height: int, file_id: str, page_index: int) -> list[Candidate]:
    top_band = image[: max(1, round(height * 0.22)), :]
    gray = cv2.cvtColor(top_band, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 180)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[Candidate] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < width * height * 0.001 or area > width * height * 0.08:
            continue
        if w / max(h, 1) > 6 or h / max(w, 1) > 6:
            continue
        candidates.append(
            Candidate(
                file_id=file_id,
                page_index=page_index,
                rect_normalized=_rect_from_pixels(x, y, w, h, width, height),
                category="employer_logo",
                source="vision",
                confidence=0.48,
                color="#d97706",
            )
        )
    return candidates[:5]


def _rect_from_pixels(x: int, y: int, width: int, height: int, page_width: int, page_height: int) -> Rect:
    return Rect(
        x=round(x / page_width, 6),
        y=round(y / page_height, 6),
        width=round(width / page_width, 6),
        height=round(height / page_height, 6),
    ).clamped()


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    seen: set[tuple[int, int, int, int, str]] = set()
    result: list[Candidate] = []
    for candidate in candidates:
        rect = candidate.rect_normalized
        key = (
            round(rect.x * 100),
            round(rect.y * 100),
            round(rect.width * 100),
            round(rect.height * 100),
            candidate.category,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result
