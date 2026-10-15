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
    # render del rewind se cubre en las pruebas de rewind dedicadas de abajo.
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


def test_genera_html_time_format_24h(viz, tmp_path):
    """El formato de hora se ve en la página: con 12h las horas llevan AM/PM y
    con 24h no (antes la prueba solo miraba la variable interna)."""
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-13T09:00:00Z",
             "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}}]
    paginas = {}
    for fmt in ("12h", "24h"):
        out = tmp_path / f"chat-{fmt}.html"
        viz.generate_html(msgs, str(out), time_format=fmt)
        cuerpo = out.read_text(encoding="utf-8").split("</style>", 1)[1]
        paginas[fmt] = cuerpo[cuerpo.index('data-msg-uuid="u1"'):][:1500]
    assert " AM" in paginas["12h"] or " PM" in paginas["12h"]
    assert " AM" not in paginas["24h"] and " PM" not in paginas["24h"]


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


def test_imagen_inline_reemplaza_marcador(viz, tmp_path):
    """Cada [Image #N] del texto se convierte en un enlace inline a su imagen
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
    out = tmp_path / "imagenes.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert html.count('class="msg-image-link inline-img"') == 2
    assert 'title="image/png,' in html
    assert '>[Image #1]</a>' in html and '>[Image #2]</a>' in html
    assert "Open image" not in html  # sin botones separados


def test_metadata_modelo_antes_de_fecha(viz, tmp_path):
    """En el metadata del asistente, el modelo precede a la fecha, y la
    fecha/hora va resaltada en negrita (<strong>) para que destaque."""
    import re
    msgs = [{
        "type": "assistant", "uuid": "a1", "timestamp": "2026-06-16T10:00:00Z", "gitBranch": "main",
        "message": {"role": "assistant", "model": "claude-opus-4-8",
                    "content": [{"type": "text", "text": "Hola."}]},
    }]
    out = tmp_path / "metadata.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    meta = re.search(r'class="metadata">(.*?)</span>', html, re.S).group(1)
    assert meta.index("claude-opus-4-8") < meta.index("2026-06-16")
    assert "<strong>2026-06-16" in meta


def test_rewind_apunta_al_destino(viz, tmp_path):
    """Un prompt con texto y un hermano POSTERIOR con texto (mismo
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
    out = tmp_path / "rewind.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert 'class="rewind"' in html
    assert "Punto de partida." in html
    assert "1 message back" in html  # solo "Primer intento." se descartó
    assert 'data-goto="dest"' in html            # destino en data-attr
    assert 'onclick="gotoMessage' not in html    # XSS: el uuid ya no se interpola en un handler inline
    assert 'data-msg-uuid="dest"' in html


def test_snapshot_sin_mensaje_se_omite(viz, tmp_path):
    """Un snapshot cuyo messageId no apunta a ningún mensaje no se muestra."""
    msgs = [{"type": "file-history-snapshot", "messageId": "uuid-inexistente-9999"}]
    out = tmp_path / "snapshot.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert '<div class="rewind">' not in html


def test_rama_activa_no_es_rewind(viz, tmp_path):
    """El snapshot de la rama activa (su prompt no tiene hermano posterior)
    no es un rewind y no se muestra."""
    msgs = [
        {"type": "assistant", "uuid": "dest", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Inicio."}]}},
        {"type": "user", "uuid": "soloUno", "parentUuid": "dest", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Único intento."}]}},
        {"type": "file-history-snapshot", "messageId": "soloUno"},
    ]
    out = tmp_path / "rama-activa.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert '<div class="rewind">' not in html


def test_fork_de_herramientas_no_es_rewind(viz, tmp_path):
    """Un 'fork' cuyo prompt abandonado no tiene texto humano
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
    out = tmp_path / "fork.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert '<div class="rewind">' not in html


def test_destino_del_rewind_salta_marcadores_de_sistema(viz, tmp_path):
    """El destino del rewind ignora los marcadores de sistema
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
    out = tmp_path / "marcadores.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    # El destino del rewind es la línea humana, no el marcador de sistema
    assert 'class="rewind-dest">&laquo;Mi pregunta real.' in html


def test_dos_rewinds_mismo_destino_distancia_visual(viz, tmp_path):
    """Regresión (el «24 messages back»): con dos rewinds al MISMO destino,
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
    out = tmp_path / "dos-rewinds.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "1 message back" in html       # rewind 1: dest→su marcador = 1 humano (r1)
    assert "2 messages back" in html      # rewind 2: dest→su marcador = 2 humanos (r1, r2)
    assert "4 messages back" not in html  # NO la rama larga acumulada (el bug daba esto)


def test_destino_justo_encima_just_above(viz, tmp_path):
    """Si el marcador del rewind queda justo sobre el destino (0 mensajes
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
    out = tmp_path / "just-above.html"
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


def test_boton_copiar_presente(viz, demo_chat_path, tmp_path):
    """El HTML incluye el botón de copiar y su lógica JS."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "copiar.html"
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


def test_imagenes_no_consecutivas(viz, tmp_path):
    """[Image #1] + [Image #3] (no consecutivos): cada marcador mapea a su imagen
    inline; antes [Image #3] se salía de rango y quedaba como texto plano."""
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-18T10:00:00.000Z",
             "message": {"role": "user", "content": [
                 {"type": "text", "text": "Compara [Image #1] con [Image #3]"},
                 _img_item("QUFB"), _img_item("QkJC")]}}]
    out = tmp_path / "no-consecutivas.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert html.count("inline-img") >= 2  # ambos marcadores van inline


def test_mas_imagenes_que_marcadores(viz, tmp_path):
    """Más imágenes que marcadores: el marcador va inline y la imagen extra sale
    como botón — ninguna imagen se pierde."""
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-18T10:00:00.000Z",
             "message": {"role": "user", "content": [
                 {"type": "text", "text": "Solo [Image #1]"},
                 _img_item("QUFB"), _img_item("QkJC")]}}]
    out = tmp_path / "imagen-extra.html"
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
    """Los saltos prev/next parten de la última parada navegada mientras siga en
    pantalla (memoria — sin ella, las paradas pegadas al tope nunca alcanzan el
    centro del viewport y se saltan; y un mensaje más alto que la pantalla atrapa
    el recorrido). Fallback por scroll consciente de extremos: al tope la posición
    es la primera parada VISIBLE (no la más centrada), al fondo la última; una
    parada que cubre el centro del viewport gana directamente."""
    out = tmp_path / "nav2.html"
    viz.generate_html([{"type": "user", "uuid": "u1", "timestamp": "2026-06-19T10:00:00.000Z",
                        "message": {"role": "user", "content": "hola"}}], str(out))
    html = out.read_text(encoding="utf-8")
    assert "currentNavIndexFromScroll" in html
    assert "navStepBase" in html                          # memoria de la última parada
    assert "container.scrollTop <= 2" in html             # extremo superior: primer visible
    assert "container.scrollHeight - 2" in html           # extremo inferior: último visible
    assert "r.top <= cMid && r.bottom >= cMid" in html    # cubre el centro => es la posición


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
    assert "getEntriesByType('navigation')" in html  # refrescar (F5) mantiene; reabrir empieza limpio
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


# ====== Colapsables <details> + anclas únicas + XSS ======

def test_compact_details_sin_id_colisionable(viz, tmp_path):
    """El compact usa <details> nativo (sin id colisionable); y un rewind que duplica
    la misma entrada (mismo uuid) se deduplica a UN bloque, conservando el primero."""
    msgs = [
        {"_compact_group": True, "summary_text": "resumen A", "uuid": "same-uuid-1234",
         "command_display": "/compact", "time_str": ""},
        {"_compact_group": True, "summary_text": "resumen B", "uuid": "same-uuid-1234",
         "command_display": "/compact", "time_str": ""},
    ]
    out = tmp_path / "compact.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert html.count('class="compact-details"') == 1   # el duplicado (mismo uuid) se deduplica
    assert "getElementById('compact-" not in html       # sin el mecanismo viejo por id
    assert "resumen A" in html and "resumen B" not in html   # keep-first


def test_rewind_go_sin_onclick_inline(viz, tmp_path):
    """El botón Go del rewind lleva el destino en data-goto, no en un onclick con el
    uuid interpolado (cierra la XSS ejecutable seguridad-01)."""
    msgs = [
        {"type": "assistant", "uuid": "d", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Inicio."}]}},
        {"type": "user", "uuid": "r1", "parentUuid": "d", "timestamp": "2026-06-16T10:01:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Uno."}]}},
        {"type": "file-history-snapshot", "messageId": "r1"},
        {"type": "user", "uuid": "r2", "parentUuid": "d", "timestamp": "2026-06-16T10:02:00Z",
         "message": {"role": "user", "content": [{"type": "text", "text": "Dos."}]}},
    ]
    out = tmp_path / "go.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert 'class="rewind-goto"' in html and 'data-goto="d"' in html
    assert 'onclick="gotoMessage' not in html


