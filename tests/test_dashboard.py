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
    # El bloque Search/Clear va a la IZQUIERDA de Select/Delete en la toolbar.
    assert html.index('id="searchToggle"') < html.index('id="selectModeBtn"')
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


def test_dashboard_embebe_custom_assets_locales(mgr, dashboard_sandbox, monkeypatch, tmp_path):
    """Punto de extensión local: si existen custom/dashboard.css y
    custom/dashboard.js (carpeta gitignorada), sus contenidos se embeben en el
    dashboard — CSS al final del <head>, JS al final del <body>. Sin ellos, el
    dashboard no cambia."""
    config, output_dir, _ = dashboard_sandbox
    custom = tmp_path / "custom-assets"
    custom.mkdir()
    monkeypatch.setattr(mgr, "CUSTOM_DIR", custom)

    # Sin archivos: nada embebido.
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    assert "custom/dashboard.css (local)" not in html
    assert "custom/dashboard.js (local)" not in html

    # Con archivos: contenido embebido verbatim en su zona.
    (custom / "dashboard.css").write_text(
        "body.mi-tweak tr { display: none; }", encoding="utf-8")
    (custom / "dashboard.js").write_text(
        "console.log('mi-tweak-local');", encoding="utf-8")
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    assert "body.mi-tweak tr { display: none; }" in html
    assert "console.log('mi-tweak-local');" in html
    head = html.split("</head>", 1)[0]
    assert "custom/dashboard.css (local)" in head          # CSS dentro del head
    body = html.split("</head>", 1)[1]
    assert "custom/dashboard.js (local)" in body           # JS en el body
    assert html.index("mi-tweak-local") > html.index("copyUuid")  # tras el JS nativo


def test_enlace_de_fork_sobrevive_al_mover_el_chat(mgr, tmp_path):
    """Al archivar un chat se reescriben sus enlaces al panel; el del banner de
    fork lleva `#open=` y antes se quedaba sin corregir (enlace roto)."""
    html = tmp_path / "Chat 2026-01-01 09-00 a1b2c3d4.html"
    html.write_text('<a href="../CCV-Dashboard.html">D</a>'
                    '<a class="fork-link" href="../CCV-Dashboard.html#open=abc">o</a>',
                    encoding="utf-8")
    mgr.fix_dashboard_link(html, "CCV-Dashboard.html")
    t = html.read_text(encoding="utf-8")
    assert 'href="../../CCV-Dashboard.html"' in t
    assert 'href="../../CCV-Dashboard.html#open=abc"' in t
    assert 'href="../CCV-Dashboard.html' not in t


