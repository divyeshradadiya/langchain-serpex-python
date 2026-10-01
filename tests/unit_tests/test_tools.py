"""Tests for the Serpex Search Tool (offline; HTTP is not called)."""

import os
import warnings
from typing import Any

import pytest
from pydantic import SecretStr

import langchain_serpex_python
from langchain_serpex_python import SerpexSearchResults
from langchain_serpex_python.tools import USER_AGENT

IGNORED_PARAMS = ("engine", "engines", "category", "time_range", "num")


def test_serpex_initialization() -> None:
    """Test that Serpex can be initialized with API key."""
    tool = SerpexSearchResults(api_key=SecretStr("test_api_key_12345"))
    assert tool.name == "serpex_search"
    assert tool.include_content is False
    assert tool.content_results == 5


def test_serpex_initialization_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that Serpex can be initialized from environment variable."""
    monkeypatch.setenv("SERPEX_API_KEY", "env_test_key")
    tool = SerpexSearchResults()
    assert tool.name == "serpex_search"
    assert tool.api_key.get_secret_value() == "env_test_key"


def test_deprecated_init_params_are_accepted_warned_and_not_sent() -> None:
    """engine/category/time_range still construct, warn, and never reach the API."""
    with pytest.warns(DeprecationWarning):
        tool = SerpexSearchResults(
            api_key=SecretStr("test_api_key"),
            engine="legacy-value",
            category="web",
            time_range="day",
        )
    params = tool._build_params("test query")
    assert params == {"q": "test query"}


def test_no_warning_without_deprecated_params() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        tool = SerpexSearchResults(api_key=SecretStr("test_key"))
        tool._build_params("test query")


def test_build_params_sends_only_q() -> None:
    tool = SerpexSearchResults(api_key=SecretStr("test_key"))
    params = tool._build_params("test query")
    assert params == {"q": "test query"}
    for name in IGNORED_PARAMS:
        assert name not in params


def test_build_params_drops_deprecated_overrides() -> None:
    tool = SerpexSearchResults(api_key=SecretStr("test_key"))
    with pytest.warns(DeprecationWarning):
        params = tool._build_params("test query", engine="legacy-b", time_range="month")
    assert params == {"q": "test query"}


def test_build_params_include_content() -> None:
    tool = SerpexSearchResults(
        api_key=SecretStr("test_key"), include_content=True, content_results=10
    )
    params = tool._build_params("test query")
    assert params == {"q": "test query", "include_content": "true", "content_results": 10}
    assert tool._timeout(params) >= 60


def test_content_results_must_be_5_or_10() -> None:
    with pytest.raises(ValueError):
        SerpexSearchResults(api_key=SecretStr("test_key"), content_results=7)


def test_user_agent_names_package_and_version() -> None:
    tool = SerpexSearchResults(api_key=SecretStr("test_key"))
    assert USER_AGENT == "langchain-serpex-python/0.2.0"
    assert tool._headers()["User-Agent"] == USER_AGENT
    assert langchain_serpex_python.__version__ == "0.2.0"


def test_serpex_format_results_with_organic() -> None:
    """Test formatting organic search results."""
    tool = SerpexSearchResults(api_key=SecretStr("test_key"))

    mock_data: dict[str, Any] = {
        "metadata": {"number_of_results": 2},
        "results": [
            {
                "position": 1,
                "title": "Test Result 1",
                "url": "https://example.com/1",
                "snippet": "This is a test snippet",
            },
            {
                "position": 2,
                "title": "Test Result 2",
                "url": "https://example.com/2",
                "snippet": "Another test snippet",
            },
        ],
    }

    formatted = tool._format_results(mock_data)

    assert "Found 2 results" in formatted
    assert "Test Result 1" in formatted
    assert "Test Result 2" in formatted
    assert "https://example.com/1" in formatted
    assert "This is a test snippet" in formatted


def test_serpex_format_results_with_content() -> None:
    tool = SerpexSearchResults(api_key=SecretStr("test_key"))
    mock_data: dict[str, Any] = {
        "metadata": {"number_of_results": 2},
        "results": [
            {"title": "A", "url": "https://a.example", "snippet": "s", "content": "# Page A"},
            {"title": "B", "url": "https://b.example", "snippet": "s", "content_error": "timeout"},
        ],
    }
    formatted = tool._format_results(mock_data)
    assert "# Page A" in formatted
    assert "Content unavailable: timeout" in formatted


def test_serpex_format_results_without_deprecated_engine_fields() -> None:
    tool = SerpexSearchResults(api_key=SecretStr("test_key"))
    formatted = tool._format_results(
        {"results": [{"title": "T", "url": "https://t.example", "snippet": "s"}]}
    )
    assert "T" in formatted


def test_serpex_format_results_no_results_message() -> None:
    tool = SerpexSearchResults(api_key=SecretStr("test_key"))
    formatted = tool._format_results({"results": [], "message": "No results found for this query"})
    assert formatted == "No results found for this query"


def test_serpex_format_results_empty() -> None:
    """Test formatting when no results."""
    tool = SerpexSearchResults(api_key=SecretStr("test_key"))

    mock_data: dict[str, Any] = {"results": []}

    formatted = tool._format_results(mock_data)
    assert formatted == "No search results found."


def test_serpex_custom_base_url() -> None:
    """Test that custom base URL is respected."""
    custom_url = "https://custom-api.example.com"
    tool = SerpexSearchResults(api_key=SecretStr("test_key"), base_url=custom_url)
    assert tool.base_url == custom_url


# Integration test (requires real API key)
@pytest.mark.skipif("SERPEX_API_KEY" not in os.environ, reason="SERPEX_API_KEY not set")
def test_serpex_real_search() -> None:
    """Test with real API (requires SERPEX_API_KEY environment variable)."""
    api_key = os.getenv("SERPEX_API_KEY")

    if not api_key:
        pytest.skip("SERPEX_API_KEY not set")

    tool = SerpexSearchResults(api_key=SecretStr(api_key))

    result = tool._run("weather in San Francisco")

    assert result
    assert len(result) > 0
    assert "Error" not in result or "No search results" in result
