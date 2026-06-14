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
    marcas = [
        "thinking", "tool-use", "command-msg", "stdout-msg", "ask-result-msg",
        "reject-msg", "compact-msg", "summary-msg", "snapshot", "assistant-msg",
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
