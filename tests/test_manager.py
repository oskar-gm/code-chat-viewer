"""Capa 2 — utilidades de orquestación de manager.py.

Funciones que deciden qué se procesa, cómo se nombra y cómo se clasifica cada
chat: extracción de hash, decodificación del nombre de proyecto, lectura de
metadata del JSONL, detección de snapshots, categorización y frescura.

Las que leen disco usan sandboxes temporales (tmp_path / write_jsonl); nunca se
tocan rutas reales del usuario.
"""

import json
import os


# ====== get_hash_from_filename ======

def test_hash_desde_jsonl_uuid(mgr):
    assert mgr.get_hash_from_filename("a1b2c3d4-0000-0000-0000-000000000000.jsonl") == "a1b2c3d4"


def test_needs_force_recommendation(mgr):
    """Solo un salto minor/major (o sin dato) recomienda re-ejecutar Force."""
    f = mgr._needs_force_recommendation
    assert f(None, "2.5.0") is True       # sin dato → recomendar
    assert f("2.4.0", "2.5.0") is True    # minor
    assert f("2.5.0", "3.0.0") is True    # major
    assert f("2.5.0", "2.5.1") is False   # patch
    assert f("2.5.0", "2.5.0") is False   # igual
    assert f("2.6.0", "2.5.0") is False   # downgrade


def test_hash_desde_html_con_formato(mgr):
    assert mgr.get_hash_from_filename("Chat 2026-06-13 09-00 a1b2c3d4.html") == "a1b2c3d4"


def test_hash_desde_agent(mgr):
    # Los chats de agente usan el hash completo (segmento final), no un prefijo
    # fijo — con cientos de agentes un prefijo de 8 chars colisionaría.
    assert mgr.get_hash_from_filename("agent-abcdef123456.jsonl") == "abcdef123456"
    # Agente nombrado: el id único es el último segmento tras el guion.
    assert mgr.agent_hash_from_filename("agent-aside_question-1a104980fbea3b18.jsonl") == "1a104980fbea3b18"
    assert mgr.agent_hash_from_filename("agent-acompact-9f315b1c0102be2b.jsonl") == "9f315b1c0102be2b"
    # El HTML del agente lleva 'Agent-<hash>' y se recupera el mismo hash.
    assert mgr.get_hash_from_filename("Chat 2026-06-19 Agent-1a104980fbea3b18.html") == "1a104980fbea3b18"


def test_is_fork_context_ref(mgr, write_jsonl):
    """En subagents/, distingue una referencia de contexto (no es un chat) de un
    chat de agente real — la primera se excluye del escaneo."""
    fork = write_jsonl([{"type": "fork-context-ref", "agentId": "x",
                         "parentSessionId": "s", "contextLength": 1000}],
                        name="agent-aoye-x.jsonl")
    real = write_jsonl([{"type": "user", "isSidechain": True, "sessionId": "s",
                         "message": {"role": "user", "content": "hola"}}],
                       name="agent-ax.jsonl")
    assert mgr.is_fork_context_ref(fork) is True
    assert mgr.is_fork_context_ref(real) is False


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


def test_parse_html_filename_agente_conserva_el_hash_completo(mgr):
    """Regresión: truncar el hash a 8 caracteres dejaba a los chats de agente
    con 'Agent-XX' (dos hex de entropía), así que la clave de deduplicado
    colisionaba y el dashboard escondía casi todos. El hash de un agente es su
    sufijo completo, y dos agentes distintos NO pueden compartir clave."""
    a = mgr.parse_html_filename("Chat 2026-06-13 09-00 Agent-deadbeef12345678.html")
    b = mgr.parse_html_filename("Chat 2026-06-13 09-05 Agent-deadbeef87654321.html")
    assert a["hash"] == "deadbeef12345678"
    assert b["hash"] == "deadbeef87654321"
    assert a["hash"] != b["hash"]          # sin colisión de clave de dedupe
    assert a["date"] is not None           # la fecha sigue parseándose
    # los chats normales mantienen su prefijo de 8
    assert mgr.parse_html_filename("Chat 2026-06-13 09-00 a1b2c3d4.html")["hash"] == "a1b2c3d4"


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


