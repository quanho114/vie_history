#!/usr/bin/env python3
"""Seed a minimal development corpus directly through the API."""

import argparse
import asyncio

import httpx


SEED_URLS = [
    "https://vi.wikipedia.org/wiki/C%C3%A1ch_m%E1%BA%A1ng_Th%C3%A1ng_T%C3%A1m",
    "https://vi.wikipedia.org/wiki/Chi%E1%BA%BFn_d%E1%BB%8Bch_%C4%90i%E1%BB%87n_Bi%C3%AAn_Ph%E1%BB%A7",
    "https://vi.wikipedia.org/wiki/Hi%E1%BB%87p_%C4%91%E1%BB%8Bnh_Paris_1973",
]


async def seed(api_base: str, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=120) as client:
        for url in SEED_URLS:
            response = await client.post(
                f"{api_base.rstrip('/')}/api/v1/ingest/url",
                json={"url": url, "tags": ["seed"]},
                headers=headers,
            )
            response.raise_for_status()
            print(response.json())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://localhost:12701")
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    asyncio.run(seed(api_base=args.api_base, token=args.token))


if __name__ == "__main__":
    main()
