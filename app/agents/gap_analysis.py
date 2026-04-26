"""GapAnalysisAgent — evaluates DORA Art.30 obligations against a contract.

Each obligation is an independent LLM call. A semaphore caps concurrency so
we don't burst-hit Cerebras's rate limit. Results are yielded as they complete
so the caller can stream them to the frontend immediately.
"""

import asyncio
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import structlog
import yaml
from llama_index.core.llms import ChatMessage, LLM
from llama_index.core.query_engine import BaseQueryEngine

from app.llm.retry import chat_with_retry
from app.config import settings
from app.rag.ingestion_pipeline import get_contract_pdf_path, parse_pdf
from app.schemas import EvidenceSpan, ObligationFinding, Verdict

log = structlog.get_logger()

_OBLIGATIONS_PATH = Path(__file__).parent.parent / "data" / "dora_obligations.yaml"
_CONTRACT_CONTEXT_TARGET = 3
_TOTAL_CONTEXT_LIMIT = 4
_MIN_CONTRACT_EVIDENCE = 2
_MIN_CONTRACT_PAGES = 1
_DEFAULT_PREFILTER_LIMIT = 10
_FAST_PREFILTER_LIMIT = 6
_CRITICAL_OBLIGATION_IDS = {
    "DORA-Art30-2-b",  # data residency + location change notice
    "DORA-Art30-2-d",  # return/recovery/portability
    "DORA-Art30-2-e",  # measurable SLAs
    "DORA-Art30-3-b",  # termination rights
    "DORA-Art30-3-g",  # BCP / DR / TLPT
}

_RETRIEVAL_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_FINDING_CACHE: dict[str, tuple[float, ObligationFinding]] = {}
_CONTRACT_INDEX_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}

_SYSTEM = """\
You are a DORA (EU 2022/2554) compliance analyst. Given a DORA obligation and excerpts
from a vendor contract, assess whether the contract satisfies the obligation.

Return ONLY a valid JSON object — no markdown fences:
{
  "verdict": "met" | "partially_met" | "unmet" | "unknown",
  "rationale": "one to three sentence explanation citing specific contract language",
  "gap_description": "what is missing or weak (empty string if verdict is met)",
  "risk_level": "low" | "medium" | "high" | "critical",
  "evidence_quotes": ["verbatim excerpt from contract that is most relevant, ≤ 150 chars"]
}

Be strict: 'met' requires explicit contractual language. 'partially_met' if present but incomplete.
'unmet' if the obligation is not addressed at all.
"""

_BATCH_SYSTEM = """\
You are a DORA (EU 2022/2554) compliance analyst.
Assess multiple obligations in one pass using only provided contract evidence and DORA references.

Return ONLY valid JSON with this shape:
{
  "results": [
    {
      "obligation_id": "DORA-Art30-2-a",
      "verdict": "met|partially_met|unmet|unknown",
      "rationale": "1-3 concise sentences grounded in evidence",
      "gap_description": "missing or weak contractual element (empty if met)",
      "risk_level": "low|medium|high|critical",
      "evidence_quotes": ["short verbatim quote <= 150 chars"]
    }
  ]
}

Rules:
- Be strict and contract-grounded.
- If evidence is insufficient: verdict must be "unknown".
- Never output markdown.
"""


def _load_obligations() -> list[dict]:
    data = yaml.safe_load(_OBLIGATIONS_PATH.read_text())
    return data["obligations"]


def _parse_verdict_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


def _cache_get_entry[T](cache: dict[str, tuple[float, T]], key: str, ttl: int) -> T | None:
    hit = cache.get(key)
    if not hit:
        return None
    ts, value = hit
    if time.time() - ts > ttl:
        cache.pop(key, None)
        return None
    return value


def _cache_set_entry[T](cache: dict[str, tuple[float, T]], key: str, value: T) -> None:
    cache[key] = (time.time(), value)


