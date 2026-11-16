# -*- coding: utf-8 -*-
"""v3.94: si el programa AÚN se está descargando en el navegador de Xubuntu, Kira espera a que acabe y entonces lo
instala (antes cogía el anterior, o el archivo vacío que Firefox deja mientras baja «X.part»)."""
import os, sys, tempfile, threading, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATOS_NUCLEO"] = T
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import github_buscar_kira as gb

fallos = n = 0
def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1

D = os.path.join(T, "Descargas"); os.makedirs(D)
def escribe(nombre, datos=b"x" * 100, hace=0):
    r = os.path.join(D, nombre)
    open(r, "wb").write(datos)
    t = time.time() - hace
    os.utime(r, (t, t))
    return r

viejo = escribe("viejo-1.0.AppImage", hace=3600)
# Firefox: archivo final VACÍO + «.part» que va creciendo
escribe("nuevo-2.0.AppImage", b"")
parte = escribe("nuevo-2.0.AppImage.part", b"y" * 500)
ok(gb.ultimo_descargado([D]) == viejo, "mientras baja, el archivo vacío de Firefox NO cuenta como descargado")
cur = gb.descargas_en_curso([D])
ok(len(cur) == 1 and cur[0][1] == "nuevo-2.0.AppImage", "ve la descarga en curso: " + str(cur))
escribe("foto.jpg.part", b"z")
ok(len(gb.descargas_en_curso([D])) == 1, "una foto descargándose no cuenta (no es un programa)")
os.remove(os.path.join(D, "foto.jpg.part"))
escribe("Sin confirmar 12345.crdownload", b"q" * 10)
ok(len(gb.descargas_en_curso([D])) == 2, "Chrome «Sin confirmar NNN.crdownload» sí cuenta")
os.remove(os.path.join(D, "Sin confirmar 12345.crdownload"))

# espera a que acabe: un hilo «termina» la descarga como Firefox (renombra el .part al final)
avisos = []
def termina():
    time.sleep(0.4)
    open(parte, "ab").write(b"y" * 500)
    time.sleep(0.4)
    os.replace(parte, os.path.join(D, "nuevo-2.0.AppImage"))
threading.Thread(target=termina).start()
ruta, motivo = gb.esperar_descarga([D], al_paso=avisos.append, cada=0.1)
ok(motivo == "ok" and ruta and ruta.endswith("nuevo-2.0.AppImage"), f"espera y devuelve el NUEVO: {ruta} {motivo}")
ok(any("Se está descargando nuevo-2.0.AppImage" in a for a in avisos) and any("Ya ha acabado" in a for a in avisos),
   "va contando la descarga: " + " | ".join(avisos[:3]))

# parar mientras espera
escribe("otro-3.0.AppImage.part", b"a")
ruta, motivo = gb.esperar_descarga([D], parar=lambda: True, cada=0.05)
ok(ruta is None and motivo == "parada", "«para» deja de esperar")
# atascada (no crece)
ruta, motivo = gb.esperar_descarga([D], quieta=0.2, cada=0.05)
ok(ruta is None and motivo == "atascada", "una descarga que no avanza se da por atascada")
os.remove(os.path.join(D, "otro-3.0.AppImage.part"))
# sin nada en curso: lo de siempre
ruta, motivo = gb.esperar_descarga([D], cada=0.05)
ok(motivo == "ok" and ruta.endswith("nuevo-2.0.AppImage"), "sin descargas en curso: el último descargado")

# órdenes
for f in ("instala lo que estoy descargando", "instala el programa que se está bajando",
          "cuando acabe de descargarse, instálalo", "kira, instala lo que se está descargando",
          "instala lo que he descargado"):
    ok(gb.es_orden_descargado(f), "orden: " + f)
ok(not gb.es_orden_descargado("instala vlc"), "«instala vlc» no es esto")

# el núcleo espera y luego instala ESE
import nucleo_portatil as nu
instalados = []
nu._instalar_app = lambda core, fuente, paso, **kw: (instalados.append(fuente), {"texto": "instalado"})[1]
escribe("final-4.0.AppImage", b"")
p2 = escribe("final-4.0.AppImage.part", b"b" * 50)
gb_carpetas = gb.carpetas_descargas
gb.carpetas_descargas = lambda: [D]
def termina2():
    time.sleep(0.3)
    os.replace(p2, os.path.join(D, "final-4.0.AppImage"))
threading.Thread(target=termina2).start()
_esperar = gb.esperar_descarga
gb.esperar_descarga = lambda **kw: _esperar(**dict(kw, cada=0.1))
class Core:
    def cancelado(self): return False
pasos = []
r = nu._instalar_descargado(Core(), lambda f, t: pasos.append(t))
ok(instalados and instalados[-1].endswith("final-4.0.AppImage"), "el núcleo espera y instala el que acaba de bajar: " + str(instalados))
ok("final-4.0.AppImage" in r["texto"], "lo dice: " + r["texto"][:80])
class CoreParada:
    def cancelado(self): return True
open(os.path.join(D, "otro.AppImage.part"), "wb").write(b"c")
r = nu._instalar_descargado(CoreParada(), lambda f, t: None)
ok(not r.get("ok", True) and "dejo de esperar" in r["texto"], "«para» en el núcleo: " + r["texto"][:60])

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
