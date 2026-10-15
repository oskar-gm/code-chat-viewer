"""Configuración pytest de la suite de Code Chat Viewer.

Carga los módulos del proyecto (`scripts/visualizer.py` y `scripts/manager.py`)
y los expone como fixtures `viz` y `mgr`.

Dos detalles del entorno se blindan aquí, sin tocar el código de producción:

- Ambos módulos llaman a ``sys.stdout.reconfigure()`` al importarse. Bajo la
  captura de pytest, el stream activo puede no soportar ``reconfigure`` y el
  import fallaría; se sustituye stdout temporalmente por un stream que sí lo
  soporta y se restaura justo después.
- ``manager.py`` invoca ``webbrowser.open`` al abrir resultados en el navegador.
  Se parchea a un no-op durante toda la sesión para que ningún test abra una
  ventana real si llama a esa ruta por error.
"""

import importlib
import io
import json
import sys
import webbrowser
from pathlib import Path

import pytest

# scripts/ está un nivel por encima de tests/.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def _import_script(module_name: str):
    """Importa un módulo de ``scripts/`` blindando ``sys.stdout.reconfigure()``.

    Devuelve el módulo ya cacheado en ``sys.modules`` si se importó antes, por
    lo que es seguro llamarla varias veces (p. ej. manager reusa visualizer).
    """
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    real_stdout = sys.stdout
    needs_shim = not hasattr(real_stdout, "reconfigure")
    if needs_shim:
        # Stream descartable que sí soporta reconfigure(); su contenido se tira.
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    try:
        return importlib.import_module(module_name)
    finally:
        if needs_shim:
            sys.stdout = real_stdout


@pytest.fixture(scope="session", autouse=True)
def _isolate_environment():
    """Evita que cualquier test abra el navegador (manager.open_in_browser)."""
    original = webbrowser.open
    webbrowser.open = lambda *a, **k: True
    yield
    webbrowser.open = original


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Cada test deja el estado global de los módulos como lo encontró.

    El visualizador guarda en variables de módulo el formato de hora, el mapa
    agente → HTML y las etiquetas de agente del chat en curso; el manager, una
    caché de invocaciones. Sin limpiarlas, un test podía heredar lo que dejó el
    anterior y pasar o fallar según el orden de ejecución.
    """
    yield
    viz_mod = sys.modules.get("visualizer")
    if viz_mod is not None:
        viz_mod.TIME_FORMAT = "12h"
        viz_mod.AGENT_HTML_MAP.clear()
        viz_mod._TASK_AGENT_LABELS = {}
        viz_mod._DASHBOARD_URL = None
    mgr_mod = sys.modules.get("manager")
    if mgr_mod is not None:
        mgr_mod._AGENT_INV_CACHE.clear()


@pytest.fixture(scope="session")
def viz():
    """Módulo ``visualizer.py`` — core: convierte un JSONL en un HTML."""
    return _import_script("visualizer")


@pytest.fixture(scope="session")
def mgr():
    """Módulo ``manager.py`` — orquestador: escaneo, dashboard, organización.

    visualizer se carga primero porque manager lo importa al inicializarse.
    """
    _import_script("visualizer")
    return _import_script("manager")


@pytest.fixture
def ejecuta_js(tmp_path):
    """Ejecuta con Node un guion de prueba —trozos reales del JavaScript de una
    página más los dobles del navegador que necesiten— y devuelve lo que imprime
    como JSON. Se omite el test si no hay Node (dependencia opcional de la suite).
    """
    import shutil
    import subprocess

    def _run(codigo: str):
        node = shutil.which("node")
        if not node:
            pytest.skip("Node no disponible")
        f = tmp_path / "prueba.js"
        f.write_text(codigo, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr[:800]
        return json.loads(r.stdout)
    return _run


@pytest.fixture
def ejecuta_red_de_carga(ejecuta_js):
    """Ejecuta con Node la red de seguridad de la pantalla de carga de una página
    (el pequeño script independiente que va justo detrás del overlay) y dice si
    retira el overlay ante un error de JavaScript y tras la carga.

    Devuelve `[tras_error, tras_carga]`. Se omite el test si no hay Node.
    """
    import re

    def _run(page_html: str, overlay_id: str):
        tras = page_html[page_html.index(f'id="{overlay_id}"'):]
        script = re.search(r"<script>(.*?)</script>", tras, re.S).group(1)
        return ejecuta_js(
            "function run(evento) {\n"
            "  var quitado = false, handlers = {};\n"
            "  var window = {addEventListener: function(ev, fn) { handlers[ev] = fn; }};\n"
            "  var document = {getElementById: function() {\n"
            "      return {remove: function() { quitado = true; }}; }};\n"
            "  var setTimeout = function(fn) { fn(); };\n"
            f"  {script}\n"
            "  if (handlers[evento]) handlers[evento]();\n"
            "  return quitado;\n"
            "}\n"
            "console.log(JSON.stringify([run('error'), run('load')]));\n")
    return _run


# Dobles del navegador para ejecutar con Node los botones de copiar: temporizador
# con reloj manual (`avanza(ms)`), un botón con clases y manejadores, y un
# portapapeles que acepta o falla según `copiaOk`.
DOBLES_DE_COPIAR = """
var ahora = 0, temporizadores = [];
function setTimeout(fn, ms) { var t = {fn: fn, at: ahora + ms}; temporizadores.push(t); return t; }
function clearTimeout(t) { if (t) t.muerto = true; }
function avanza(ms) {
  ahora += ms;
  temporizadores.forEach(function(t) { if (!t.muerto && t.at <= ahora) { t.muerto = true; t.fn(); } });
}
function boton(icono) {
  var clases = {};
  return {
    innerHTML: icono, dataset: {}, manejadores: {},
    set textContent(v) { this.innerHTML = v; },
    classList: {
      add: function() { for (var i = 0; i < arguments.length; i++) clases[arguments[i]] = 1; },
      remove: function() { for (var i = 0; i < arguments.length; i++) delete clases[arguments[i]]; },
      lista: function() { return Object.keys(clases).sort().join(' '); }
    },
    addEventListener: function(ev, fn) { this.manejadores[ev] = fn; },
    parentNode: { querySelector: function() { return { textContent: 'uuid' }; } },
    closest: function() { return { querySelector: function() { return { textContent: 'uuid' }; } }; }
  };
}
function estado(b) { return b.innerHTML + '|' + b.classList.lista(); }
var copiaOk = true;
var navigator = { clipboard: { writeText: function() {
  return { then: function(ok, ko) { copiaOk ? ok() : ko(); } }; } } };
"""


@pytest.fixture
def dobles_de_copiar():
    """Dobles del navegador para los botones de copiar (ver DOBLES_DE_COPIAR)."""
    return DOBLES_DE_COPIAR


@pytest.fixture
def demo_chat_path():
    """Ruta a la fixture demo rica (un chat sintético con un poco de todo), para
    los tests de integración del HTML."""
    return Path(__file__).resolve().parent / "fixtures" / "chat_demo.jsonl"


@pytest.fixture
def write_jsonl(tmp_path):
    """Escribe una lista de dicts como un ``.jsonl`` en un sandbox temporal.

    Devuelve la ruta al archivo. Cada test recibe su propio ``tmp_path``, así
    que nunca se tocan archivos reales del usuario.
    """
    def _write(records, name="chat.jsonl"):
        path = tmp_path / name
        lines = [json.dumps(record, ensure_ascii=False) for record in records]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
    return _write
