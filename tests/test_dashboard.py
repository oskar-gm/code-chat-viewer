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


def test_generate_index_control_ambito_filtro(mgr, dashboard_sandbox):
    config, output_dir, _ = dashboard_sandbox
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    # Control de ámbito presente, por defecto "solo nombres" (checkbox checked).
    assert "searchScopeNames" in html
    assert "Search names only" in html
    assert "namesOnly" in html  # la lógica de filtrado lo usa


def test_generate_index_toolbar_rediseno(mgr, dashboard_sandbox):
    config, output_dir, _ = dashboard_sandbox
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    # Botón Search (toggle), fila de búsqueda desplegable con selector directo.
    assert "searchToggle" in html
    assert 'id="searchRow"' in html
    assert "scope-check" in html  # selector directo (sin popover)
    # Select sigue presente (modo selección clásico restaurado).
    assert "selectModeBtn" in html
    # Overlay de carga (anti doble-salto al restaurar estado).
    assert 'id="dashLoading"' in html


def test_generate_index_clear_y_responsive(mgr, dashboard_sandbox):
    config, output_dir, _ = dashboard_sandbox
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    # Botón Clear: resetea el estado guardado y recarga.
    assert "clearBtn" in html
    assert "removeItem(STATE_KEY)" in html
    # Saltos responsive escalonados (dos breakpoints).
    assert "tb-break-1" in html
    assert "tb-break-2" in html
    assert "max-width: 1000px" in html
    assert "max-width: 680px" in html
    # Separadores robustos: el primer bloque de cada línea pierde su separador.
    assert "tb-rowstart" in html
    assert "syncToolbarSeparators" in html


def test_generate_index_persiste_select_mode(mgr, dashboard_sandbox):
    """El dashboard persiste el modo Select en localStorage; las marcas
    individuales de borrado NO se persisten (transitorias, evita borrados tras
    refresh)."""
    config, output_dir, _ = dashboard_sandbox
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    assert "state.selectMode = selectMode" in html            # se guarda
    assert "if (saved.selectMode) selectBtn.click()" in html  # se restaura


def test_agente_vinculado_a_invocador(mgr, dashboard_sandbox):
    """Un chat de agente (en subagents/) se escanea y se vincula a su chat
    invocador por el UUID de sesión (parent_session); no es huérfano si el
    invocador está presente, y su título es el prompt de invocación."""
    config, output_dir, source_dir = dashboard_sandbox
    proj = source_dir / "C--Users-demo-proyecto"
    sess = "a1b2c3d4-0000-0000-0000-000000000000"
    sub = proj / sess / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-deadbeef12345678.jsonl").write_text(
        json.dumps({"type": "user", "isSidechain": True, "sessionId": sess,
                    "cwd": "/home/demo/proyecto",
                    "message": {"role": "user",
                                "content": [{"type": "text", "text": "Audita la seguridad"}]}}) + "\n",
        encoding="utf-8")
    (output_dir / "Chats" / "Chat 2026-06-13 09-00 Agent-deadbeef12345678.html").write_text(
        "<html>agent</html>", encoding="utf-8")

    chats = mgr.collect_chats_data(config)
    agent = next(c for c in chats if c["is_agent"])
    normal = next(c for c in chats if not c["is_agent"])
    assert agent["parent_session"] == sess
    assert normal["session_id_full"] == sess           # el invocador está presente
    assert agent["is_orphan_agent"] is False           # vinculado, no huérfano
    assert agent["name"] == "Audita la seguridad"  # título = prompt de invocación


