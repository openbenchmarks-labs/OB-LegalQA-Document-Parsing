import json

from judge.board import derive, score


def test_score_buckets():
    result = score([{"bucket": "correct"}, {"bucket": "correct"}, {"bucket": "stale"}])
    assert result["accuracy"] == 2 / 3
    assert result["stale_rate"] == 1 / 3


def test_unscored_rows_leave_the_denominator():
    result = score([{"bucket": "correct"}, {"bucket": "unscored"}])
    assert result["accuracy"] == 1
    assert result["unscored"] == 1
    assert result["n"] == 1


def test_replicate_sd_across_repeat_and_ask():
    rows = [{"bucket": "correct", "repeat": 1, "ask": 1},
            {"bucket": "stale", "repeat": 2, "ask": 1}]
    result = score(rows)
    assert result["replicates"] == {"r1a1": 1.0, "r2a1": 0.0}
    assert round(result["accuracy_sd"], 4) == 0.7071


def test_offline_derivation_recomputes_and_sorts(tmp_path):
    payload = {
        "workflow": "redline-parsing", "split": "tagged", "model": "reader",
        "dataset": {"repo": "example/data", "revision": "abc"},
        "arms": [
            {"arm": "low", "rows": [{"bucket": "stale"}], "cost": {}},
            {"arm": "high", "rows": [{"bucket": "correct"}], "cost": {}},
        ],
    }
    (tmp_path / "result.json").write_text(json.dumps(payload))
    report = derive(tmp_path)
    assert [row["arm"] for row in report["ranking"]] == ["high", "low"]
    assert (tmp_path / "report.md").is_file()


def test_derivation_calculates_gap_closed_and_latency(tmp_path):
    def arm(name, correct, seconds):
        return {"arm": name, "rows": ([{"bucket": "correct"}] * correct
                                       + [{"bucket": "stale"}] * (10 - correct)),
                "documents": [{"seconds": value} for value in seconds], "cost": {}}

    payload = {"workflow": "redline-parsing", "split": "tagged", "model": "reader",
               "dataset": {"repo": "example/data", "revision": "abc"},
               "arms": [arm("blind", 2, [1, 3]), arm("oracle", 10, [2, 4]),
                        arm("vendor", 6, [10, 20, 30])]}
    (tmp_path / "result.json").write_text(json.dumps(payload))
    report = derive(tmp_path)
    vendor = next(row for row in report["ranking"] if row["arm"] == "vendor")
    assert vendor["gap_closed"] == 0.5
    assert vendor["median_seconds"] == 20


def test_board_columns_are_per_pass(tmp_path):
    # 2 parses x 1 ask: the vendor bill covers two parses, the columns price one.
    usage = {"input_tokens": 900, "output_tokens": 100}
    rows = ([{"bucket": "correct", "repeat": r, "usage": usage} for r in (1, 2)] * 4
            + [{"bucket": "stale", "repeat": r, "usage": usage} for r in (1, 2)])
    payload = {"workflow": "redline-parsing", "split": "tagged", "model": "reader",
               "dataset": {"repo": "example/data", "revision": "abc"},
               "arms": [{"arm": "vendor", "vendor": "Example", "repeats": 2, "asks": 1,
                         "rows": rows, "cost": {"vendor_usd": 2.0, "total_usd": 2.5},
                         "documents": [{"repeat": 1, "cost": {"pages": 100}},
                                       {"repeat": 2, "cost": {"pages": 100}}]},
                        {"arm": "oracle", "vendor": "reference", "rows": rows,
                         "cost": {"total_usd": 1.0}}]}
    (tmp_path / "result.json").write_text(json.dumps(payload))
    ranking = {row["arm"]: row for row in derive(tmp_path)["ranking"]}
    vendor = ranking["vendor"]
    assert vendor["parser_usd_per_1k_pages"] == 10.0     # $1 per pass over 100 pages
    assert vendor["parser_usd_per_1k_correct"] == 250.0  # $1 per pass over 4 correct
    assert vendor["tokens_per_1k_correct"] == 1_250_000  # 5,000 tokens per pass over 4 correct
    assert ranking["oracle"]["parser_usd_per_1k_correct"] is None

def test_unscored_answer_cost_per_correct(tmp_path):
    usage = {"input_tokens": 80, "output_tokens": 20}
    rows = [
        {"bucket": "correct", "repeat": 1, "ask": 1, "usage": usage},
        {"bucket": "unscored", "repeat": 1, "ask": 1, "usage": usage},
    ]
    payload = {
        "workflow": "redline-parsing",
        "split": "tagged",
        "model": "reader",
        "dataset": {"repo": "example/data", "revision": "abc"},
        "arms": [{
            "arm": "vendor",
            "vendor": "Example",
            "repeats": 1,
            "asks": 1,
            "rows": rows,
            "cost": {"vendor_usd": 10.0, "total_usd": 10.0},
            "documents": [{"repeat": 1, "cost": {"pages": 1}}],
        }],
    }
    (tmp_path / "result.json").write_text(json.dumps(payload))
    vendor = derive(tmp_path)["ranking"][0]

    assert vendor["parser_usd_per_1k_correct"] == 10_000
    assert vendor["tokens_per_1k_correct"] == 200_000