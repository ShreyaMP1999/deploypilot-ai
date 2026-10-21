import json
from pathlib import Path

import pytest

from backend.evaluations.runner import run_case

CASES = json.loads((Path(__file__).resolve().parents[1] / "evaluations/cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"] + "-" + c["category"])
def test_labeled_policy_cases(case):
    assert run_case(case)[0] == case["expected"]
