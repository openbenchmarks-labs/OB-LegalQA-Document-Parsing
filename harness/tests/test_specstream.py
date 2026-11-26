"""Offline tests for the SpecStream Extract adapter."""
from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness.adapters import specstream
from harness.pricing import cost_of_parse
from harness.tool_registry import TOOLS


def test_specstream_registered_in_tools():
    assert "specstream" in TOOLS
    tool = TOOLS["specstream"]
    assert tool.vendor == "SpecStream"
    assert tool.tracked_changes_opt_in is False
    assert tool.settings["format"] == "markdown"


def test_specstream_parse_unwraps_data_and_reports_vendor_cost(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SPECSTREAM_API_KEY", "ss_live_test_secret")
    pdf_bytes = b"%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n2 0 obj << /Type /Page >> endobj\n%%EOF"
    pdf_path = tmp_path / "contract.pdf"
    pdf_path.write_bytes(pdf_bytes)

    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {"content-type": "application/json"}
        resp.json.return_value = {
            "data": {
                "request_id": "req_123",
                "took_ms": 140,
                "price_usd": 0.0008,
                "results": [
                    {
                        "url": "https://local.invalid/contract.pdf",
                        "status": "ok",
                        "read_from": "pdf",
                        "text": "Payment due within ~~30~~ 45 days.",
                        "full_text": "Section 1. Payment due within ~~30~~ 45 days.",
                    }
                ],
            }
        }
        return resp

    with patch("httpx.post", side_effect=fake_post):
        md, meta = specstream.parse(pdf_path, TOOLS["specstream"].settings)

    assert captured["url"] == specstream.URL
    assert captured["headers"]["Authorization"] == "Bearer ss_live_test_secret"
    assert base64.b64decode(captured["body"]["pages"][0]["pdf_b64"]) == pdf_bytes
    assert md == "Section 1. Payment due within ~~30~~ 45 days."
    assert meta["n_pages"] == 2
    assert meta["io"]["request"]["headers"]["Authorization"] == "<redacted>"
    assert "ss_live_test_secret" not in str(meta)

    cost = cost_of_parse("specstream", meta)
    assert cost["basis"] == "vendor cost"
    assert cost["usd"] == pytest.approx(0.0008)
