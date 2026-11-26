"""The pinned public dataset and the one workflow this benchmark runs."""
from __future__ import annotations

DATASET_REPO = "openbenchmarks/OB-LegalQA-Document-Parsing"
DATASET_REVISION = "3c7c599d0221adc38f11b3e87c788787077a81fe"
UPSTREAM_REPO = "crosbylegal/RedlineBench"
UPSTREAM_REVISION = "eee1b6790982ed1279e86bec7616b662a61993e6"
WORKFLOW = "redline-parsing"
WORKFLOWS = {
    WORKFLOW: "Measure whether parser output preserves legal redlines for downstream QA.",
}
SMOKE_CASES = 12
EXPECTED_CASES = 95
