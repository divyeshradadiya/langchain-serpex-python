# Changelog

## 0.1.6 — 2026-09-22

- docs: positioning — Serpex is a real-time web search API; README, docstrings and the tool description updated. Docstring examples now use the real package/module names (`langchain-serpex-python` / `langchain_serpex_python`).
- `engine` deprecated (ignored by the API since 2026-06). The `engine` field is still accepted with the same default; request behaviour is unchanged. Class, tool name and exports unchanged.
- Tests: engine names removed; integration tests import the real module. Removed committed `__pycache__` files.
- package description, keywords and repository URLs updated.
