"""Capa 2 — integración del chat completo (generate_html).

generate_html ensambla el documento HTML del chat y lo escribe a disco. Estos
tests lo ejercitan sobre la fixture demo rica (un chat con un poco de todo) y
verifican que el documento sale bien formado, que cada tipo de mensaje deja su
marca y que el contenido del chat se escapa.
"""


def test_demo_fixture_carga_limpia(viz, demo_chat_path, capsys):
    """La fixture demo es un JSONL válido: carga sin warnings y entera."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    salida = capsys.readouterr().out
    assert "Warning" not in salida
    lineas = [l for l in demo_chat_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(msgs) == len(lineas)


def test_genera_html_estructura(viz, demo_chat_path, tmp_path):
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out), chat_title="Demo", chat_uuid="a1b2c3d4-0014-0014-0014-000000000014")
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert 'charset="UTF-8"' in html
    assert viz.APP_VERSION in html


def test_genera_html_incluye_todos_los_tipos(viz, demo_chat_path, tmp_path):
    """Cada tipo de mensaje de la fixture deja su marca en el HTML final."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    # "snapshot" no está: el file-history-snapshot de la fixture es un guard
    # (sin hermano posterior), no un rewind, así que se omite por diseño. El
    # render del rewind se cubre en los tests F3 dedicados de abajo.
    marcas = [
        "thinking", "tool-use", "command-msg", "stdout-msg", "ask-result-msg",
        "reject-msg", "compact-msg", "summary-msg", "assistant-msg",
        "tool-result-msg", "[COMPLETED]",
    ]
    faltan = [m for m in marcas if m not in html]
    assert not faltan, f"Faltan marcas en el HTML generado: {faltan}"


def test_genera_html_contenido_textual(viz, demo_chat_path, tmp_path):
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "estructura" in html
    assert "Next.js" in html


def test_genera_html_titulo_y_dashboard(viz, demo_chat_path, tmp_path):
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out), dashboard_url="index.html", chat_title="Mi Demo")
    html = out.read_text(encoding="utf-8")
    assert "Mi Demo" in html
    assert "Dashboard" in html


def test_genera_html_lista_vacia_no_rompe(viz, tmp_path):
    out = tmp_path / "vacio.html"
    viz.generate_html([], str(out))
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")


def test_genera_html_escapa_xss(viz, tmp_path):
    msgs = [{
        "type": "user", "uuid": "x", "timestamp": "2026-06-13T09:00:00Z",
        "message": {"role": "user", "content": [{"type": "text", "text": "<script>alert(1)</script>"}]},
    }]
    out = tmp_path / "xss.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    # El payload del chat no debe colarse como etiqueta <script> ejecutable.
    assert "<script>alert(1)</script>" not in html


