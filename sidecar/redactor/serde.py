from __future__ import annotations

from typing import Any

from .models import Candidate, ExportRequest, Rect, ReviewStatus


def candidate_to_dict(candidate: Candidate) -> dict[str, Any]:
    return {
        "fileId": candidate.file_id,
        "pageIndex": candidate.page_index,
        "rectNormalized": {
            "x": candidate.rect_normalized.x,
            "y": candidate.rect_normalized.y,
            "width": candidate.rect_normalized.width,
            "height": candidate.rect_normalized.height,
        },
        "category": candidate.category,
        "source": candidate.source,
        "confidence": candidate.confidence,
        "status": candidate.status.value,
        "color": candidate.color,
        "text": candidate.text,
    }


def candidate_from_dict(payload: dict[str, Any]) -> Candidate:
    rect_payload = payload["rectNormalized"]
    return Candidate(
        file_id=payload["fileId"],
        page_index=int(payload["pageIndex"]),
        rect_normalized=Rect(
            x=float(rect_payload["x"]),
            y=float(rect_payload["y"]),
            width=float(rect_payload["width"]),
            height=float(rect_payload["height"]),
        ),
        category=payload["category"],
        source=payload["source"],
        confidence=float(payload["confidence"]),
        status=ReviewStatus(payload.get("status", ReviewStatus.PENDING.value)),
        color=payload.get("color", "#2563eb"),
        text=payload.get("text"),
    )


def export_request_from_dict(payload: dict[str, Any]) -> ExportRequest:
    return ExportRequest(
        source_path=payload["sourcePath"],
        output_path=payload["outputPath"],
        candidates=[candidate_from_dict(item) for item in payload.get("candidates", [])],
        rasterize_pdf_pages=bool(payload.get("rasterizePdfPages", False)),
    )