def test_extract_metadata_ai_title(mgr, write_jsonl):
    path = write_jsonl([
        {"type": "ai-title", "aiTitle": "Título generado por IA", "sessionId": "s"},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}},
    ])
    meta = mgr.extract_jsonl_metadata(path)
    assert meta["ai_title"] == "Título generado por IA"


def test_extract_metadata_first_prompt_salta_caveat(mgr, write_jsonl):
    # Un caveat al inicio (típico tras un compact) no debe ser el first_prompt.
    path = write_jsonl([
        {"type": "user", "message": {"role": "user",
         "content": [{"type": "text", "text": "<local-command-caveat>Caveat: ...</local-command-caveat>"}]}},
        {"type": "user", "message": {"role": "user",
         "content": [{"type": "text", "text": "el prompt real del usuario"}]}},
    ])
    meta = mgr.extract_jsonl_metadata(path)
    assert meta["first_prompt"].startswith("el prompt real")
    assert meta["messages"] == 1  # el caveat no cuenta como mensaje


def test_extract_metadata_first_prompt_salta_command_stdout(mgr, write_jsonl):
    path = write_jsonl([
        {"type": "user", "message": {"role": "user",
         "content": [{"type": "text", "text": "<command-name>/estado</command-name>"}]}},
        {"type": "user", "message": {"role": "user",
         "content": [{"type": "text", "text": "<local-command-stdout>salida</local-command-stdout>"}]}},
        {"type": "user", "message": {"role": "user",
         "content": [{"type": "text", "text": "prompt de verdad"}]}},
    ])
    meta = mgr.extract_jsonl_metadata(path)
    assert meta["first_prompt"].startswith("prompt de verdad")
    assert meta["messages"] == 1


# ====== resolve_chat_title (cadena de nombres) ======

def test_resolve_title_ai_title_sobre_first_prompt(mgr, write_jsonl):
    # Sin /rename ni summary: ai-title gana al primer prompt.
    path = write_jsonl([
        {"type": "ai-title", "aiTitle": "Título IA", "sessionId": "s"},
        {"type": "user", "message": {"role": "user",
         "content": [{"type": "text", "text": "primer prompt largo del chat"}]}},
    ])
    assert mgr.resolve_chat_title(path, sessions_meta={}) == "Título IA"


def test_resolve_title_rename_gana_a_ai_title(mgr, write_jsonl):
    # El /rename (custom-title) siempre prevalece sobre ai-title.
    path = write_jsonl([
        {"type": "custom-title", "customTitle": "Mi rename"},
        {"type": "ai-title", "aiTitle": "Título IA", "sessionId": "s"},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}},
    ])
    assert mgr.resolve_chat_title(path, sessions_meta={}) == "Mi rename"


def test_resolve_title_first_prompt_si_no_hay_ai_title(mgr, write_jsonl):
    # Sin ai-title, cae al primer prompt como antes.
    path = write_jsonl([
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "el primer prompt"}]}},
    ])
    assert mgr.resolve_chat_title(path, sessions_meta={}) == "el primer prompt"


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


# ====== is_snapshot_only conservador ante error de lectura ======

def test_is_snapshot_only_error_lectura_es_conservador(mgr, tmp_path):
    """Un fichero ilegible se trata como chat real (False), nunca como snapshot-only,
    para no borrar un HTML bueno por un fallo transitorio de lectura."""
    assert mgr.is_snapshot_only(tmp_path / "no-existe.jsonl") is False


def test_is_snapshot_only_solo_snapshots(mgr, tmp_path):
    """Un JSONL sin mensajes user/assistant (solo snapshots) sí es snapshot-only."""
    p = tmp_path / "snap.jsonl"
    p.write_text('{"type":"file-history-snapshot","messageId":"m1"}\n', encoding="utf-8")
    assert mgr.is_snapshot_only(p) is True


