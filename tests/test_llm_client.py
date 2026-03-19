from __future__ import annotations

from unittest.mock import patch

import pytest


def test_rule_based_mode_when_no_keys() -> None:
    """When neither API key is set, LLMClient falls back to rule_based mode."""
    env = {
        "SUPABASE_URL": "https://fake.supabase.co",
        "SUPABASE_KEY": "fake-key",
        "ANTHROPIC_API_KEY": "",
        "OPENAI_API_KEY": "",
    }
    with patch.dict("os.environ", env, clear=False):
        from importlib import reload

        import config as _cfg

        reload(_cfg)

        import core.llm.client as _mod

        reload(_mod)

        client = _mod.LLMClient()
        assert client.mode == "rule_based"
        assert client.is_ai_available() is False


def test_ask_json_parses_correctly() -> None:
    """ask_json should strip markdown fences and return a parsed dict."""
    env = {
        "SUPABASE_URL": "https://fake.supabase.co",
        "SUPABASE_KEY": "fake-key",
        "ANTHROPIC_API_KEY": "sk-fake-key",
    }
    with patch.dict("os.environ", env, clear=False):
        from importlib import reload

        import config as _cfg

        reload(_cfg)

        import core.llm.client as _mod

        reload(_mod)

        client = _mod.LLMClient.__new__(_mod.LLMClient)
        client._anthropic_client = None
        client._openai_client = None
        client._mode = "anthropic"

        raw_response = '```json\n{"compliant": false, "issues": ["ESA fee"]}\n```'
        with patch.object(client, "ask", return_value=raw_response):
            result = client.ask_json(system="test", user="test")

        assert isinstance(result, dict)
        assert result["compliant"] is False
        assert result["issues"] == ["ESA fee"]