def test_genera_html_sin_llaves_fstring_rotas(viz, demo_chat_path, tmp_path):
    """La fixture no contiene '{{', así que ningún '{{' en el HTML implicaría
    un f-string mal escapado en el template (placeholder roto)."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "{{" not in html
    assert "}}" not in html


def test_genera_html_time_format_24h(viz, demo_chat_path, tmp_path):
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out), time_format="24h")
    assert viz.TIME_FORMAT == "24h"


def test_genera_html_incluye_open_image(viz, demo_chat_path, tmp_path):
    # La función JS que abre imágenes embebidas vía blob: debe estar en el chat.
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "function openImage" in html
    assert "createObjectURL" in html


def test_genera_html_incluye_modal_imagen(viz, demo_chat_path, tmp_path):
    # El modal/lightbox de imágenes (overlay + cierre) debe estar en el chat.
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert 'id="imgModal"' in html
    assert "closeImageModal" in html
    assert "img-modal" in html


def test_separador_es_linea_css_adaptable(viz, demo_chat_path, tmp_path):
    """Regresión (bug #6): el separador entre mensajes se dibuja con `border-top`
    CSS — se adapta al 100% del ancho del contenedor — en vez de un texto `─`×80
    de ancho fijo que desbordaba (scroll horizontal) en ventanas estrechas. El
    documento no debe contener ningún `─`, y cada separador es un div vacío."""
    import re
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    # El borde lo pinta el CSS, no un texto de ancho fijo
    assert "border-top: 1px solid #EEEEEE" in html
    # Ningún box-drawing ─ (U+2500) en el documento
    assert "─" not in html
    # Todos los separadores son divs vacíos (el borde es CSS)
    seps = re.findall(r'<div class="separator">(.*?)</div>', html)
    assert seps, "la fixture demo debe producir al menos un separador"
    assert all(s == "" for s in seps), "los separadores deben estar vacíos"


def test_f1_imagen_inline_reemplaza_marcador(viz, tmp_path):
    """F1: cada [Image #N] del texto se convierte en un enlace inline a su imagen
    (mapeo por orden) con el peso en el title; sin botón "Open image" duplicado."""
    img = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
           "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    msgs = [{
        "type": "user", "uuid": "u1", "timestamp": "2026-06-16T10:00:00Z",
        "message": {"role": "user", "content": [
            {"type": "text", "text": "Mira [Image #1] y [Image #2]."},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}},
        ]},
    }]
    out = tmp_path / "f1.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert html.count('class="msg-image-link inline-img"') == 2
    assert 'title="image/png,' in html
    assert '>[Image #1]</a>' in html and '>[Image #2]</a>' in html
    assert "Open image" not in html  # sin botones separados


def test_f2_metadata_modelo_antes_de_fecha(viz, tmp_path):
    """F2: en el metadata del asistente, el modelo precede a la fecha, y la
    fecha/hora va resaltada en negrita (<strong>) para que destaque."""
    import re
    msgs = [{
        "type": "assistant", "uuid": "a1", "timestamp": "2026-06-16T10:00:00Z", "gitBranch": "main",
        "message": {"role": "assistant", "model": "claude-opus-4-8",
                    "content": [{"type": "text", "text": "Hola."}]},
    }]
    out = tmp_path / "f2.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    meta = re.search(r'class="metadata">(.*?)</span>', html, re.S).group(1)
    assert meta.index("claude-opus-4-8") < meta.index("2026-06-16")
    assert "<strong>2026-06-16" in meta


def test_f3_rewind_apunta_al_destino(viz, tmp_path):
    """F3: un prompt con texto y un hermano POSTERIOR con texto (mismo
    parentUuid) es una rama abandonada por un rewind; se muestra como bloque
    .rewind en una línea (icono + conteo + «destino»), y el botón lleva al
    destino (ancestro con texto humano), no al propio prompt."""
    msgs = [
        {"type": "assistant", "uuid": "dest", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Punto de partida."}]}},
        {"type": "user", "uuid": "rama1", "parentUuid": "dest", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Primer intento."}]}},
        {"type": "file-history-snapshot", "messageId": "rama1"},
        {"type": "user", "uuid": "rama2", "parentUuid": "dest", "timestamp": "2026-06-16T10:02:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Segundo intento."}]}},
    ]
    out = tmp_path / "f3.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert 'class="rewind"' in html
    assert "Punto de partida." in html
    assert "1 message back" in html  # solo "Primer intento." se descartó
    assert "gotoMessage('dest')" in html
    assert 'data-msg-uuid="dest"' in html


def test_f3_snapshot_sin_mensaje_se_omite(viz, tmp_path):
    """F3: un snapshot cuyo messageId no apunta a ningún mensaje no se muestra."""
    msgs = [{"type": "file-history-snapshot", "messageId": "uuid-inexistente-9999"}]
    out = tmp_path / "f3b.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert '<div class="rewind">' not in html


def test_f3_rama_activa_no_es_rewind(viz, tmp_path):
    """F3: el snapshot de la rama activa (su prompt no tiene hermano posterior)
    no es un rewind y no se muestra."""
    msgs = [
        {"type": "assistant", "uuid": "dest", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Inicio."}]}},
        {"type": "user", "uuid": "soloUno", "parentUuid": "dest", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Único intento."}]}},
        {"type": "file-history-snapshot", "messageId": "soloUno"},
    ]
    out = tmp_path / "f3c.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert '<div class="rewind">' not in html


def test_f3_fork_de_herramientas_no_es_rewind(viz, tmp_path):
    """F3 (robustez): un 'fork' cuyo prompt abandonado no tiene texto humano
    (un assistant con solo tool_use) NO es un rewind de conversación y no se
    muestra, aunque comparta parentUuid con un hermano posterior."""
    msgs = [
        {"type": "assistant", "uuid": "dest", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Texto real."}]}},
        {"type": "assistant", "uuid": "tooluse", "parentUuid": "dest", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Bash", "id": "t1", "input": {}}]}},
        {"type": "file-history-snapshot", "messageId": "tooluse"},
        {"type": "user", "uuid": "toolresult", "parentUuid": "dest", "timestamp": "2026-06-16T10:02:00Z",
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}},
    ]
    out = tmp_path / "f3d.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert '<div class="rewind">' not in html


def test_f3_destino_salta_marcadores_de_sistema(viz, tmp_path):
    """F3 (robustez): el destino del rewind ignora los marcadores de sistema
    (<system-reminder>…) y toma la primera línea de texto humano del mensaje."""
    msgs = [
        {"type": "user", "uuid": "dest", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "user", "content": [{"type": "text",
             "text": "<system-reminder>\nrecordatorio interno\n</system-reminder>\nMi pregunta real."}]}},
        {"type": "user", "uuid": "rama1", "parentUuid": "dest", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento A."}]}},
        {"type": "file-history-snapshot", "messageId": "rama1"},
        {"type": "user", "uuid": "rama2", "parentUuid": "dest", "timestamp": "2026-06-16T10:02:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento B."}]}},
    ]
    out = tmp_path / "f3e.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    # El destino del rewind es la línea humana, no el marcador de sistema
    assert 'class="rewind-dest">&laquo;Mi pregunta real.' in html


def test_f3_dos_rewinds_mismo_destino_distancia_visual(viz, tmp_path):
    """F3 (regresión del "24 messages back"): con dos rewinds al MISMO destino,
    cada bloque cuenta los mensajes hasta SU propio marcador (distancia visual
    en pantalla), no la rama abandonada. El 2º no debe inflar el conteo con la
    rama larga que vino DESPUÉS de su marcador."""
    msgs = [
        {"type": "assistant", "uuid": "dest", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Destino."}]}},
        {"type": "user", "uuid": "r1", "parentUuid": "dest", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento 1."}]}},
        {"type": "file-history-snapshot", "messageId": "r1"},
        {"type": "user", "uuid": "r2", "parentUuid": "dest", "timestamp": "2026-06-16T10:02:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento 2."}]}},
        {"type": "file-history-snapshot", "messageId": "r2"},
        {"type": "assistant", "uuid": "a2", "parentUuid": "r2", "timestamp": "2026-06-16T10:03:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Trabajo largo A."}]}},
        {"type": "assistant", "uuid": "a2b", "parentUuid": "a2", "timestamp": "2026-06-16T10:04:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Trabajo largo B."}]}},
        {"type": "user", "uuid": "r3", "parentUuid": "dest", "timestamp": "2026-06-16T10:05:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento 3."}]}},
    ]
    out = tmp_path / "f3f.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "1 message back" in html       # rewind 1: dest→su marcador = 1 humano (r1)
    assert "2 messages back" in html      # rewind 2: dest→su marcador = 2 humanos (r1, r2)
    assert "4 messages back" not in html  # NO la rama larga acumulada (el bug daba esto)


def test_f3_destino_justo_encima_just_above(viz, tmp_path):
    """F3: si el marcador del rewind queda justo sobre el destino (0 mensajes
    entre medias), se muestra "just above" en vez de "0 messages back"."""
    msgs = [
        {"type": "assistant", "uuid": "dest", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Destino."}]}},
        {"type": "file-history-snapshot", "messageId": "rama1"},
        {"type": "user", "uuid": "rama1", "parentUuid": "dest", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento A."}]}},
        {"type": "user", "uuid": "rama2", "parentUuid": "dest", "timestamp": "2026-06-16T10:02:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento B."}]}},
    ]
    out = tmp_path / "f3g.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "just above" in html
    assert "0 messages back" not in html


def test_stats_bar_cuenta_rewinds_no_snapshots(viz, tmp_path):
    """El stats-bar muestra "Rewinds: N" (rewinds reales) y ya no "Snapshots":
    los snapshots-guard (sin rama hermana) no cuentan."""
    msgs = [
        {"type": "assistant", "uuid": "dest", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Destino."}]}},
        {"type": "user", "uuid": "rama1", "parentUuid": "dest", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento A."}]}},
        {"type": "file-history-snapshot", "messageId": "rama1"},
        {"type": "user", "uuid": "rama2", "parentUuid": "dest", "timestamp": "2026-06-16T10:02:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Intento B."}]}},
        {"type": "file-history-snapshot", "messageId": "guard-no-existe"},
    ]
    out = tmp_path / "stats.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "Rewinds: 1" in html      # solo el rewind real, no el guard
    assert "Snapshots:" not in html


def test_toggle_tema_edit_label_accion(viz, demo_chat_path, tmp_path):
    """El toggle de tema de los diffs Edit indica la ACCIÓN ("Switch to …")
    en vez de un ambiguo "Dark"/"Light" suelto."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "theme.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "Switch to light" in html   # label inicial (tema oscuro por defecto)
    assert "Switch to dark" in html    # estado alternativo (en el JS)


def test_f5_boton_copiar_presente(viz, demo_chat_path, tmp_path):
    """F5: el HTML incluye el botón de copiar y su lógica JS."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "f5.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert ".copy-btn" in html
    assert "navigator.clipboard.writeText" in html
    assert "querySelectorAll('.message')" in html


def test_filtro_messages_only_presente(viz, demo_chat_path, tmp_path):
    """Filtro 'Messages only': checkbox junto al buscador + lógica JS combinada
    (texto AND tipo) que conserva solo user/assistant con texto real."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "filter.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert 'id="messagesOnly"' in html
    assert "Messages only" in html
    assert "applyConversationFilter" in html
    assert "isConversationMsg" in html


def test_ask_result_wording_nuevo_se_parsea(viz):
    """El result de AskUserQuestion con el wording nuevo ('Your questions have been
    answered:') se parsea en pares Q/A (antes caía a tool-result crudo en gris)."""
    txt = ('Your questions have been answered: "¿Dónde?"="Aquí", '
           '"¿Cuándo?"="Ahora". You can now continue with these answers in mind.')
    pairs = viz.parse_ask_result(txt)
    assert len(pairs) == 2
    assert pairs[0]["question"] == "¿Dónde?" and pairs[0]["answer"] == "Aquí"
    assert pairs[1]["answer"] == "Ahora"


def test_ask_result_wording_antiguo_sigue(viz):
    """El wording antiguo ('User has answered your questions:') se sigue reconociendo."""
    txt = 'User has answered your questions: "¿Q?" = "A". You can now continue.'
    pairs = viz.parse_ask_result(txt)
    assert len(pairs) == 1 and pairs[0]["answer"] == "A"


def test_mensaje_en_cola_se_renderiza(viz, tmp_path):
    """Un mensaje del usuario en cola (attachment/queued_command, sin message.role)
    se renderiza como user-msg en vez de desaparecer del HTML."""
    msgs = [{
        "type": "attachment", "uuid": "q1", "timestamp": "2026-06-18T10:00:00.000Z",
        "attachment": {"type": "queued_command", "prompt": "mensaje en cola xyz",
                       "commandMode": "prompt"},
    }]
    out = tmp_path / "queued.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "mensaje en cola xyz" in html
    assert "user-msg" in html


def test_task_notification_failed_en_rojo(viz):
    """Un task-notification con status 'failed' se colorea en rojo (#DC2626)."""
    html = viz.render_task_notification(
        "<task-notification><summary>algo</summary><status>failed</status>"
        "</task-notification>", "u1")
    assert "#DC2626" in html
    assert "[FAILED]" in html


def _img_item(data):
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


def test_f1_imagenes_no_consecutivas(viz, tmp_path):
    """[Image #1] + [Image #3] (no consecutivos): cada marcador mapea a su imagen
    inline; antes [Image #3] se salía de rango y quedaba como texto plano."""
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-18T10:00:00.000Z",
             "message": {"role": "user", "content": [
                 {"type": "text", "text": "Compara [Image #1] con [Image #3]"},
                 _img_item("QUFB"), _img_item("QkJC")]}}]
    out = tmp_path / "f1nc.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert html.count("inline-img") >= 2  # ambos marcadores van inline


