from pathlib import Path

import pytest

from config.settings import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_env_example_loads_supported_values_and_json_cors_lists(monkeypatch):
    for key in (
        "ENVIRONMENT",
        "DATABASE_URL",
        "ALLOWED_ORIGINS",
        "CORS_ALLOW_METHODS",
        "CORS_ALLOW_HEADERS",
        "LLM_PROVIDER",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=PROJECT_ROOT / ".env.example")

    assert settings.ENVIRONMENT == "development"
    assert settings.DATABASE_URL == "sqlite:///./storage/ai_interviewer.db"
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3000", "http://localhost:8000"]
    assert settings.CORS_ALLOW_METHODS == ["*"]
    assert settings.CORS_ALLOW_HEADERS == ["*"]
    assert settings.LLM_PROVIDER == "none"


def test_known_legacy_dotenv_keys_are_ignored_but_unknown_keys_are_rejected(tmp_path):
    env_file = tmp_path / "settings.env"
    env_file.write_text(
        "ENVIRONMENT=test\nCORS_ORIGINS=*\n"
        "UNKNOWN_SETTING=must-not-appear-in-errors\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported \\.env variables: UNKNOWN_SETTING") as exc:
        Settings(_env_file=env_file)

    assert "must-not-appear-in-errors" not in str(exc.value)


def test_llm_provider_and_timeout_settings_are_validated():
    with pytest.raises(ValueError, match="LLM_PROVIDER must be one of"):
        Settings(_env_file=None, LLM_PROVIDER="unconfigured-provider")

    with pytest.raises(ValueError, match="LLM_TIMEOUT_SECONDS"):
        Settings(_env_file=None, LLM_TIMEOUT_SECONDS=float("inf"))

    with pytest.raises(ValueError):
        Settings(_env_file=None, LLM_TIMEOUT_SECONDS=0)


def test_legacy_cors_alias_does_not_override_allowed_origins(tmp_path):
    env_file = tmp_path / "settings.env"
    env_file.write_text(
        'ALLOWED_ORIGINS=["https://frontend.example"]\nCORS_ORIGINS=*\n',
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.ALLOWED_ORIGINS == ["https://frontend.example"]
