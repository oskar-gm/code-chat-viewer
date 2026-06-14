"""Capa 1 — parseo y clasificación del JSONL.

Cubre las funciones puras de visualizer.py que interpretan cada línea del
JSONL: lectura del archivo, normalización de texto, clasificadores de tipo de
mensaje y los parsers estructurados (comandos, AskUserQuestion, rechazos).

Todas reciben sus datos por argumento y devuelven por valor — sin disco, sin
red, sin estado compartido. parse_chat_json es la única que lee un archivo, y
lo hace sobre un sandbox temporal (fixture write_jsonl).
"""

import pytest


# ====== parse_chat_json ======

def test_parse_chat_json_basico(viz, write_jsonl):
    path = write_jsonl([
        {"type": "user", "message": {"role": "user", "content": "hola"}},
        {"type": "assistant", "message": {"role": "assistant", "content": "qué tal"}},
    ])
    msgs = viz.parse_chat_json(str(path))
    assert len(msgs) == 2
    assert msgs[0]["type"] == "user"
    assert msgs[1]["message"]["content"] == "qué tal"


def test_parse_chat_json_numera_lineas(viz, write_jsonl):
    path = write_jsonl([{"a": 1}, {"a": 2}, {"a": 3}])
    msgs = viz.parse_chat_json(str(path))
    assert [m["_line_number"] for m in msgs] == [1, 2, 3]


def test_parse_chat_json_ignora_lineas_vacias(viz, tmp_path):
    path = tmp_path / "con_vacias.jsonl"
    path.write_text('{"a": 1}\n\n   \n{"a": 2}\n', encoding="utf-8")
    msgs = viz.parse_chat_json(str(path))
    assert len(msgs) == 2
    # La numeración corresponde a la línea física del archivo.
    assert msgs[1]["_line_number"] == 4


def test_parse_chat_json_linea_malformada_no_rompe(viz, tmp_path, capsys):
    path = tmp_path / "malformada.jsonl"
    path.write_text('{"ok": 1}\n{ esto no es json }\n{"ok": 2}\n', encoding="utf-8")
    msgs = viz.parse_chat_json(str(path))
    # La línea corrupta se salta; las válidas se conservan.
    assert [m["ok"] for m in msgs] == [1, 2]
    assert "line 2" in capsys.readouterr().out.lower()


def test_parse_chat_json_preserva_unicode(viz, write_jsonl):
    path = write_jsonl([{"message": {"role": "user", "content": "ñandú € 日本語"}}])
    msgs = viz.parse_chat_json(str(path))
    assert msgs[0]["message"]["content"] == "ñandú € 日本語"


# ====== format_timestamp ======

def test_format_timestamp_valido_estructura(viz):
    out = viz.format_timestamp("2026-06-13T15:30:00.000Z")
    # No fijamos la hora exacta (depende de la zona local), sí el formato fecha.
    assert out.startswith("2026-06-13 ") or out.startswith("2026-06-1")
    assert len(out) >= len("2026-06-13 00:00")


def test_format_timestamp_invalido_devuelve_vacio(viz):
    assert viz.format_timestamp("no-es-fecha") == ""
    assert viz.format_timestamp("") == ""
    assert viz.format_timestamp(None) == ""


def test_format_timestamp_12h_lleva_meridiano(viz, monkeypatch):
    monkeypatch.setattr(viz, "TIME_FORMAT", "12h")
    out = viz.format_timestamp("2026-06-13T15:30:00+00:00")
    assert out.endswith("AM") or out.endswith("PM")


def test_format_timestamp_24h_sin_meridiano(viz, monkeypatch):
    monkeypatch.setattr(viz, "TIME_FORMAT", "24h")
    out = viz.format_timestamp("2026-06-13T15:30:00+00:00")
    assert not out.endswith("AM") and not out.endswith("PM")


# ====== escape_html_preserve_structure ======

