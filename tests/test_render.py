"""Capa 2 — renderizado a HTML (renderers individuales).

Cada función ``render_*`` / ``format_*`` recibe datos ya parseados y devuelve
un fragmento de HTML. Aquí se verifica, por renderer:

- la **marca distintiva** (clase CSS / etiqueta) que lo identifica,
- el **escapado seguro** del contenido que viene del chat (defensa anti-XSS),
- los **casos límite** (entradas vacías que deben devolver ``None``).

El camino del bug de AskUserQuestion con ``questions`` serializado como string
NO se prueba aquí (rompería): vive en test_regresion.py, ya con el fix.
"""

# Payload reutilizable para verificar que el contenido del chat se escapa.
XSS = '<script>alert(1)</script>'


# ====== render_command_message ======

def test_render_command_message_marca(viz):
    html = viz.render_command_message("/estado", "10:00", "10:00", "uuid123456789", "/proj")
    assert "command-msg" in html
    assert "[COMMAND]" in html
    assert "/estado" in html


def test_render_command_message_escapa(viz):
    html = viz.render_command_message(XSS, "", "", "u", "")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_command_message_uuid_vacio(viz):
    html = viz.render_command_message("/x", "", "", "", "")
    assert "N/A" in html


# ====== render_stdout_message ======

def test_render_stdout_message_marca(viz):
    html = viz.render_stdout_message("salida del comando", "10:00", "10:00", "u1", "/p")
    assert "stdout-msg" in html
    assert "[OUTPUT]" in html
    assert "nav-skip" in html
    assert "salida del comando" in html


def test_render_stdout_message_escapa(viz):
    html = viz.render_stdout_message(XSS, "", "", "u", "")
    assert "<script>" not in html


# ====== render_task_notification ======

def test_render_task_notification_completed(viz):
    text = "<task-notification><summary>tarea lista</summary><status>completed</status></task-notification>"
    html = viz.render_task_notification(text, "u1")
    assert "[COMPLETED]" in html
    assert "tarea lista" in html


def test_render_task_notification_in_progress(viz):
    text = "<task-notification><summary>en marcha</summary><status>in_progress</status></task-notification>"
    html = viz.render_task_notification(text, "u1")
    assert "[IN_PROGRESS]" in html


def test_render_task_notification_sin_status(viz):
    text = "<task-notification><summary>aviso suelto</summary></task-notification>"
    html = viz.render_task_notification(text, "u1")
    assert "[TASK]" in html


# ====== render_ask_result_block ======

def test_render_ask_result_block_qa(viz):
    pares = [{"question": "¿Color?", "answer": "Azul", "notes": "", "markdown": ""}]
    html = viz.render_ask_result_block(pares, "toolu_1", "u1")
    assert "ask-result-msg" in html
    assert "[USER RESPONSE]" in html
    assert "¿Color?" in html
    assert "Azul" in html


def test_render_ask_result_block_notas_y_markdown(viz):
    pares = [{"question": "Q", "answer": "A", "notes": "una nota", "markdown": "print(1)"}]
    html = viz.render_ask_result_block(pares, "t", "u")
    assert "una nota" in html
    assert "print(1)" in html
    assert "<pre" in html


def test_render_ask_result_block_sin_pregunta(viz):
    pares = [{"question": "", "answer": "respuesta libre", "notes": "", "markdown": ""}]
    html = viz.render_ask_result_block(pares, "t", "u")
    assert "respuesta libre" in html
    assert "Q: " not in html


def test_render_ask_result_block_escapa(viz):
    pares = [{"question": XSS, "answer": XSS, "notes": "", "markdown": ""}]
    html = viz.render_ask_result_block(pares, "t", "u")
    assert "<script>" not in html


# ====== render_user_rejection_block ======

def test_render_user_rejection_con_feedback(viz):
    rej = {"feedback": "mejor no hagas eso", "has_feedback": True}
    html = viz.render_user_rejection_block(rej, "toolu_1", "u1")
    assert "reject-msg" in html
    assert "[REJECTED]" in html
    assert "mejor no hagas eso" in html
    assert "User feedback" in html


def test_render_user_rejection_sin_feedback(viz):
    rej = {"feedback": "", "has_feedback": False}
    html = viz.render_user_rejection_block(rej, "toolu_1", "u1")
    assert "[REJECTED]" in html
    assert "nav-skip" in html


def test_render_user_rejection_escapa(viz):
    rej = {"feedback": XSS, "has_feedback": True}
    html = viz.render_user_rejection_block(rej, "t", "u")
    assert "<script>" not in html


# ====== render_compact_block ======

def test_render_compact_block_summary(viz):
    data = {"summary_text": "resumen del compact", "command_display": "/compact", "uuid": "u1234567"}
    html = viz.render_compact_block(data)
    assert "compact-msg" in html
    assert "[COMPACT]" in html
    assert "resumen del compact" in html


def test_render_compact_block_pre_compact(viz):
    data = {"summary_text": "", "pre_compact": "texto previo", "command_display": "/compact", "uuid": "u1"}
    html = viz.render_compact_block(data)
    assert "Pre-compact" in html
    assert "texto previo" in html


