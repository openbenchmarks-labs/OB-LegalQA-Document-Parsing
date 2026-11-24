# data

No PDFs or question files are committed to this folder.

## Public vs. held-out evaluation sets

- **Public split:** Hosted on Hugging Face at [`openbenchmarks/OB-LegalQA-Document-Parsing`](https://huggingface.co/datasets/openbenchmarks/OB-LegalQA-Document-Parsing). Run `python -m harness.run init` to download the pinned revision into `.openbench/redline-parsing/dataset/`.

## Files and schema

Files downloaded into `.openbench/redline-parsing/dataset/`:

| Path | Description |
|---|---|
| `data/eval.jsonl` | 95 questions, one JSON object per line (`question`, `answer`, `answer_detail`, `documents`, `pdf`, `pdf_scanned`, `match_correct`, `match_stale`, `match_fused`). |
| `documents/*.pdf` | Redlined contracts with tracked changes preserved as digital text layers. |
| `documents_scanned/*.pdf` | The same contracts rendered as scanned PDFs (`--split scanned`). |
| `views/<contract>.oracle.md` | Reference parse preserving struck text as `~~…~~`. |
| `views/<contract>.blind.md` | Reference parse with all edit markup removed. |

A **stale** answer treats deleted language as still binding; a **fused** answer reads deleted and surviving text as one sentence.