def test_f1_mas_imagenes_que_marcadores(viz, tmp_path):
    """Más imágenes que marcadores: el marcador va inline y la imagen extra sale
    como botón — ninguna imagen se pierde."""
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-18T10:00:00.000Z",
             "message": {"role": "user", "content": [
                 {"type": "text", "text": "Solo [Image #1]"},
                 _img_item("QUFB"), _img_item("QkJC")]}}]
    out = tmp_path / "f1ex.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "inline-img" in html  # marcador #1 inline
    assert html.count("msg-image-link") >= 2  # imagen extra también se muestra (botón)


def test_ask_result_estructurado_render_rico(viz, tmp_path):
    """Un tool_result de AskUserQuestion con toolUseResult estructurado se renderiza
    con la opción elegida resaltada, el header como chip y las opciones ofrecidas."""
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
             "toolUseResult": {
                 "questions": [{"question": "¿Framework?", "header": "Stack", "multiSelect": False,
                                "options": [{"label": "Next.js", "description": "react"},
                                            {"label": "Astro", "description": "mpa"}]}],
                 "answers": {"¿Framework?": "Next.js"}},
             "message": {"role": "user", "content": [
                 {"type": "tool_result", "tool_use_id": "toolu_x",
                  "content": 'Your questions have been answered: "¿Framework?"="Next.js". You can now continue.'}]}}]
    out = tmp_path / "askrich.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "ask-result-msg" in html
    assert "ask-opt-sel" in html   # la opción elegida, resaltada
    assert "ask-chip" in html      # el header como chip
    assert "Astro" in html         # también lista la opción no elegida