def _prefilter_obligations(
    obligations: list[dict[str, Any]],
    contract_text_preview: str,
    *,
    enabled: bool,
    fast_mode: bool,
) -> list[dict[str, Any]]:
    if not obligations:
        return []
    if not enabled:
        return obligations

    preview = (contract_text_preview or "").lower()
    scored: list[tuple[float, dict[str, Any]]] = []
    for ob in obligations:
        keys = [k.lower() for k in (ob.get("keywords") or [])]
        keyword_hits = sum(1 for k in keys if k and k in preview)
        pass_hits = sum(1 for t in re.findall(r"[a-z0-9]{5,}", str(ob.get("pass_criteria", "")).lower())[:10] if t in preview)
        critical_boost = 2.5 if ob.get("id") in _CRITICAL_OBLIGATION_IDS else 0.0
        score = keyword_hits * 1.2 + pass_hits * 0.4 + critical_boost
        scored.append((score, ob))

    scored.sort(key=lambda x: x[0], reverse=True)
    limit = _FAST_PREFILTER_LIMIT if fast_mode else _DEFAULT_PREFILTER_LIMIT
    selected = [ob for _, ob in scored[:limit]]
    selected_ids = {ob["id"] for ob in selected}
    for _, ob in scored:
        if ob["id"] in _CRITICAL_OBLIGATION_IDS and ob["id"] not in selected_ids:
            selected.append(ob)
            selected_ids.add(ob["id"])
    return selected


async def _evaluate_one(
    llm: LLM,
    citation_engine: BaseQueryEngine,
    obligation: dict,
    contract_id: str,
    contract_text_preview: str,
) -> ObligationFinding:
    """Single obligation evaluation grounded by contract-specific retrieved chunks."""
    ob_id = obligation["id"]
    finding_cache_key = f"{contract_id}|{ob_id}|{hash(contract_text_preview[:800])}"
    cached_finding = _cache_get_entry(_FINDING_CACHE, finding_cache_key, settings.finding_cache_ttl_sec)
    if cached_finding:
        return cached_finding

    contract_chunks, dora_chunks = await _retrieve_evidence_lanes(citation_engine, contract_id, obligation)
    contract_chunks, dora_chunks = _apply_evidence_guardrails(contract_chunks, dora_chunks)

    if _is_evidence_insufficient(contract_chunks):
        return ObligationFinding(
            obligation_id=ob_id,
            article=obligation["article"],
            paragraph=obligation["paragraph"],
            description=obligation["text"],
            verdict=Verdict.UNKNOWN,
            rationale="Insufficient contract-grounded evidence to assess this obligation reliably.",
            evidence_spans=[],
            gap_description="",
            risk_level="medium",
        )

    context_block = _render_context_block(contract_chunks, dora_chunks)
    preview_block = contract_text_preview[:3000].strip()

    combined_context = context_block
    if preview_block:
        combined_context = f"{combined_context}\n\n[Contract preview]\n{preview_block}" if combined_context else preview_block

    user_msg = (
        f"DORA Obligation (Art.{obligation['article']} §{obligation['paragraph']}):\n"
        f"{obligation['text']}\n\n"
        f"Pass criteria: {obligation.get('pass_criteria', '')[:300]}\n\n"
        f"Contract evidence (contract_id={contract_id}):\n"
        f"{combined_context or 'No contract context found. Return unknown unless explicit evidence exists.'}"
    )
    messages = [
        ChatMessage(role="system", content=_SYSTEM),
        ChatMessage(role="user", content=user_msg),
    ]

    resp = await chat_with_retry(llm, messages)
    raw = resp.message.content.strip()

    try:
        data = _parse_verdict_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("gap_analysis_json_failed", obligation_id=ob_id, error=str(exc))
        data = {
            "verdict": "unknown",
            "rationale": f"Parse error: {exc}",
            "gap_description": "",
            "risk_level": "medium",
            "evidence_quotes": [],
        }

    evidence_spans = _build_evidence_spans(
        evidence_quotes=data.get("evidence_quotes", []),
        retrieved_chunks=contract_chunks,
        contract_id=contract_id,
    )

    try:
        verdict = Verdict(data.get("verdict", "unknown"))
    except ValueError:
        verdict = Verdict.UNKNOWN

    finding = ObligationFinding(
        obligation_id=ob_id,
        article=obligation["article"],
        paragraph=obligation["paragraph"],
        description=obligation["text"],
        verdict=verdict,
        rationale=data.get("rationale", ""),
        evidence_spans=evidence_spans,
        gap_description=data.get("gap_description", ""),
        risk_level=data.get("risk_level", "medium"),
    )
    log.info("gap_finding", obligation_id=ob_id, verdict=verdict.value, risk=finding.risk_level)
    _cache_set_entry(_FINDING_CACHE, finding_cache_key, finding)
    return finding


