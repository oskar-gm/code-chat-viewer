"""Capa 2 — utilidades de orquestación de manager.py.

Funciones que deciden qué se procesa, cómo se nombra y cómo se clasifica cada
chat: extracción de hash, decodificación del nombre de proyecto, lectura de
metadata del JSONL, detección de snapshots, categorización y frescura.

Las que leen disco usan sandboxes temporales (tmp_path / write_jsonl); nunca se
tocan rutas reales del usuario.
"""

import os
from pathlib import Path


# ====== get_hash_from_filename ======

def test_hash_desde_jsonl_uuid(mgr):
    assert mgr.get_hash_from_filename("a1b2c3d4-0000-0000-0000-000000000000.jsonl") == "a1b2c3d4"


def test_hash_desde_html_con_formato(mgr):
    assert mgr.get_hash_from_filename("Chat 2026-06-13 09-00 a1b2c3d4.html") == "a1b2c3d4"


def test_hash_desde_agent(mgr):
    # 'agent-' se retira y se toman los primeros 8 caracteres.
    assert mgr.get_hash_from_filename("agent-abcdef123456.jsonl") == "abcdef12"


# ====== format_project_name ======

def test_project_name_windows(mgr):
    assert mgr.format_project_name("C--Users-john-projects-myapp") == "projects/myapp"


def test_project_name_unix(mgr):
    assert mgr.format_project_name("-home-user-code-app") == "code/app"


def test_project_name_vacio(mgr):
    assert mgr.format_project_name("") == "Unknown"


def test_project_name_sin_patron(mgr):
    assert mgr.format_project_name("proyectosuelto") == "proyectosuelto"


# ====== parse_html_filename ======

def test_parse_html_filename_con_formato(mgr):
    info = mgr.parse_html_filename("Chat 2026-06-13 09-00 a1b2c3d4.html")
    assert info["hash"] == "a1b2c3d4"
    assert info["date"] is not None
    assert info["date"].year == 2026 and info["date"].month == 6 and info["date"].day == 13


def test_parse_html_filename_sin_formato(mgr):
    info = mgr.parse_html_filename("documento_suelto.html")
    assert info["date"] is None
    assert "hash" in info


# ====== needs_update (frescura por mtime) ======

def test_needs_update_jsonl_mas_nuevo(mgr, tmp_path):
    jsonl = tmp_path / "c.jsonl"
    jsonl.write_text("{}", encoding="utf-8")
    html = tmp_path / "c.html"
    html.write_text("x", encoding="utf-8")
    os.utime(html, (1000, 1000))
    os.utime(jsonl, (2000, 2000))
    assert mgr.needs_update(jsonl, html) is True


def test_needs_update_html_al_dia(mgr, tmp_path):
    jsonl = tmp_path / "c.jsonl"
    jsonl.write_text("{}", encoding="utf-8")
    html = tmp_path / "c.html"
    html.write_text("x", encoding="utf-8")
    os.utime(jsonl, (1000, 1000))
    os.utime(html, (2000, 2000))
    assert mgr.needs_update(jsonl, html) is False


# ====== is_snapshot_only ======

def test_is_snapshot_only_verdadero(mgr, write_jsonl):
    path = write_jsonl([
        {"type": "file-history-snapshot", "messageId": "snap1"},
        {"type": "file-history-snapshot", "messageId": "snap2"},
    ])
    assert mgr.is_snapshot_only(path) is True


def test_is_snapshot_only_falso_con_mensajes(mgr, write_jsonl):
    path = write_jsonl([
        {"type": "file-history-snapshot", "messageId": "snap1"},
        {"type": "user", "message": {"role": "user", "content": "hola"}},
    ])
    assert mgr.is_snapshot_only(path) is False


# ====== extract_jsonl_metadata ======

def test_extract_metadata_basico(mgr, write_jsonl):
    path = write_jsonl([
        {"type": "user", "cwd": "/home/user/proj", "gitBranch": "main",
         "message": {"role": "user", "content": [{"type": "text", "text": "primer prompt del chat"}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}},
    ])
    meta = mgr.extract_jsonl_metadata(path)
    assert meta["messages"] == 1
    assert meta["first_prompt"].startswith("primer prompt")
    assert meta["cwd"] == "/home/user/proj"
    assert meta["git_branch"] == "main"


def test_extract_metadata_tool_result_no_cuenta(mgr, write_jsonl):
    path = write_jsonl([
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}},
        {"type": "user", "message": {"role": "user",
                                     "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "x"}]}},
    ])
    meta = mgr.extract_jsonl_metadata(path)
    assert meta["messages"] == 1


def test_extract_metadata_custom_title(mgr, write_jsonl):
    path = write_jsonl([
        {"type": "custom-title", "customTitle": "Mi chat renombrado"},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}},
    ])
    meta = mgr.extract_jsonl_metadata(path)
    assert meta["custom_title"] == "Mi chat renombrado"


def test_extract_metadata_recap_desde_summary(mgr, write_jsonl):
    path = write_jsonl([
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}},
        {"type": "summary", "summary": "resumen de la sesión"},
    ])
    meta = mgr.extract_jsonl_metadata(path)
    assert meta["recap"] == "resumen de la sesión"


# ====== get_chat_category ======

def test_categoria_active(mgr, tmp_path):
    base = tmp_path
    html = base / "Chats" / "chat.html"
    assert mgr.get_chat_category(html, base, {}) == "Active"


def test_categoria_archived(mgr, tmp_path):
    base = tmp_path
    html = base / "Chats" / "Archived" / "chat.html"
    assert mgr.get_chat_category(html, base, {}) == "Archived"


def test_categoria_short(mgr, tmp_path):
    base = tmp_path
    html = base / "Chats" / "Shorts" / "chat.html"
    assert mgr.get_chat_category(html, base, {}) == "Short"


def test_categoria_sin_html(mgr, tmp_path):
    assert mgr.get_chat_category(None, tmp_path, {}) == "No HTML"


# ====== _fmt_dt ======

def test_fmt_dt_12h(mgr):
    from datetime import datetime
    out = mgr._fmt_dt(datetime(2026, 6, 13, 15, 30), "12h")
    assert out.startswith("2026-06-13")
    assert out.endswith("AM") or out.endswith("PM")


def test_fmt_dt_24h(mgr):
    from datetime import datetime
    out = mgr._fmt_dt(datetime(2026, 6, 13, 15, 30), "24h")
    assert "15:30" in out
    assert not out.endswith("AM") and not out.endswith("PM")
