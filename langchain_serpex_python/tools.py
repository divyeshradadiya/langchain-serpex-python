"""Serpex Search Tool for LangChain."""

import os
import re
import warnings
from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import Field, PrivateAttr, SecretStr, model_validator

# The official SDK owns the HTTP contract (params, timeouts, error parsing), so
# this tool cannot drift from the API on its own.
from serpex import SearchParams, SearchResponse, SerpApiException, SerpexClient

__version__ = "0.3.0"

#: Product token appended to the SDK's User-Agent.
USER_AGENT = f"langchain-serpex-python/{__version__}"

# Accepted for backward compatibility, ignored by the Serpex API, never sent.
DEPRECATED_PARAMS = ("engine", "engines", "category", "time_range")

BILLING_URL = "https://app.serpex.dev/dashboard/billing"


def _warn_deprecated(names: list[str]) -> None:
    warnings.warn(
        f"{', '.join(names)} {'is' if len(names) == 1 else 'are'} deprecated and "
        "ignored by the Serpex API; the value is not sent. Remove it from your "
        "code; it will be removed in 0.4.0.",
        DeprecationWarning,
        stacklevel=2,
    )


def _sentence(text: str) -> str:
    return text if re.search(r"[.!?]$", text) else f"{text}."


def _api_message(err: SerpApiException) -> str:
    """The API's own error text (string, ``{"message"}`` or framework ``message``)."""
    details = err.details or {}
    error = details.get("error")
    if isinstance(error, str) and error:
        message = details.get("message")
        if err.status_code == 404 and isinstance(message, str) and message:
            return message
        return error
    if (
        isinstance(error, dict)
        and isinstance(error.get("message"), str)
        and error["message"]
    ):
        return str(error["message"])
    if isinstance(details.get("message"), str) and details["message"]:
        return str(details["message"])
    return str(err.args[0]) if err.args else "API request failed"


def describe_serpex_error(err: Exception) -> str:
    """One actionable sentence per failure.

    Says what happened, whether it was charged and whether to retry.
    """
    if not isinstance(err, SerpApiException):
        return _sentence(str(err))
    status = err.status_code
    details = err.details or {}
    msg = _api_message(err)
    if status is None:
        return f"{_sentence(msg)} Safe to retry."
    if status == 400:
        return f"Request rejected (HTTP 400): {_sentence(msg)}"
    if status == 401:
        return f"API key rejected (HTTP 401): {_sentence(msg)} Check SERPEX_API_KEY."
    if status == 402:
        balance = details.get("remainingCredits")
        balance_text = (
            f" Balance: {balance} credits." if isinstance(balance, int) else ""
        )
        return (
            f"Out of Serpex credits (HTTP 402).{balance_text} Top up at {BILLING_URL}."
        )
    if status == 429:
        limit = details.get("limit")
        limit_text = (
            f" (limit: {limit} requests per second)" if isinstance(limit, int) else ""
        )
        wait = details.get("retryAfterMs")
        wait_ms = wait if isinstance(wait, int) else 1000
        return f"Rate limit exceeded{limit_text}. Retry in {wait_ms} ms."
    if status >= 500:
        charged = "" if re.search("charged", msg, re.I) else " Not charged."
        retry = "" if re.search("retry", msg, re.I) else " Retry shortly."
        return (
            f"Serpex is temporarily unavailable (HTTP {status}): "
            f"{_sentence(msg)}{charged}{retry}"
        )
    return f"HTTP {status}: {_sentence(msg)}"


