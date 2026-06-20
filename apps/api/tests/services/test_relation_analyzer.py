import pytest
from app.services.graph.relation_analyzer import RelationAnalyzer

@pytest.mark.asyncio
async def test_neo4j_multihop():
    analyzer = RelationAnalyzer()
    
    # Pre-populate test nodes and relationship to make test robust and self-contained
    async with analyzer.driver.session() as session:
        # Create source node, target node and relationship
        await session.run(
            "MERGE (s:Person {name: $source}) "
            "MERGE (t:Event {name: $target}) "
            "MERGE (s)-[:PARTICIPATED_IN]->(t)",
            source="Nhà Trần", target="Trận Bạch Đằng 1288"
        )
        
    try:
        path = await analyzer.find_connection("Nhà Trần", "Trận Bạch Đằng 1288")
        assert len(path) > 0
        assert "Nhà Trần" in path
        assert "Trận Bạch Đằng 1288" in path
    finally:
        # Clean up test nodes and relationship
        async with analyzer.driver.session() as session:
            await session.run(
                "MATCH (s {name: $source}) DETACH DELETE s",
                source="Nhà Trần"
            )
            await session.run(
                "MATCH (t {name: $target}) DETACH DELETE t",
                target="Trận Bạch Đằng 1288"
            )
        await analyzer.close()
