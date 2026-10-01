"""Serpex integration for LangChain.

This module provides a LangChain tool for web search with Serpex, the web
search API and extract API for AI agents.
"""

from langchain_serpex_python.tools import SerpexSearchResults, __version__

__all__ = ["SerpexSearchResults", "__version__"]