def test_render_compact_block_escapa(viz):
    data = {"summary_text": XSS, "command_display": "/compact", "uuid": "u1"}
    html = viz.render_compact_block(data)
    assert "<script>" not in html


# ====== render_ask_tool_use ======

def test_render_ask_tool_use_estructura(viz):
    tool_input = {
        "questions": [{
            "question": "¿Qué color?",
            "header": "Color",
            "multiSelect": False,
            "options": [
                {"label": "Azul", "description": "el del cielo"},
                {"label": "Rojo", "description": "el del fuego"},
            ],
        }]
    }
    html = viz.render_ask_tool_use("toolu_abc", tool_input)
    assert "Tool: AskUserQuestion" in html
    assert "¿Qué color?" in html
    assert "Azul" in html
    assert "el del cielo" in html
    assert "Single-select" in html


def test_render_ask_tool_use_multiselect(viz):
    # El indicador single/multi se muestra junto al header de la pregunta.
    tool_input = {"questions": [{"question": "Q", "header": "Tema", "multiSelect": True, "options": []}]}
    html = viz.render_ask_tool_use("t", tool_input)
    assert "Multi-select" in html


def test_render_ask_tool_use_markdown_opcion(viz):
    tool_input = {"questions": [{"question": "Q", "options": [{"label": "L", "markdown": "codigo()"}]}]}
    html = viz.render_ask_tool_use("t", tool_input)
    assert "codigo()" in html
    assert "<pre" in html


def test_render_ask_tool_use_sin_questions_devuelve_none(viz):
    assert viz.render_ask_tool_use("t", {"questions": []}) is None
    assert viz.render_ask_tool_use("t", {}) is None


def test_render_ask_tool_use_escapa(viz):
    tool_input = {"questions": [{"question": XSS, "options": [{"label": XSS}]}]}
    html = viz.render_ask_tool_use("t", tool_input)
    assert "<script>" not in html


# ====== render_write_tool_use ======

def test_render_write_tool_use_estructura(viz):
    tool_input = {"file_path": "/tmp/x.py", "content": "print('hola')"}
    html = viz.render_write_tool_use("toolu_w", tool_input)
    assert "tool-use-write" in html
    assert "write-block" in html
    assert "Tool: Write" in html
    assert "/tmp/x.py" in html
    assert "print(&#x27;hola&#x27;)" in html or "print('hola')" not in html


def test_render_write_tool_use_escapa(viz):
    html = viz.render_write_tool_use("t", {"file_path": "f", "content": XSS})
    assert "<script>" not in html


def test_render_write_tool_use_content_vacio(viz):
    html = viz.render_write_tool_use("t", {"file_path": "f"})
    assert "write-block" in html


# ====== render_edit_tool_use ======

def test_render_edit_tool_use_edit(viz):
    tool_input = {"file_path": "a.py", "old_string": "viejo", "new_string": "nuevo"}
    html = viz.render_edit_tool_use("toolu_e", "Edit", tool_input)
    assert "tool-use-edit" in html
    assert "edit-diff" in html
    assert "viejo" in html
    assert "nuevo" in html
    assert "Tool: Edit" in html


def test_render_edit_tool_use_multiedit(viz):
    tool_input = {"file_path": "a.py", "edits": [
        {"old_string": "a", "new_string": "b"},
        {"old_string": "c", "new_string": "d"},
    ]}
    html = viz.render_edit_tool_use("t", "MultiEdit", tool_input)
    assert "Edit 1/2" in html
    assert "Edit 2/2" in html


def test_render_edit_tool_use_replace_all_badge(viz):
    tool_input = {"old_string": "x", "new_string": "y", "replace_all": True}
    html = viz.render_edit_tool_use("t", "Edit", tool_input)
    assert "replace_all" in html


def test_render_edit_tool_use_multiedit_sin_edits_none(viz):
    assert viz.render_edit_tool_use("t", "MultiEdit", {"edits": []}) is None


def test_render_edit_tool_use_escapa(viz):
    tool_input = {"old_string": XSS, "new_string": XSS}
    html = viz.render_edit_tool_use("t", "Edit", tool_input)
    assert "<script>" not in html


# ====== render_btw_history_message ======

def test_render_btw_history_message(viz):
    data = {"query": "una pregunta rápida", "timestamp": ""}
    html = viz.render_btw_history_message(data)
    assert "btw-history-msg" in html
    assert "una pregunta rápida" in html
    assert "/btw" in html


def test_render_btw_history_message_escapa(viz):
    html = viz.render_btw_history_message({"query": XSS, "timestamp": ""})
    assert "<script>" not in html


# ====== format_tool_result_content ======

def test_format_tool_result_content_string(viz):
    html = viz.format_tool_result_content({"content": "resultado texto"})
    assert "resultado texto" in html


def test_format_tool_result_content_lista_text(viz):
    data = {"content": [{"type": "text", "text": "parte uno"}]}
    assert "parte uno" in viz.format_tool_result_content(data)


def test_format_tool_result_content_lista_no_text(viz):
    data = {"content": [{"type": "image", "source": {}}]}
    assert "[image]" in viz.format_tool_result_content(data)


def test_format_tool_result_content_escapa(viz):
    assert "<script>" not in viz.format_tool_result_content({"content": XSS})