def test_modal_imagen_accesible(viz, tmp_path):
    """El modal de imagen declara role=dialog + aria-modal y gestiona el foco
    (lo devuelve al cerrar). El HTML del modal va en todo chat generado."""
    out = tmp_path / "a11y.html"
    viz.generate_html([{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
                        "message": {"role": "user", "content": "hola"}}], str(out))
    html = out.read_text(encoding="utf-8")
    assert 'id="imgModal"' in html
    assert 'role="dialog"' in html and 'aria-modal="true"' in html
    assert "lastFocusedBeforeModal" in html  # el foco vuelve al disparador al cerrar


def test_gotomessage_fallback_visible(viz, tmp_path):
    """gotoMessage no queda inerte si no encuentra el destino: muestra un toast
    de aviso (fallback visible)."""
    out = tmp_path / "nav.html"
    viz.generate_html([{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
                        "message": {"role": "user", "content": "hola"}}], str(out))
    html = out.read_text(encoding="utf-8")
    assert "showNavToast" in html and "nav-toast" in html


def test_gotomessage_revela_destino_oculto(viz, tmp_path):
    """Si el destino del Go está oculto por un filtro activo (búsqueda / Messages
    only), gotoMessage limpia el filtro antes de hacer scroll."""
    out = tmp_path / "navf.html"
    viz.generate_html([{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
                        "message": {"role": "user", "content": "hola"}}], str(out))
    html = out.read_text(encoding="utf-8")
    assert "target.offsetParent === null" in html  # detecta destino oculto por filtro


