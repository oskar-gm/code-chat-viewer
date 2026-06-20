"""Capa 3 — regresión de bugs conocidos.

Cada test reproduce un bug real y verifica que ya NO ocurre. Si un cambio
futuro lo reintroduce, el test cae.

BUG (resuelto): AskUserQuestion con `questions` serializado como string.
Algunos clientes emiten el tool_use de AskUserQuestion con `questions` (o el
`input` entero, o los `edits` de MultiEdit) como string JSON en vez de como
lista/objeto. El render iteraba los caracteres del string y reventaba con
"'str' object has no attribute 'get'". Caso real detectado en un JSONL de
cli-dev (2026-05-03). Fix: parse defensivo (_coerce_json_list/_dict) + guardas
isinstance antes de iterar estructuras anidadas.

Nota: el bug de separadores triplicados en comandos sigue abierto — carece de
reproducción documentada y no se blinda aquí hasta disponer de un chat que lo
dispare (ver SLIPKNOT.md).
"""

import json


QUESTIONS_OBJ = [{
    "question": "¿Qué color?",
    "header": "Color",
    "multiSelect": False,
    "options": [{"label": "Azul", "description": "el del cielo"}],
}]


def test_ask_questions_como_string_no_revienta(viz):
    tool_input = {"questions": json.dumps(QUESTIONS_OBJ)}
    html = viz.render_ask_tool_use("toolu_1", tool_input)
    assert html is not None
    assert "¿Qué color?" in html
    assert "Azul" in html


def test_ask_questions_string_invalido_devuelve_none(viz):
    # Un string que no decodifica a JSON no debe romper: devuelve None.
    assert viz.render_ask_tool_use("t", {"questions": "no soy json"}) is None


def test_ask_end_to_end_desde_mensaje(viz):
    # El camino real del bug: format_message_html → format_content_item →
    # render_ask_tool_use, con questions serializado dentro del JSONL.
    msg = {
        "type": "assistant", "uuid": "x", "timestamp": "2026-06-13T09:00:00Z",
        "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "AskUserQuestion",
             "input": {"questions": json.dumps(QUESTIONS_OBJ)}},
        ]},
    }
    html = viz.format_message_html(msg, 0)  # antes: AttributeError
    assert "¿Qué color?" in html


def test_tool_use_input_como_string_no_revienta(viz):
    # input completo serializado como string JSON.
    item = {"type": "tool_use", "name": "Bash", "id": "t", "input": json.dumps({"command": "ls -la"})}
    html = viz.format_content_item(item)
    assert "Tool: Bash" in html
    assert "ls -la" in html


def test_multiedit_edits_como_string_no_revienta(viz):
    edits = json.dumps([{"old_string": "viejo", "new_string": "nuevo"}])
    html = viz.render_edit_tool_use("t", "MultiEdit", {"edits": edits})
    assert html is not None
    assert "viejo" in html
    assert "nuevo" in html


def test_ask_questions_lista_normal_sigue_funcionando(viz):
    # Retrocompatibilidad: el camino feliz (lista de verdad) no se rompe.
    html = viz.render_ask_tool_use("t", {"questions": QUESTIONS_OBJ})
    assert "¿Qué color?" in html