class SerpexSearchResults(BaseTool):
    """Web search tool backed by Serpex.

    Serpex is the web search API and extract API for AI agents. Search returns
    ranked web results, optionally with page content as markdown.

    Setup:
        Install `langchain-serpex-python` and set environment variable
        `SERPEX_API_KEY`.

        ```bash
        pip install -U langchain-serpex-python
        export SERPEX_API_KEY="your-serpex-api-key"
        ```

    Instantiation:
        ```python
        from langchain_serpex_python import SerpexSearchResults

        # With explicit API key
        tool = SerpexSearchResults(api_key="your-serpex-api-key")

        # Also fetch page content (markdown) for the top 5 results
        tool = SerpexSearchResults(include_content=True, content_results=5)

        # Or using environment variable
        tool = SerpexSearchResults()
        ```

    Invocation:
        ```python
        results = tool.invoke("latest AI developments")
        print(results)
        ```

    Errors are returned as a sentence the agent can act on (the tool does not
    raise): ``Error searching with Serpex: ...`` with the HTTP status, whether
    the request was charged and whether to retry.
    """

    name: str = "serpex_search"
    description: str = (
        "A web search tool. "
        "Useful for answering questions about current events and "
        "finding information from the web. "
        "Input should be a search query string."
    )

    api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    include_content: bool = Field(
        default=False,
        description=(
            "Also fetch page content (markdown) for the top results. Best-effort: "
            "a page that cannot be extracted carries content_error instead."
        ),
    )
    content_results: int = Field(
        default=5,
        description=(
            "How many top results get content when include_content is on: 5 or 10."
        ),
    )
    timeout: Optional[float] = Field(
        default=None,
        description=(
            "Request timeout in seconds. Default: 60 s, or 100 s with include_content."
        ),
    )
    # Deprecated: ignored by the Serpex API and never sent. Still accepted so
    # existing code keeps working; a DeprecationWarning is emitted when set.
    # Removed in 0.4.0. For a date filter put after:/before: in the query.
    engine: Optional[str] = Field(default=None, description="Deprecated; ignored.")
    category: Optional[str] = Field(default=None, description="Deprecated; ignored.")
    time_range: Optional[str] = Field(default=None, description="Deprecated; ignored.")

    base_url: str = Field(default="https://api.serpex.dev")

    _client: Optional[SerpexClient] = PrivateAttr(default=None)
    _client_key: Optional[tuple[str, str, Optional[float]]] = PrivateAttr(default=None)

    @model_validator(mode="before")
    @classmethod
    def validate_environment(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Validate that API key exists in environment."""
        api_key = values.get("api_key")
        if not api_key or (
            isinstance(api_key, SecretStr) and not api_key.get_secret_value()
        ):
            api_key_from_env = os.getenv("SERPEX_API_KEY", "")
            if api_key_from_env:
                values["api_key"] = SecretStr(api_key_from_env)
        elif isinstance(api_key, str):
            values["api_key"] = SecretStr(api_key)

        passed = [k for k in DEPRECATED_PARAMS if values.get(k) is not None]
        if passed:
            _warn_deprecated(passed)

        if values.get("content_results", 5) not in (5, 10):
            raise ValueError("content_results must be 5 or 10")

        return values

    def _get_client(self) -> SerpexClient:
        """One SDK client per (key, base URL, timeout), reused across calls."""
        key = (self.api_key.get_secret_value(), self.base_url, self.timeout)
        if self._client is None or self._client_key != key:
            client = SerpexClient(key[0], base_url=self.base_url, timeout=self.timeout)
            # Identify this package next to the SDK:
            # "serpex-python/<v> langchain-serpex-python/<v>".
            base_ua = client.session.headers.get("User-Agent", "")
            if isinstance(base_ua, bytes):
                base_ua = base_ua.decode("ascii", "replace")
            client.session.headers["User-Agent"] = f"{base_ua} {USER_AGENT}".strip()
            self._client = client
            self._client_key = key
        return self._client

    def _build_params(self, query: str, **kwargs: Any) -> SearchParams:
        """The search request: only q, plus include_content / content_results."""
        passed = [k for k in DEPRECATED_PARAMS if kwargs.get(k) is not None]
        if passed:
            _warn_deprecated(passed)

        include_content = bool(kwargs.get("include_content", self.include_content))
        if not include_content:
            return SearchParams(q=query)
        content_results = kwargs.get("content_results", self.content_results)
        if content_results not in (5, 10):
            raise ValueError("content_results must be 5 or 10")
        return SearchParams(
            q=query, include_content=True, content_results=content_results
        )

    def _format_results(self, data: SearchResponse) -> str:
        """Format the search results into a readable string."""
        results = [r for r in data.results if r.snippet or r.title][:10]
        if not results:
            return data.message or data.metadata.message or "No search results found."

        num_results = data.metadata.number_of_results or len(results)
        results_parts: list[str] = [f"Found {num_results} results:"]

        for i, result in enumerate(results, 1):
            result_text = f"[{i}] {result.title}"
            if result.url:
                result_text += f"\nURL: {result.url}"
            if result.snippet:
                result_text += f"\n{result.snippet}"
            if result.content is not None:
                result_text += f"\nContent:\n{result.content}"
            elif result.content_error is not None:
                result_text += f"\nContent unavailable: {result.content_error}"
            results_parts.append(result_text)

        return "\n\n".join(results_parts)

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> str:
        """Execute the search.

        The async path (``ainvoke``) runs this in LangChain's thread executor.
        """
        try:
            params = self._build_params(query, **kwargs)
            response = self._get_client().search(params)
        except Exception as e:  # the tool reports failures to the agent as text
            return f"Error searching with Serpex: {describe_serpex_error(e)}"
        return self._format_results(response)


__all__ = ["SerpexSearchResults", "describe_serpex_error"]
