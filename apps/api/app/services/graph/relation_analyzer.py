from neo4j import AsyncGraphDatabase
from app.core.config import settings

class RelationAnalyzer:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URL,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    async def find_connection(self, source: str, target: str) -> list:
        query = (
            "MATCH (s {name: $source}), (t {name: $target}), "
            "p = shortestPath((s)-[*..4]-(t)) "
            "RETURN [n in nodes(p) | n.name] as path"
        )
        async with self.driver.session() as session:
            result = await session.run(query, source=source, target=target)
            record = await result.single()
            return record["path"] if record else []

    async def close(self):
        await self.driver.close()
