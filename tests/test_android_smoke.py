import pytest

from showcase.mobile.android.smoke_test import smoke_test


@pytest.mark.unit
def test_android_smoke_argv_after_separator(monkeypatch):
    monkeypatch.setattr(smoke_test.sys, "argv", ["run.py", "showcase/mobile/android/smoke_test/smoke_test", "--", "--output", "x.json"])

    assert smoke_test._argv() == ["--output", "x.json"]
