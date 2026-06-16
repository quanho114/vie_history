#!/usr/bin/env python3
"""Seed an expanded development corpus spanning all Vietnamese historical eras."""

import argparse
import asyncio
import httpx

SEED_URLS = [
    # ── 1. Độc lập & Kháng chiến chống Pháp/Mỹ ──
    "https://vi.wikipedia.org/wiki/C%C3%A1ch_m%E1%BA%A1ng_Th%C3%A1ng_T%C3%A1m",
    "https://vi.wikipedia.org/wiki/Chi%E1%BA%BFn_d%E1%BB%8Bch_%C4%90i%E1%BB%87n_Bi%C3%AAn_Ph%E1%BB%A7",
    "https://vi.wikipedia.org/wiki/Hi%E1%BB%87p_%C4%91%E1%BB%8Bnh_Paris_1973",
    "https://vi.wikipedia.org/wiki/Chi%E1%BA%BFn_d%E1%BB%8Bch_H%E1%BB%93_Ch%C3%AD_Minh",
    "https://vi.wikipedia.org/wiki/Kh%C3%A1ng_chi%E1%BA%BFn_ch%C3%B4ng_M%E1%BB%B9",
    "https://vi.wikipedia.org/wiki/S%E1%BB%B1_ki%E1%BB%87n_30_th%C3%A1ng_4_n%C4%83m_1975",
    "https://vi.wikipedia.org/wiki/Chi%E1%BA%BFn_tranh_Vi%E1%BB%87t_Nam",
    "https://vi.wikipedia.org/wiki/Hi%E1%BB%87p_%C4%91%E1%BB%8Bnh_Gen%C3%A8ve_1954",
    "https://vi.wikipedia.org/wiki/S%E1%BB%B1_ki%E1%BB%87n_T%E1%BA%BFt_M%E1%BA%ADu_Th%C3%A2n",

    # ── 2. Các triều đại Phong kiến & Độc lập cổ đại ──
    "https://vi.wikipedia.org/wiki/Hai_B%C3%A0_Tr%C6%B0ng",
    "https://vi.wikipedia.org/wiki/Ng%C3%B4_Quy%E1%BB%81n",
    "https://vi.wikipedia.org/wiki/Tr%E1%BA%ADn_B%E1%BA%A1ch_%C4%90%E1%BA%B1ng,_938",
    "https://vi.wikipedia.org/wiki/Kh%C3%A1ng_chi%E1%BA%BFn_ch%C3%B4ng_qu%C3%A2n_x%C3%A2m_l%C6%B0%E1%BB%A3c_M%C3%B4ng-Nguy%C3%AAn",
    "https://vi.wikipedia.org/wiki/L%C3%AA_Th%C3%A1i_T%E1%BB%95",
    "https://vi.wikipedia.org/wiki/Kh%E1%BB%9Fi_ngh%C4%A9a_Lam_S%C6%A1n",
    "https://vi.wikipedia.org/wiki/Quang_Trung",
    "https://vi.wikipedia.org/wiki/Tr%E1%BA%ADn_Ng%E1%BB%8Dc_H%E1%BB%93i_-_%C4%90%E1%BB%91ng_%C4%90a",
    "https://vi.wikipedia.org/wiki/Chi%E1%BA%BFn_tranh_Tr%E1%BB%8Bnh_-_Nguy%E1%BB%85n",
    "https://vi.wikipedia.org/wiki/Nh%C3%A0_Nguy%E1%BB%85n",

    # ── 3. Thuộc địa & Phong trào Yêu nước đầu TK 20 ──
    "https://vi.wikipedia.org/wiki/H%C3%A0m_Nghi",
    "https://vi.wikipedia.org/wiki/Phong_tr%C3%A0o_C%E1%BA%A7n_V%C6%B0%C6%A1ng",
    "https://vi.wikipedia.org/wiki/X%C3%B4_Vi%E1%BA%BFt_Ngh%E1%BB%87_T%C4%A9nh",
    "https://vi.wikipedia.org/wiki/Phong_tr%C3%A0o_%C4%90%E1%BB%93ng_kh%E1%BB%9Fi",

    # ── 4. Lãnh đạo lịch sử chủ chốt ──
    "https://vi.wikipedia.org/wiki/H%E1%BB%93_Ch%C3%AD_Minh",
    "https://vi.wikipedia.org/wiki/V%C3%B5_Nguy%C3%AAn_Gi%C3%A1p",
    "https://vi.wikipedia.org/wiki/Tr%C6%B0%E1%BB%9Dng_Chinh",
    "https://vi.wikipedia.org/wiki/L%C3%AA_Du%E1%BB%83n",

    # ── 5. Lịch sử hiện đại ──
    "https://vi.wikipedia.org/wiki/%C4%90%E1%BB%95i_M%E1%BB%9Bi",
    "https://vi.wikipedia.org/wiki/L%E1%BB%8Bch_s%E1%BB%AD_Vi%E1%BB%87t_Nam"
]

async def seed(api_base: str, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=120) as client:
        for i, url in enumerate(SEED_URLS, 1):
            print(f"[{i}/{len(SEED_URLS)}] Ingesting {url}...")
            try:
                response = await client.post(
                    f"{api_base.rstrip('/')}/api/v1/ingest/url",
                    json={"url": url, "tags": ["expanded_seed"]},
                    headers=headers,
                )
                response.raise_for_status()
                print(f"  ✓ Success: {response.json().get('status', 'OK')}")
            except Exception as exc:
                print(f"  ✗ Failed to ingest {url}: {exc}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed expanded Vietnamese history corpus")
    parser.add_argument("--api-base", default="http://localhost:12701")
    parser.add_argument("--token", required=True, help="Access token for authorization")
    args = parser.parse_args()
    asyncio.run(seed(api_base=args.api_base, token=args.token))

if __name__ == "__main__":
    main()
