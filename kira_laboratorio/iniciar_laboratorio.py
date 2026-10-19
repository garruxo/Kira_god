# -*- coding: utf-8 -*-
"""
iniciar_laboratorio.py - Arranca el servidor del laboratorio con un token ALEATORIO propio.
Guarda el token en datos/../token_lab.txt (solo legible por tu usuario). Cópialo en el panel de
Kira ('config pasarela'). Para cambiarlo, borra token_lab.txt y vuelve a ejecutar.
Uso:  python iniciar_laboratorio.py            (solo este equipo)
      python iniciar_laboratorio.py --host 0.0.0.0   (accesible desde tu WiFi)
"""
import os
import secrets
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(AQUI, "token_lab.txt")


def token():
    if os.path.isfile(RUTA):
        t = open(RUTA, encoding="utf-8").read().strip()
        if len(t) >= 16:
            return t
    t = secrets.token_urlsafe(32)
    fd = os.open(RUTA, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(t)
    return t


if __name__ == "__main__":
    t = token()
    print(f"Token del laboratorio (también en {RUTA}):\n{t}\n")
    env = dict(os.environ, KIRA_LAB_TOKEN=t)
    sys.exit(subprocess.call([sys.executable, os.path.join(AQUI, "servidor_lab.py")] + sys.argv[1:], env=env))
