import pytest
from app.services.graph.relation_analyzer import RelationAnalyzer

@pytest.mark.asyncio
async def test_relation_analyzer_alias_resolution(mocker):
    # Mock AsyncGraphDatabase driver and session
    mock_driver = mocker.MagicMock()
    mock_session = mocker.MagicMock()
    
    # Mock session run return value
    mock_result = mocker.MagicMock()
    
    # We mock record to return a path
    mock_record = {"path": ["Nguyễn Huệ", "Bắc Bình Vương", "nhà Tây Sơn"]}
    
    async def mock_single():
        return mock_record
    mock_result.single = mock_single
    
    async def mock_run(query, source, target):
        # Verify query checks aliases
        assert "s.aliases" in query
        assert "t.aliases" in query
        return mock_result
    
    mock_session.run = mock_run
    
    # Set up session context manager using standard MagicMock
    mock_session_context = mocker.MagicMock()
    async def mock_enter(self=None):
        return mock_session
    async def mock_exit(self=None, exc_type=None, exc_val=None, exc_tb=None):
        pass
        
    mock_session_context.__aenter__ = mock_enter
    mock_session_context.__aexit__ = mock_exit
    
    mock_driver.session.return_value = mock_session_context
    
    # Inject mock driver
    mocker.patch("app.services.graph.relation_analyzer.AsyncGraphDatabase.driver", return_value=mock_driver)
    
    analyzer = RelationAnalyzer()
    path = await analyzer.find_connection("Quang Trung", "Tây Sơn")
    
    assert path == ["Nguyễn Huệ", "Bắc Bình Vương", "nhà Tây Sơn"]