# ====== Dedup de segmentos re-emitidos por rewind ======

def test_dedup_reemitted_keep_first(viz):
    """Un uuid repetido (segmento re-emitido) se conserva una vez, en su primera
    posición; las entradas sin uuid (metadata) no se tocan."""
    msgs = [
        {"type": "user", "uuid": "a", "message": {"role": "user", "content": "uno"}},
        {"type": "assistant", "uuid": "b", "message": {"role": "assistant", "content": "dos"}},
        {"type": "user", "uuid": "a", "message": {"role": "user", "content": "uno"}},   # re-emitido
        {"type": "assistant", "uuid": "c", "message": {"role": "assistant", "content": "tres"}},
        {"type": "last-prompt"}, {"type": "last-prompt"},   # sin uuid
    ]
    out = viz.dedup_reemitted_messages(msgs)
    assert [m.get("uuid") for m in out if m.get("uuid")] == ["a", "b", "c"]
    assert len(out) == 5   # 3 con uuid + 2 sin uuid


def test_generate_html_dedup_segmento_reemitido(viz, tmp_path):
    """Un segmento re-emitido (mismos uuids) no se pinta dos veces en el HTML."""
    seg = [
        {"type": "user", "uuid": "u1", "timestamp": "2026-07-10T09:00:00Z",
         "message": {"role": "user", "content": "mensaje ALFA"}},
        {"type": "assistant", "uuid": "a1", "timestamp": "2026-07-10T09:01:00Z",
         "message": {"role": "assistant", "content": "respuesta BETA"}},
    ]
    out = tmp_path / "dedup.html"
    viz.generate_html(seg + seg, str(out))   # el mismo segmento dos veces
    html = out.read_text(encoding="utf-8")
    assert html.count("mensaje ALFA") == 1
    assert html.count("respuesta BETA") == 1
    assert html.count('data-msg-uuid="u1"') == 1


# ====== Red de seguridad de render ======

def test_render_aislado_un_mensaje_que_revienta_no_tumba_el_chat(viz, tmp_path, monkeypatch):
    """Un renderer que lanza sobre un mensaje degrada a un bloque de error VISIBLE
    sin abortar el resto del chat (aislamiento por mensaje)."""
    def boom(*a, **k):
        raise ValueError("boom")
    monkeypatch.setattr(viz, "render_compact_block", boom)
    messages = [
        {"type": "user", "uuid": "u1", "timestamp": "2026-07-10T09:00:00.000Z",
         "message": {"role": "user", "content": "hola antes"}},
        {"_compact_group": True, "summary_text": "x", "uuid": "c1"},
        {"type": "user", "uuid": "u2", "timestamp": "2026-07-10T09:01:00.000Z",
         "message": {"role": "user", "content": "hola despues"}},
    ]
    out = tmp_path / "boom.html"
    viz.generate_html(messages, str(out))
    html = out.read_text(encoding="utf-8")
    assert "render-error" in html and "ValueError: boom" in html
    assert "hola antes" in html and "hola despues" in html


