"""Capa 2 — dashboard (collect_chats_data + generate_index).

El dashboard escanea los HTML generados y los enriquece con la metadata de los
JSONL. Se ejercita sobre un sandbox temporal con un chat de ejemplo.

Aislamiento crítico: collect_chats_data busca un history.jsonl en
``source_path.parent`` y, si no lo encuentra, recurre a ``~/.claude/history.jsonl``
(real del usuario). El sandbox crea uno vacío para cortar ese fallback.
"""

import json

import pytest


@pytest.fixture
def dashboard_sandbox(tmp_path):
    base = tmp_path
    output_dir = base / "output"
    source_dir = base / "projects"
    chats_dir = output_dir / "Chats"
    chats_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)

    # Aislamiento: history.jsonl vacío en source_dir.parent (= base) para que
    # collect_chats_data NO recurra al ~/.claude/history.jsonl real.
    (base / "history.jsonl").write_text("", encoding="utf-8")

    # Proyecto con un JSONL cuyo hash coincide con el del HTML.
    proj = source_dir / "C--Users-demo-proyecto"
    proj.mkdir()
    jsonl = proj / "a1b2c3d4-0000-0000-0000-000000000000.jsonl"
    jsonl.write_text(
        json.dumps({
            "type": "user", "cwd": "/home/demo/proyecto", "gitBranch": "main",
            "message": {"role": "user", "content": [{"type": "text", "text": "hola dashboard"}]},
        }) + "\n",
        encoding="utf-8",
    )

    # HTML generado, con el formato de nombre que el dashboard espera.
    html = chats_dir / "Chat 2026-06-13 09-00 a1b2c3d4.html"
    html.write_text("<html>contenido del chat</html>", encoding="utf-8")

    config = {
        "_resolved": {"output_path": output_dir, "source_path": source_dir},
        "output": {"index_filename": "CCV-Dashboard.html"},
        "time_format": "12h",
        "inactive_days": 5,
        "shorts": {"enabled": False, "folder": "Shorts", "max_size_kb": 40},
        "archive": {"enabled": False, "folder": "Archived"},
    }
    return config, output_dir, source_dir


def test_collect_chats_data_detecta_chat(mgr, dashboard_sandbox):
    config, _, _ = dashboard_sandbox
    chats = mgr.collect_chats_data(config)
    assert len(chats) == 1
    chat = chats[0]
    assert chat["session_id"] == "a1b2c3d4"
    assert chat["category"] == "Active"
    assert chat["html_link"]


def test_collect_chats_data_enriquece_desde_jsonl(mgr, dashboard_sandbox):
    config, _, _ = dashboard_sandbox
    chat = mgr.collect_chats_data(config)[0]
    # La metadata del JSONL alimenta mensajes, rama y primer prompt.
    assert chat["messages"] == 1
    assert chat["branch"] == "main"
    assert "hola dashboard" in chat["first_prompt_full"]


def test_generate_index_crea_dashboard(mgr, dashboard_sandbox):
    config, output_dir, _ = dashboard_sandbox
    total = mgr.generate_index(config)
    assert total == 1
    dashboard = output_dir / "CCV-Dashboard.html"
    assert dashboard.exists()
    html = dashboard.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    # El chat aparece en la tabla (por su UUID) y hay barra de totales.
    assert "a1b2c3d4" in html
    assert "Total:" in html


def test_generate_index_dashboard_vacio(mgr, tmp_path):
    """Sin HTMLs, el dashboard se genera igualmente con 0 chats (sin romper)."""
    output_dir = tmp_path / "output"
    source_dir = tmp_path / "projects"
    output_dir.mkdir()
    source_dir.mkdir()
    (tmp_path / "history.jsonl").write_text("", encoding="utf-8")
    config = {
        "_resolved": {"output_path": output_dir, "source_path": source_dir},
        "output": {"index_filename": "CCV-Dashboard.html"},
        "time_format": "12h",
        "inactive_days": 5,
        "shorts": {"enabled": False, "folder": "Shorts", "max_size_kb": 40},
        "archive": {"enabled": False, "folder": "Archived"},
    }
    total = mgr.generate_index(config)
    assert total == 0
    assert (output_dir / "CCV-Dashboard.html").exists()
