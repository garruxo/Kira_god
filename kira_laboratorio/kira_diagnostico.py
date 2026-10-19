# -*- coding: utf-8 -*-
"""
kira_diagnostico.py - Comprobaciones REALES del laboratorio. Termina con código 0 solo si todo pasa.
(La versión anterior imprimía "TODO OPERATIVO" siempre.)  Uso:  python kira_diagnostico.py
"""
import ast
import glob
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))


def comprobar():
    """Devuelve lista de (nombre, ok, detalle)."""
    r = []

    def paso(nombre, f):
        try:
            detalle = f()
            r.append((nombre, True, str(detalle or "")))
        except Exception as e:
            r.append((nombre, False, f"{type(e).__name__}: {e}"))

    def sintaxis():
        for p in glob.glob(os.path.join(AQUI, "*.py")) + glob.glob(os.path.join(AQUI, "tests_fijos", "*.py")):
            with open(p, encoding="utf-8") as f:
                ast.parse(f.read(), p)
        return "todos los .py compilan"

    def rutas():
        from lab_rutas import ruta_segura, RutaNoPermitida
        for malo in ("../x.py", "/etc/passwd", ".oculto.py"):
            try:
                ruta_segura(malo)
            except RutaNoPermitida:
                continue
            raise AssertionError(f"ruta_segura aceptó {malo!r}")
        return "rechaza rutas peligrosas"

    def escritura():
        with tempfile.TemporaryDirectory() as t:
            os.environ["KIRA_LAB_DATA"] = t
            from kira_bridge import KiraBridge
            b = KiraBridge()
            assert b.guardar_archivo("prueba.txt", "hola").startswith("[OK]")
            assert b.leer_texto("prueba.txt") == "hola"
            os.environ.pop("KIRA_LAB_DATA")
        return "lectura/escritura en datos/"

    def sandbox():
        with tempfile.TemporaryDirectory() as t:
            os.environ["KIRA_LAB_DATA"] = t
            with open(os.path.join(t, "ok.py"), "w") as f:
                f.write("print(2+2)")
            with open(os.path.join(t, "bucle.py"), "w") as f:
                f.write("while True: pass")
            from kira_sandbox import KiraSandbox
            s = KiraSandbox()
            a = s.ejecutar("ok.py", timeout=5)
            assert a["ok"] and "4" in a["salida"], a
            b = s.ejecutar("bucle.py", timeout=2)
            assert not b["ok"], "el bucle infinito no fue detenido"
            os.environ.pop("KIRA_LAB_DATA")
        return "ejecuta y corta bucles"

    def tests_fijos():
        assert glob.glob(os.path.join(AQUI, "tests_fijos", "test_*.py")), "no hay tests fijos"
        return "hay tests fijos"

    for n, f in (("sintaxis", sintaxis), ("rutas", rutas), ("escritura", escritura),
                 ("sandbox", sandbox), ("tests_fijos", tests_fijos)):
        paso(n, f)
    return r


def main():
    sys.path.insert(0, AQUI)
    resultados = comprobar()
    for n, ok, d in resultados:
        print(f"[{'OK' if ok else 'FALLA'}] {n}: {d}")
    fallos = sum(1 for _, ok, _ in resultados if not ok)
    print(f"\n{len(resultados) - fallos}/{len(resultados)} comprobaciones superadas.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
