# -*- coding: utf-8 -*-
"""
Test FIJO del laboratorio. Kira no debe poder modificar esta carpeta.
Recibe la ruta del módulo en sys.argv[1]. Salida 0 = pasa, otra = falla.
Añade aquí tus propias comprobaciones (por ejemplo, funciones que todo módulo debe tener).
"""
import importlib.util
import sys

s = importlib.util.spec_from_file_location("mejora", sys.argv[1])
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

# Contrato: si el módulo define 'registrar', debe ser invocable
if hasattr(m, "registrar"):
    assert callable(m.registrar), "'registrar' debe ser una función"

# Contrato: un módulo no puede pisar el núcleo
assert not hasattr(m, "KiraGodCore"), "Un módulo no puede redefinir KiraGodCore"
# Contrato: registrar() devuelve {prefijo: función de 1 parámetro (texto) o 2 (texto, kira)}
if hasattr(m, "registrar"):
    import inspect
    tabla = m.registrar()
    assert isinstance(tabla, dict) and tabla, "registrar() debe devolver un diccionario no vacío"
    for prefijo, fn in tabla.items():
        assert isinstance(prefijo, str) and prefijo.strip() == prefijo and prefijo == prefijo.lower() and prefijo, \
            f"prefijo no válido: {prefijo!r}"
        assert callable(fn), f"'{prefijo}' no es una función"
        try:
            ps = [x for x in inspect.signature(fn).parameters.values() if x.default is x.empty and x.kind in (x.POSITIONAL_ONLY, x.POSITIONAL_OR_KEYWORD)]
        except (TypeError, ValueError):
            ps = None
        assert ps is None or len(ps) in (1, 2), f"'{prefijo}' debe recibir (texto) o (texto, kira)"
print("CONTRATO_OK")
