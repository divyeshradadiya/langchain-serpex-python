"""Serpex Search Tool for LangChain."""

import os
import warnings
from typing import Any, Optional

import httpx
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import Field, SecretStr, model_validator

__version__ = "0.2.0"

USER_AGENT = f"langchain-serpex-python/{__version__}"

# Client timeouts (seconds), above the server's own budget for each call
# (search 30 s upstream, 45 s with include_content), so the tool never gives
# up on a request the server still finishes and bills.
SEARCH_TIMEOUT = 60.0
SEARCH_CONTENT_TIMEOUT = 100.0

# Accepted for backward compatibility, ignored by the Serpex API, never sent.
DEPRECATED_PARAMS = ("engine", "engines", "category", "time_range")


def _warn_deprecated(names: list[str]) -> None:
    warnings.warn(
        f"{', '.join(names)} {'is' if len(names) == 1 else 'are'} deprecated and "
        "ignored by the Serpex API; the value is not sent. Remove it from your "
        "code; it will be removed in 0.3.0.",
        DeprecationWarning,
        stacklevel=2,
    )


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

    Example with Agent:
        ```python
        from langchain_serpex_python import SerpexSearchResults
        from langchain_openai import ChatOpenAI
        from langchain.agents import initialize_agent, AgentType

        search = SerpexSearchResults(api_key="your-key")
        llm = ChatOpenAI(temperature=0)

        agent = initialize_agent(
            tools=[search],
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
        )

        result = agent.run("What's the latest news about AI?")
        ```
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
        description="How many top results get content when include_content is on: 5 or 10.",
    )
    timeout: Optional[float] = Field(
        default=None,
        description=(
            "Request timeout in seconds. Default: 60 s, or 100 s with include_content."
        ),
    )
    # Deprecated: ignored by the Serpex API and never sent. Still accepted so
    # existing code keeps working; a DeprecationWarning is emitted when set.
    # Removed in 0.3.0.
    engine: Optional[str] = Field(default=None, description="Deprecated; ignored.")
    category: Optional[str] = Field(default=None, description="Deprecated; ignored.")
    time_range: Optional[str] = Field(default=None, description="Deprecated; ignored.")

    base_url: str = Field(default="https://api.serpex.dev")

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

    def _build_params(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Build the query string: only q, include_content and content_results."""
        passed = [k for k in DEPRECATED_PARAMS if kwargs.get(k) is not None]
        if passed:
            _warn_deprecated(passed)

        params: dict[str, Any] = {"q": query}
        include_content = kwargs.get("include_content", self.include_content)
        if include_content:
            content_results = kwargs.get("content_results", self.content_results)
            if content_results not in (5, 10):
                raise ValueError("content_results must be 5 or 10")
            params["include_content"] = "true"
            params["content_results"] = content_results
        return params

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    def _timeout(self, params: dict[str, Any]) -> float:
        if self.timeout is not None:
            return self.timeout
        return SEARCH_CONTENT_TIMEOUT if "include_content" in params else SEARCH_TIMEOUT

    def _format_results(self, data: dict[str, Any]) -> str:
        """Format the search results into a readable string."""
        results = data.get("results")
        if not isinstance(results, list) or not results:
            message = data.get("message")
            return message if message else "No search results found."

        num_results = (data.get("metadata") or {}).get("number_of_results", len(results))
        results_parts: list[str] = [f"Found {num_results} results:"]

        for i, result in enumerate(results[:10], 1):
            result_text = f"[{i}] {result.get('title', '')}"
            if result.get("url"):
                result_text += f"\nURL: {result['url']}"
            if result.get("snippet"):
                result_text += f"\n{result['snippet']}"
            if result.get("content"):
                result_text += f"\nContent:\n{result['content']}"
            elif result.get("content_error"):
                result_text += f"\nContent unavailable: {result['content_error']}"
            results_parts.append(result_text)

        return "\n\n".join(results_parts)

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> str:
        """Execute the search."""
        params = self._build_params(query, **kwargs)
        url = f"{self.base_url}/api/search"

        try:
            with httpx.Client() as client:
                response = client.get(
                    url, params=params, headers=self._headers(), timeout=self._timeout(params)
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    return f"SERPEX API error: {data['error']}"

                return self._format_results(data)

        except httpx.HTTPStatusError as e:
            return f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Request error occurred: {str(e)}"
        except Exception as e:
            return f"Error searching with SERPEX: {str(e)}"

    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> str:
        """Execute the search asynchronously."""
        params = self._build_params(query, **kwargs)
        url = f"{self.base_url}/api/search"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, params=params, headers=self._headers(), timeout=self._timeout(params)
                )
                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    return f"SERPEX API error: {data['error']}"

                return self._format_results(data)

        except httpx.HTTPStatusError as e:
            return f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            return f"Request error occurred: {str(e)}"
        except Exception as e:
            return f"Error searching with SERPEX: {str(e)}"


__all__ = ["SerpexSearchResults"]
