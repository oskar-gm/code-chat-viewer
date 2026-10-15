"""Compatibilidad con versiones anteriores de Python.

La documentación declara la versión con la que se prueba CCV, pero el código
evita a propósito lo que solo existe desde Python 3.12, para no dejar fuera sin
necesidad a quien use una anterior. Desde 3.12 (PEP 701), la parte de expresión
de un f-string admite barras invertidas, comentarios y el mismo delimitador que
la cadena exterior; antes son un error de sintaxis y el script ni siquiera
arranca. Una versión reciente lo acepta todo sin avisar: esta prueba lo busca en
el código para que no vuelva a colarse.

Necesita Python 3.12 o superior para leer los f-strings por piezas; en versiones
anteriores se omite.
"""

import io
import sys
import tokenize
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _construcciones_de_312(codigo: str) -> list:
    """(línea, motivo) de cada construcción de f-string que exige Python 3.12."""
    hallazgos = []
    pila = []   # f-strings abiertos: delimitador y nivel de llaves de su expresión
    for tok in tokenize.generate_tokens(io.StringIO(codigo).readline):
        en_expresion = any(fs["llaves"] > 0 for fs in pila)
        if tok.type == tokenize.FSTRING_START:
            delim = tok.string.lstrip("rRbBfFuU")
            if any(fs["llaves"] > 0 and fs["delim"] == delim for fs in pila):
                hallazgos.append((tok.start[0], "f-string anidado con el mismo delimitador"))
            pila.append({"delim": delim, "llaves": 0})
            continue
        if tok.type == tokenize.FSTRING_END:
            pila.pop()
            continue
        if not pila:
            continue
        actual = pila[-1]
        if tok.type == tokenize.OP and tok.string in "{}":
            actual["llaves"] += 1 if tok.string == "{" else -1
            continue
        exterior_en_expresion = any(fs["llaves"] > 0 for fs in pila[:-1])
        if tok.type == tokenize.FSTRING_MIDDLE and actual["llaves"] == 0 and not exterior_en_expresion:
            continue   # texto literal del f-string: ahí sí valen
        if not (en_expresion or exterior_en_expresion):
            continue
        if "\\" in tok.string:
            hallazgos.append((tok.start[0], "barra invertida en la expresión"))
        if tok.type == tokenize.COMMENT:
            hallazgos.append((tok.start[0], "comentario en la expresión"))
        if tok.type == tokenize.STRING:
            cuerpo = tok.string.lstrip("rRbBfFuU")
            if any(fs["llaves"] > 0 and cuerpo.startswith(fs["delim"]) for fs in pila):
                hallazgos.append((tok.start[0], "cadena con el delimitador exterior"))
    return hallazgos


@pytest.mark.skipif(sys.version_info < (3, 12), reason="los f-strings se tokenizan por piezas desde 3.12")
def test_detector_reconoce_lo_que_rompe_python_310():
    """El detector caza cada construcción prohibida antes de 3.12 y deja pasar
    las válidas (comillas distintas, texto literal con barras)."""
    malos = [
        'x = f"{\'a\\nb\'}"\n',
        'x = f"{1 # c\n}"\n',
        "x = f'''{'''a'''}'''\n",
    ]
    for codigo in malos:
        assert _construcciones_de_312(codigo), codigo
    buenos = 'x = f"{\'a\'}\\n"\ny = f\'\'\'{"b" if 1 else \'c\'}\'\'\'\n'
    assert _construcciones_de_312(buenos) == []


@pytest.mark.skipif(sys.version_info < (3, 12), reason="los f-strings se tokenizan por piezas desde 3.12")
@pytest.mark.parametrize("script", ["visualizer.py", "manager.py"])
def test_scripts_sin_fstrings_de_python_312(script):
    """Regresión: una barra invertida dentro de una expresión de f-string (la
    cabecera del chat) impedía arrancar CCV en Python 3.10 y 3.11."""
    codigo = (SCRIPTS / script).read_text(encoding="utf-8")
    assert _construcciones_de_312(codigo) == []