def test_escape_html_neutraliza_etiquetas(viz):
    out = viz.escape_html_preserve_structure("<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_escape_html_saltos_a_br(viz):
    out = viz.escape_html_preserve_structure("línea1\nlínea2")
    assert "línea1<br>línea2" == out


def test_escape_html_compacta_saltos_excesivos(viz):
    out = viz.escape_html_preserve_structure("a\n\n\n\n\nb")
    # 3 o más saltos seguidos se reducen a 2 (un párrafo en blanco).
    assert "<br><br>" in out
    assert "<br><br><br>" not in out


def test_escape_html_espacios_multiples_a_nbsp(viz):
    out = viz.escape_html_preserve_structure("a    b")
    assert "&nbsp;" in out


def test_escape_html_recorta_br_extremos(viz):
    out = viz.escape_html_preserve_structure("\n\nhola\n\n")
    assert out == "hola"


def test_escape_html_vacio(viz):
    assert viz.escape_html_preserve_structure("") == ""


def test_escape_html_normaliza_crlf(viz):
    out = viz.escape_html_preserve_structure("a\r\nb")
    assert "\r" not in out
    assert out == "a<br>b"


# ====== strip_ansi_codes ======

def test_strip_ansi_con_escape(viz):
    assert viz.strip_ansi_codes("\x1b[31mrojo\x1b[0m") == "rojo"


def test_strip_ansi_bare(viz):
    assert viz.strip_ansi_codes("[31mrojo[0m") == "rojo"


def test_strip_ansi_colapsa_saltos(viz):
    assert viz.strip_ansi_codes("a\n\n\n\n\nb") == "a\n\nb"


# ====== Clasificadores booleanos ======

def test_is_tool_result_message(viz):
    assert viz.is_tool_result_message([{"type": "tool_result", "content": "x"}]) is True
    assert viz.is_tool_result_message([{"type": "text", "text": "x"}]) is False
    assert viz.is_tool_result_message("texto plano") is False
    assert viz.is_tool_result_message([]) is False


def test_is_compact_summary(viz):
    assert viz.is_compact_summary("This session is being continued from a previous conversation...") is True
    assert viz.is_compact_summary("  This session is being continued from a previous conversation") is True
    assert viz.is_compact_summary("mensaje normal") is False


def test_is_caveat_message(viz):
    assert viz.is_caveat_message("<local-command-caveat>texto</local-command-caveat>") is True
    assert viz.is_caveat_message("sin caveat") is False


def test_is_stdout_message(viz):
    assert viz.is_stdout_message("<local-command-stdout>salida</local-command-stdout>") is True
    assert viz.is_stdout_message("sin stdout") is False


def test_is_task_notification(viz):
    assert viz.is_task_notification("<task-notification>aviso</task-notification>") is True
    assert viz.is_task_notification("sin notificación") is False


# ====== extract_tag_content / has_tag ======

def test_extract_tag_content(viz):
    assert viz.extract_tag_content("<a>hola</a>", "a") == "hola"
    assert viz.extract_tag_content("sin tag", "a") == ""


def test_extract_tag_content_multilinea(viz):
    texto = "<cmd>línea1\nlínea2</cmd>"
    assert viz.extract_tag_content(texto, "cmd") == "línea1\nlínea2"


def test_has_tag(viz):
    assert viz.has_tag("<command-name>x</command-name>", "command-name") is True
    assert viz.has_tag("nada", "command-name") is False


# ====== parse_command_tags ======

def test_parse_command_tags_completo(viz):
    texto = "<command-name>/commit</command-name><command-args>-m fix</command-args>"
    cmd = viz.parse_command_tags(texto)
    assert cmd is not None
    assert cmd["name"] == "/commit"
    assert cmd["args"] == "-m fix"
    assert cmd["display"] == "/commit -m fix"


def test_parse_command_tags_anade_barra(viz):
    texto = "<command-name>estado</command-name>"
    cmd = viz.parse_command_tags(texto)
    assert cmd["display"] == "/estado"


def test_parse_command_tags_sin_comando(viz):
    assert viz.parse_command_tags("texto normal sin tags") is None


def test_parse_command_tags_nombre_vacio(viz):
    # Tag presente pero sin nombre → no es un comando válido.
    assert viz.parse_command_tags("<command-name></command-name>") is None


# ====== parse_ask_result ======

def test_parse_ask_result_sin_prefijo(viz):
    assert viz.parse_ask_result("cualquier texto") == []


def test_parse_ask_result_par_simple(viz):
    texto = 'User has answered your questions: "¿Color?" = "Azul". You can now continue.'
    pares = viz.parse_ask_result(texto)
    assert len(pares) == 1
    assert pares[0]["question"] == "¿Color?"
    assert pares[0]["answer"] == "Azul"
    assert pares[0]["notes"] == ""
    assert pares[0]["markdown"] == ""


def test_parse_ask_result_varios_pares(viz):
    texto = ('User has answered your questions: "¿Color?" = "Azul", '
             '"¿Talla?" = "M". You can now continue.')
    pares = viz.parse_ask_result(texto)
    assert len(pares) == 2
    respuestas = {p["question"]: p["answer"] for p in pares}
    assert respuestas == {"¿Color?": "Azul", "¿Talla?": "M"}


def test_parse_ask_result_con_notas(viz):
    texto = ('User has answered your questions: "¿Color?" = "Azul" '
             'user notes: prefiero el oscuro. You can now continue.')
    pares = viz.parse_ask_result(texto)
    assert len(pares) == 1
    assert "oscuro" in pares[0]["notes"]


def test_parse_ask_result_markdown_backticks_quita_lenguaje(viz):
    texto = ('User has answered your questions: "¿Code?" = "Sí" '
             'selected markdown: ```python\nprint(1)```. You can now continue.')
    pares = viz.parse_ask_result(texto)
    assert len(pares) == 1
    assert "print(1)" in pares[0]["markdown"]
    assert "python" not in pares[0]["markdown"].splitlines()[0]


# ====== parse_user_rejection ======

def test_parse_user_rejection_con_feedback(viz):
    texto = "The user doesn't want to proceed with this tool use. the user said:\nmejor no"
    rej = viz.parse_user_rejection(texto)
    assert rej is not None
    assert rej["has_feedback"] is True
    assert rej["feedback"] == "mejor no"


def test_parse_user_rejection_sin_feedback(viz):
    texto = "The user doesn't want to proceed with this tool use."
    rej = viz.parse_user_rejection(texto)
    assert rej is not None
    assert rej["has_feedback"] is False
    assert rej["feedback"] == ""


def test_parse_user_rejection_no_es_rechazo(viz):
    assert viz.parse_user_rejection("una respuesta normal") is None


# ====== Extractores de texto ======

def test_get_text_from_content_string(viz):
    assert viz._get_text_from_content("hola") == "hola"


def test_get_text_from_content_lista(viz):
    content = [{"type": "text", "text": "primero"}, {"type": "text", "text": "segundo"}]
    assert viz._get_text_from_content(content) == "primero"


def test_get_text_from_content_vacio(viz):
    assert viz._get_text_from_content([]) == ""
    assert viz._get_text_from_content([{"type": "tool_use", "name": "x"}]) == ""


def test_get_message_text(viz):
    msg = {"message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}}
    assert viz._get_message_text(msg) == "hola"


def test_get_message_text_sin_mensaje(viz):
    assert viz._get_message_text({}) == ""


def test_get_tool_result_text_string(viz):
    assert viz._get_tool_result_text({"content": "resultado"}) == "resultado"


def test_get_tool_result_text_lista(viz):
    item = {"content": [{"type": "text", "text": "resultado"}]}
    assert viz._get_tool_result_text(item) == "resultado"
