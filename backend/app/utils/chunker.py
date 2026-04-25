import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

_LEGAL_SEPARATORS = [
    r"\n(?:Article|Section|Clause|Annexe|Annex|ARTICLE|SECTION)\s+\d+",
    r"\n\d+\.\d+\s",
    r"\n\d+\.\s",
    "\n\n",
    "\n",
    " ",
]

_CATEGORY_PATTERNS: dict[str, re.Pattern] = {
    "rto_rpo": re.compile(
        r"rto|rpo|recovery time|recovery point|continuité|continuity", re.I
    ),
    "audit_rights": re.compile(
        r"audit|inspection|droit de visite|right to audit|contrôle", re.I
    ),
    "data_residency": re.compile(
        r"résidence|residency|data location|stockage|localisation|hébergement|sovereign", re.I
    ),
    "subcontracting": re.compile(
        r"sous-traitant|subcontract|prestataire tiers|fourth party", re.I
    ),
    "incident_reporting": re.compile(
        r"incident|notification|signalement|reporting|alerte|breach", re.I
    ),
    "exit_strategy": re.compile(
        r"exit|sortie|résiliation|portabilité|transition|termination", re.I
    ),
}


def chunk_by_clause(
    pages_text: list[dict],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[dict]:
    """
    Split page-level text dicts into clause-aligned chunks.
    Each output chunk: {'chunk_id': str, 'text': str, 'page': int, 'category': str}
    """
    splitter = RecursiveCharacterTextSplitter(
        separators=_LEGAL_SEPARATORS,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        is_separator_regex=True,
    )
    chunks = []
    for page_data in pages_text:
        page_num = page_data["page"]
        text = page_data["text"].strip()
        if not text:
            continue
        for i, chunk_text in enumerate(splitter.split_text(text)):
            chunks.append({
                "chunk_id": f"p{page_num}_c{i}",
                "text": chunk_text,
                "page": page_num,
                "category": _classify(chunk_text),
            })
    return chunks


def _classify(text: str) -> str:
    for category, pattern in _CATEGORY_PATTERNS.items():
        if pattern.search(text):
            return category
    return "general"