def test_escritura_atomica_no_deja_tmp(viz, tmp_path):
    """generate_html escribe de forma atómica: el HTML final existe y no queda
    ningún fichero temporal .tmp."""
    out = tmp_path / "chat.html"
    viz.generate_html([{"type": "user", "uuid": "u1", "timestamp": "2026-07-10T09:00:00.000Z",
                        "message": {"role": "user", "content": "hola"}}], str(out))
    assert out.exists()
    assert not (tmp_path / "chat.html.tmp").exists()


def test_linea_malformada_sale_como_bloque_de_error(viz, tmp_path):
    """Una línea JSONL corrupta se renderiza como bloque de error visible, no se
    pierde en silencio."""
    path = tmp_path / "malformada.jsonl"
    path.write_text('{"type":"user","uuid":"u1","message":{"role":"user","content":"antes"}}\n'
                    '{ no es json }\n'
                    '{"type":"user","uuid":"u2","message":{"role":"user","content":"despues"}}\n',
                    encoding="utf-8")
    msgs = viz.parse_chat_json(str(path))
    out = tmp_path / "malformada.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "CCV parse error" in html and "render-error" in html
    assert "antes" in html and "despues" in html


def test_navegacion_y_filtro_sincronizados(viz, demo_chat_path, tmp_path):
    """Regresión: `applyConversationFilter` ocultaba mensajes con display:none
    pero NO reconstruía la lista de paradas, así que con un filtro activo los
    saltos ▲/▼ apuntaban a elementos invisibles: la vista no se movía y el
    contador mentía. Ahora las paradas ocultas se excluyen y el filtro
    reinicializa la navegación."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    # initNavigation excluye lo oculto
    assert "display === 'none'" in html
    assert ".filter(el =>" in html
    # y el filtro reconstruye la lista al terminar
    cuerpo = html[html.index("function applyConversationFilter()"):]
    cuerpo = cuerpo[:cuerpo.index("document.getElementById('searchInput').addEventListener")]
    assert "initNavigation();" in cuerpo


def test_datos_del_chat_nunca_entran_al_html_sin_escapar(viz, tmp_path):
    """Regresión: cinco puntos interpolaban datos del JSONL en el HTML sin
    escaparlos (tipo de un bloque de tool_result, tipo desconocido, Leaf UUID de
    un summary, rol de un mensaje y bloques que no son texto ni diccionario). Un
    JSONL manipulado podía inyectar marcado. Cada punto lleva su marca distinta."""
    msgs = [
        {"type": "summary", "summary": "s", "leafUuid": "<b id=PLF>"},
        {"type": "assistant", "uuid": "a1", "timestamp": "2026-06-13T09:00:00Z",
         "message": {"role": "assistant", "content": [
             {"type": "<b id=P_TYPE>"},
             ["<b id=P_RAW>"],
         ]}},
        {"type": "user", "uuid": "u1", "timestamp": "2026-06-13T09:01:00Z",
         "message": {"role": "<b id=P_ROLE>", "content": [{"type": "text", "text": "hola"}]}},
        {"type": "user", "uuid": "u2", "timestamp": "2026-06-13T09:02:00Z",
         "message": {"role": "user", "content": [
             {"type": "tool_result", "tool_use_id": "t1",
              "content": [{"type": "<b id=P_TR>"}]}]}},
    ]
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    low = html.lower()   # el rol se pinta en mayúsculas: comparar sin distinguir
    for marca in ("plf", "p_type", "p_raw", "p_role", "p_tr"):
        assert f"<b id={marca}>" not in low, f"{marca} entró al HTML sin escapar"
        assert f"&lt;b id={marca}&gt;" in low, f"{marca} no aparece escapado (¿se perdió?)"


def test_bloque_document_se_etiqueta(viz, tmp_path):
    """Los PDF adjuntos (bloques `document`) se nombran en vez de pintarse como
    un hueco anónimo."""
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-13T09:00:00Z",
             "message": {"role": "user", "content": [
                 {"type": "text", "text": "mira el pdf"},
                 {"type": "document", "source": {"type": "base64",
                  "media_type": "application/pdf", "data": "A" * 4096}}]}}]
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "[Document: PDF · 3 KB]" in html
    assert "[Type: document]" not in html


def test_buscador_espera_a_que_termines_de_escribir(viz, demo_chat_path, tmp_path):
    """El filtro recorre el texto de todos los mensajes; en chats de decenas de
    MB, hacerlo en cada tecla bloqueaba la escritura. La búsqueda se programa con
    una pausa (~150 ms) y el interruptor «Messages only» sigue siendo inmediato.
    Límite: es JavaScript embebido y el proyecto no tiene pruebas en navegador,
    así que aquí se comprueba el enlace de eventos, no la pausa en sí."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "addEventListener('input', scheduleConversationFilter)" in html
    assert "addEventListener('input', applyConversationFilter)" not in html
    assert "setTimeout(applyConversationFilter, 150)" in html
    assert "addEventListener('change', applyConversationFilter)" in html


def test_javascript_embebido_es_sintacticamente_valido(viz, demo_chat_path, tmp_path):
    """Red mínima para el JavaScript del chat, que va dentro de una plantilla de
    Python y no tiene pruebas en navegador: un error de llaves o de sintaxis en la
    plantilla rompería TODA la interacción del chat sin que ningún test Python lo
    notara. Se extrae el <script> de un chat generado y se pasa por `node --check`.
    Se omite si Node no está instalado."""
    import re, shutil, subprocess
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("Node no disponible")
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    js = "\n;\n".join(re.findall(r"<script>(.*?)</script>", out.read_text(encoding="utf-8"), re.S))
    assert js.strip(), "el chat no lleva JavaScript"
    js_file = tmp_path / "chat.js"
    js_file.write_text(js, encoding="utf-8")
    r = subprocess.run([node, "--check", str(js_file)], capture_output=True, text=True)
    assert r.returncode == 0, f"JavaScript inválido:\n{r.stderr[:800]}"


