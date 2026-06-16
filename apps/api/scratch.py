import asyncio
from app.services.retrieval.vector_search import VectorSearch

async def main():
    vs = VectorSearch()
    await vs.connect()
    # Just query anything to see the payload
    results = await vs.search([0.1]*768, top_k=1)
    if results:
        print(results[0]["payload"])

asyncio.run(main())
