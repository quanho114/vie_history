#!/usr/bin/env python3
"""Bulk-ingest URLs through the public API."""

import argparse
import asyncio
from pathlib import Path

import httpx


async def ingest_urls(api_base: str, token: str, urls: list[str]) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=120) as client:
        for url in urls:
            response = await client.post(
                f"{api_base.rstrip('/')}/api/v1/ingest/url",
                json={"url": url},
                headers=headers,
            )
            response.raise_for_status()
            print(response.json())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url_file", type=Path)
    parser.add_argument("--api-base", default="http://localhost:12701")
    parser.add_argument("--token", required=True)
    args = parser.parse_args()

    urls = [
        line.strip()
        for line in args.url_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    asyncio.run(ingest_urls(api_base=args.api_base, token=args.token, urls=urls))


if __name__ == "__main__":
    main()