def test_navegacion_recalcula_por_geometria(viz, demo_chat_path, tmp_path):
    """Causa raíz del bug de navegación: el vigilante de scroll asignaba la
    posición «al último mensaje >50% visible» en cada lote, envenenando la memoria
    justo después de abrir; y los lotes tardíos burlaban la ventana fija de 100 ms.
    Ahora el vigilante solo avisa y la posición se recalcula por geometría, con un
    sello temporal tras cada salto. Límite: JavaScript sin pruebas en navegador;
    aquí se fija la estructura, el comportamiento lo valida el uso real."""
    msgs = viz.parse_chat_json(str(demo_chat_path))
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    obs = html[html.index("function setupScrollObserver()"):]
    obs = obs[:obs.index("navMessages.forEach(msg => navObserver.observe(msg))")]
    assert "currentNavIndexFromScroll()" in obs           # recalcula por geometría
    assert "navMessages.indexOf(entry.target)" not in obs # ya no asigna por entrada
    assert "performance.now() < navSuppressUntil" in obs  # ignora lotes tardíos
    assert "navSuppressUntil = performance.now() + 150" in html


def test_cambio_de_modelo_visible_y_fontaneria_oculta(viz, tmp_path):
    """Un bloque `fallback` (el servicio cambió de modelo a mitad de respuesta)
    se muestra legible; `tool_addition` (definiciones de herramientas añadidas a
    mitad de sesión) es fontanería interna y no se pinta."""
    msgs = [
        {"type": "assistant", "uuid": "a1", "timestamp": "2026-06-13T09:00:00Z",
         "message": {"role": "assistant", "content": [
             {"type": "fallback", "from": {"model": "claude-opus-5-5"},
              "to": {"model": "claude-opus-4-8"}},
             {"type": "text", "text": "respuesta"}]}},
        {"type": "user", "uuid": "s1", "timestamp": "2026-06-13T09:01:00Z",
         "message": {"role": "system", "content": [
             {"type": "tool_addition", "tool": {"type": "tool_definition"}}]}},
    ]
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out))
    html = out.read_text(encoding="utf-8")
    assert "[Model fallback: claude-opus-5-5 &#8594; claude-opus-4-8]" in html
    assert "tool_addition" not in html.split("</style>", 1)[1]


def test_catalogo_cubre_los_tipos_actuales_de_claude_code(viz):
    """Los tipos que Claude Code escribe hoy (censados en el corpus real) están
    catalogados: el Audit no los marca como «posible cambio de formato»."""
    for t in ("atis-latch", "file-history-delta", "progress", "agent-color",
              "cost-state", "api-request", "api-request-blob", "fork-context-ref",
              "frame-link", "relocated", "agent-setting", "api-request-shape",
              "artifact-autoreact-ledger", "artifact-comment-monitor"):
        assert t in viz.KNOWN_METADATA_TYPES, t
    for t in ("document", "fallback", "tool_addition"):
        assert t in viz.KNOWN_CONTENT_TYPES, t


def test_banner_de_fork_enlaza_via_panel(viz, tmp_path):
    """Un chat bifurcado de otra sesión abre con un banner. El enlace va al panel
    (`<panel>#open=<sesión origen>`), que sabe dónde vive cada chat aunque se
    mueva entre carpetas; sin panel (uso suelto) solo nombra la sesión."""
    msgs = [{"type": "user", "uuid": "u1", "timestamp": "2026-06-13T09:00:00Z",
             "forkedFrom": {"sessionId": "021592e5-dd40-4105-abed-baae3b80cd67",
                            "messageUuid": "x"},
             "message": {"role": "user", "content": [{"type": "text", "text": "hola"}]}}]
    out = tmp_path / "con.html"
    viz.generate_html(msgs, str(out), dashboard_url="../CCV-Dashboard.html")
    html = out.read_text(encoding="utf-8")
    assert 'class="fork-banner"' in html
    assert 'href="../CCV-Dashboard.html#open=021592e5-dd40-4105-abed-baae3b80cd67"' in html
    # el banner va antes que el primer mensaje
    body = html.split("</style>", 1)[1]
    assert body.index("fork-banner") < body.index('data-msg-uuid="u1"')
    # sin panel: informativo, sin enlace
    out2 = tmp_path / "sin.html"
    viz.generate_html(msgs, str(out2))
    h2 = out2.read_text(encoding="utf-8")
    assert "session 021592e5" in h2 and 'class="fork-link"' not in h2
    # un chat normal no lleva banner
    out3 = tmp_path / "normal.html"
    viz.generate_html([{**msgs[0], "forkedFrom": None}], str(out3))
    assert 'class="fork-banner"' not in out3.read_text(encoding="utf-8")


def _chat_cada_hora(viz_tz):
    """Tres mensajes a las 10, 11 y 12 UTC, con las fechas escritas en el formato
    pedido (`None` = «Z», como las escribe Claude Code; si no, ese desfase)."""
    from datetime import datetime, timedelta, timezone
    base = datetime(2026, 6, 13, 10, 0, tzinfo=timezone.utc)
    msgs = []
    for i in range(3):
        d = base + timedelta(hours=i)
        ts = (d.strftime("%Y-%m-%dT%H:%M:%S.000Z") if viz_tz is None
              else d.astimezone(timezone(timedelta(hours=viz_tz))).isoformat())
        msgs.append({"type": "user", "uuid": f"m{i}", "timestamp": ts,
                     "message": {"role": "user", "content": [{"type": "text", "text": f"mensaje {i}"}]}})
    return msgs, base