def test_panel_redirige_open_al_chat_y_avisa_si_no_existe(mgr, dashboard_sandbox, tmp_path):
    """El panel atiende `#open=<sesión>` (el enlace del banner de fork): ejecuta
    con Node el código real del panel sobre sus filas reales y comprueba a dónde
    redirige. Casa por sesión completa (sin distinguir mayúsculas) y por prefijo
    (filas cuyo JSONL ya no existe y solo conservan el hash corto); sin chat,
    no redirige, limpia el hash y deja el aviso para la carga. Además, todo el
    JavaScript del panel es sintácticamente válido. Se omite sin Node."""
    import html as htmlmod, re, shutil, subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("Node no disponible")
    config, output_dir, _ = dashboard_sandbox
    mgr.generate_index(config)
    page = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")

    scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
    check = tmp_path / "dash.js"
    check.write_text("\n;\n".join(scripts), encoding="utf-8")
    r = subprocess.run([node, "--check", str(check)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:800]

    start = page.index("(function()", page.index('Deep link "#open='))
    iife = page[start:page.index("})();", start) + len("})();")]
    rows = [{"uuid": htmlmod.unescape(u), "html": htmlmod.unescape(h)} for u, h in
            re.findall(r'<tr[^>]*\sdata-uuid="([^"]*)"[^>]*\sdata-html="([^"]*)"', page)]
    assert len(rows) == 1 and rows[0]["uuid"] == "a1b2c3d4-0000-0000-0000-000000000000"
    real = rows[0]["html"]
    corto = [{"uuid": "", "html": "vacio.html"}, {"uuid": "b9e8f7a6", "html": "Archived/b.html"}]
    sin_html = [{"uuid": "c0000000-0000-0000-0000-000000000000", "html": ""}]

    harness = (
        "function run(hash, rows) {\n"
        "  var out = {replaced: null, cleared: false, onload: false};\n"
        "  var location = {hash: hash, pathname: '/d.html', search: '',\n"
        "                  replace: function(u) { out.replaced = u; }};\n"
        "  var document = {querySelectorAll: function() {\n"
        "      return rows.map(function(r) { return {dataset: r}; }); }};\n"
        "  var history = {replaceState: function() { out.cleared = true; }};\n"
        "  var window = {addEventListener: function(ev) { if (ev === 'load') out.onload = true; }};\n"
        f"  {iife}\n"
        "  return out;\n"
        "}\n"
        "console.log(JSON.stringify([\n"
        f"  run('#open=a1b2c3d4-0000-0000-0000-000000000000', {json.dumps(rows)}),\n"
        f"  run('#open=A1B2C3D4-0000-0000-0000-000000000000', {json.dumps(rows)}),\n"
        f"  run('#open=b9e8f7a6-1111-2222-3333-444444444444', {json.dumps(corto)}),\n"
        f"  run('#open=c0000000-0000-0000-0000-000000000000', {json.dumps(sin_html)}),\n"
        f"  run('#open=ffffffff-0000-0000-0000-000000000000', {json.dumps(rows)}),\n"
        f"  run('#sort=name', {json.dumps(rows)})\n"
        "]));\n")
    f = tmp_path / "harness.js"
    f.write_text(harness, encoding="utf-8")
    r = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[:800]
    exacto, mayus, prefijo, sin_pagina, ausente, otro_hash = json.loads(r.stdout)

    for caso in (exacto, mayus):
        assert caso == {"replaced": real, "cleared": False, "onload": False}
    assert prefijo["replaced"] == "Archived/b.html"
    for caso in (sin_pagina, ausente):
        assert caso == {"replaced": None, "cleared": True, "onload": True}
    assert otro_hash == {"replaced": None, "cleared": False, "onload": False}


def test_categoria_desactivada_con_chats_sigue_visible(mgr, dashboard_sandbox):
    """Regresión: desactivar Shorts o Archive después de usarlos dejaba los
    chats ya movidos invisibles para siempre (el filtro de su categoría dejaba
    de existir). La categoría conserva su filtro mientras tenga chats, y la
    ayuda de categorías explica qué son aunque la función esté apagada."""
    config, output_dir, _ = dashboard_sandbox
    shorts = output_dir / "Chats" / "Shorts"
    shorts.mkdir()
    (output_dir / "Chats" / "Chat 2026-06-13 09-00 a1b2c3d4.html").rename(
        shorts / "Chat 2026-06-13 09-00 a1b2c3d4.html")
    assert config["shorts"]["enabled"] is False
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    assert 'id="filterShort"' in html
    assert "(category === 'Short' && showShort)" in html
    assert "<strong>Short:</strong> Small chats moved to Shorts/ while Shorts was enabled" in html
    assert 'id="filterArchived"' not in html       # sin chats archivados, sin filtro
    assert "<strong>Archived:</strong>" not in html


def test_panel_estado_y_controles_robustos(mgr, dashboard_sandbox, ejecuta_red_de_carga,
                                           ejecuta_js, dobles_de_copiar):
    """La pantalla de carga del panel no puede quedarse fija si el JavaScript
    falla (se ejecuta su red con Node); el botón de copiar el identificador,
    ejecutado con Node, no se atasca con un doble clic y avisa si falla; el
    modo Select se restaura AL FINAL (antes guardaba el estado con el orden y el
    interruptor Agents aún por defecto, y se perdían en la segunda recarga); y
    las columnas de texto ordenan de la A a la Z en el primer clic. Límite: estos
    dos últimos se fijan en el código (no hay pruebas en navegador)."""
    config, output_dir, _ = dashboard_sandbox
    mgr.generate_index(config)
    html = (output_dir / "CCV-Dashboard.html").read_text(encoding="utf-8")
    assert ejecuta_red_de_carga(html, "dashLoading") == [True, True]
    assert ".dash-loading {{ display: none".replace("{{", "{") in html   # <noscript>
    copia = html[html.index("function copyUuid"):]
    copia = copia[:copia.index("</script>")]
    r = ejecuta_js(dobles_de_copiar + copia + """
var b = boton('ICONO'); copyUuid(b); avanza(400); copyUuid(b); avanza(1100);
var doble = estado(b);
copiaOk = false; var f = boton('ICONO'); copyUuid(f); var fallo = estado(f);
avanza(1100);
console.log(JSON.stringify([doble, fallo, estado(f)]));
""")
    assert r == ["ICONO|", "✗|", "ICONO|"]
    restaura = html[html.index("if (saved.delMode)"):]
    assert restaura.index("sortTable(saved.sort.col") < restaura.index("selectBtn.click()")
    assert "TEXT_SORT_COLS.includes(col) ? 'asc' : 'desc'" in html