def _safe_node_text(node: Any) -> str:
    getter = getattr(node, "get_content", None)
    if callable(getter):
        try:
            return getter(metadata_mode="none")
        except Exception:
            return getter()
    return (getattr(node, "text", "") or "").strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{4,}", (text or "").lower())


def _is_toc_like(text: str) -> bool:
    t = (text or "").lower()
    toc_markers = ("table des matieres", "sommaire", "annexe", "table of contents")
    short_line = len(t) < 220
    many_dots = t.count("...") >= 2 or t.count(" .") >= 5
    return short_line and (any(m in t for m in toc_markers) or many_dots)


def _obligation_anchor_terms(obligation: dict[str, Any]) -> set[str]:
    text = f"{obligation.get('text', '')} {obligation.get('pass_criteria', '')}".lower()
    anchors: set[str] = set()
    mapping = [
        (("termination", "resiliation", "notice period", "préavis", "mise en demeure"), {"résiliation", "preavis", "préavis", "mise", "demeure", "termination"}),
        (("subcontract", "sous-trait", "outsourc"), {"sous-traitance", "sous-traiter", "subcontracting", "subprocessor"}),
        (("location", "region", "country", "residency", "localisation"), {"localisation", "localization", "region", "country", "notifié", "notification"}),
        (("tlpt", "continuity", "business continuity", "pca", "recovery"), {"tlpt", "pca", "continuité", "continuity", "recovery", "resilience"}),
        (("insolvency", "resolution", "return", "reversibility", "portability"), {"insolvabilité", "resolution", "restitution", "réversibilité", "portabilité"}),
    ]
    for keys, terms in mapping:
        if any(k in text for k in keys):
            anchors.update(terms)
    return anchors


def _chunk_contract_page(text: str, max_len: int = 700) -> list[str]:
    raw_parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text or "")
    parts = [p.strip() for p in raw_parts if p and len(p.strip()) >= 40]
    chunks: list[str] = []
    current = ""
    for part in parts:
        if not current:
            current = part
            continue
        if len(current) + 1 + len(part) <= max_len:
            current = f"{current} {part}"
        else:
            chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks[:20]


def _build_contract_evidence_index(contract_id: str) -> dict[str, Any]:
    path = get_contract_pdf_path(contract_id)
    if not path:
        return {"chunks": [], "inv": {}, "doc_id": contract_id}
    try:
        pages = parse_pdf(path.read_bytes(), None)
    except Exception:
        return {"chunks": [], "inv": {}, "doc_id": contract_id}

    chunks: list[dict[str, Any]] = []
    inv: dict[str, set[int]] = defaultdict(set)
    for page in pages:
        page_no = int(page.get("page", 0) or 0)
        for snippet in _chunk_contract_page(page.get("text", "")):
            token_set = set(_tokenize(snippet))
            if not token_set:
                continue
            idx = len(chunks)
            chunks.append(
                {
                    "text": snippet,
                    "page": page_no,
                    "document_id": contract_id,
                    "node_id": f"local-{contract_id}-p{page_no}-c{idx}",
                    "token_set": token_set,
                }
            )
            for tok in token_set:
                inv[tok].add(idx)
    return {"chunks": chunks, "inv": inv, "doc_id": contract_id}


def _get_contract_evidence_index(contract_id: str) -> dict[str, Any]:
    cached = _cache_get_entry(_CONTRACT_INDEX_CACHE, contract_id, settings.rag_cache_ttl_sec)
    if cached is not None:
        return cached
    built = _build_contract_evidence_index(contract_id)
    _cache_set_entry(_CONTRACT_INDEX_CACHE, contract_id, built)
    return built


