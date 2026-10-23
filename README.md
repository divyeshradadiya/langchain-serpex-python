# langchain-serpex-python

[![PyPI - Version](https://img.shields.io/pypi/v/langchain-serpex-python?label=%20)](https://pypi.org/project/langchain-serpex-python/#history)
[![PyPI - License](https://img.shields.io/pypi/l/langchain-serpex-python)](https://opensource.org/licenses/MIT)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/langchainai.svg?style=social&label=Follow%20%40LangChainAI)](https://twitter.com/langchainai)

This package contains the LangChain integration with Serpex (Python).

## Installation

```bash
pip install langchain-serpex-python
```

## What is Serpex?

Serpex is the web search API and extract API for AI agents. Search returns
ranked web results (title, URL, snippet), optionally with page content as
markdown; Extract turns known URLs into clean markdown. It's built for AI
agents, LLM tools and RAG pipelines.

## Features

- **Web search**: ranked results for any query, optionally with page content as markdown
- **Nothing to configure**: every search is routed automatically
- **LangChain-native**: a drop-in `BaseTool` for agents and chains
- **Easy integration**: API key via argument or `SERPEX_API_KEY`

## Quick Start

### Get Your API Key

Sign up at [SERPEX](https://serpex.dev) to get your API key.

### Basic Usage

```python
from langchain_serpex_python import SerpexSearchResults

# Initialize the tool
tool = SerpexSearchResults(api_key="your-serpex-api-key")

# Perform a search
results = tool.invoke("latest AI developments")
print(results)
```

### With Agents

```python
from langchain_serpex_python import SerpexSearchResults
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType

# Initialize the search tool
search_tool = SerpexSearchResults(api_key="your-serpex-api-key")

# Initialize the LLM
llm = ChatOpenAI(temperature=0)

# Create an agent with the search tool
agent = initialize_agent(
    tools=[search_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Run the agent
result = agent.run("What are the latest developments in quantum computing?")
print(result)
```

### Advanced Configuration

```python
from langchain_serpex_python import SerpexSearchResults

# Also fetch page content (markdown) for the top 5 or 10 results
tool = SerpexSearchResults(
    api_key="your-serpex-api-key",
    include_content=True,
    content_results=5,
)

results = tool.invoke("best restaurants")
print(results)
```

### Deprecated parameters

Every search is routed automatically, so there is nothing to select. `engine`,
`category` and `time_range` are deprecated and ignored by the Serpex API; they
are still accepted so existing code keeps working, emit a `DeprecationWarning`,
and are not sent. They will be removed in 0.3.0. For a date filter, put
`after:YYYY-MM-DD` / `before:YYYY-MM-DD` in the query; `site:` and `-site:` work
the same way.

## Configuration

### Environment Variables

You can set your SERPEX API key as an environment variable:

```bash
export SERPEX_API_KEY="your-serpex-api-key"
```

Then use the tool without passing the API key:

```python
from langchain_serpex_python import SerpexSearchResults

tool = SerpexSearchResults()  # Will use SERPEX_API_KEY from environment
```

### Parameters

- `api_key` (str): Your Serpex API key (required)
- `include_content` (bool): Also fetch page content (markdown) for the top results (default: `False`). Best-effort: a page that can't be extracted shows its `content_error` instead.
- `content_results` (int): How many top results get content, `5` or `10` (default: `5`)
- `timeout` (float): Request timeout in seconds (default: 60, or 100 with `include_content`)
- `base_url` (str): API base URL (default `https://api.serpex.dev`)
- `engine`, `category`, `time_range`: **Deprecated** — ignored by the Serpex API and not sent; removed in 0.3.0

The tool sends only `q`, plus `include_content` / `content_results` when page content is on.

### Output

A numbered list: title, URL and snippet per result, then `Content:` (page markdown) or
`Content unavailable: <reason>` for the top `content_results` results when `include_content` is
on. An empty search returns the API's explanation, including whether it was charged.

### Errors

Errors are returned as text the agent can act on (the tool does not raise):
`Error searching with Serpex: ...` with one sentence per HTTP status — 400 (bad argument), 401
(check `SERPEX_API_KEY`), 402 (out of credits), 429 (rate limit: 5, 25 or 50 requests per second
by plan, with the wait), 5xx (temporary, not charged).

### Credits

1 per search. With `include_content`: 1 when no page came back, 3 for 1-5 pages, 6 for 6-10
pages. An empty result is charged only when it was confirmed as genuinely empty.

## How it calls the API

Through the official [`serpex`](https://pypi.org/project/serpex/) SDK, so request parameters,
timeouts and error parsing follow the SDK. `ainvoke` runs the same call in LangChain's thread
executor. Requests carry `User-Agent: serpex-python/<sdk version> langchain-serpex-python/<version>`.

## Documentation

For more detailed documentation, visit:
- [LangChain Documentation](https://python.langchain.com)
- [SERPEX API Documentation](https://serpex.dev/docs)

## Support

For issues and questions:
- GitHub Issues: [langchain-serpex issues](https://github.com/langchain-ai/langchain/issues)
- SERPEX Support: [support@serpex.dev](mailto:support@serpex.dev)

## License

This package is licensed under the MIT License.

## CI / Publishing

A GitHub Actions workflow is provided to publish the package to PyPI when a tag like `v*` is pushed or when a release is published.

Required repository secret:
- `PYPI_API_TOKEN` — a PyPI API token with permission to upload the package. Set this in the repository's Settings → Secrets → Actions.

To publish a new release, create a tag `vMAJOR.MINOR.PATCH` and push it or create a release in GitHub; the workflow will build sdist and wheel and upload them to PyPI.
