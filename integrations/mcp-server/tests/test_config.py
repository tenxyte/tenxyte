import pytest

from tenxyte_mcp_server.config import ConfigError, load_config


def test_loads_with_required_vars_only():
    config = load_config({"TENXYTE_BASE_URL": "https://x.test/", "TENXYTE_AGENT_TOKEN": "raw"})
    assert config.base_url == "https://x.test"  # trailing slash stripped
    assert config.agent_token == "raw"
    assert config.access_key is None
    assert config.access_secret is None


def test_loads_with_all_vars():
    config = load_config(
        {
            "TENXYTE_BASE_URL": "https://x.test",
            "TENXYTE_AGENT_TOKEN": "raw",
            "TENXYTE_ACCESS_KEY": "key",
            "TENXYTE_ACCESS_SECRET": "secret",
        }
    )
    assert config.access_key == "key"
    assert config.access_secret == "secret"


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"TENXYTE_BASE_URL": "https://x.test"},
        {"TENXYTE_AGENT_TOKEN": "raw"},
    ],
)
def test_missing_required_vars_raises(env):
    with pytest.raises(ConfigError):
        load_config(env)


def test_error_message_names_every_missing_var():
    with pytest.raises(ConfigError) as exc_info:
        load_config({})
    message = str(exc_info.value)
    assert "TENXYTE_BASE_URL" in message
    assert "TENXYTE_AGENT_TOKEN" in message
