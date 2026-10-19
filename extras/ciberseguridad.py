# -*- coding: utf-8 -*-
"""
ciberseguridad.py - Análisis POR PATRONES de código y puertos (NO va en el APK).
Sustituye a 'Cybersecurity Bunker Core' y 'Scanner Core'. Diferencias:
- Importable (nombre sin espacios) y una regex mala no rompe el módulo: se valida antes de aprenderla.
- Más patrones (rm -rf ~, os.system, subprocess, eval/exec, pickle...).
- Dice la verdad: AVISA, no bloquea ni aísla nada. Es una ayuda para revisar, no una protección.
- Escáner de puertos: solo 127.0.0.1, puertos 8000 (pasarela extra) y 8765 (laboratorio).
"""
import json
import os
import re
import socket

PATRONES_BASE = [
    (r"rm\s+-rf\s+(/|~|\$HOME)", "borrado recursivo peligroso"),
    (r"\bos\.system\s*\(", "ejecuta comandos del sistema"),
    (r"\bsubprocess\b", "usa subprocess"),
    (r"\beval\s*\(", "eval()"),
    (r"\bexec\s*\(", "exec()"),
    (r"\bpickle\.loads?\s*\(", "pickle (puede ejecutar código)"),
    (r"\b__import__\s*\(", "import dinámico"),
    (r"\bsocket\b", "usa sockets de red"),
    (r"(api[_-]?key|token|password)\s*=\s*['\"][^'\"]{8,}", "posible secreto escrito en el código"),
]


def _dir_datos():
    d = os.environ.get("KIRA_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".kira")
    os.makedirs(d, exist_ok=True)
    return d


class AnalizadorPatrones:
    def __init__(self):
        self.ruta = os.path.join(_dir_datos(), "patrones_aprendidos.json")
        self.patrones = [(re.compile(p, re.I), d) for p, d in PATRONES_BASE]
        for p, d in self._leer():
            self.aprender(p, d, guardar=False)

    def _leer(self):
        try:
            with open(self.ruta, encoding="utf-8") as f:
                return [(str(a), str(b)) for a, b in json.load(f)]
        except (OSError, ValueError, TypeError):
            return []

    def aprender(self, patron, descripcion="patrón aprendido", guardar=True):
        """Añade un patrón solo si es una regex válida. Devuelve True/False."""
        try:
            comp = re.compile(patron, re.I)
        except (re.error, TypeError):
            return False
        self.patrones.append((comp, str(descripcion)[:100]))
        if guardar:
            extra = self._leer() + [(patron, str(descripcion)[:100])]
            tmp = self.ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(extra[-200:], f, ensure_ascii=False)
            os.replace(tmp, self.ruta)
        return True

    def analizar(self, codigo):
        """Lista de hallazgos (línea, descripción). Vacía = ningún patrón conocido (no garantiza que sea seguro)."""
        hallazgos = []
        for n, linea in enumerate(str(codigo).splitlines(), 1):
            for comp, desc in self.patrones:
                if comp.search(linea):
                    hallazgos.append((n, desc))
        return hallazgos

    def informe(self, codigo):
        h = self.analizar(codigo)
        if not h:
            return "Sin coincidencias con los patrones conocidos (esto NO garantiza que sea seguro)."
        return "Coincidencias (solo aviso; no se ha bloqueado nada):\n" + "\n".join(f"  línea {n}: {d}" for n, d in h)


def escanear_puertos(puertos=(8000, 8765), host="127.0.0.1", timeout=0.5):
    """{puerto: abierto?} - solo en este equipo."""
    abiertos = {}
    for p in puertos:
        with socket.socket() as s:
            s.settimeout(timeout)
            abiertos[p] = s.connect_ex((host, int(p))) == 0
    return abiertos


if __name__ == "__main__":
    print(AnalizadorPatrones().informe("import os\nos.system('ls')"))
    print(escanear_puertos())