def test_btw_se_coloca_en_su_momento_real(viz):
    """Regresión: cada /btw se colocaba comparando fechas como TEXTO, y las del
    chat (UTC, «…Z») y las del /btw (hora local, «…+02:00») no se ordenan así, y
    los /btw caían horas más tarde en el flujo, o al final.
    Se prueban fechas en «Z» y con desfase +05:00 para que el fallo aparezca en
    cualquier zona horaria del equipo (con la vieja comparación, al menos uno de
    los dos casos falla siempre)."""
    from datetime import timedelta
    for tz in (None, 5):
        msgs, base = _chat_cada_hora(tz)
        ms = lambda d: int(d.timestamp() * 1000)   # noqa: E731
        btws = [
            {"query": "antes de todo", "timestamp": ms(base - timedelta(minutes=5))},
            {"query": "segunda", "timestamp": ms(base + timedelta(hours=1, minutes=40))},
            {"query": "primera", "timestamp": ms(base + timedelta(hours=1, minutes=30))},
            {"query": "al final", "timestamp": ms(base + timedelta(hours=5))},
        ]
        merged = viz.merge_btw_history_into_messages(msgs, btws)
        orden = [m.get("uuid") or m.get("query") for m in merged]
        assert orden == ["antes de todo", "m0", "m1", "primera", "segunda", "m2", "al final"], (tz, orden)


def test_btw_aparece_en_su_sitio_en_el_chat_generado(viz, tmp_path):
    """Extremo a extremo: con las entradas de history.jsonl de la sesión, el
    chat generado pinta el /btw entre los dos mensajes que lo rodean en el
    tiempo, solo los de esa sesión, y los cuenta en la barra de totales."""
    from datetime import timedelta
    msgs, base = _chat_cada_hora(None)
    sid = "a1b2c3d4-0000-0000-0000-000000000000"
    hist = [
        {"query": "pregunta lateral", "sessionId": sid,
         "timestamp": int((base + timedelta(minutes=20)).timestamp() * 1000)},
        {"query": "de otra sesion", "sessionId": "ffffffff-0000-0000-0000-000000000000",
         "timestamp": int((base + timedelta(minutes=20)).timestamp() * 1000)},
    ]
    out = tmp_path / "chat.html"
    viz.generate_html(msgs, str(out), chat_uuid=sid, history_entries=hist)
    html = out.read_text(encoding="utf-8")
    assert "BTW: 1" in html
    assert "de otra sesion" not in html
    body = html.split("</style>", 1)[1]
    assert (body.index('data-msg-uuid="m0"') < body.index("/btw pregunta lateral")
            < body.index('data-msg-uuid="m1"'))


def _user(uid, text, minute=0, **extra):
    return {"type": "user", "uuid": uid, "timestamp": f"2026-06-13T09:{minute:02d}:00Z",
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}, **extra}


def _cuerpo(viz, tmp_path, msgs, nombre="chat.html"):
    out = tmp_path / nombre
    viz.generate_html(msgs, str(out))
    return out.read_text(encoding="utf-8").split("</style>", 1)[1]


def test_mensajes_que_citan_marcas_de_sistema_no_se_pierden(viz, tmp_path):
    """Regresión (pérdida de contenido): las marcas de sistema se buscaban en
    cualquier parte del texto, así que un mensaje que solo las CITA desaparecía
    entero (caveat), se sustituía por el contenido de la marca (salida de
    consola) o se convertía en una notificación de tarea. En el corpus real
    pasaba con mensajes de otras sesiones, notas de reapertura y encargos a
    agentes. Ahora un mensaje es de sistema solo si EMPIEZA por su marca."""
    body = _cuerpo(viz, tmp_path, [
        _user("c1", "Mira: <local-command-caveat>x</local-command-caveat> PROSA-CAVEAT", 0),
        _user("s1", "Otra sesión: <local-command-stdout>salida</local-command-stdout> PROSA-STDOUT", 1),
        _user("t1", "El formato es <task-notification><status>completed</status>"
                    "</task-notification> PROSA-TAREA", 2),
    ])
    for marca in ("PROSA-CAVEAT", "PROSA-STDOUT", "PROSA-TAREA"):
        assert marca in body, marca
    assert "[COMPLETED]" not in body
    assert "stdout-msg" not in body


def test_mensajes_de_sistema_reales_se_siguen_reconociendo(viz, tmp_path):
    """La otra cara del anclaje: los mensajes de sistema reales siguen tratándose
    como tales — la caveat se oculta, la salida de consola va en su bloque y la
    notificación de tarea se pinta como notificación, también cuando llega bajo
    la cabecera de aviso del arnés («[SYSTEM NOTIFICATION …]»)."""
    body = _cuerpo(viz, tmp_path, [
        _user("c1", "<local-command-caveat>Caveat: CAVEAT-REAL</local-command-caveat>", 0),
        _user("s1", "<local-command-stdout>STDOUT-REAL</local-command-stdout>", 1),
        _user("t1", "<task-notification><task-id>x</task-id><status>completed</status>"
                    "<summary>TAREA-REAL</summary></task-notification>", 2),
        _user("t2", "[SYSTEM NOTIFICATION - NOT USER INPUT]\nThis is an automated event.\n"
                    "<task-notification><task-id>y</task-id><status>completed</status>"
                    "<summary>TAREA-ARNES</summary></task-notification>", 3),
    ])
    assert "CAVEAT-REAL" not in body
    assert "stdout-msg" in body and "STDOUT-REAL" in body
    assert body.count("[COMPLETED]") == 2
    assert "TAREA-ARNES" in body and "NOT USER INPUT" not in body


