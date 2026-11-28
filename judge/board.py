"""Board numbers: score each arm from its judged answers, then rank the arms."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from harness.storage import atomic_json

from .grader import SCORED


def _rates(rows: list[dict]) -> dict:
    scored = [r for r in rows if r.get("bucket") in SCORED]
    counts = {bucket: sum(1 for r in scored if r["bucket"] == bucket) for bucket in SCORED}
    total = len(scored) or 1
    return {"n": len(scored), "buckets": counts,
            "accuracy": counts["correct"] / total,
            "stale_rate": counts["stale"] / total,
            "fused_rate": counts["fused"] / total}


def score(rows: list[dict]) -> dict:
    """Board numbers for one arm.

    Only judged rows count. A row the judge could not bucket is `unscored`: it
    says nothing about the parser, so it is left out of the denominator and
    reported as a count instead of being counted wrong.

    With several (parse repeat, ask) rows per question, the rates are over all of
    them, and each (repeat, ask) pair is also scored as a board of its own.
    `accuracy_sd` is the sample SD of those replicate scores: how far the number
    moves between one parse-and-read of the corpus and the next, parser noise
    and reader noise together.
    """
    out = _rates(rows)
    out["rows"] = len(rows)
    out["unscored"] = sum(1 for r in rows if r.get("bucket") not in SCORED)
    cells: dict[tuple[int, int], list[dict]] = {}
    for row in rows:
        cells.setdefault((row.get("repeat") or 1, row.get("ask") or 1), []).append(row)
    if len(cells) > 1:
        replicates = {f"r{r}a{a}": _rates(cell) for (r, a), cell in sorted(cells.items())}
        for field in ("accuracy", "stale_rate", "fused_rate"):
            values = [rep[field] for rep in replicates.values() if rep["n"]]
            out[f"{field}_sd"] = statistics.stdev(values) if len(values) > 1 else 0.0
        out["replicates"] = {k: round(v["accuracy"], 4) for k, v in replicates.items()}
    return out


def derive(run_dir: Path) -> dict:
    result_path = run_dir / "result.json"
    if not result_path.is_file():
        raise SystemExit(f"missing {result_path}")
    result = json.loads(result_path.read_text())
    rows = []
    accuracies = {arm["arm"]: score(arm.get("rows") or [])["accuracy"]
                  for arm in result.get("arms", [])}
    floor, ceiling = accuracies.get("blind"), accuracies.get("oracle")
    for arm in result.get("arms", []):
        arm_score = score(arm.get("rows") or [])
        arm["score"] = arm_score
        parse_seconds = sorted(float(doc.get("seconds") or 0) for doc in arm.get("documents", [])
                               if doc.get("seconds") is not None)
        median = _percentile(parse_seconds, 0.5)
        p95 = _percentile(parse_seconds, 0.95)
        gap = None
        if floor is not None and ceiling is not None and ceiling != floor:
            gap = round((arm_score["accuracy"] - floor) / (ceiling - floor), 8)
        # The board's cost columns are per pass: one parse of the corpus and one
        # answer per question, averaged over the replicates, so a 3x3 run and a
        # single-shot run price the same thing.
        cost = arm.get("cost") or {}
        repeats, asks = arm.get("repeats") or 1, arm.get("asks") or 1
        all_rows = arm.get("rows") or []
        correct_count= sum(1 for row in all_rows if row.get("bucket") == "correct")
        correct = correct_count / (repeats * asks)
        pages = sum((doc.get("cost") or {}).get("pages") or doc.get("n_pages") or 0
                    for doc in arm.get("documents", []) if (doc.get("repeat") or 1) == 1)
        vendor = cost.get("vendor_usd")
        is_reference = arm.get("vendor") == "reference"
        parse_pass = vendor / repeats if vendor is not None and not is_reference else None
        tokens = sum(((row.get("usage") or {}).get("input_tokens") or 0)
                     + ((row.get("usage") or {}).get("output_tokens") or 0) for row in all_rows)
        tokens_pass = tokens / (repeats * asks) if tokens else None
        per_1k_pages = round(parse_pass / pages * 1000, 4) if parse_pass is not None and pages else None
        per_1k = round(parse_pass / correct * 1000, 4) if parse_pass is not None and correct else None
        tokens_1k = round(tokens_pass / correct * 1000) if tokens_pass and correct else None
        rows.append({"arm": arm["arm"], "accuracy": arm_score["accuracy"],
                     "accuracy_sd": arm_score.get("accuracy_sd"),
                     "stale_rate": arm_score["stale_rate"], "fused_rate": arm_score["fused_rate"],
                     "n": arm_score["n"], "unscored": arm_score["unscored"],
                     "gap_closed": gap, "median_seconds": median, "p95_seconds": p95,
                     "vendor_usd": cost.get("vendor_usd"), "total_usd": cost.get("total_usd"),
                     "parser_usd_per_1k_pages": per_1k_pages,
                     "parser_usd_per_1k_correct": per_1k,
                     "tokens_per_1k_correct": tokens_1k})
    rows.sort(key=lambda item: (-item["accuracy"], item["arm"]))
    report = {"workflow": result["workflow"], "dataset": result["dataset"],
              "split": result["split"], "model": result["model"],
              "judge_model": result.get("judge_model"),
              "repeats": result.get("repeats"), "asks": result.get("asks"),
              "ranking": rows}
    atomic_json(run_dir / "report.json", report)
    lines = ["# Redline parsing benchmark", "",
             f"Dataset: `{result['dataset']['repo']}@{result['dataset']['revision']}`",
             f"Reader: `{result['model']}` · judge: `{result.get('judge_model') or 'n/a'}` · "
             f"{result.get('repeats') or 1} parse(s) x {result.get('asks') or 1} ask(s)", "",
             "| Rank | Arm | Accuracy | Gap closed | Median parse time | Parser $ / 1k pages "
             "| Parser $ / 1k correct | Total tokens / 1k correct | Stale | Fused | Unscored | N |",
             "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for rank, row in enumerate(rows, 1):
        accuracy = f"{row['accuracy']:.1%}"
        if row["accuracy_sd"] is not None:
            accuracy += f" ± {row['accuracy_sd']:.1%}"
        gap = f"{row['gap_closed']:.0%}" if row["gap_closed"] is not None else "n/a"
        latency = (f"{row['median_seconds']:.0f}s (p95 {row['p95_seconds']:.0f}s)"
                   if row["median_seconds"] is not None else "n/a")
        usd = lambda v: f"${v:.2f}" if v is not None else "n/a"  # noqa: E731
        tokens = row["tokens_per_1k_correct"]
        tokens_text = ("n/a" if tokens is None else
                       f"{tokens / 1e6:.1f}M" if tokens >= 1e6 else f"{tokens / 1e3:.0f}K")
        lines.append(f"| {rank} | {row['arm']} | {accuracy} | {gap} | {latency} | "
                     f"{usd(row['parser_usd_per_1k_pages'])} | {usd(row['parser_usd_per_1k_correct'])} | "
                     f"{tokens_text} | {row['stale_rate']:.1%} | {row['fused_rate']:.1%} | "
                     f"{row['unscored']} | {row['n']} |")
    (run_dir / "report.md").write_text("\n".join(lines) + "\n")
    atomic_json(result_path, result)
    return report


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    index = round((len(values) - 1) * quantile)
    return values[index]