# ====== find_jsonl_by_ident (resolución de un chat para --only) ======

def _make_source(tmp_path):
    """Monta un source_path con un proyecto vacío y devuelve (source, project_dir)."""
    source = tmp_path / "projects"
    proj = source / "C--Users-x-proj"
    proj.mkdir(parents=True)
    return source, proj


def test_find_jsonl_by_ident_hash_y_uuid(mgr, tmp_path):
    """Un hash prefix (>= 8 hex) o el UUID completo resuelven al JSONL por nombre."""
    source, proj = _make_source(tmp_path)
    jsonl = proj / "a1b2c3d4-0000-0000-0000-000000000000.jsonl"
    jsonl.write_text(
        json.dumps({"type": "user", "message": {"role": "user",
                    "content": [{"type": "text", "text": "hola"}]}}) + "\n",
        encoding="utf-8")
    assert mgr.find_jsonl_by_ident("a1b2c3d4", source) == jsonl
    assert mgr.find_jsonl_by_ident("a1b2c3d4-0000-0000-0000-000000000000", source) == jsonl


def test_find_jsonl_by_ident_no_encontrado(mgr, tmp_path):
    """Un identificador que no casa con ningún chat (ni vacío) devuelve None."""
    source, proj = _make_source(tmp_path)
    (proj / "a1b2c3d4-0000-0000-0000-000000000000.jsonl").write_text(
        json.dumps({"type": "user", "message": {"role": "user",
                    "content": [{"type": "text", "text": "hola"}]}}) + "\n",
        encoding="utf-8")
    assert mgr.find_jsonl_by_ident("ffffffff", source) is None
    assert mgr.find_jsonl_by_ident("", source) is None


def test_find_jsonl_by_ident_texto_por_titulo(mgr, tmp_path):
    """Texto libre casa contra el custom-title del chat (case-insensitive)."""
    source, proj = _make_source(tmp_path)
    jsonl = proj / "a1b2c3d4-0000-0000-0000-000000000000.jsonl"
    jsonl.write_text(
        json.dumps({"type": "custom-title", "customTitle": "Proyecto VTC"}) + "\n" +
        json.dumps({"type": "user", "message": {"role": "user",
                    "content": [{"type": "text", "text": "hola"}]}}) + "\n",
        encoding="utf-8")
    assert mgr.find_jsonl_by_ident("proyecto vtc", source) == jsonl


def test_jsonl_con_byte_no_utf8_no_aborta(mgr, tmp_path):
    """Regresión: un solo byte no-UTF8 (una sesión viva a medio escribir, un
    archivo truncado) lanzaba UnicodeDecodeError. Como NO es subclase de OSError,
    escapaba de los guards y abortaba la ejecución COMPLETA del manager. Las
    lecturas de JSONL toleran ahora bytes inválidos y los guards lo contemplan."""
    malo = tmp_path / "corrupto.jsonl"
    linea = json.dumps({"type": "user", "message": {"role": "user",
                        "content": [{"type": "text", "text": "hola"}]}})
    # byte 0x80 suelto: inválido en UTF-8
    malo.write_bytes(linea.encode("utf-8") + b"\n" + b'{"type": "user", "x": "\x80"}\n')

    # ninguna de las dos lecturas puede lanzar: antes, ambas reventaban la pasada
    assert mgr.is_snapshot_only(malo) is False      # hay un user real -> no es snapshot-only
    meta = mgr.extract_jsonl_metadata(malo)
    assert isinstance(meta, dict)


def test_version_tuple_tolera_tags_no_numericos(mgr):
    """Regresión: un tag de release con sufijo ('2.7.0-rc1') hacía que
    _version_tuple devolviera None, y la comparación `None <= tuple` reventaba
    la opción [6] Check updates con un TypeError."""
    assert mgr._version_tuple("2.6.0") == (2, 6, 0)
    assert mgr._version_tuple("2.7.0-rc1") == (2, 7, 0)     # sufijo tolerado
    assert mgr._version_tuple("2.7.0+build5") == (2, 7, 0)
    assert mgr._version_tuple("sin-numeros") is None        # sigue avisando
    # la comparación que usa Check updates no puede lanzar con ninguno de ellos
    for tag in ("2.7.0-rc1", "2.6.0", "sin-numeros", ""):
        latest, current = mgr._version_tuple(tag), mgr._version_tuple(mgr.APP_VERSION)
        assert (not tag or not latest or not current or latest <= current) in (True, False)


