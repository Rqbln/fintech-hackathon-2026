from app.utils.chunker import chunk_by_clause, _classify


def test_classify_rto_keywords():
    assert _classify("The RTO shall not exceed 4 hours") == "rto_rpo"
    assert _classify("RPO target is 1 hour maximum") == "rto_rpo"


def test_classify_audit_keywords():
    assert _classify("Right to audit the provider's premises annually") == "audit_rights"
    assert _classify("Le droit d'inspection s'exerce annuellement") == "audit_rights"


def test_classify_data_residency():
    assert _classify("Data residency must remain within EEA") == "data_residency"
    assert _classify("Localisation des données : France uniquement") == "data_residency"


def test_classify_general_fallback():
    assert _classify("Payment terms are net 30 days") == "general"


def test_chunk_preserves_page_numbers():
    pages = [
        {"page": 1, "text": "Article 1. Scope.\n\nThe provider shall deliver cloud services."},
        {"page": 2, "text": "Article 2. SLA.\n\nThe RTO shall be 4 hours."},
    ]
    chunks = chunk_by_clause(pages)
    assert all("page" in c and "chunk_id" in c and "category" in c for c in chunks)
    page2_chunks = [c for c in chunks if c["page"] == 2]
    assert any(c["category"] == "rto_rpo" for c in page2_chunks)


def test_empty_pages_are_skipped():
    pages = [{"page": 1, "text": "   "}, {"page": 2, "text": "Article 1. Content here."}]
    chunks = chunk_by_clause(pages)
    assert all(c["page"] == 2 for c in chunks)


def test_chunk_ids_are_unique():
    pages = [{"page": 1, "text": "word " * 400}]
    chunks = chunk_by_clause(pages, chunk_size=100, chunk_overlap=10)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
