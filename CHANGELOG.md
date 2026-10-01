# Changelog

## 0.2.0 — 2026-10-01

- New `include_content` / `content_results` (5 or 10): page content (markdown) for the top results, rendered under each result; failed pages show their `content_error`.
- Only `q` (plus the content options) is sent. `engine`, `category` and `time_range` are still accepted but emit a `DeprecationWarning` and are not sent (the API ignores them); removed in 0.3.0. Their defaults are now `None`.
- Removed parsing of `answers`, `infoboxes`, `suggestions`, `corrections` and `published_date` (the API never returns them). A no-results response shows the API's `message`.
- Timeouts: 60 s, or 100 s with `include_content`; new `timeout` field.
- Every request sends `User-Agent: langchain-serpex-python/<version>`; `__version__` exported.

## 0.1.6 — 2026-09-22

- docs: positioning — Serpex is a real-time web search API; README, docstrings and the tool description updated. Docstring examples now use the real package/module names (`langchain-serpex-python` / `langchain_serpex_python`).
- `engine` deprecated (ignored by the API since 2026-06). The `engine` field is still accepted with the same default; request behaviour is unchanged. Class, tool name and exports unchanged.
- Tests: engine names removed; integration tests import the real module. Removed committed `__pycache__` files.
- package description, keywords and repository URLs updated.
