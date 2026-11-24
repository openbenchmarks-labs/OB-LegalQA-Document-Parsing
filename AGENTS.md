# AGENTS.md — OB-LegalQA-Document-Parsing

Quick navigation guide for coding agents working in `OB-LegalQA-Document-Parsing`.

## Structure (Zero Overlap)

| Folder | Owns | Files |
|---|---|---|
| **`data/`** | Format of the public questions and contracts (downloaded, not committed) | `data/README.md` |
| **`harness/`** | Execution only: CLI runner, dataset loading, tool adapters and registry, reader, parse cache, costs | `harness/run.py`, `harness/runner.py`, `harness/parsing.py`, `harness/tool_registry.py`, `harness/adapters/<tool>.py`, `harness/pricing.py` |
| **`tools/`** | Tool setups & prices (one file per tool for clean PRs) | `tools/<tool>.yaml` (9 tools, 11 setups) |
| **`judge/`** | Grading only: judge prompt, answer buckets, board math | `judge/grader.py`, `judge/board.py` |

Benchmark order & win condition live at the root in `benchmark.yaml`.

## Commands

```sh
# Offline tests (no API keys)
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest
```

## Guidelines

- **Keep folders strictly separated:** Question format in `data/`; execution in `harness/`; per-tool setups and prices in `tools/<tool>.yaml`; grading in `judge/`.
- **Adding or tuning a tool:** Edit `tools/<tool>.yaml` (and `harness/adapters/<tool>.py` for a new tool), then run `pytest`.
- **Settings are part of the cache key:** change a setup's `settings` and every cached parse for that setup is redone. A different prompt or option is a different measurement and gets its own setup name.
- **No secrets or raw run logs in git:** Keep API keys in `.env` and run outputs in `runs/` (both gitignored).
- **Consistent terminology:** Use `tool`, `setup`, `question`, `ground truth`, `reader`, `judge`, `board`. On the CLI a setup or reference view is called an `arm`.
