from unittest.mock import patch, MagicMock


def _make_mock_doc(text: str) -> MagicMock:
    doc = MagicMock()
    doc.text = text
    seg = MagicMock()
    seg.start_index = 0
    seg.end_index = len(text)
    page = MagicMock()
    page.page_number = 1
    page.layout.text_anchor.text_segments = [seg]
    page.tables = []
    doc.pages = [page]
    return doc


@patch("app.services.document_ai.documentai.DocumentProcessorServiceClient")
def test_extract_from_bytes_returns_structure(MockClient):
    text = "Article 1. Scope of services.\n\nArticle 2. RTO is 4h."
    MockClient.return_value.process_document.return_value.document = _make_mock_doc(text)

    from app.services.document_ai import extract_from_bytes
    result = extract_from_bytes(b"%PDF-fake")

    assert result["total_pages"] == 1
    assert result["pages_text"][0]["page"] == 1
    assert "Article 1" in result["pages_text"][0]["text"]
    assert isinstance(result["tables"], list)


@patch("app.services.document_ai.documentai.DocumentProcessorServiceClient")
def test_extract_from_bytes_parses_tables(MockClient):
    text = "RTO | 4h\nRPO | 1h"
    doc = _make_mock_doc(text)

    def make_cell(start, end):
        seg = MagicMock()
        seg.start_index = start
        seg.end_index = end
        cell = MagicMock()
        cell.layout.text_anchor.text_segments = [seg]
        return cell

    header_row = MagicMock()
    header_row.cells = [make_cell(0, 3), make_cell(6, 8)]  # "RTO", "4h"
    table = MagicMock()
    table.header_rows = [header_row]
    table.body_rows = []
    doc.pages[0].tables = [table]
    MockClient.return_value.process_document.return_value.document = doc

    from app.services.document_ai import extract_from_bytes
    result = extract_from_bytes(b"%PDF-fake")

    assert len(result["tables"]) == 1
    assert result["tables"][0]["headers"] == ["RTO", "4h"]
    assert result["tables"][0]["page"] == 1
