from app.core.config import get_settings


def test_get_settings_loads_vllm_values_from_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "VLLM_MOCK=false",
                "VLLM_BASE_URL=https://vlm.example/v1",
                "VLLM_MODEL=chargellm-real-vlm",
                "VLLM_API_KEY=test-api-key",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CHARGELLM_ENV_FILE", str(env_file))
    monkeypatch.delenv("VLLM_MOCK", raising=False)
    monkeypatch.delenv("VLLM_BASE_URL", raising=False)
    monkeypatch.delenv("VLLM_MODEL", raising=False)
    monkeypatch.delenv("VLLM_API_KEY", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.vllm_mock is False
    assert settings.vllm_base_url == "https://vlm.example/v1"
    assert settings.vllm_model == "chargellm-real-vlm"
    assert settings.vllm_api_key == "test-api-key"
