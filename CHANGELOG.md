# Changelog

## 0.3.0 — 2026-10-23

Breaking (minor bump, pre-1.0): private helpers changed (below), error texts changed, `httpx` is replaced by `serpex>=2.12.0`. The deprecated `engine`, `category` and `time_range` are still accepted and will be removed in 0.4.0 (was announced for 0.3.0).

- Calls the API through the official `serpex` SDK (`>=2.12.0,<3`) instead of its own `httpx` code, so parameters, timeouts and error parsing cannot drift from the API. The response is typed (`serpex.SearchResponse`). `httpx` is no longer a dependency. The async path (`ainvoke`) runs the same call in LangChain's thread executor.
- Errors: one actionable sentence per HTTP status (400, 401 check `SERPEX_API_KEY`, 402 out of credits, 429 retry after N ms with the plan limit, 5xx temporary and not charged) instead of the raw response body.
- Private helpers changed: `_build_params()` returns `serpex.SearchParams`; `_format_results()` takes a `serpex.SearchResponse`; `_headers()` / `_timeout()` removed (the SDK owns them). New `describe_serpex_error()`.
- `uv.lock` regenerated: the old one was for a package named `langchain-serpex` and pinned langchain-core 1.0.1 against this package's `<1.0.0` constraint.
- `User-Agent: serpex-python/<sdk> langchain-serpex-python/0.3.0`.
- Offline tests against recorded API responses (`tests/unit_tests/fixtures/`).

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
