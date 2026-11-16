# -*- coding: utf-8 -*-
"""v3.95: «instala el archivo X de las descargas» → busca ESE archivo en Descargas por su nombre y lo instala."""
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

# órdenes
for f, esp in (("instala el archivo vlc de las descargas", "vlc"),
               ("instala el archivo Krita-5.2.AppImage de descargas", "Krita-5.2.AppImage"),
               ("kira, instala «mi programa» desde mis descargas", "mi programa"),
               ("instala obsidian de la carpeta de descargas", "obsidian"),
               ("instala el programa geany que está en descargas", "geany"),
               ("instálame la app blender de las descargas.", "blender")):
    ok(gb.es_orden_archivo(f) == esp, f"«{f}» → {gb.es_orden_archivo(f)!r}")
for f in ("instala lo de descargas", "instala vlc", "instala lo que he descargado", "instala esto de descargas"):
    ok(gb.es_orden_archivo(f) is None, "no es esto: " + f)

D = os.path.join(T, "Descargas"); os.makedirs(D)
def escribe(nombre, datos=b"x" * 100, hace=0):
    r = os.path.join(D, nombre); open(r, "wb").write(datos)
    t = time.time() - hace; os.utime(r, (t, t)); return r
k = escribe("Krita-5.2.6-x86_64.AppImage", hace=100)
o = escribe("Obsidian-1.6.7.AppImage", hace=50)
escribe("foto-krita.jpg")
g1 = escribe("geany-2.0.tar.gz", hace=30)
g2 = escribe("geany-plugins-2.0.tar.gz", hace=20)
escribe("vacio.AppImage", b"")
e = gb.buscar_en_descargas("krita", [D])
ok(e["listos"] == [k], "por una palabra, sin la foto: " + str(e))
ok(gb.buscar_en_descargas("KRITA-5.2.6-x86_64.AppImage", [D])["listos"] == [k], "nombre exacto con mayúsculas")
ok(gb.buscar_en_descargas("obsidian 1.6", [D])["listos"] == [o], "con espacios en vez de guiones")
ok(len(gb.buscar_en_descargas("geany", [D])["listos"]) == 2, "dos parecidos: geany y geany-plugins")
ok(gb.buscar_en_descargas("vacio", [D])["listos"] == [], "un archivo vacío no cuenta")
ok(gb.buscar_en_descargas("gimp", [D]) == {"listos": [], "bajando": []}, "nada que se llame así")
ok(gb.programas_en_descargas([D])[0] == "geany-plugins-2.0.tar.gz" and "foto-krita.jpg" not in gb.programas_en_descargas([D]),
   "lista de programas en Descargas (lo nuevo primero, sin fotos)")
# a medias
escribe("Blender-4.2.tar.xz", b"")
pb = escribe("Blender-4.2.tar.xz.part", b"b" * 10)
e = gb.buscar_en_descargas("blender", [D])
ok(not e["listos"] and e["bajando"] and e["bajando"][0][1] == "Blender-4.2.tar.xz", "lo ve bajándose: " + str(e))
def acaba():
    time.sleep(0.3); os.replace(pb, os.path.join(D, "Blender-4.2.tar.xz"))
threading.Thread(target=acaba).start()
avisos = []
r, mot = gb.esperar_archivo(pb, al_paso=avisos.append, cada=0.1)
ok(mot == "ok" and r.endswith("Blender-4.2.tar.xz") and avisos, f"espera a que acabe ESE: {r} {mot}")

# núcleo
import nucleo_portatil as nu
gb.carpetas_descargas = lambda: [D]
inst = []
nu._instalar_app = lambda core, fuente, paso, **kw: (inst.append(fuente), {"texto": "instalado"})[1]
class Core:
    def cancelado(self): return False
r = nu.ejecutar(Core(), "instala el archivo krita de las descargas", lambda *a: None)
ok(inst and inst[-1] == k and "Krita-5.2.6" in r["texto"], "el núcleo instala ESE: " + r["texto"][:70])
inst.clear()
r = nu.ejecutar(Core(), "instala el archivo geany de las descargas", lambda *a: None)
ok(not inst and "varios" in r["texto"] and "geany-plugins" in r["texto"], "con varios parecidos, pregunta: " + r["texto"][:90])
r = nu.ejecutar(Core(), "instala el archivo geany-2.0.tar.gz de las descargas", lambda *a: None)
ok(inst and inst[-1] == g1, "con el nombre exacto, ese")
inst.clear()
r = nu.ejecutar(Core(), "instala el archivo gimp de las descargas", lambda *a: None)
ok(not inst and "No encuentro" in r["texto"] and "Krita" in r["texto"], "si no está, dice lo que hay: " + r["texto"][:90])

import mando_kira
ok(mando_kira.es_trabajo("instala el archivo krita de las descargas"), "desde el móvil se le pasa a KiraOS")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
