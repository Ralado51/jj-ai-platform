from app.services.chat_providers import OllamaChatProvider


def test_ollama_payload_limits_generation() -> None:
    provider = OllamaChatProvider(
        base_url="http://ollama:11434",
        model="qwen2.5:3b",
        timeout_seconds=180,
        temperature=0.2,
        max_tokens=1024,
        repeat_penalty=1.15,
        max_characters=12000,
    )

    payload = provider._payload(
        system_prompt="Sistema",
        user_prompt="Usuário",
        stream=True,
    )

    assert payload["options"]["num_predict"] == 1024
    assert payload["options"]["repeat_penalty"] == 1.15
    assert provider.max_characters == 12000


def test_ollama_provider_has_safe_default_limits() -> None:
    provider = OllamaChatProvider(
        base_url="http://ollama:11434",
        model="qwen2.5:3b",
        timeout_seconds=180,
        temperature=0.2,
    )

    assert provider.max_tokens == 2048
    assert provider.repeat_penalty == 1.12
    assert provider.max_characters == 24000
