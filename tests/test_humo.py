"""Humo — la suite descubre pytest y los módulos del proyecto cargan limpios.

Si estos tests fallan, el problema es del andamiaje (carga de módulos o
configuración pytest), no de la lógica de Code Chat Viewer.
"""


def test_visualizer_carga(viz):
    assert isinstance(viz.APP_VERSION, str) and viz.APP_VERSION
    assert callable(viz.parse_chat_json)
    assert callable(viz.generate_html)


def test_manager_carga(mgr):
    assert callable(mgr.collect_chats_data)
    assert callable(mgr.generate_index)
    # manager reexporta símbolos de visualizer al importarlo.
    assert callable(mgr.parse_chat_json)
