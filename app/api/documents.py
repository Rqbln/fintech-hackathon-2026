"""Serve contract PDFs and optional evidence highlighting."""

import io
import re
from urllib.parse import unquote

import pymupdf
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.rag.ingestion_pipeline import get_contract_pdf_path

router = APIRouter()

_SAFE_ID = re.compile(r"^[a-zA-Z0-9_\-]+$")
_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    collapsed = _SPACE_RE.sub(" ", lowered).strip()
    return _PUNCT_RE.sub("", collapsed)


def _phrase_candidates(phrase: str) -> list[str]:
    cleaned = _SPACE_RE.sub(" ", phrase).strip()
    if not cleaned:
        return []
    words = cleaned.split(" ")
    candidates = [cleaned]
    if len(words) > 14:
        candidates.append(" ".join(words[:14]))
    if len(words) > 8:
        candidates.append(" ".join(words[:8]))
    if len(words) > 6:
        mid = max(0, len(words) // 2 - 4)
        candidates.append(" ".join(words[mid : mid + 8]))
    if len(words) > 5:
        candidates.append(" ".join(words[-6:]))

    # Extra robustness: sliding windows help when quotes include OCR noise or line breaks.
    if len(words) > 10:
        for i in range(0, min(len(words) - 5, 18), 3):
            candidates.append(" ".join(words[i : i + 6]))
    return list(dict.fromkeys(candidates))


def _find_rects_for_phrase(page: pymupdf.Page, phrase: str) -> list[pymupdf.Rect]:
    for candidate in _phrase_candidates(phrase):
        rects = page.search_for(candidate)
        if rects:
            return rects
    return []


def _resolve_page_for_phrase(doc: pymupdf.Document, phrase: str) -> tuple[int, bool]:
    if not phrase.strip():
        return 1, False

    normalized_query = _normalize_text(phrase)
    for idx in range(doc.page_count):
        page = doc[idx]
        if _find_rects_for_phrase(page, phrase):
            return idx + 1, True

    # Fallback for line-break/spacing OCR differences.
    for idx in range(doc.page_count):
        page_text = doc[idx].get_text("text")
        if normalized_query and normalized_query in _normalize_text(page_text):
            return idx + 1, True

    return 1, False


def _validate_contract_and_path(contract_id: str) -> str:
    if not _SAFE_ID.match(contract_id):
        raise HTTPException(status_code=400, detail="Invalid contract ID")

    path = get_contract_pdf_path(contract_id)
    if not path:
        raise HTTPException(
            status_code=404,
            detail=f"PDF for contract '{contract_id}' not found. Re-ingest the document.",
        )
    return path


@router.get("/documents/{contract_id}/find-text", summary="Find phrase page in contract PDF")
async def find_text(contract_id: str, q: str):
    path = _validate_contract_and_path(contract_id)
    phrase = unquote(q or "")
    try:
        with pymupdf.open(path) as doc:
            page, found = _resolve_page_for_phrase(doc, phrase)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to search PDF text: {exc}") from exc

    return JSONResponse(
        content={
            "contract_id": contract_id,
            "query": phrase,
            "page": page,
            "found": found,
        }
    )


@router.get("/documents/{contract_id}/pdf", summary="Serve contract PDF (optional highlighting)")
async def get_pdf(
    contract_id: str,
    highlight: str | None = None,
    highlights: list[str] | None = None,
    page: int | None = None,
):
    path = _validate_contract_and_path(contract_id)

    phrases = [unquote(highlight or "").strip()] if highlight else []
    if highlights:
        phrases.extend(unquote(p or "").strip() for p in highlights)
    phrases = [p for p in phrases if p]
    if not phrases:
        return FileResponse(
            path=path,
            media_type="application/pdf",
            filename=f"{contract_id}.pdf",
            headers={"Content-Disposition": "inline"},
        )

    try:
        with pymupdf.open(path) as doc:
            page_indices = range(doc.page_count)
            if page and 1 <= page <= doc.page_count:
                page_indices = [page - 1]

            highlighted = 0
            for idx in page_indices:
                p = doc[idx]
                for phrase in phrases:
                    rects = _find_rects_for_phrase(p, phrase)
                    for rect in rects:
                        annot = p.add_highlight_annot(rect)
                        annot.set_colors(stroke=(1, 1, 0))
                        annot.update()
                        highlighted += 1
                        if highlighted >= 40:
                            break
                    if highlighted >= 40:
                        break
                if highlighted >= 40:
                    break

            payload = doc.tobytes()

        return StreamingResponse(
            io.BytesIO(payload),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to render highlighted PDF: {exc}") from exc
