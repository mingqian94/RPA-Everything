"""No-key first-run preview tests."""

from harness.demo import build_first_run_demo


def test_first_run_demo_is_local_and_read_only():
    result = build_first_run_demo()

    assert result["status"] == "ready_to_inspect"
    assert result["guarantees"] == {
        "llm_key_required": False,
        "network_used": False,
        "external_action": False,
        "files_written": False,
    }
    assert len(result["dry_run_steps"]) == 2
    assert result["evidence"]["counts"] == {"browser_command": 1, "dom_selector": 1}