def test_resultado_que_cita_la_frase_de_rechazo_conserva_su_contenido(viz, tmp_path):
    """Regresión (pérdida de contenido): cualquier resultado de herramienta que
    CONTUVIERA «doesn't want to proceed» se pintaba como [REJECTED] y perdía su
    contenido (p. ej. la lectura de un archivo que cita la frase). Un rechazo
    real empieza por la frase de Claude Code, y ese sigue detectándose."""
    def resultado(uid, texto, minute):
        return {"type": "user", "uuid": uid, "timestamp": f"2026-06-13T09:{minute:02d}:00Z",
                "message": {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": f"t-{uid}", "content": texto}]}}
    body = _cuerpo(viz, tmp_path, [
        resultado("r1", "1\tdef parse(text):\n2\t    if \"doesn't want to proceed\" in text:"
                        "\n3\t        return CONTENIDO-LEIDO", 0),
        resultado("r2", "The user doesn't want to proceed with this tool use. "
                        "The tool use was rejected.", 1),
    ])
    assert "CONTENIDO-LEIDO" in body
    assert body.count("[REJECTED]") == 1


def test_compact_reconocido_por_su_marca_aunque_cambie_la_frase(viz, tmp_path):
    """Un compact se reconocía solo por su frase inicial en inglés; si Anthropic
    la cambiara, cada resumen se pintaría como un mensaje gigante del usuario.
    Ahora basta la marca estructural `isCompactSummary` (y la frase queda de
    respaldo para chats antiguos)."""
    body = _cuerpo(viz, tmp_path, [
        _user("k1", "Resumen redactado de otra forma RESUMEN-NUEVO", 0, isCompactSummary=True),
        _user("u1", "This session is being continued from a previous conversation. RESUMEN-VIEJO", 1),
        _user("u2", "hola", 2),
    ])
    assert body.count('class="compact-details"') == 2
    assert "RESUMEN-NUEVO" in body and "RESUMEN-VIEJO" in body
    assert "User: 1 |" in body and "Summaries: 2 |" in body


def test_bloques_largos_tienen_tope_de_altura(viz, tmp_path):
    """Un bloque de pensamiento, una herramienta o un resultado abierto crecían
    sin límite: un resultado de miles de líneas enterraba el resto del chat.
    Ahora ocupan como mucho media pantalla, con su propio scroll. Y nunca dos
    barras anidadas: los Edit, los Write y los compact ya limitan cada panel por
    dentro, así que el bloque que los envuelve no hace scroll."""
    import re
    out = tmp_path / "chat.html"
    viz.generate_html([_user("k1", "Resumen", 0, isCompactSummary=True), _user("u1", "hola", 1)], str(out))
    html = out.read_text(encoding="utf-8")
    css = html.split("<style>", 1)[1].split("</style>", 1)[0]
    for selector in (".tool-result-msg > .msg-content", ".thinking-content", ".tool-use-content"):
        regla = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
        assert regla, selector
        assert "max-height: 55vh" in regla.group(1) and "overflow-y: auto" in regla.group(1), selector
    for panel in (".edit-diff-body", ".write-block-body"):
        assert "max-height: 420px" in re.search(re.escape(panel) + r"\s*\{([^}]*)\}", css).group(1), panel
    sin_tope = re.search(r"\.tool-use-edit > \.tool-use-content,\s*"
                         r"\.tool-use-write > \.tool-use-content\s*\{([^}]*)\}", css)
    assert sin_tope and "max-height: none" in sin_tope.group(1) and "overflow-y: visible" in sin_tope.group(1)
    compact = re.search(r'class="compact-content" style="([^"]*)"', html).group(1)
    assert "max-height" not in compact and "overflow" not in compact


def test_controles_de_la_barra_y_navegacion_extremos(viz, tmp_path):
    """Retoques de la barra: botones de primer y último mensaje junto a ▲/▼, el
    botón Edits/Writes resaltado mientras haya bloques abiertos, la barra que
    pasa a dos líneas en ventanas estrechas y el botón de tema con su borde
    izquierdo. Límite: JavaScript sin pruebas en navegador; aquí se fija la
    estructura y el enlace de eventos (la sintaxis la vigila `node --check`)."""
    import re
    out = tmp_path / "chat.html"
    viz.generate_html([_user("u1", "hola")], str(out))
    html = out.read_text(encoding="utf-8")
    nav = html[html.index('id="firstMsg"'):html.index('id="navCounter"')]
    assert nav.index('id="prevMsg"') < nav.index('id="nextMsg"') < nav.index('id="lastMsg"')
    assert "getElementById('firstMsg').addEventListener" in html
    assert "scrollToNavMessage(navMessages.length - 1)" in html
    assert "btn.classList.toggle('is-open', anyOpen)" in html
    css = html.split("<style>", 1)[1].split("</style>", 1)[0]
    assert ".edit-ctrl-btn.is-open" in css
    barra = re.search(r"\.search-bar\s*\{([^}]*)\}", css).group(1)
    assert "flex-wrap: wrap" in barra
    tema = re.search(r"\.edit-ctrl-group \.edit-ctrl-btn-theme\s*\{([^}]*)\}", css).group(1)
    assert "border-left-width: 0" not in tema


def test_go_del_rewind_no_apunta_a_una_salida_de_consola(viz, tmp_path):
    """Regresión (botón muerto): una salida de consola de varias líneas
    («Copied to clipboard…» y debajo «Also written to…») contaba como texto
    humano por su segunda línea y acababa de destino del Go, pero se pinta sin
    ancla, así que el botón no llevaba a ningún sitio. El destino salta ahora el
    bloque entero y aterriza en el mensaje real."""
    msgs = [
        {"type": "assistant", "uuid": "d", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Destino real."}]}},
        {**_user("s", "<local-command-stdout>Copied to clipboard\nAlso written to C:\\x.txt"
                      "</local-command-stdout>", 1), "parentUuid": "d"},
        {**_user("r1", "Intento A.", 2), "parentUuid": "s"},
        {"type": "file-history-snapshot", "messageId": "r1"},
        {**_user("r2", "Intento B.", 3), "parentUuid": "s"},
    ]
    body = _cuerpo(viz, tmp_path, msgs)
    assert 'data-goto="d"' in body and 'data-msg-uuid="d"' in body
    assert 'data-goto="s"' not in body


def test_enlace_a_chat_de_agente_pasa_por_el_panel(viz, tmp_path):
    """El «↗ open chat» de una notificación de agente abre su chat en otra
    pestaña. Con panel, el enlace pasa por él (`#open=<agentId>`), que sabe dónde
    vive cada chat: enlazar el archivo por su nombre se rompía en cuanto el chat
    del agente se archivaba aparte del que lo enlaza. Sin panel (uso suelto),
    sigue al archivo; sin HTML del agente, no hay enlace."""
    viz.AGENT_HTML_MAP["abc123"] = "Chat 2026 Agent-abc123.html"
    msgs = [_user("u1", "<task-notification><task-id>abc123</task-id><status>completed</status>"
                        "<summary>hecho</summary></task-notification>")]
    out = tmp_path / "con-panel.html"
    viz.generate_html(msgs, str(out), dashboard_url="../CCV-Dashboard.html")
    html = out.read_text(encoding="utf-8")
    assert 'href="../CCV-Dashboard.html#open=abc123"' in html
    assert 'class="agent-open"' in html and 'target="_blank"' in html
    out2 = tmp_path / "suelto.html"
    viz.generate_html(msgs, str(out2))
    assert 'href="Chat 2026 Agent-abc123.html"' in out2.read_text(encoding="utf-8")
    viz.AGENT_HTML_MAP.clear()
    out3 = tmp_path / "sin-agente.html"
    viz.generate_html(msgs, str(out3))
    assert 'class="agent-open"' not in out3.read_text(encoding="utf-8")


def test_chat_controles_robustos(viz, tmp_path, ejecuta_red_de_carga):
    """La pantalla de carga no puede quedarse fija si el JavaScript falla (se
    ejecuta su red con Node); sin mensaje de depuración en la consola; el
    resaltado de navegación se limpia en cualquier elemento; el resultado de una
    herramienta se abre también con el teclado; y la cabecera de los resúmenes
    antiguos no usa líneas de ancho fijo. Límite: salvo la red de carga, aquí se
    fija el código, no su efecto (no hay pruebas en navegador)."""
    out = tmp_path / "chat.html"
    viz.generate_html([{"type": "summary", "summary": "s", "leafUuid": "l"}, _user("u1", "hola")], str(out))
    html = out.read_text(encoding="utf-8")
    assert ejecuta_red_de_carga(html, "chatLoading") == [True, True]
    assert "console.log" not in html
    salto = html[html.index("function scrollToNavMessage"):]
    assert "document.querySelectorAll('.nav-highlight')" in salto[:salto.index("currentNavIndex = index")]
    assert "header.setAttribute('role', 'button')" in html and "e.key === 'Enter'" in html
    assert "━" not in html and "CONVERSATION SUMMARY</div>" in html


def test_botones_de_copiar_avisan_y_no_se_atascan(viz, tmp_path, ejecuta_js, dobles_de_copiar):
    """Los botones de copiar del chat, ejecutados con Node sobre su código real:
    un segundo clic durante el aviso no deja el botón atascado en él; el aviso va
    en verde si la copia funciona y en rojo, con aspa, si falla — el del
    identificador del chat y el de cada mensaje."""
    out = tmp_path / "chat.html"
    viz.generate_html([_user("u1", "hola")], str(out), chat_uuid="u-1")
    html = out.read_text(encoding="utf-8")
    funciones = html[html.index("function flashCopyButton"):html.index("// ====== Edit blocks")]
    por_mensaje = html[html.index("// Copy button on every message"):]
    por_mensaje = por_mensaje[:por_mensaje.index("</script>")]
    r = ejecuta_js(dobles_de_copiar + """
var alCargar = null, creado = null;
var document = {
  addEventListener: function(ev, fn) { if (ev === 'DOMContentLoaded') alCargar = fn; },
  querySelectorAll: function() {
    return [{ querySelector: function() { return { innerText: 'x' }; }, appendChild: function() {} }]; },
  createElement: function() { creado = boton(''); return creado; }
};
""" + funciones + por_mensaje + """
var r = {};
var b = boton('ICONO');
flashCopyButton(b, 'OK'); avanza(500); flashCopyButton(b, 'OK'); avanza(1300);
r.doble_clic = estado(b);
var u = boton('ICONO'); copyChatUuid(u); r.uuid_ok = estado(u);
copiaOk = false; var u2 = boton('ICONO'); copyChatUuid(u2); r.uuid_fallo = estado(u2);
alCargar(); creado.manejadores.click({ stopPropagation: function() {} });
r.mensaje_fallo = [creado.innerHTML.indexOf('M4 4l8 8') >= 0, creado.classList.lista()];
avanza(2000); r.mensaje_restaurado = creado.innerHTML.indexOf('M4 4l8 8') < 0 && creado.classList.lista() === '';
console.log(JSON.stringify(r));
""")
    assert r["doble_clic"] == "ICONO|"
    assert r["uuid_ok"] == "✓|copied"
    assert r["uuid_fallo"] == "✗|copy-failed"
    assert r["mensaje_fallo"] == [True, "copy-failed"]
    assert r["mensaje_restaurado"] is True


def test_teclas_n_y_p_ignoran_los_modificadores(viz, tmp_path, ejecuta_js):
    """N y P saltan al mensaje siguiente y anterior; con Ctrl, Cmd o Alt son
    atajos del navegador (imprimir, ventana nueva) y no deben mover el chat, ni
    tampoco mientras se escribe en el buscador. Se ejecuta el manejador real con
    Node."""
    out = tmp_path / "chat.html"
    viz.generate_html([_user("u1", "hola")], str(out))
    html = out.read_text(encoding="utf-8")
    teclas = html[html.index("// Keyboard shortcuts (N = next, P = previous)"):]
    teclas = teclas[:teclas.index("// Intersection Observer")]
    r = ejecuta_js("""
var saltos = [], manejador = null;
function goToNext() { saltos.push('N'); }
function goToPrev() { saltos.push('P'); }
var document = { addEventListener: function(ev, fn) { if (ev === 'keydown') manejador = fn; } };
""" + teclas + """
function pulsa(tecla, extra) {
  var e = { key: tecla, target: { tagName: 'BODY' }, ctrlKey: false, metaKey: false, altKey: false };
  for (var k in extra) e[k] = extra[k];
  manejador(e);
}
pulsa('p', { ctrlKey: true }); pulsa('n', { metaKey: true }); pulsa('P', { altKey: true });
pulsa('n', { target: { tagName: 'INPUT' } });
pulsa('n', {}); pulsa('P', {});
console.log(JSON.stringify(saltos));
""")
    assert r == ["N", "P"]


def test_copias_internas_de_claude_code_no_se_pintan_ni_cuentan(viz, tmp_path):
    """Regresión (contenido duplicado): Claude Code guarda en entradas
    `api-request-blob` copias de caché de mensajes que ya están en el chat, con
    su rol. Se pintaban como mensajes reales —la respuesta aparecía dos veces y
    las estadísticas se inflaban—, y una copia de notificación salía como
    mensaje del usuario con las etiquetas a la vista. Ahora ninguna entrada de
    contabilidad interna se pinta ni cuenta, y la cadena de mensajes que sigue
    el botón Go del rewind no se corta por ellas."""
    msgs = [
        _user("u1", "PREGUNTA-ORIGINAL", 0),
        {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-13T09:01:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "RESPUESTA-ORIGINAL"}]}},
        {"type": "api-request-blob", "hash": "h1", "sessionId": "s",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "RESPUESTA-ORIGINAL"}]}},
        {"type": "api-request-blob", "hash": "h2", "sessionId": "s",
         "message": {"role": "user", "content": "<system-reminder>\n<task-notification>\n"
                     "<status>completed</status>\n</task-notification>\n</system-reminder>"}},
        {"type": "progress", "uuid": "p1", "parentUuid": "a1", "data": {"type": "x"}},
        {**_user("r1", "Intento A.", 2), "parentUuid": "p1"},
        {"type": "file-history-snapshot", "messageId": "r1"},
        {**_user("r2", "Intento B.", 3), "parentUuid": "p1"},
    ]
    body = _cuerpo(viz, tmp_path, msgs)
    assert body.count("[ASSISTANT]:") == 1 and body.count("[USER]:") == 3
    assert "&lt;task-notification&gt;" not in body
    assert "User: 3 |" in body and "Assistant: 1 |" in body
    assert 'data-goto="a1"' in body


