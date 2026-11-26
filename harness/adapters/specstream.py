"""SpecStream Extract API over HTTP. Settings come from tools/specstream.yaml."""
from __future__ import annotations

import base64
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from ..vendor_errors import VendorError
from .common import exchange, redact

URL = "https://api.specstream.ai/v1/extract"
_PAGE_OBJ_RE = re.compile(rb"/Type\s*/Page(?![A-Za-z])")


def _count_pdf_pages(raw: bytes) -> int:
    """Estimate PDF page count without extra dependencies."""
    return max(1, len(_PAGE_OBJ_RE.findall(raw)))


def parse(pdf: Path, settings: dict) -> tuple[str, dict]:
    """SpecStream Extract API, one synchronous call per PDF document.

    Sends the PDF inline as base64 in `pages[0].pdf_b64` with `format` and
    `include` from settings. SpecStream marks redline deletions as `~~struck~~`
    by default with no tracked changes opt-in flag.
    """
    import httpx

    from ..llm_client import load_environment

    load_environment()
    api_key = os.environ.get("SPECSTREAM_API_KEY")
    if not api_key:
        raise RuntimeError("SPECSTREAM_API_KEY is required for specstream")

    raw = pdf.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    fmt = settings.get("format", "markdown")
    include = list(settings.get("include") or ["full_text"])
    body = {
        "pages": [{"pdf_b64": encoded, "url": f"https://local.invalid/{pdf.name}"}],
        "format": fmt,
        "include": include,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = httpx.post(URL, headers=headers, json=body, timeout=300)
    if response.status_code >= 400:
        raise VendorError(
            f"specstream {response.status_code}: {response.text[:400]}",
            status=response.status_code,
            arm="specstream",
        )

    payload = response.json()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    results = data.get("results") or []
    item = results[0] if results and isinstance(results[0], dict) else {}
    status = item.get("status")
    if status != "ok":
        raise VendorError(
            f"specstream extract status={status}: {item.get('error') or ''}",
            status=response.status_code,
            arm="specstream",
        )

    markdown = (item.get("full_text") or item.get("text") or "").strip()
    if not markdown:
        raise RuntimeError(f"specstream returned no markdown; keys={sorted(item)}")

    price_usd = data.get("price_usd")
    meta: dict = {
        "request_id": data.get("request_id"),
        "read_from": item.get("read_from"),
        "took_ms": data.get("took_ms"),
        "n_pages": _count_pdf_pages(raw),
        "parsed_at": datetime.now(timezone.utc).isoformat(),
    }
    if isinstance(price_usd, (int, float)) and price_usd > 0:
        meta["cost_cents"] = {"final_cost_cents": round(float(price_usd) * 100.0, 6)}

    meta["io"] = exchange(
        {
            "method": "POST",
            "url": URL,
            "headers": redact(headers),
            "body": {
                **body,
                "pages": [{"pdf_b64": f"<base64 {pdf.name}>", "url": body["pages"][0]["url"]}],
            },
        },
        {
            "status": response.status_code,
            "headers": dict(response.headers),
            "body": {
                "data": {
                    "request_id": data.get("request_id"),
                    "took_ms": data.get("took_ms"),
                    "price_usd": price_usd,
                    "results": [f"<1 pdf result, {len(markdown)} chars>"],
                }
            },
        },
    )
    return markdown, meta
