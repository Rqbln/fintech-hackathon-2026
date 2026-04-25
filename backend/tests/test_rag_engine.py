from unittest.mock import patch, MagicMock


@patch("app.services.rag_engine.rag")
@patch("app.services.rag_engine.vertexai")
def test_get_or_create_corpus_creates_new_when_absent(mock_vertexai, mock_rag):
    mock_rag.list_corpora.return_value = []
    mock_corpus = MagicMock()
    mock_corpus.name = "projects/p/locations/europe-west1/ragCorpora/123"
    mock_rag.create_corpus.return_value = mock_corpus

    from app.services.rag_engine import get_or_create_corpus
    result = get_or_create_corpus()

    mock_rag.create_corpus.assert_called_once()
    assert result == mock_corpus.name


@patch("app.services.rag_engine.rag")
@patch("app.services.rag_engine.vertexai")
def test_get_or_create_corpus_returns_existing(mock_vertexai, mock_rag):
    existing = MagicMock()
    existing.display_name = "regagent-corpus-v1"
    existing.name = "projects/p/locations/europe-west1/ragCorpora/456"
    mock_rag.list_corpora.return_value = [existing]

    from app.services.rag_engine import get_or_create_corpus
    result = get_or_create_corpus()

    mock_rag.create_corpus.assert_not_called()
    assert result == existing.name


@patch("app.services.rag_engine.rag")
@patch("app.services.rag_engine.vertexai")
def test_upload_text_to_corpus_calls_rag_upload(mock_vertexai, mock_rag):
    mock_rag_file = MagicMock()
    mock_rag_file.name = "projects/p/locations/europe-west1/ragCorpora/123/ragFiles/abc"
    mock_rag.upload_file.return_value = mock_rag_file

    from app.services.rag_engine import upload_text_to_corpus
    result = upload_text_to_corpus(
        corpus_name="projects/p/locations/europe-west1/ragCorpora/123",
        text="Article 1. Test clause about RTO.",
        display_name="test_contract",
    )

    mock_rag.upload_file.assert_called_once()
    call_kw = mock_rag.upload_file.call_args.kwargs
    assert call_kw["corpus_name"] == "projects/p/locations/europe-west1/ragCorpora/123"
    assert call_kw["display_name"] == "test_contract"
    assert result == mock_rag_file.name


@patch("app.services.rag_engine.rag")
@patch("app.services.rag_engine.vertexai")
def test_query_corpus_returns_list_of_dicts(mock_vertexai, mock_rag):
    ctx = MagicMock()
    ctx.text = "RTO shall not exceed 4 hours."
    ctx.source_uri = "gs://bucket/file.txt"
    ctx.score = 0.92
    mock_rag.retrieval_query.return_value.contexts.contexts = [ctx]

    from app.services.rag_engine import query_corpus
    results = query_corpus(
        "projects/p/locations/europe-west1/ragCorpora/123", "RTO requirements"
    )

    mock_rag.retrieval_query.assert_called_once()
    call_kw = mock_rag.retrieval_query.call_args.kwargs
    assert call_kw["rag_retrieval_config"] is not None
    assert len(results) == 1
    assert results[0]["text"] == "RTO shall not exceed 4 hours."
    assert results[0]["source"] == "gs://bucket/file.txt"
    assert results[0]["score"] == 0.92