def test_carpeta_de_archivo_vacia_no_borra_los_html(mgr, tmp_path):
    """Regresión: con `archive.folder` vacío (o '.'), la carpeta destino era la
    misma Chats/, mover el archivo sobre sí mismo caía en la rama de «duplicado»
    y el HTML se BORRABA. Ahora un nombre inválido cae al valor por defecto y el
    chat se archiva, no se pierde."""
    import os, time
    for malo in ("", ".", "  ", "../fuera", "a/b"):
        base = tmp_path / f"caso{abs(hash(malo))}"
        chats = base / "out" / "Chats"
        chats.mkdir(parents=True)
        (base / "projects").mkdir()
        html = chats / "Chat 2026-01-01 09-00 a1b2c3d4.html"
        html.write_text("<html>chat</html>", encoding="utf-8")
        viejo = time.time() - 60 * 86400
        os.utime(html, (viejo, viejo))
        config = {"_resolved": {"chats_path": chats, "source_path": base / "projects"},
                  "output": {"index_filename": "D.html"}, "inactive_days": 5,
                  "archive": {"enabled": True, "folder": malo}}
        mgr.manage_archived(config)
        supervivientes = list((base / "out").rglob("*.html"))
        assert supervivientes, f"folder={malo!r}: el HTML se borró"
        assert supervivientes[0].parent.name == "Archived", f"folder={malo!r}: no se archivó"


def test_safe_subfolder_acepta_nombres_validos(mgr):
    assert mgr._safe_subfolder("Archivados", "Archived") == "Archivados"
    assert mgr._safe_subfolder(" Old ", "Archived") == "Old"
    assert mgr._safe_subfolder(None, "Shorts") == "Shorts"


_CONFIG_EXISTENTE = {
    "source": {"projects_path": "~/x"},
    "output": {"folder": "~/o", "index_filename": "D.html"},
    "time_format": "24h",
    "agents": {"include": True, "min_size_kb": 3, "include_compaction": False},
    "inactive_days": 5,
    "shorts": {"enabled": True, "folder": "Shorts", "max_size_kb": 40},
    "archive": {"enabled": True, "folder": "Archived"},
    "last_run_version": "2.6.0",
}


def test_reconfigurar_conserva_lo_que_no_pregunta(mgr, tmp_path, monkeypatch):
    """Regresión: el setup guiado reescribía config.json desde cero y perdía
    `last_run_version` (volvía el aviso de «regenera todo» tras cada
    reconfiguración), y lo escribía siempre en la raíz del proyecto aunque la
    configuración en uso estuviera en otra carpeta. La raíz se redirige a una
    carpeta temporal: el test nunca puede tocar la configuración real."""
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    monkeypatch.setattr(mgr, "PROJECT_ROOT", raiz)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")   # Enter: valores actuales
    destino = tmp_path / "en-uso" / "config.json"
    destino.parent.mkdir()
    assert mgr.interactive_setup(existing=dict(_CONFIG_EXISTENTE), config_path=destino) == destino
    guardado = json.loads(destino.read_text(encoding="utf-8"))
    assert guardado["last_run_version"] == "2.6.0"
    assert guardado["time_format"] == "24h"
    assert not (raiz / "config.json").exists()