def _keyword_overlap_score(text: str, obligation: dict) -> float:
    keys = _obligation_keywords(obligation)
    if not keys:
        return 0.0
    tl = text.lower()
    matched = sum(1 for k in keys if k in tl)
    return matched / max(1, len(keys))


async def _retrieve_contract_chunks(
    citation_engine: BaseQueryEngine,
    contract_id: str,
    obligation: dict,
) -> list[dict[str, Any]]:
    """Retrieve from in-memory lexical index (single-pass retrieval model)."""

    cache_key = f"contract|{contract_id}|{obligation['id']}"
    cached = _cache_get_entry(_RETRIEVAL_CACHE, cache_key, settings.rag_cache_ttl_sec)
    if cached is not None:
        return cached

    index = _get_contract_evidence_index(contract_id)
    chunks = index.get("chunks", [])
    inv = index.get("inv", {})
    if not chunks or not inv:
        return []

    keys = _obligation_keywords(obligation)
    key_set = set(keys)
    anchor_set = _obligation_anchor_terms(obligation)
    candidate_ids: set[int] = set()
    for k in keys:
        candidate_ids.update(inv.get(k, set()))
    for a in anchor_set:
        candidate_ids.update(inv.get(a, set()))
    if not candidate_ids:
        candidate_ids = set(range(min(len(chunks), 120)))

    candidates: list[dict[str, Any]] = []
    for idx in candidate_ids:
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = chunks[idx]
        text = chunk["text"]
        token_set = chunk.get("token_set", set())
        overlap = len(token_set & key_set)
        anchor_hits = len(token_set & anchor_set)
        toc_penalty = 0.8 if _is_toc_like(text) else 0.0
        candidates.append(
            {
                "text": text,
                "page": int(chunk.get("page", 0) or 0),
                "document_id": str(chunk.get("document_id", contract_id)),
                "node_id": str(chunk.get("node_id", "")),
                "score": float(overlap + anchor_hits * 1.3 - toc_penalty),
                "kw_score": _keyword_overlap_score(text, obligation),
            }
        )

    # Precision fallback: if index matches are weak, scan whole indexed contract once.
    if len(candidates) < 8:
        for chunk in chunks[:400]:
            text = chunk["text"]
            if _is_toc_like(text):
                continue
            token_set = chunk.get("token_set", set())
            overlap = len(token_set & key_set)
            anchor_hits = len(token_set & anchor_set)
            if overlap <= 0 and anchor_hits <= 0:
                continue
            candidates.append(
                {
                    "text": text,
                    "page": int(chunk.get("page", 0) or 0),
                    "document_id": str(chunk.get("document_id", contract_id)),
                    "node_id": str(chunk.get("node_id", "")),
                    "score": float(overlap + anchor_hits * 1.2),
                    "kw_score": _keyword_overlap_score(text, obligation),
                }
            )

    # Hybrid lexical rank from index (no repeated vector DB round-trips).
    candidates.sort(key=lambda c: (c["score"] * 0.7 + c["kw_score"] * 0.3, -c["page"]), reverse=True)
    selected = candidates[:6]
    if len(selected) < 4:
        local_fallback = _local_contract_fallback_chunks(contract_id, obligation, max_chunks=3)
        for item in local_fallback:
            if any(c["text"] == item["text"] and c["page"] == item["page"] for c in selected):
                continue
            selected.append(item)
            if len(selected) >= 6:
                break
    final_selected = selected[:6]
    _cache_set_entry(_RETRIEVAL_CACHE, cache_key, final_selected)
    return final_selected


def _is_dora_metadata(metadata: dict[str, Any]) -> bool:
    doc_type = str(metadata.get("doc_type", "")).lower()
    document_id = str(metadata.get("document_id", ""))
    return doc_type == "dora" or document_id.startswith("DORA-")


