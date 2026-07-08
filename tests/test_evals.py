import pytest

from evals import run as eval_run


@pytest.mark.unit
def test_static_evals_pass():
    results = eval_run.run_static(eval_run.load_cases())

    assert results
    assert all(item["ok"] for item in results)


@pytest.mark.unit
def test_static_eval_detects_missing_skill():
    results = eval_run.run_static([{
        "id": "bad",
        "goal": "bad",
        "expected_skill": "skill:not/real",
    }])

    assert not results[0]["ok"]
    assert "missing expected skill" in results[0]["reasons"][0]
