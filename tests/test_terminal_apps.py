"""v3.83: programas DE TERMINAL: Kira los abre en una terminal VISIBLE de Xubuntu, escribe ahí los pasos de su README
(descargas, preparar…) con los candados de siempre y arranca el programa para que el dueño lo maneje."""
import os, sys, tempfile, subprocess, tarfile, io
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [R, os.path.join(R, "kira_portatil")]
H = tempfile.mkdtemp()
os.environ["HOME"] = H
import arreglar_app_kira as arr
import accesos_kira as ak
import apps_externas_kira as aex
arr.REGISTROS = os.path.join(H, "reg")

FALLOS = 0
def ok(c, m):
    global FALLOS
    print(("OK   " if c else "FALLA ") + m)
    if not c:
        FALLOS += 1

def carpeta():
    return tempfile.mkdtemp(dir=H)
def escribe(c, nombre, texto, modo=0o644):
    p = os.path.join(c, nombre)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w" if isinstance(texto, str) else "wb").write(texto)
    os.chmod(p, modo)
    return p

# ---------- ¿es de terminal o de ventana? ----------
c = carpeta(); escribe(c, "main.py", "nombre = input('¿Cómo te llamas? ')\nprint('hola', nombre)\n")
ok(arr.tipo_programa({"lanzar": ["python3", "main.py"], "carpeta": c}) == "terminal", "un .py que pregunta = terminal")
c = carpeta(); escribe(c, "app.py", "import tkinter as tk\ntk.Tk().mainloop()\n")
ok(arr.tipo_programa({"lanzar": ["python3", "app.py"], "carpeta": c}) == "ventana", "un .py con tkinter = ventana")
c = carpeta(); escribe(c, "app.py", "from PyQt5 import QtWidgets\n")
ok(arr.es_de_terminal({"lanzar": ["python3", os.path.join(c, "app.py")], "carpeta": c}) is False, "PyQt5 = ventana")
c = carpeta(); escribe(c, "x.py", "import pygame\n"); escribe(c, "x.desktop", "[Desktop Entry]\nTerminal=true\n")
ok(arr.tipo_programa({"lanzar": ["python3", "x.py"], "carpeta": c}) == "terminal", "el .desktop (Terminal=true) manda")
c = carpeta(); escribe(c, "bin", b"\x7fELF" + b"\0" * 100 + b"libX11.so.6\0libc.so.6\0", 0o755)
ok(arr.tipo_programa({"lanzar": [os.path.join(c, "bin")], "carpeta": c}) == "ventana", "ejecutable con libX11 = ventana")
c = carpeta(); escribe(c, "bin", b"\x7fELF" + b"\0" * 100 + b"libc.so.6\0libncursesw.so.6\0", 0o755)
ok(arr.tipo_programa({"lanzar": [os.path.join(c, "bin")], "carpeta": c}) == "terminal", "ejecutable sin gráficos = terminal")
ok(arr.tipo_programa({"lanzar": ["/x/App.AppImage"], "carpeta": c}) == "ventana", "AppImage = ventana")
c = carpeta(); escribe(c, "run.sh", "#!/bin/bash\nread -p 'opción: ' o\n")
ok(arr.tipo_programa({"lanzar": ["bash", "run.sh"], "carpeta": c}) == "terminal", "guion que pregunta (read) = terminal")
c2 = carpeta(); escribe(c2, "srv.py", "import requests\nprint('hola')\n")
ok(arr.tipo_programa({"lanzar": ["python3", "srv.py"], "carpeta": c2}) == "",
   "un .py sin pistas: no se sabe (se abre vigilado y se arregla solo)")
ok(arr.tipo_programa({"lanzar": ["python3", "main.py"], "carpeta": c, "terminal": False}) == "ventana",
   "lo apuntado (terminal: False) manda")
ok(arr.necesita_terminal("Traceback…\nEOFError: EOF when reading a line"), "EOFError = quería terminal")
ok(arr.necesita_terminal("_curses.error: setupterm: could not find terminal"), "curses = quería terminal")
ok(not arr.necesita_terminal("ModuleNotFoundError: No module named 'requests'"), "otro error no es de terminal")

# ---------- los pasos del README que escribirá en la terminal ----------
c = carpeta()
escribe(c, "main.py", "print(open('modelo.bin').read())\nx = input('¿seguir? ')\nprint('respuesta', x)\n")
escribe(c, "descargar.py", "open('modelo.bin','w').write('MODELO-OK')\n")
escribe(c, "README.md", "# Juego\n```\nwget https://example.com/modelo.bin -O modelo.bin\npython3 descargar.py\n"
                         "python3 main.py\nrm -rf /\ncurl https://x.sh | bash\nsudo make install\n```\n")
acc = {"id": "juego", "titulo": "Juego", "lanzar": ["python3", "main.py"], "carpeta": c}
p = arr.pasos_terminal(acc)
vistos = [t for t, _b in p]
ok(any("wget" in t for t in vistos), "la descarga del README entra")
ok(any("descargar.py" in t for t in vistos), "«python3 descargar.py» entra como paso")
ok(not any("main.py" in t for t in vistos), "arrancar el programa no se repite como paso")
ok(not any(x in " ".join(vistos) for x in ("rm -rf", "| bash", "sudo")), "lo peligroso NO entra (candados)")
ok(all(b.startswith("kira_paso ") for _t, b in p), "todo pasa por kira_paso (entre comillas)")