async def _retrieve_dora_chunks(
    citation_engine: BaseQueryEngine,
    obligation: dict,
) -> list[dict[str, Any]]:
    cache_key = f"dora|{obligation['id']}"
    cached = _cache_get_entry(_RETRIEVAL_CACHE, cache_key, settings.rag_cache_ttl_sec)
    if cached is not None:
        return cached

    # Local lightweight reference avoids one vector query per obligation.
    selected = [
        {
            "text": f"{obligation.get('text', '')} Pass criteria: {obligation.get('pass_criteria', '')[:220]}".strip(),
            "page": 0,
            "document_id": "DORA-2022-2554-EN",
            "node_id": f"dora-ref-{obligation['id']}",
            "score": 1.0,
        }
    ]
    _cache_set_entry(_RETRIEVAL_CACHE, cache_key, selected)
    return selected


async def _retrieve_evidence_lanes(
    citation_engine: BaseQueryEngine,
    contract_id: str,
    obligation: dict,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contract_task = _retrieve_contract_chunks(citation_engine, contract_id, obligation)
    dora_task = _retrieve_dora_chunks(citation_engine, obligation)
    contract_chunks, dora_chunks = await asyncio.gather(contract_task, dora_task)
    return contract_chunks, dora_chunks


def _apply_evidence_guardrails(
    contract_chunks: list[dict[str, Any]],
    dora_chunks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # Contract evidence is mandatory for deterministic verdicts.
    filtered_contract = contract_chunks[:_CONTRACT_CONTEXT_TARGET]
    filtered_contract = _ensure_page_diversity(filtered_contract)
    filtered_dora = dora_chunks[: max(1, _TOTAL_CONTEXT_LIMIT - len(filtered_contract))]
    return filtered_contract, filtered_dora


def _ensure_page_diversity(contract_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not contract_chunks:
        return []
    primary_page = contract_chunks[0].get("page", 0)
    diversified = [contract_chunks[0]]
    for chunk in contract_chunks[1:]:
        if len(diversified) >= _CONTRACT_CONTEXT_TARGET:
            break
        if chunk.get("page", 0) != primary_page:
            diversified.append(chunk)
    for chunk in contract_chunks[1:]:
        if len(diversified) >= _CONTRACT_CONTEXT_TARGET:
            break
        if chunk not in diversified:
            diversified.append(chunk)
    return diversified


def _is_evidence_insufficient(contract_chunks: list[dict[str, Any]]) -> bool:
    if len(contract_chunks) < _MIN_CONTRACT_EVIDENCE:
        return True
    pages = {int(c.get("page", 0) or 0) for c in contract_chunks if int(c.get("page", 0) or 0) > 0}
    return len(pages) < _MIN_CONTRACT_PAGES


def _render_context_block(contract_chunks: list[dict[str, Any]], dora_chunks: list[dict[str, Any]]) -> str:
    if not contract_chunks and not dora_chunks:
        return ""
    lines: list[str] = []
    for i, chunk in enumerate(contract_chunks, start=1):
        snippet = chunk["text"].strip().replace("\n", " ")
        lines.append(
            f"[Contract Excerpt {i}] page={chunk['page']} node_id={chunk['node_id']}\n"
            f"{snippet[:320]}"
        )
    for i, chunk in enumerate(dora_chunks, start=1):
        snippet = chunk["text"].strip().replace("\n", " ")
        lines.append(
            f"[DORA Reference {i}] page={chunk['page']} node_id={chunk['node_id']}\n"
            f"{snippet[:220]}"
        )
    return "\n\n".join(lines)


def _build_obligation_batches(obligations: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size <= 1:
        return [[ob] for ob in obligations]
    sorted_obs = sorted(obligations, key=lambda ob: str(ob.get("paragraph", "")))
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for ob in sorted_obs:
        if not current:
            current = [ob]
            continue
        same_group = str(current[0].get("paragraph", ""))[:1] == str(ob.get("paragraph", ""))[:1]
        if same_group and len(current) < batch_size:
            current.append(ob)
        else:
            batches.append(current)
            current = [ob]
    if current:
        batches.append(current)
    return batches


async def _evaluate_batch(
    llm: LLM,
    citation_engine: BaseQueryEngine,
    obligations: list[dict[str, Any]],
    contract_id: str,
    contract_text_preview: str,
) -> list[ObligationFinding]:
    if len(obligations) <= 1:
        return [await _evaluate_one(llm, citation_engine, obligations[0], contract_id, contract_text_preview)]

    prepared: list[tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]] = []
    fallback: list[ObligationFinding] = []
    for ob in obligations:
        contract_chunks, dora_chunks = await _retrieve_evidence_lanes(citation_engine, contract_id, ob)
        contract_chunks, dora_chunks = _apply_evidence_guardrails(contract_chunks, dora_chunks)
        if _is_evidence_insufficient(contract_chunks):
            fallback.append(
                ObligationFinding(
                    obligation_id=ob["id"],
                    article=ob["article"],
                    paragraph=ob["paragraph"],
                    description=ob["text"],
                    verdict=Verdict.UNKNOWN,
                    rationale="Insufficient contract-grounded evidence to assess this obligation reliably.",
                    evidence_spans=[],
                    gap_description="",
                    risk_level="medium",
                )
            )
            continue
        prepared.append((ob, contract_chunks, dora_chunks))

    if not prepared:
        return fallback

    payload = []
    for ob, contract_chunks, dora_chunks in prepared:
        payload.append(
            {
                "obligation_id": ob["id"],
                "article": ob["article"],
                "paragraph": ob["paragraph"],
                "text": ob["text"],
                "pass_criteria": (ob.get("pass_criteria") or "")[:200],
                "contract_evidence": contract_chunks[:3],
                "dora_reference": dora_chunks[:1],
            }
        )
    user_msg = (
        f"Contract ID: {contract_id}\n"
        f"Contract preview: {(contract_text_preview or '')[:1200]}\n\n"
        f"Obligations with evidence JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    resp = await chat_with_retry(
        llm,
        [ChatMessage(role="system", content=_BATCH_SYSTEM), ChatMessage(role="user", content=user_msg)],
    )
    raw = resp.message.content.strip()
    try:
        parsed = _parse_verdict_json(raw)
        items = parsed.get("results", [])
    except Exception:
        # fallback to per-obligation calls if model output is malformed
        return fallback + [
            await _evaluate_one(llm, citation_engine, ob, contract_id, contract_text_preview) for ob, _, _ in prepared
        ]

    by_id: dict[str, dict[str, Any]] = {str(item.get("obligation_id", "")): item for item in items if item}
    findings: list[ObligationFinding] = []
    for ob, contract_chunks, _ in prepared:
        data = by_id.get(ob["id"], {})
        try:
            verdict = Verdict(str(data.get("verdict", "unknown")))
        except ValueError:
            verdict = Verdict.UNKNOWN
        findings.append(
            ObligationFinding(
                obligation_id=ob["id"],
                article=ob["article"],
                paragraph=ob["paragraph"],
                description=ob["text"],
                verdict=verdict,
                rationale=str(data.get("rationale", "")),
                evidence_spans=_build_evidence_spans(
                    evidence_quotes=data.get("evidence_quotes", []),
                    retrieved_chunks=contract_chunks,
                    contract_id=contract_id,
                ),
                gap_description=str(data.get("gap_description", "")),
                risk_level=str(data.get("risk_level", "medium")),
            )
        )
    return fallback + findings


def _obligation_keywords(obligation: dict) -> list[str]:
    text = f"{obligation.get('text', '')} {obligation.get('pass_criteria', '')}".lower()
    tokens = re.findall(r"[a-z0-9]{4,}", text)
    stop = {
        "shall",
        "must",
        "with",
        "from",
        "that",
        "this",
        "their",
        "under",
        "into",
        "where",
        "article",
        "paragraph",
    }
    uniq: list[str] = []
    for t in tokens:
        if t in stop or t.isdigit():
            continue
        if t not in uniq:
            uniq.append(t)
    return uniq[:20]


def _local_contract_fallback_chunks(contract_id: str, obligation: dict, max_chunks: int = 3) -> list[dict[str, Any]]:
    path = get_contract_pdf_path(contract_id)
    if not path:
        return []
    try:
        pages = parse_pdf(path.read_bytes(), None)
    except Exception:
        return []

    keywords = _obligation_keywords(obligation)
    if not keywords:
        return []

    scored: list[dict[str, Any]] = []
    for p in pages:
        page_no = int(p.get("page", 0) or 0)
        text = p.get("text", "")
        if not text:
            continue
        snippets = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
        for snippet in snippets:
            s = snippet.strip()
            if len(s) < 40:
                continue
            sl = s.lower()
            score = sum(1 for k in keywords if k in sl)
            if score <= 0:
                continue
            scored.append(
                {
                    "text": s[:650],
                    "page": page_no,
                    "document_id": contract_id,
                    "node_id": f"local-{contract_id}-p{page_no}",
                    "score": float(score),
                }
            )

    scored.sort(key=lambda c: (c["score"], -c["page"]), reverse=True)
    return scored[:max_chunks]


def _build_evidence_spans(
    evidence_quotes: list[str],
    retrieved_chunks: list[dict[str, Any]],
    contract_id: str,
) -> list[EvidenceSpan]:
    spans: list[EvidenceSpan] = []
    for raw_quote in evidence_quotes:
        quote = (raw_quote or "").strip()
        if not quote:
            continue

        selected = None
        quote_l = quote.lower()
        for chunk in retrieved_chunks:
            if quote_l in chunk["text"].lower() or chunk["text"].lower()[:120] in quote_l:
                selected = chunk
                break
        if selected is None and retrieved_chunks:
            selected = retrieved_chunks[0]

        spans.append(
            EvidenceSpan(
                text=quote,
                page=selected["page"] if selected else 0,
                document_id=selected["document_id"] if selected else contract_id,
                node_id=selected["node_id"] if selected else "",
            )
        )
    return spans


async def stream_gap_analysis(
    llm: LLM,
    citation_engine: BaseQueryEngine,
    contract_id: str,
    contract_text_preview: str,
    obligation_ids: list[str] | None = None,
    fast_mode: bool = False,
    concurrency: int | None = None,
    batch_size: int | None = None,
):
    """Async generator that yields ObligationFinding as each evaluation completes.

    Uses a semaphore to cap concurrency at _CONCURRENCY simultaneous calls.
    Uses contract-grounded retrieval + optional text preview fallback.
    """
    obligations = _load_obligations()
    if obligation_ids:
        obligations = [o for o in obligations if o["id"] in obligation_ids]
    else:
        obligations = _prefilter_obligations(
            obligations,
            contract_text_preview,
            enabled=settings.obligation_prefilter_enabled,
            fast_mode=fast_mode,
        )

    log.info("gap_analysis_start", obligations=len(obligations), contract_id=contract_id)
    effective_concurrency = concurrency or settings.gap_concurrency
    effective_batch_size = batch_size or settings.gap_batch_size
    sem = asyncio.Semaphore(effective_concurrency)
    batches = _build_obligation_batches(obligations, effective_batch_size)

    async def eval_with_sem(batch: list[dict]) -> list[ObligationFinding]:
        async with sem:
            return await _evaluate_batch(llm, citation_engine, batch, contract_id, contract_text_preview)

    tasks = [asyncio.create_task(eval_with_sem(batch)) for batch in batches]

    for coro in asyncio.as_completed(tasks):
        try:
            finding_batch = await coro
            for finding in finding_batch:
                yield finding
        except Exception as exc:
            log.warning("gap_finding_failed", error=str(exc)[:120])

    log.info("gap_analysis_complete", contract_id=contract_id)


# Kept for backward compat (scripts/test_pipeline.py etc.)
async def run_gap_analysis(
    llm: LLM,
    citation_engine: BaseQueryEngine,
    contract_id: str,
    contract_text_preview: str,
    obligation_ids: list[str] | None = None,
    fast_mode: bool = False,
    concurrency: int | None = None,
    batch_size: int | None = None,
) -> list[ObligationFinding]:
    findings: list[ObligationFinding] = []
    async for f in stream_gap_analysis(
        llm, citation_engine, contract_id, contract_text_preview, obligation_ids, fast_mode, concurrency, batch_size
    ):
        findings.append(f)
    return findings