def test_go_del_rewind_solo_apunta_a_mensajes_con_ancla(viz, tmp_path):
    """Regresión (botón muerto): el destino del Go se elegía por tener texto
    humano, aunque el mensaje se pintara sin ancla — una notificación bajo la
    cabecera del arnés, un comentario junto a un resultado de herramienta, un
    comando. Ahora el destino sigue la misma regla que el pintado, y el botón
    siempre lleva a un mensaje que existe en la página. Un bloque de texto sin
    contenido (`text: null`) tampoco tumba el chat."""
    import re
    def rama(uid, previo):
        return [
            {**_user(f"{uid}-a", "Intento A.", 5), "parentUuid": previo},
            {"type": "file-history-snapshot", "messageId": f"{uid}-a"},
            {**_user(f"{uid}-b", "Intento B.", 6), "parentUuid": previo},
        ]
    destino = {"type": "assistant", "uuid": "d", "timestamp": "2026-06-16T10:00:00Z",
               "message": {"role": "assistant", "content": [{"type": "text", "text": "Destino real."}]}}
    candidatos = {
        "arnes": "[SYSTEM NOTIFICATION - NOT USER INPUT]\nAutomated event.\n<task-notification>"
                 "<task-id>t</task-id><status>completed</status></task-notification>",
        "comando": "<command-name>/x</command-name>\n<command-args>uno</command-args>\nTexto tras el comando",
    }
    msgs = [destino]
    for nombre, texto in candidatos.items():
        msgs.append({**_user(nombre, texto, 1), "parentUuid": "d"})
        msgs += rama(nombre, nombre)
    msgs.append({"type": "user", "uuid": "coment", "parentUuid": "d", "timestamp": "2026-06-16T10:01:00Z",
                 "message": {"role": "user", "content": [
                     {"type": "tool_result", "tool_use_id": "tu", "content": "ok"},
                     {"type": "text", "text": "COMENTARIO del usuario"}]}})
    msgs += rama("coment", "coment")
    msgs.append({"type": "user", "uuid": "nulo", "parentUuid": "d", "timestamp": "2026-06-16T10:02:00Z",
                 "message": {"role": "user", "content": [{"type": "text", "text": None}]}})
    body = _cuerpo(viz, tmp_path, msgs)
    destinos = re.findall(r'data-goto="([^"]*)"', body)
    assert len(destinos) == 3
    for uid in destinos:
        assert f'data-msg-uuid="{uid}"' in body, uid
    assert set(destinos) == {"d"}
    assert 'class="message render-error' not in body   # el text: null no rompe su mensaje


def test_go_del_rewind_atraviesa_los_attachments(viz, tmp_path):
    """Regresión (rewind sin marcador): el camino hacia atrás que busca el
    destino solo pasaba por mensajes de usuario, asistente y sistema; un
    `attachment` intercalado (Claude Code los mete entre mensajes) lo cortaba y
    el rewind se quedaba sin marcador. Ahora recorre todas las entradas."""
    msgs = [
        {"type": "assistant", "uuid": "d", "timestamp": "2026-06-16T10:00:00Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Destino real."}]}},
        {"type": "attachment", "uuid": "a", "parentUuid": "d", "timestamp": "2026-06-16T10:00:30Z",
         "attachment": {"type": "edited_text_file", "filename": "x.py"}},
        {**_user("r1", "Intento A.", 2), "parentUuid": "a"},
        {"type": "file-history-snapshot", "messageId": "r1"},
        {**_user("r2", "Intento B.", 3), "parentUuid": "a"},
    ]
    body = _cuerpo(viz, tmp_path, msgs)
    assert 'class="rewind"' in body and 'data-goto="d"' in body