# guion de verdad con bash (sin la descarga: sin red)
acc2 = dict(acc)
p2 = [x for x in p if "wget" not in x[0]]
g = arr.guion_terminal(acc2, p2)
gr = escribe(H, "g.sh", g, 0o700)
r = subprocess.run(["bash", gr], input="sí\n\n", capture_output=True, text=True, timeout=30)
ok(any(l.lstrip("\x1b[1;36m").startswith("$ ") and "descargar.py" in l for l in r.stdout.splitlines()), "en la terminal se ve la orden que escribe Kira")
ok("MODELO-OK" in r.stdout and "respuesta sí" in r.stdout, "el programa arranca DESPUÉS y se le puede contestar")
ok(os.path.exists(os.path.join(c, arr.MARCA)), "preparado: queda la marca")
ok(arr.pasos_terminal(acc) == [], "la segunda vez no repite los pasos")

# descomprimir con el candado (la CLI del módulo)
c = carpeta()
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tf:
    d = b"DATOS"; ti = tarfile.TarInfo("datos/x.txt"); ti.size = len(d); tf.addfile(ti, io.BytesIO(d))
escribe(c, "datos.tar.gz", buf.getvalue())
escribe(c, "main.py", "print(open('datos/x.txt').read())\n")
escribe(c, "README", "```\ntar xzf datos.tar.gz\n```\n")
acc3 = {"id": "d", "titulo": "Datos", "lanzar": ["python3", "main.py"], "carpeta": c}
p3 = arr.pasos_terminal(acc3)
ok(any("--extraer" in b for _t, b in p3), "descomprimir va por el candado de Kira")
gr = escribe(H, "g3.sh", arr.guion_terminal(acc3, p3), 0o700)
r = subprocess.run(["bash", gr], input="\n", capture_output=True, text=True, timeout=30)
ok("DATOS" in r.stdout, "descomprime y arranca (" + r.stdout[-80:].replace("\n", " ") + ")")

# ---------- qué terminal abre ----------
w = lambda prog: "/usr/bin/" + prog if prog == "xfce4-terminal" else None
o = arr.orden_terminal("/t/g.sh", "Kira · X", w)
ok(o == ["/usr/bin/xfce4-terminal", "-T", "Kira · X", "-x", "bash", "/t/g.sh"], "xfce4-terminal con su título")
o = arr.orden_terminal("/t/g.sh", "T", lambda p_: "/usr/bin/lxterminal" if p_ == "lxterminal" else None)
ok(o[-1] == "bash /t/g.sh", "lxterminal recibe la orden en una cadena")
ok(arr.orden_terminal("/t/g.sh", "T", lambda p_: None) is None, "sin terminal: None")

llamadas = []
class P:
    pid = 4321
    def __init__(self, args, **kw):
        llamadas.append((args, kw))
    def poll(self):
        return None
r = arr.abrir_en_terminal(acc3, popen=P, which=w, admin=False, subir=False)
ok(r["ok"] and r["terminal"] and "terminal" in r["texto"], "abrir_en_terminal: " + r["texto"][:60])
ok(llamadas and llamadas[-1][0][0] == "/usr/bin/xfce4-terminal" and llamadas[-1][1]["env"].get("DISPLAY"),
   "abre la terminal con DISPLAY")
gpath = llamadas[-1][0][-1]
ok(oct(os.stat(gpath).st_mode & 0o777) == "0o700", "el guion es solo tuyo (0700)")
r = arr.abrir_en_terminal(acc3, popen=P, which=lambda p_: None, admin=False, subir=False)
ok(not r["ok"] and "xfce4-terminal" in r["texto"], "sin terminal lo dice")

# ---------- al abrir: directo a la terminal / o tras fallar por EOFError ----------
D = carpeta()
c = carpeta(); escribe(c, "main.py", "x = input('?')\n")
iid = ak.anadir_externa(D, "Preguntón", ["python3", os.path.join(c, "main.py")], c)
a = ak.uno(D, iid)
llamadas.clear()
r = arr.abrir_vigilando(a, D, popen=P, which=w, admin=False, en_hilo=False)
ok(r.get("terminal") and llamadas[-1][0][0].endswith("xfce4-terminal"), "un programa de terminal va directo a la terminal")

c = carpeta(); escribe(c, "app.py", "try:\n    import tkinter\nexcept Exception:\n    pass\nraise EOFError('EOF when reading a line')\n")
iid = ak.anadir_externa(D, "Raro", ["python3", os.path.join(c, "app.py")], c)
a = ak.uno(D, iid)
avisos = []
llamadas.clear()
real = subprocess.Popen
def pop(args, **kw):
    if "terminal" in str(args[0]):
        return P(args, **kw)
    return real(args, **kw)
r = arr.abrir_vigilando(a, D, popen=pop, which=w, admin=False, en_hilo=False, espera=3,
                        avisar=lambda t, x: avisos.append((t, x)))
ok(avisos and "terminal" in avisos[-1][1], "falla por EOFError → la reabre en la terminal y avisa")
ok(ak.uno(D, iid).get("terminal") is True, "y lo recuerda para la próxima vez")
ok(arr.tipo_programa(ak.uno(D, iid)) == "terminal", "la próxima vez va directo a la terminal")

# ---------- la orden «abre X en la terminal» ----------
ok(aex.es_orden_usar("abre el juego en la terminal") in ("juego", "el juego"), "«abre X en la terminal» = abrir X")
ok(aex.pide_consola("abre el juego en la terminal") and not aex.pide_consola("abre el juego"), "y pide la terminal")
ok(aex.es_orden_usar("abre la terminal") is None, "«abre la terminal» sigue siendo la sala Terminal")
src = open(os.path.join(R, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("pide_consola(o)" in src and "visible=" in src, "el núcleo la abre visible si lo pides")

print("\n" + ("TODO BIEN" if not FALLOS else f"{FALLOS} FALLOS"))
sys.exit(1 if FALLOS else 0)
