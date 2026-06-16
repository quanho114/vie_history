import asyncio
from app.core.database import async_session
from app.models.document import Document
from sqlalchemy import select

async def main():
    async with async_session() as session:
        result = await session.execute(select(Document))
        docs = result.scalars().all()
        print(f"Total documents in SQL DB: {len(docs)}")
        for doc in docs:
            print(f"- {doc.title} (dynasty: {doc.dynasty}, region: {doc.geographical_region})")

if __name__ == "__main__":
    asyncio.run(main())