def test_navegacion_parte_del_scroll_actual(viz, tmp_path):
    """Los saltos prev/next recalculan la posición desde el scroll real (mensaje
    más centrado), no desde un índice acumulado — fiable tras Ctrl+F o scroll."""
    out = tmp_path / "nav2.html"
    viz.generate_html([{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
                        "message": {"role": "user", "content": "hola"}}], str(out))
    html = out.read_text(encoding="utf-8")
    assert "currentNavIndexFromScroll" in html


def test_chat_persiste_estado_sessionstorage(viz, tmp_path):
    """El chat persiste estado por-apertura en sessionStorage (scroll, tema, navMode,
    búsqueda/Messages only, bloques Edit/Write): sobrevive a F5, limpio al reabrir."""
    out = tmp_path / "persist.html"
    viz.generate_html([{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
                        "message": {"role": "user", "content": "hola"}}], str(out),
                       chat_uuid="abc-uuid-123")
    html = out.read_text(encoding="utf-8")
    assert "ccv-chat-state-" in html
    assert '"abc-uuid-123"' in html       # clave por-chat
    assert "sessionStorage.getItem" in html and "sessionStorage.setItem" in html
    assert "getEntriesByType('navigation')" in html  # F5 mantiene, reabrir limpio
    assert "restoreChatState" in html and "saveChatState" in html
    assert "editBlocksOpen" in html       # persiste los desplegables Edit/Write
    assert 'id="chatLoading"' in html      # overlay de carga (anti doble-salto)


