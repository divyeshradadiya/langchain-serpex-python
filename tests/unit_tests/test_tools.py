"""Tests for the Serpex Search Tool (offline; HTTP is stubbed).

tests/unit_tests/fixtures holds sanitized responses captured from
api.serpex.dev on 2026-10-23 (statuses that cannot be triggered safely use the
exact body from the backend code); manifest.json has each status and headers.
The tool runs its real path through the official serpex SDK; only the SDK's
HTTP session is replaced.
"""

import json
import os
import warnings
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from pydantic import SecretStr
from serpex import SearchParams

import langchain_serpex_python
from langchain_serpex_python import SerpexSearchResults
from langchain_serpex_python.tools import USER_AGENT

FIXTURES = Path(__file__).parent / "fixtures"
MANIFEST: dict[str, Any] = json.loads((FIXTURES / "manifest.json").read_text())
IGNORED_PARAMS = ("engine", "engines", "category", "time_range", "num", "num_results")


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeResponse:
    def __init__(self, name: str) -> None:
        meta = MANIFEST[name]
        self.status_code: int = meta["status"]
        self.ok = 200 <= self.status_code < 300
        self.reason = ""
        self.headers: dict[str, str] = meta["headers"]
        self._body = fixture(name)

    def json(self) -> Any:
        return self._body


def serve(tool: SerpexSearchResults, name: str) -> list[dict[str, Any]]:
    """Answer every request of the tool's SDK client with one fixture."""
    sent: list[dict[str, Any]] = []
    client = tool._get_client()

    def get(url: str, **kw: Any) -> FakeResponse:
        sent.append(
            {
                "url": url,
                "query": {k: v[0] for k, v in parse_qs(urlparse(url).query).items()},
                **kw,
            }
        )
        return FakeResponse(name)

    client.session.get = get  # type: ignore[method-assign,assignment]
    return sent


def make(**kw: Any) -> SerpexSearchResults:
    return SerpexSearchResults(
        api_key=SecretStr("test_key"), base_url="https://example.invalid", **kw
    )


def test_serpex_initialization() -> None:
    tool = SerpexSearchResults(api_key=SecretStr("test_api_key_12345"))
    assert tool.name == "serpex_search"
    assert tool.include_content is False
    assert tool.content_results == 5


def test_serpex_initialization_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERPEX_API_KEY", "env_test_key")
    tool = SerpexSearchResults()
    assert tool.api_key.get_secret_value() == "env_test_key"


def test_version_and_user_agent() -> None:
    assert langchain_serpex_python.__version__ == "0.2.1"
    assert USER_AGENT == "langchain-serpex-python/0.2.1"
    ua = make()._get_client().session.headers["User-Agent"]
    assert isinstance(ua, str)
    assert ua.startswith("serpex-python/")
    assert ua.endswith(" langchain-serpex-python/0.2.1")


def test_deprecated_init_params_are_accepted_warned_and_not_sent() -> None:
    with pytest.warns(DeprecationWarning):
        tool = make(engine="legacy-value", category="web", time_range="day")
    sent = serve(tool, "search_repeat_deprecated_engine")
    out = tool.invoke("python asyncio tutorial")
    assert sent[0]["query"] == {"q": "python asyncio tutorial"}
    assert out.startswith("Found 10 results:")


def test_no_warning_without_deprecated_params() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        make()._build_params("test query")


def test_build_params_sends_only_q() -> None:
    params = make()._build_params("test query")
    assert params == SearchParams(q="test query")


def test_build_params_drops_deprecated_overrides() -> None:
    with pytest.warns(DeprecationWarning):
        params = make()._build_params(
            "test query", engine="legacy-b", time_range="month"
        )
    assert params == SearchParams(q="test query")


def test_content_results_must_be_5_or_10() -> None:
    with pytest.raises(ValueError):
        make(content_results=7)


def test_plain_search_end_to_end() -> None:
    tool = make()
    sent = serve(tool, "search_plain")
    out = tool.invoke("python asyncio tutorial")
    assert sent[0]["url"].startswith("https://example.invalid/api/search?")
    assert sent[0]["query"] == {"q": "python asyncio tutorial"}
    for name in IGNORED_PARAMS:
        assert name not in sent[0]["query"]
    assert sent[0]["timeout"] >= 60
    assert out.startswith("Found 10 results:\n\n[1] ")
    assert "Content" not in out


def test_include_content_end_to_end() -> None:
    tool = make(include_content=True, content_results=5)
    sent = serve(tool, "search_content")
    out = tool.invoke("what is retrieval augmented generation")
    q = sent[0]["query"]
    assert q["include_content"].lower() == "true"
    assert q.get("content_results", "5") == "5"
    assert sent[0]["timeout"] >= 100
    assert out.count("\nContent:\n") == 5


def test_content_errors_are_rendered() -> None:
    tool = make(include_content=True)
    serve(tool, "search_content_errors")
    out = tool.invoke("x")
    assert out.count("Content unavailable: robots_disallowed") == 5
    assert "\nContent:\n" not in out


def test_no_results_returns_the_api_message() -> None:
    tool = make()
    serve(tool, "search_no_results")
    assert tool.invoke("x") == fixture("search_no_results")["message"]


@pytest.mark.parametrize(
    "name,expected",
    [
        ("error_401_bad_key", "API key rejected (HTTP 401)"),
        ("error_402_search", "Out of Serpex credits (HTTP 402)"),
        ("error_429", "Rate limit exceeded"),
        (
            "error_400_content_results",
            "Request rejected (HTTP 400): content_results must be 5 or 10.",
        ),
        (
            "error_503_search",
            "Serpex is temporarily unavailable (HTTP 503): "
            "Search temporarily unavailable, please retry. Not charged.",
        ),
        (
            "error_500_search",
            "Serpex is temporarily unavailable (HTTP 500): "
            "Internal server error. Not charged. Retry shortly.",
        ),
        ("error_500_malformed_json", "Unexpected end of JSON input"),
    ],
)
def test_errors_are_one_actionable_sentence(name: str, expected: str) -> None:
    tool = make()
    serve(tool, name)
    out = tool.invoke("x")
    assert out.startswith("Error searching with Serpex: ")
    assert expected in out
    assert "{" not in out  # never a dict repr


def test_rate_limit_and_balance_details_when_the_sdk_keeps_the_body() -> None:
    # serpex >= 2.11.1 keeps the error body for 402/429; 2.11.0 drops it.
    tool = make()
    serve(tool, "error_429")
    out = tool.invoke("x")
    assert "Retry in 292 ms" in out or "Retry in 1000 ms" in out


async def test_async_path_uses_the_same_client() -> None:
    tool = make()
    sent = serve(tool, "search_plain")
    out = await tool.ainvoke("python asyncio tutorial")
    assert sent and out.startswith("Found 10 results:")


def test_serpex_custom_base_url() -> None:
    custom_url = "https://custom-api.example.com"
    tool = SerpexSearchResults(api_key=SecretStr("test_key"), base_url=custom_url)
    assert tool.base_url == custom_url
    assert tool._get_client().base_url == custom_url


# Integration test (requires real API key)
@pytest.mark.skipif("SERPEX_API_KEY" not in os.environ, reason="SERPEX_API_KEY not set")
def test_serpex_real_search() -> None:
    api_key = os.getenv("SERPEX_API_KEY")
    if not api_key:
        pytest.skip("SERPEX_API_KEY not set")
    tool = SerpexSearchResults(api_key=SecretStr(api_key))
    result = tool._run("weather in San Francisco")
    assert result and not result.startswith("Error")
