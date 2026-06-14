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
def demo_chat_path():
    """Ruta a la fixture demo rica (un chat sintético con un poco de todo).

    Doble uso: tests de integración del HTML y material para las capturas del
    README/RELEASE (generar CCV sobre este JSONL produce una muestra completa).
    """
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
