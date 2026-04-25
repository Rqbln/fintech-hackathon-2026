from unittest.mock import patch, AsyncMock, MagicMock
import pytest


@pytest.mark.asyncio
@patch("app.agents.extractor.upload_document", new_callable=AsyncMock)
@patch("app.agents.extractor.extract_from_bytes")
@patch("app.agents.extractor.get_or_create_corpus")
@patch("app.agents.extractor.upload_text_to_corpus")
async def test_extractor_returns_vendor_document(
    mock_upload_text, mock_get_corpus, mock_docai, mock_gcs_upload
):
    mock_gcs_upload.return_value = "gs://bucket/uploads/test.pdf"
    mock_docai.return_value = {
        "total_pages": 2,
        "pages_text": [
            {"page": 1, "text": "Article 1. Cloud services scope."},
            {"page": 2, "text": "Article 2. RTO shall be 4 hours maximum."},
        ],
        "tables": [],
    }
    mock_get_corpus.return_value = "projects/p/locations/europe-west1/ragCorpora/123"
    mock_upload_text.return_value = "projects/p/.../ragFiles/abc"

    from app.agents.extractor import ExtractorAgent
    result = await ExtractorAgent().extract(b"%PDF-fake", "aws_contract.pdf", "AWS")

    assert result.vendor_name == "AWS"
    assert result.filename == "aws_contract.pdf"
    assert len(result.clauses) >= 1
    assert any(c.category == "rto_rpo" for c in result.clauses)
    mock_upload_text.assert_called_once()
