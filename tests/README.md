# Tests

Pytest suite that protects the core logic of Code Chat Viewer (JSONL parsing,
message classification and HTML rendering) against regressions.

## Running

```bash
cd tests
python -m pytest          # whole suite
python -m pytest -v       # verbose
python -m pytest test_parseo.py   # one file
```

Coverage report:

```bash
python -m pytest --cov=visualizer --cov=manager --cov-report=term-missing
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
| `fixtures/chat_demo.jsonl` | Synthetic chat with a bit of everything (also used for screenshots) |

## Shared schema catalog

`visualizer.py` declares `KNOWN_MESSAGE_TYPES` / `KNOWN_CONTENT_TYPES` — the
single source of truth for what CCV recognizes. `test_cobertura.py` checks the
renderers handle every type listed; the audit report (`manager.py --audit`)
flags anything outside them on real chats. Keep both in sync when adding
support for a new type.

## How modules are loaded

`visualizer.py` and `manager.py` live in `../scripts/` and are not an installed
package. `conftest.py` puts `scripts/` on `sys.path` and exposes them as the
`viz` and `mgr` fixtures. Both call `sys.stdout.reconfigure()` at import time,
which can fail under pytest capture; the loader shims stdout during import.

## Isolation

Tests never touch the user's real files:

- File-reading tests use pytest's `tmp_path` sandbox and the `write_jsonl` helper.
- `webbrowser.open` is patched to a no-op for the whole session.
- The dashboard tests create an empty `history.jsonl` inside the sandbox so
  `collect_chats_data` does not fall back to the real `~/.claude/history.jsonl`.

Tests are deterministic: same input, same result, no network.

## Dependencies

- Python 3.10+
- `pytest` (and `pytest-cov` for the coverage report)
