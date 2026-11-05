"""Provider labels stay attached to their configured endpoint; no network calls."""
import pytest

from advisor.llm_client import OpenAICompatibleClient


@pytest.mark.parametrize('explicit_url,label,expected', [
    (None, 'Groq', 'Groq'),
    ('https://api.groq.com/openai/v1/', 'Groq', 'Groq'),
    ('https://example.test/v1', 'Groq', 'example.test'),
    (None, '', 'api.groq.com'),
])
def test_provider_label_matches_selected_endpoint(monkeypatch, explicit_url, label, expected):
    monkeypatch.setenv('LLM_BASE_URL', 'https://api.groq.com/openai/v1/')
    monkeypatch.setenv('LLM_PROVIDER_NAME', label)
    client = OpenAICompatibleClient(api_key='test-key', model='test-model', base_url=explicit_url)
    assert client.usage.provider == expected
    assert client.available
