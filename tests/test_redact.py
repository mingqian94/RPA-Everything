import pytest

from core.redact import redact, redact_text
from core.secrets import environment_name, expand_secret_references


@pytest.mark.unit
def test_redact_masks_secret_fields_and_common_personal_data():
    value = {
        "api_key": "real-value",
        "url": "https://example.test/?token=private-token",
        "contact": "person@example.com, 13800138000",
    }

    result = redact(value)

    assert result["api_key"] == "<redacted>"
    assert "private-token" not in result["url"]
    assert "person@example.com" not in result["contact"]
    assert "13800138000" not in result["contact"]


@pytest.mark.unit
def test_redact_text_masks_bearer_value():
    assert "abc123" not in redact_text("Authorization: Bearer abc123")


@pytest.mark.unit
def test_expand_secret_references_reads_environment(monkeypatch):
    monkeypatch.setenv(environment_name("crm-password"), "local-only")

    assert expand_secret_references("${secret:crm-password}") == "local-only"


@pytest.mark.unit
def test_expand_secret_references_fails_when_missing(monkeypatch):
    monkeypatch.delenv(environment_name("missing"), raising=False)

    with pytest.raises(ValueError, match="RPA_SECRET_MISSING"):
        expand_secret_references("${secret:missing}")
