"""What a run costs, in one place, so a trace can show money next to a score.

Two bills arrive from a run and they are not comparable by eye: the parser is
billed per page, once per contract, and the reader is billed per token, once per
question. Many questions share one parse, so a tool that looks expensive
per page can be the cheap half of the case, and usually is.

Tool prices live in tools/<tool>.yaml. Where a tool reports what it charged,
its own number wins and the yaml price is only the fallback -- see cost_of_parse.
"""
from __future__ import annotations

from .tool_registry import TOOLS

# The date the tool prices in tools/*.yaml were last checked.
RATES_AS_OF = "2026-11-26"
# The GPT-6 reader and judge rates were added later than the tool prices.
LLM_RATES_AS_OF = "2026-09-29"


# USD per million tokens. `write` is the rate for tokens written into the prompt
# cache, which on the 5.6 family is charged *above* the plain input rate -- so a
# model that writes the cache and never reads it costs more than one with no
# cache at all. `long` applies to the whole request once input passes 272k
# tokens; our largest contract is ~50k, so it should never trigger here.
LLM_RATES = {
    "gpt-5.6-sol":   {"input": 4.00, "cached": 0.40, "write": 5.00, "output": 20.00},
    "gpt-5.6-terra": {"input": 2.00, "cached": 0.20, "write": 2.50, "output": 12.00},
    "gpt-5.6-luna":  {"input": 0.20, "cached": 0.02, "write": 0.25, "output": 1.20},
    "gpt-6-astra":   {"input": 10.00, "cached": 1.00, "write": 12.50, "output": 50.00},
    # Native OpenAI list prices, checked 2026-09-29. The default reader and judge:
    # gpt-6-sol is exactly half of gpt-5.6-sol on every line, and gpt-6-luna
    # exactly a fortieth.
    "gpt-6-sol":     {"input": 2.00, "cached": 0.20, "write": 2.50, "output": 10.00},
    "gpt-6-luna":    {"input": 0.10, "cached": 0.01, "write": 0.125, "output": 0.50},
    "gpt-5.1":       {"input": 1.25, "cached": 0.125, "write": None, "output": 10.00},
}
LONG_CONTEXT_TOKENS = 272_000


def cost_of_llm(model: str, usage: dict | None) -> dict:
    """USD for one call, split the way the rate card splits it.

    Cache writes are priced separately because they are priced separately: on
    the 5.6 family a model that writes the prompt cache and never reads it back
    pays a 25% surcharge over plain input for nothing. Keeping the line visible
    per call is how that stops being invisible.
    """
    rates = LLM_RATES.get(model)
    usage = usage or {}
    total_in = usage.get("input_tokens") or 0
    out = usage.get("output_tokens") or 0
    if not rates or not (total_in or out):
        return {"usd": None, "model": model, "priced": False}

    details = usage.get("input_tokens_details") or {}
    cached = details.get("cached_tokens") or 0
    written = details.get("cache_write_tokens") or 0
    fresh = max(total_in - cached - written, 0)

    if total_in > LONG_CONTEXT_TOKENS:
        # Long context repricing applies to the whole request, not the excess.
        return {"usd": None, "model": model, "priced": False,
                "note": "input above 272k; long-context rates not tabulated"}

    write_rate = rates["write"] if rates["write"] is not None else rates["input"]
    input_usd = (fresh * rates["input"] + cached * rates["cached"]
                 + written * write_rate) / 1e6
    output_usd = out * rates["output"] / 1e6
    return {
        "usd": round(input_usd + output_usd, 6),
        "input_usd": round(input_usd, 6),
        "output_usd": round(output_usd, 6),
        "tokens_fresh": fresh,
        "tokens_cached": cached,
        "tokens_written": written,
        "tokens_output": out,
        "model": model,
        "priced": True,
        "rates_as_of": LLM_RATES_AS_OF,
    }


def cost_of_parse(arm: str, meta: dict | None) -> dict:
    """USD for one document under one arm.

    Preference order is how much the number is worth doubting: a cost the vendor
    stated in money, then one it stated in its own credits, then our rate card
    against tokens it counted, then our rate card against a page count.
    """
    meta = meta or {}
    pricing = TOOLS[arm].pricing if arm in TOOLS else {}
    pages = meta.get("n_pages") or 0
    credits = meta.get("credits") or 0
    breakdown = meta.get("cost_cents")
    cents = breakdown.get("final_cost_cents") or 0 if isinstance(breakdown, dict) else 0

    if cents:
        return {"usd": round(cents / 100, 6), "basis": "vendor cost", "pages": pages,
                "credits": credits or None, "rates_as_of": RATES_AS_OF}
    if credits and "usd_per_credit" in pricing:
        return {"usd": round(credits * pricing["usd_per_credit"], 6),
                "basis": "vendor credits", "pages": pages, "credits": credits,
                "rates_as_of": RATES_AS_OF}
    if "usd_per_million_tokens" in pricing:
        # Ranked here, above the per-page card, because the tokens are measured
        # off the response the same way a vendor's credits are -- only the rate
        # is ours. A frontier arm that returned no usage is unpriced rather than
        # billed at a page rate it does not have.
        rates = pricing["usd_per_million_tokens"]
        usage = meta.get("usage") or {}
        tokens_in = usage.get("input_tokens") or 0
        tokens_out = usage.get("output_tokens") or 0
        if not (tokens_in or tokens_out):
            return {"usd": None, "basis": "unknown", "pages": pages,
                    "note": "frontier arm returned no token usage"}
        usd = (tokens_in * rates["input"] + tokens_out * rates["output"]) / 1e6
        return {"usd": round(usd, 6), "basis": "token rate card", "pages": pages,
                "tokens_input": tokens_in, "tokens_output": tokens_out,
                "credits": None, "rates_as_of": RATES_AS_OF}
    if pages and "usd_per_page" in pricing:
        return {"usd": round(pages * pricing["usd_per_page"], 6), "basis": "rate card",
                "pages": pages, "credits": credits or None, "rates_as_of": RATES_AS_OF}
    return {"usd": 0.0 if meta.get("reference") else None,
            "basis": "reference arm" if meta.get("reference") else "unknown",
            "pages": pages, "credits": credits or None}
