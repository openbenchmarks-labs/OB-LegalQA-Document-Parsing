# OB-LegalQA (Document Parsing)

Open, independent document processing benchmark: which document parsing APIs and frontier vision models keep tracked changes (redlines) in legal contracts intact well enough for a reader model to answer contract questions. Every tool parses the same redlined contracts, the same reader model answers the same questions from each parse, and the same judge grades every answer. Tools measured: Datalab, Extend, LlamaParse, Mistral OCR, Pulse, Reducto, Unstructured, GPT-6 Astra and Claude Fable 5.1.

**Live leaderboard:** [openbenchmarks.com/document-processing](https://openbenchmarks.com/document-processing) · **Public dataset:** [`openbenchmarks/OB-LegalQA-Document-Parsing`](https://huggingface.co/datasets/openbenchmarks/OB-LegalQA-Document-Parsing)

Published and maintained by **[OpenBenchmarks Labs](https://openbenchmarks.com)**.

## Methodology

In a redlined contract rendered to PDF, deleted clauses are only visual strikethroughs. A parser that drops strikethrough markup causes downstream models to read deleted terms as still binding (**stale**) or merge deleted and surviving clauses into one sentence (**fused**).

- **Two splits:** Tagged digital PDFs (`documents/*.pdf`) and scanned PDFs (`--split scanned`).
- **Fixed protocol:** Every parser runs on the same redlined contracts; the same reader model answers 95 contract questions from each parser's output.
- **Scoring:** `judge/grader.py` classifies each answer as `correct`, `stale`, `fused`, `other`, or `ambiguous` alongside a phrase-match audit check. `judge/board.py` computes downstream accuracy, gap closed (relative to oracle vs. blind parses), median parse time, cost per 1,000 pages, and cost per 1,000 correct answers.

## Tools evaluated

9 parsing tools (11 setups) configured in [`tools/`](tools/README.md):

`astra`, `datalab`, `extend`, `fable`, `llamaparse`, `mistral`, `pulse`, `reducto`, `unstructured`

## Dataset

No PDFs or question files are committed to this repository. Running `python -m harness.run init` downloads the 95 public questions and redlined contracts at a pinned revision from [`openbenchmarks/OB-LegalQA-Document-Parsing`](https://huggingface.co/datasets/openbenchmarks/OB-LegalQA-Document-Parsing) into `.openbench/redline-parsing/dataset/`.

See [`data/README.md`](data/README.md) for the downloaded file layout and schema.

## Repository structure

- [`data/`](data/README.md): Dataset download instructions and schema documentation (no PDFs or questions committed).
- [`harness/`](harness/README.md): CLI runner (`init`, `smoke`, `run`, `watch`, `derive-full-run`), dataset loader, and parser adapters.
- [`tools/`](tools/README.md): One `<tool>.yaml` config per parsing tool (9 tools, 11 setups).
- [`judge/`](judge/README.md): Answer classifier, phrase-match audit, and leaderboard report builder.
- [`benchmark.yaml`](benchmark.yaml): Benchmark contract, scope, and refresh cadence.
- [`AGENTS.md`](AGENTS.md): Entry guide for coding agents.

## Quick start

Run the offline test suite (no API keys required):

```sh
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest
```

To run against live APIs, copy `.env.example` to `.env`, add your keys, install vendor SDKs, download the dataset, and inspect the CLI:

```sh
cp .env.example .env
uv pip install -e ".[dev,vendors]"
.venv/bin/python -m harness.run init
.venv/bin/python -m harness.run --help
```

## Adding or updating a tool

1. Add or edit `tools/<tool>.yaml` (and add `harness/adapters/<tool>.py` plus its entry in `harness/tool_registry.py` if adding a new tool).
2. Run `.venv/bin/pytest`.
3. Open a pull request.

## Links

- [Live leaderboard](https://openbenchmarks.com/document-processing)
- [Hugging Face dataset](https://huggingface.co/datasets/openbenchmarks/OB-LegalQA-Document-Parsing)
- [`llms.txt`](https://openbenchmarks.com/llms.txt)

## Related benchmarks

- [OB-Inference-Microtasks](https://github.com/openbenchmarks-labs/OB-Inference-Microtasks): Serverless LLM inference latency and accuracy ([leaderboard](https://openbenchmarks.com/inference))
- [OB-Code-WebSearch](https://github.com/openbenchmarks-labs/OB-Code-WebSearch): Web search APIs for coding agents ([leaderboard](https://openbenchmarks.com/web-search-for-coding-agents))
- [OB-Voice-Latency](https://github.com/openbenchmarks-labs/OB-Voice-Latency): Real PSTN voice-agent latency ([leaderboard](https://openbenchmarks.com/voice-agent-latency))
- [All OpenBenchmarks leaderboards](https://openbenchmarks.com)

## License

MIT. See [LICENSE](LICENSE).
