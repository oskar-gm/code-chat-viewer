"""Capa 1 — cobertura del esquema JSONL y centinelas de lo desconocido.

Dos objetivos, motivados por la pregunta "¿esto detectará cambios de formato
de Anthropic / parseos nuevos?":

1. **Inventario vivo (cobertura positiva):** un caso por cada tipo de mensaje y
   de contenido que CCV reconoce HOY. Si una regresión deja de renderizar
   alguno, el test lo señala. Funciona como catálogo del esquema soportado.

2. **Centinelas de lo desconocido:** qué hace CCV ante un tipo que no conoce
   (lo que ocurriría si Anthropic añade uno nuevo). Documenta y blinda el
   comportamiento actual:
   - Un *contenido* de tipo desconocido se marca con `unknown-type` (visible,
     no se pierde). El centinela vigila que ese marcado siga existiendo.
   - Un *mensaje de nivel superior* de tipo desconocido sin campo `message` se
     descarta en silencio. El centinela deja constancia de esa pérdida — es el
     punto candidato a mejora (avisar en vez de callar).
"""

import pytest


# ====== Inventario: tipos de MENSAJE (format_message_html) ======

# (descripción, mensaje JSONL, marca que debe aparecer en el HTML)
MENSAJES_CONOCIDOS = [
    (
        "summary",
        {"type": "summary", "summary": "resumen de la conversación", "leafUuid": "abcdef123456"},
        "summary-msg",
    ),
    (
        "user real",
        {"type": "user", "uuid": "u1",
         "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}},
        "user-msg",
    ),
    (
        "assistant real",
        {"type": "assistant", "uuid": "a1",
         "message": {"role": "assistant", "model": "claude-opus",
                     "content": [{"type": "text", "text": "respuesta"}]}},
        "assistant-msg",
    ),
    (
        "command",
        {"type": "user", "uuid": "c1",
         "message": {"role": "user",
                     "content": [{"type": "text", "text": "<command-name>/estado</command-name>"}]}},
        "command-msg",
    ),
    (
        "stdout",
        {"type": "user", "uuid": "s1",
         "message": {"role": "user",
                     "content": [{"type": "text", "text": "<local-command-stdout>salida</local-command-stdout>"}]}},
        "stdout-msg",
    ),
    (
        "task-notification",
        {"type": "user", "uuid": "t1",
         "message": {"role": "user",
                     "content": [{"type": "text",
                                  "text": "<task-notification><summary>lista</summary><status>completed</status></task-notification>"}]}},
        "[COMPLETED]",
    ),
    (
        "tool_result",
        {"type": "user", "uuid": "tr1",
         "message": {"role": "user",
                     "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "resultado"}]}},
        "tool-result-msg",
    ),
    (
        "role desconocido",
        {"type": "user", "uuid": "o1",
         "message": {"role": "system", "content": [{"type": "text", "text": "mensaje de sistema"}]}},
        "other-msg",
    ),
]


@pytest.mark.parametrize("desc,msg,marca", MENSAJES_CONOCIDOS, ids=[m[0] for m in MENSAJES_CONOCIDOS])
def test_inventario_mensajes_conocidos(viz, desc, msg, marca):
    """Cada tipo de mensaje soportado produce su marca distintiva en el HTML."""
    html = viz.format_message_html(msg, 0)
    assert marca in html, f"El tipo '{desc}' no generó la marca esperada '{marca}'"


def test_caveat_se_oculta(viz):
    """Los mensajes caveat (texto interno del sistema) se ocultan por diseño."""
    msg = {
        "type": "user", "uuid": "cv1",
        "message": {"role": "user",
                    "content": [{"type": "text", "text": "<local-command-caveat>interno</local-command-caveat>"}]},
    }
    assert viz.format_message_html(msg, 0) == ""


def test_image_source_reference_se_oculta(viz):
    """El gemelo textual de una imagen ([Image: source: ...]) se oculta (duplicado)."""
    msg = {
        "type": "user", "uuid": "is1",
        "message": {"role": "user",
                    "content": [{"type": "text", "text": "[Image: source: C:\\x\\1.png]"}]},
    }
    assert viz.format_message_html(msg, 0) == ""


def test_tool_use_interrupted_se_oculta(viz):
    """El gemelo textual de un rechazo de tool se oculta (ya hay bloque [REJECTED])."""
    msg = {
        "type": "user", "uuid": "ti1",
        "message": {"role": "user",
                    "content": [{"type": "text", "text": "[Request interrupted by user for tool use]"}]},
    }
    assert viz.format_message_html(msg, 0) == ""
    # La interrupción simple sí se muestra (no se oculta).
    msg2 = {
        "type": "user", "uuid": "ti2",
        "message": {"role": "user",
                    "content": [{"type": "text", "text": "[Request interrupted by user]"}]},
    }
    assert viz.format_message_html(msg2, 0) != ""


# ====== Inventario: tipos de CONTENIDO (format_content_item) ======

# (descripción, item de contenido, marca esperada en el HTML)
CONTENIDOS_CONOCIDOS = [
    ("texto plano (str)", "hola mundo", "hola mundo"),
    ("text", {"type": "text", "text": "contenido"}, "contenido"),
    ("thinking", {"type": "thinking", "thinking": "razonando en voz alta"}, "thinking"),
    ("tool_use genérico", {"type": "tool_use", "name": "Bash", "id": "toolu_x", "input": {"command": "ls"}}, "tool-use"),
    ("image", {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "aGk="}}, "msg-image-link"),
]


@pytest.mark.parametrize("desc,item,marca", CONTENIDOS_CONOCIDOS, ids=[c[0] for c in CONTENIDOS_CONOCIDOS])
def test_inventario_contenidos_conocidos(viz, desc, item, marca):
    """Cada tipo de contenido soportado produce su marca distintiva."""
    html = viz.format_content_item(item)
    assert marca in html, f"El contenido '{desc}' no generó la marca esperada '{marca}'"


def test_tool_result_item_no_renderiza_inline(viz):
    """tool_result como item se renderiza a nivel de mensaje, no aquí (cadena vacía)."""
    assert viz.format_content_item({"type": "tool_result", "content": "x"}) == ""


def test_thinking_es_plegable(viz):
    """El bloque thinking se renderiza como <details> plegable con su preview."""
    html = viz.format_content_item({"type": "thinking", "thinking": "primera línea\nsegunda"})
    assert "<details" in html
    assert "Thinking" in html
    assert "primera línea" in html


# ====== Centinela: contenido de tipo DESCONOCIDO ======

def test_centinela_contenido_desconocido_se_marca(viz):
    """Un contenido de tipo nuevo NO se pierde: se marca visiblemente.

    Vigila la red de seguridad de visualizer.py: si Anthropic emite un tipo de
    bloque nuevo (p. ej. 'narration'), CCV lo muestra como unknown-type en vez
    de tirarlo en silencio. Si una regresión elimina ese marcado, este test cae.
    """
    html = viz.format_content_item({"type": "narration", "text": "prosa nueva de un formato futuro"})
    assert "unknown-type" in html
    assert "narration" in html


# ====== Centinela: mensaje de nivel superior de tipo DESCONOCIDO ======

def test_centinela_mensaje_desconocido_sin_message_se_descarta(viz):
    """Un mensaje top-level de tipo nuevo SIN campo 'message' se descarta callado.

    Comportamiento ACTUAL documentado (no deseado a futuro): a diferencia del
    contenido desconocido, aquí no hay marca de aviso. Es el punto donde un
    cambio de formato de Anthropic podría pasar inadvertido — candidato a
    mejora (emitir un aviso de tipo no reconocido). Si el día de mañana se
    decide avisar, este test deberá actualizarse a la nueva conducta.
    """
    msg = {"type": "narration_block", "narration": "texto que el formato nuevo trae aquí"}
    assert viz.format_message_html(msg, 0) == ""


# ====== Catálogo compartido (fuente de verdad auditor ↔ tests) ======

def test_catalogo_tipos_mensaje_declarados(viz):
    # El catálogo enumera los tipos de mensaje que CCV reconoce; el auditor
    # marca como novedad cualquiera fuera de este conjunto.
    for t in ("user", "assistant", "summary", "file-history-snapshot"):
        assert t in viz.KNOWN_MESSAGE_TYPES


def test_catalogo_tipos_contenido_declarados(viz):
    for t in ("text", "thinking", "tool_use", "tool_result"):
        assert t in viz.KNOWN_CONTENT_TYPES


def test_centinela_usa_tipo_fuera_del_catalogo(viz):
    # Coherencia: el tipo del test centinela debe estar FUERA del catálogo,
    # que es justo por lo que se marca como desconocido.
    assert "narration" not in viz.KNOWN_CONTENT_TYPES


def test_catalogo_metadata_de_sesion(viz):
    # Tipos de metadata/estado que Claude Code escribe en el JSONL; conocidos,
    # no son mensajes. El auditor no debe marcarlos como cambio de formato.
    for t in ("attachment", "agent-name", "permission-mode", "ai-title"):
        assert t in viz.KNOWN_METADATA_TYPES


def test_catalogo_image_en_contenido(viz):
    # 'image' es parte del formato (aunque CCV no lo renderice de forma propia).
    assert "image" in viz.KNOWN_CONTENT_TYPES
