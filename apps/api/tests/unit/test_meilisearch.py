import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.retrieval.meilisearch_bm25 import MeilisearchBM25

@pytest.fixture
def mock_meili_client():
    with patch("app.services.retrieval.meilisearch_bm25.AsyncClient") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        # Setup async methods
        mock_instance.get_index = AsyncMock()
        mock_instance.create_index = AsyncMock()
        
        # Index client mock
        mock_index = MagicMock()
        mock_index.update_filterable_attributes = AsyncMock()
        mock_index.update_searchable_attributes = AsyncMock()
        mock_index.update_synonyms = AsyncMock()
        mock_index.search = AsyncMock()
        mock_index.add_documents = AsyncMock()
        mock_index.delete_document = AsyncMock()
        mock_index.delete_documents_by_filter = AsyncMock()
        mock_index.get_stats = AsyncMock()
        
        mock_instance.index.return_value = mock_index
        yield mock_instance

@pytest.mark.asyncio
async def test_initialize_index_exists(mock_meili_client):
    service = MeilisearchBM25()
    
    # Simulate index already exists
    mock_meili_client.get_index.return_value = MagicMock()
    
    success = await service.initialize()
    assert success is True
    mock_meili_client.get_index.assert_called_once_with("historiai_chunks")
    mock_meili_client.create_index.assert_not_called()

@pytest.mark.asyncio
async def test_initialize_index_not_exists(mock_meili_client):
    service = MeilisearchBM25()
    
    # Simulate index does not exist (throws exception)
    mock_meili_client.get_index.side_effect = Exception("Not found")
    mock_meili_client.create_index.return_value = MagicMock()
    
    success = await service.initialize()
    assert success is True
    mock_meili_client.get_index.assert_called_once_with("historiai_chunks")
    mock_meili_client.create_index.assert_called_once_with("historiai_chunks", primary_key="chunk_id")

@pytest.mark.asyncio
async def test_search(mock_meili_client):
    service = MeilisearchBM25()
    
    # Mock search response
    mock_search_res = MagicMock()
    mock_search_res.hits = [
        {
            "chunk_id": "chunk_1",
            "content": "test content",
            "document_id": "doc_1",
            "document_title": "title_1",
            "section_title": "sec_1",
            "source_url": "http://test",
            "year": 1945,
            "quality_score": 0.9,
            "_rankingScore": 0.85,
            "_formatted": {
                "content": "test <em>content</em>"
            }
        }
    ]
    mock_meili_client.index.return_value.search.return_value = mock_search_res
    
    results = await service.search("vietnam", top_k=5, filters={"document_id": "doc_1"})
    
    assert len(results) == 1
    assert results[0]["id"] == "chunk_1"
    assert results[0]["score"] == 0.85
    assert results[0]["highlight"] == ["test <em>content</em>"]

@pytest.mark.asyncio
async def test_index_chunk(mock_meili_client):
    service = MeilisearchBM25()
    
    chunk = {
        "id": "chunk_1",
        "document_id": "doc_1",
        "content": "test content",
        "year": 1945
    }
    
    success = await service.index_chunk(chunk)
    assert success is True
    mock_meili_client.index.return_value.add_documents.assert_called_once()

@pytest.mark.asyncio
async def test_index_chunks(mock_meili_client):
    service = MeilisearchBM25()
    
    chunks = [
        {"id": "chunk_1", "content": "c1"},
        {"id": "chunk_2", "content": "c2"}
    ]
    
    count = await service.index_chunks(chunks)
    assert count == 2
    mock_meili_client.index.return_value.add_documents.assert_called_once()