def test_task_notification_nombra_agente(viz, tmp_path):
    """La notificación 'agent completed' nombra qué agente corrió (subagent_type ·
    description), cruzando el <task-id> con el Agent tool_use del mismo chat."""
    aid = "abc123def456789"
    msgs = [
        {"type": "assistant", "uuid": "a1", "timestamp": "2026-06-19T10:00:00.000Z",
         "message": {"role": "assistant", "content": [
             {"type": "tool_use", "id": "tu1", "name": "Agent",
              "input": {"subagent_type": "Auditor", "description": "Auditar el login"}}]}},
        {"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:01:00.000Z",
         "toolUseResult": {"agentId": aid, "status": "completed"},
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu1", "content": "ok"}]}},
        {"type": "user", "uuid": "u2", "timestamp": "2026-06-19T10:02:00.000Z",
         "message": {"role": "user", "content":
             f"<task-notification><task-id>{aid}</task-id><status>completed</status><summary>Listo</summary></task-notification>"}},
    ]
    out = tmp_path / "tn.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "Auditor · Auditar el login" in html  # nombra el agente en la línea verde


def test_comandos_bash_bang(viz, tmp_path):
    """Los comandos ! (bash-input) salen como '! cmd' en rojo; stdout limpio,
    stderr solo si hay; las etiquetas <bash-*> no quedan crudas."""
    msgs = [
        {"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
         "message": {"role": "user", "content": "<bash-input>git status</bash-input>"}},
        {"type": "user", "uuid": "u2", "timestamp": "2026-06-19T10:00:01.000Z",
         "message": {"role": "user", "content": "<bash-stdout>ok</bash-stdout><bash-stderr></bash-stderr>"}},
    ]
    out = tmp_path / "bash.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert '<span class="bash-bang">! git status</span>' in html  # comando en rojo con !
    assert '<span class="bash-out">ok</span>' in html             # stdout limpio
    assert "&lt;bash-input&gt;" not in html                       # etiquetas procesadas


def test_agent_completed_enlace(viz, tmp_path):
    """'agent completed' enlaza al chat del agente (nueva pestaña) si su HTML está
    en AGENT_HTML_MAP; sin entrada, no hay enlace."""
    viz.AGENT_HTML_MAP.clear()
    viz.AGENT_HTML_MAP["abc123"] = "Chat 2026 Agent-abc123.html"
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
             "message": {"role": "user", "content":
                 "<task-notification><task-id>abc123</task-id><status>completed</status><summary>done</summary></task-notification>"}}]
    out = tmp_path / "tn.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert 'href="Chat 2026 Agent-abc123.html"' in html and 'target="_blank"' in html
    assert 'class="agent-open"' in html
    viz.AGENT_HTML_MAP.clear()


def test_chat_agente_marca_en_header(viz, tmp_path):
    """El HTML de un chat de agente muestra el indicador 'AGENT CHAT' en el header,
    con el UUID de la sesión invocadora."""
    out = tmp_path / "ag.html"
    viz.generate_html([{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
                        "message": {"role": "user", "content": "hola"}}], str(out),
                       agent_of="11111111-1111-1111-1111-111111111111")
    html = out.read_text(encoding="utf-8")
    assert "agent-chip" in html and "AGENT CHAT" in html
    assert "11111111-1111-1111-1111-111111111111" in html
