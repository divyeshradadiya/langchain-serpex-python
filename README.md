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

Serpex is a real-time web search API. It returns structured JSON results
(title, URL, snippet) for any query, and offers page content extraction that
turns URLs into LLM-ready markdown. It's built for AI agents, LLM tools and
RAG pipelines.

## Features

- **Real-time web search**: current results for any query
- **One search engine**: nothing to configure — no engine to pick
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

# Configure with advanced parameters
tool = SerpexSearchResults(
    api_key="your-serpex-api-key",
    time_range="month"
)

results = tool.invoke("best restaurants")
print(results)
```

### The `engine` parameter (deprecated)

Serpex is one search engine, so there is nothing to select. `engine` is
deprecated and ignored by the Serpex API since 2026-06; it is still accepted
so existing code keeps working.

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
- `engine` (str): **Deprecated** — ignored by the Serpex API (default: "auto"); still accepted
- `category` (str): Search category - currently only "web" is supported (default: "web")
- `time_range` (str): Time filter - "all", "day", "week", "month", "year"

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