def test_agente_nombre_subagent_type_descripcion(mgr, dashboard_sandbox):
    """El nombre del agente es '[subagent_type] · [description]', tomado del Agent
    tool_use de la sesión padre y casado por toolUseResult.agentId."""
    mgr._AGENT_INV_CACHE.clear()
    config, output_dir, source_dir = dashboard_sandbox
    proj = source_dir / "C--Users-demo-proyecto"
    sess = "a1b2c3d4-0000-0000-0000-000000000000"
    aid = "deadbeef12345678"
    # Padre que invoca el agente: tool_use Agent + tool_result con toolUseResult.agentId
    (proj / (sess + ".jsonl")).write_text("\n".join([
        json.dumps({"type": "assistant", "sessionId": sess, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_X", "name": "Agent",
             "input": {"subagent_type": "Auditor", "description": "Auditar el login"}}]}}),
        json.dumps({"type": "user", "sessionId": sess,
                    "toolUseResult": {"agentId": aid, "status": "completed"},
                    "message": {"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": "toolu_X", "content": "ok"}]}}),
    ]) + "\n", encoding="utf-8")
    sub = proj / sess / "subagents"
    sub.mkdir(parents=True)
    (sub / ("agent-" + aid + ".jsonl")).write_text(
        json.dumps({"type": "user", "isSidechain": True, "agentId": aid, "sessionId": sess,
                    "message": {"role": "user", "content": [{"type": "text", "text": "Audita"}]}}) + "\n",
        encoding="utf-8")
    (output_dir / "Chats" / ("Chat 2026-06-19 Agent-" + aid + ".html")).write_text("<html>a</html>", encoding="utf-8")

    chats = mgr.collect_chats_data(config)
    agent = next(c for c in chats if c["is_agent"])
    assert agent["name"] == "Auditor · Auditar el login"


def test_dashboard_ux_agentes(mgr, dashboard_sandbox):
    """El dashboard incluye el toggle Agents y la columna Invoked by, y marca las
    filas de agente con badge + agent-row."""
    config, output_dir, source_dir = dashboard_sandbox
    proj = source_dir / "C--Users-demo-proyecto"
    sess = "a1b2c3d4-0000-0000-0000-000000000000"
    sub = proj / sess / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-deadbeef12345678.jsonl").write_text(
        json.dumps({"type": "user", "isSidechain": True, "sessionId": sess,
                    "cwd": "/home/demo/proyecto",
                    "message": {"role": "user",
                                "content": [{"type": "text", "text": "Audita la seguridad"}]}}) + "\n",
        encoding="utf-8")
    (output_dir / "Chats" / "Chat 2026-06-13 09-00 Agent-deadbeef12345678.html").write_text(
        "<html>agent</html>", encoding="utf-8")

    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    assert 'id="agentsToggle"' in html              # toggle en la toolbar
    assert "agent-badge" in html                    # badge en la fila del agente
    assert 'class="agent-row"' in html              # fila marcada para el toggle


def test_selector_solo_filas_visibles(mgr, dashboard_sandbox):
    """El selector de borrado solo cuenta filas marcadas Y visibles (nunca ocultas
    por filtro) y desmarca las que se ocultan — evita borrar chats no vistos."""
    config, output_dir, _ = dashboard_sandbox
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    assert "tr:not(.sub-row):not(.hidden-row) .sel-box:checked" in html  # selectedRows filtra visibles
    assert "Never keep a hidden row selected" in html                    # desmarca al ocultar


def test_dashboard_boton_mas_btw_audit(mgr, dashboard_sandbox):
    """Los dashboards auxiliares (BTW, Audit) salen del menú '+' de la toolbar y
    NO como filas de chat de la tabla."""
    config, output_dir, _ = dashboard_sandbox
    (output_dir / "btw.html").write_text("<html>btw</html>", encoding="utf-8")
    (output_dir / "CCV-Audit 2026-06-19 10-00.html").write_text("<html>audit</html>", encoding="utf-8")
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    assert 'id="plusBtn"' in html and 'id="plusMenu"' in html
    assert 'href="btw.html"' in html
    assert "CCV-Audit 2026-06-19 10-00" in html
    assert 'data-html="btw.html"' not in html  # no es una fila de chat
