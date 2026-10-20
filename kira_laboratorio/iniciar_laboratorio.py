# -*- coding: utf-8 -*-
"""
iniciar_laboratorio.py - Arranca el laboratorio para que Kira lo encuentre SOLA en tu WiFi.

En Windows basta con hacer doble clic en «Arrancar laboratorio.bat» (en esta misma carpeta).
La primera vez, en el móvil dile «Kira, conéctate al ordenador» y luego el código de 6 cifras que sale en esta
ventana. Después Kira se conecta sola cada vez que lo necesita, aunque cambie la dirección del ordenador.

El token se crea solo y se guarda en token_lab.txt (solo legible por tu usuario). Para echar a todos los móviles,
borra token_lab.txt y vuelve a arrancar: tendrán que emparejarse otra vez.

Uso:  python iniciar_laboratorio.py                    (por la WiFi: el móvil lo encuentra)
      python iniciar_laboratorio.py --solo-este-equipo (nadie más lo ve)
      python iniciar_laboratorio.py --con-windows      (que arranque solo al encender Windows)
      python iniciar_laboratorio.py --sin-windows      (deja de arrancar solo)
      Lo demás pasa tal cual a servidor_lab.py (por ejemplo --permitir-instalar).
"""
import os
import secrets
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(AQUI, "token_lab.txt")
NOMBRE_INICIO = "Kira laboratorio.bat"


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


def carpeta_inicio_windows():
    """La carpeta «Inicio» de Windows: lo que hay ahí arranca al encender el equipo."""
    base = os.environ.get("APPDATA")
    if os.name != "nt" or not base:
        return None
    return os.path.join(base, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def contenido_inicio(python=None, aqui=AQUI, extra=()):
    """El .bat que se deja en la carpeta Inicio: arranca el laboratorio minimizado."""
    python = python or sys.executable
    args = " ".join(f'"{a}"' for a in extra)
    return ("@echo off\r\n"
            f'cd /d "{aqui}"\r\n'
            f'start "Laboratorio de Kira" /min "{python}" "{os.path.join(aqui, "iniciar_laboratorio.py")}" {args}'.rstrip()
            + "\r\n")


def con_windows(activar, extra=()):
    carpeta = carpeta_inicio_windows()
    if carpeta is None:
        return False, "Esto solo funciona en Windows."
    ruta = os.path.join(carpeta, NOMBRE_INICIO)
    if not activar:
        if os.path.isfile(ruta):
            os.remove(ruta)
            return True, "Listo: el laboratorio ya no arrancará solo al encender Windows."
        return True, "No estaba puesto para arrancar con Windows."
    os.makedirs(carpeta, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write(contenido_inicio(extra=extra))
    return True, f"Listo: el laboratorio arrancará solo (minimizado) al encender Windows. ({ruta})"


def argumentos(argv):
    """Traduce las opciones sencillas a las de servidor_lab.py. Devuelve (args_servidor, accion_windows)."""
    salida, windows = [], None
    for a in argv:
        if a == "--solo-este-equipo":
            salida += ["--host", "127.0.0.1"]
        elif a == "--con-windows":
            windows = True
        elif a == "--sin-windows":
            windows = False
        else:
            salida.append(a)
    if "--host" not in salida:
        salida += ["--host", "0.0.0.0"]                 # por defecto, por la WiFi: así el móvil lo encuentra
    return salida, windows


if __name__ == "__main__":
    args, windows = argumentos(sys.argv[1:])
    if windows is not None:
        extra = [a for a in sys.argv[1:] if a not in ("--con-windows", "--sin-windows")]
        ok, msg = con_windows(windows, extra)
        print(msg)
        if not windows:
            sys.exit(0 if ok else 1)
    t = token()
    print("Laboratorio de Kira")
    print("  Si Windows pregunta por el cortafuegos, pulsa «Permitir» (redes privadas): así el móvil lo encuentra.")
    print(f"  (El token está en {RUTA}; no hace falta copiarlo: Kira lo recibe al emparejarse.)\n")
    env = dict(os.environ, KIRA_LAB_TOKEN=t)
    sys.exit(subprocess.call([sys.executable, os.path.join(AQUI, "servidor_lab.py")] + args, env=env))
