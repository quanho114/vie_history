import asyncio
from app.services.retrieval.query_service import QueryService

async def main():
    qs = QueryService()
    try:
        res = await qs.hybrid_search(query="Hồ Chí Minh", top_k=3)
        print("Success! Results count:", len(res))
        for r in res:
            print("- title:", r.get("document_title"))
            print("  score:", r.get("score"))
            print("  content:", r.get("content")[:100])
    except Exception as e:
        print("Error during hybrid search:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
