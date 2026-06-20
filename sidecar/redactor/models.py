from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class MaterialType(str, Enum):
    SOCIAL = "social"
    OTHER = "other"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


Category = Literal[
    "person_name",
    "identity_number",
    "employer_name",
    "employer_logo",
    "employer_address",
    "department_name",
    "phone_number",
    "portrait",
    "seal",
    "manual",
]


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    def clamped(self) -> "Rect":
        x = min(max(self.x, 0.0), 1.0)
        y = min(max(self.y, 0.0), 1.0)
        right = min(max(self.x + self.width, 0.0), 1.0)
        bottom = min(max(self.y + self.height, 0.0), 1.0)
        return Rect(
            x=round(x, 6),
            y=round(y, 6),
            width=round(max(0.0, right - x), 6),
            height=round(max(0.0, bottom - y), 6),
        )

    def to_pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        rect = self.clamped()
        left = round(rect.x * width)
        top = round(rect.y * height)
        right = round((rect.x + rect.width) * width)
        bottom = round((rect.y + rect.height) * height)
        return left, top, max(left + 1, right), max(top + 1, bottom)


@dataclass(frozen=True)
class Candidate:
    file_id: str
    page_index: int
    rect_normalized: Rect
    category: Category
    source: Literal["ocr", "vision", "manual", "rule"]
    confidence: float
    status: ReviewStatus = ReviewStatus.PENDING
    color: str = "#2563eb"
    text: str | None = None


@dataclass(frozen=True)
class ExportRequest:
    source_path: str
    output_path: str
    candidates: list[Candidate]
    rasterize_pdf_pages: bool = False