def test_reconfigurar_desde_el_menu_reescribe_la_configuracion_en_uso(mgr, tmp_path, monkeypatch):
    """El menú [5] Reconfigure → [1] rehace el setup sobre el config.json que
    está en uso (el que se cargó, esté donde esté), sin arrastrar los datos
    internos de la ejecución. La raíz se redirige a una carpeta temporal."""
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    monkeypatch.setattr(mgr, "PROJECT_ROOT", raiz)
    respuestas = iter(["1", "y"])                       # opción 1 y confirmar; luego Enter
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(respuestas, ""))
    destino = tmp_path / "en-uso" / "config.json"
    destino.parent.mkdir()
    mgr.reconfigure({**_CONFIG_EXISTENTE, "_resolved": {"config_path": destino}})
    guardado = json.loads(destino.read_text(encoding="utf-8"))
    assert guardado["last_run_version"] == "2.6.0"
    assert "_resolved" not in guardado
    assert not (raiz / "config.json").exists()


def test_sesion_actual_no_toma_otro_proyecto(mgr, tmp_path):
    """Regresión: `--current` aceptaba el primer proyecto cuyo nombre CONTENÍA
    la carpeta de trabajo, o que simplemente empezaba igual; desde una carpeta
    madre o hermana devolvía el chat de otro proyecto. Ahora gana el proyecto de
    la carpeta de trabajo o, desde una subcarpeta, el de su antepasado más
    cercano: solo antepasados reales, nunca un hermano cuyo nombre empiece igual
    (`proj_backup`, `proj.old` o `proj-otro` junto a `proj`) ni uno más profundo."""
    import re

    def codifica(carpeta):   # como nombra Claude Code las carpetas de proyecto
        return re.sub(r"[^A-Za-z0-9]", "-", str(carpeta))

    base = tmp_path / "x"
    source = tmp_path / "projects"
    for carpeta in (base / "proj", base / "proj" / "sub", base / "projotro"):
        d = source / codifica(carpeta)
        d.mkdir(parents=True)
        (d / "s.jsonl").write_text("{}", encoding="utf-8")

    def proyecto(cwd):
        r = mgr.find_current_jsonl(source, cwd=cwd)
        return r.parent.name if r else None

    assert proyecto(base / "proj") == codifica(base / "proj")
    assert proyecto(base / "proj" / "docs" / "notas") == codifica(base / "proj")
    assert proyecto(base / "proj" / "sub") == codifica(base / "proj" / "sub")
    for ajena in (base, base / "pro", base / "proj_backup", base / "proj.old", base / "proj-otro"):
        assert proyecto(ajena) is None, ajena


def test_aviso_de_force_no_sale_en_una_instalacion_nueva(mgr, tmp_path, monkeypatch):
    """Una instalación nueva (sin ningún chat generado) no tiene nada hecho con
    una versión anterior: no se le recomienda regenerarlo todo y queda apuntada
    la versión actual. Con chats ya generados y sin versión apuntada (una
    instalación anterior al aviso), sí se recomienda."""
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"time_format": "24h"}), encoding="utf-8")
    monkeypatch.setattr(mgr, "find_config", lambda: config)
    chats = tmp_path / "Chats"
    assert mgr._version_notice_needed(chats) == (False, None)
    assert json.loads(config.read_text(encoding="utf-8"))["last_run_version"] == mgr.APP_VERSION
    config.write_text(json.dumps({"time_format": "24h"}), encoding="utf-8")
    chats.mkdir()
    (chats / "Chat 2026-01-01 09-00 a1b2c3d4.html").write_text("x", encoding="utf-8")
    assert mgr._version_notice_needed(chats) == (True, None)


def test_compact_sin_bandera_no_cuenta_ni_da_nombre(mgr, write_jsonl):
    """El panel reconoce los compacts con el mismo criterio que el chat (marca
    `isCompactSummary` o la frase de continuación): un compact antiguo sin la
    marca no cuenta como mensaje ni se toma como primer prompt."""
    path = write_jsonl([
        {"type": "user", "message": {"role": "user", "content": [{"type": "text",
         "text": "This session is being continued from a previous conversation. RESUMEN"}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "prompt real"}]}},
    ])
    meta = mgr.extract_jsonl_metadata(path)
    assert meta["messages"] == 1
    assert meta["first_prompt"].startswith("prompt real")
