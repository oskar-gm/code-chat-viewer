# Tests

Pytest suite that protects the core logic of Code Chat Viewer (JSONL parsing, message classification and HTML rendering) against regressions.

## Running

From the repository root:

```bash
python -m pytest tests                  # whole suite
python -m pytest tests -v               # verbose
python -m pytest tests/test_parseo.py   # one file
```

Coverage report:

```bash
python -m pytest tests --cov=visualizer --cov=manager --cov-report=term-missing
```

## Layout

| File | What it covers |
|------|----------------|
| `test_humo.py` | Smoke: pytest discovery and module loading |
| `test_parseo.py` | JSONL reading, classifiers, command/ask/rejection parsers, text extractors |
| `test_cobertura.py` | Schema inventory (every known message/content type) + sentinels for unknown types |
| `test_render.py` | Individual renderers — CSS markers, HTML escaping (anti-XSS), `None` edge cases |
| `test_html_chat.py` | `generate_html` integration over the rich demo fixture |
| `test_manager.py` | Orchestration helpers (hash, project name, JSONL metadata, category, freshness) |
| `test_dashboard.py` | `collect_chats_data` + `generate_index` over an isolated sandbox |
| `test_regresion.py` | Known bugs reproduced and verified fixed |
| `test_audit.py` | The format-anomaly detector (`audit_chats` / `generate_audit_view`) |
| `test_compatibilidad.py` | No f-string syntax that needs Python 3.12 creeps into the scripts (runs on 3.12+) |
| `fixtures/chat_demo.jsonl` | Synthetic chat with a bit of everything, for the HTML integration tests |

## Shared schema catalog

`visualizer.py` declares `KNOWN_MESSAGE_TYPES` / `KNOWN_METADATA_TYPES` / `KNOWN_CONTENT_TYPES` — the single source of truth for what CCV recognizes. `test_cobertura.py` checks the renderers handle every type listed; the audit report (`manager.py --audit`) flags anything outside them on real chats. Keep both in sync when adding support for a new type.

## How modules are loaded

`visualizer.py` and `manager.py` live in `../scripts/` and are not an installed package. `conftest.py` puts `scripts/` on `sys.path` and exposes them as the `viz` and `mgr` fixtures. Both call `sys.stdout.reconfigure()` at import time, which can fail under pytest capture; the loader shims stdout during import.

## Isolation

Tests never touch the user's real files:

- File-reading tests use pytest's `tmp_path` sandbox and the `write_jsonl` helper.
- `webbrowser.open` is patched to a no-op for the whole session.
- The dashboard tests create an empty `history.jsonl` inside the sandbox so `collect_chats_data` does not fall back to the real `~/.claude/history.jsonl`.
- The reconfiguration tests point the project root at a temporary folder, so they can never rewrite your real `config.json`.
- An autouse fixture resets the modules' global state (time format, agent map, dashboard link, invocation cache) after every test, so no result depends on the order the tests run in.

Tests are deterministic: same input, same result, no network.

## JavaScript in the pages

The chat and dashboard pages carry their JavaScript inline. Where a behaviour matters (the loading overlay's fail-safe, the copy buttons, the N/P keys, the dashboard's `#open=` deep link), the tests cut the real code out of a generated page and run it with Node against small stand-ins for the browser (`ejecuta_js` and the stand-ins in `conftest.py`). There are no in-browser tests: layout and anything that needs a real DOM is checked by hand.

## Dependencies

- Python 3.13 (the version the suite is run on)
- `pytest` (and `pytest-cov` for the coverage report)
- Node.js, optional: the tests that run the pages' JavaScript are skipped without it
