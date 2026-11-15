# -*- coding: utf-8 -*-
"""v3.91: lo que la página pide en PROSA («necesitas tener ffmpeg»), el TÍTULO de dónde lo vio, «Ir a la web» y el
permiso de administrador en «Mis programas» (lo tengo / botón «Dar permiso»)."""
import json, os, sys, tempfile, types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_DATOS_NUCLEO"] = T
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_AVISOS"] = os.path.join(T, "avisos.json")
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
sys.path.insert(0, RAIZ)
import catalogo_programas_kira as cpk

fallos = n = 0
def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1

def fuentes(texto):
    return [x["fuente"] for x in cpk.programas_que_pide({"texto": texto})]

# ---------- en prosa ----------
ok(fuentes("Para usarlo necesitas tener ffmpeg y Python 3.10 instalados.") == ["ffmpeg", "python3"], "«necesitas tener ffmpeg y Python 3.10»")
ok(fuentes("This tool requires Node.js, git and `libfoo-dev`.") == ["nodejs", "git", "libfoo-dev"], "inglés, con alias y `código`")
ok(fuentes("Requisitos: Java 17, SDL2") == ["default-jre", "libsdl2-dev"], "«Requisitos: Java 17, SDL2»")
ok(fuentes("Antes de nada necesitas una cuenta y conexión a internet.") == [], "palabras normales no son programas")
ok(fuentes("You will need patience and coffee.") == [], "lo que no conoce y no parece paquete, no")
ok(fuentes("Es un programa que habla de ffmpeg.") == [], "nombrarlo sin pedirlo no cuenta")
p = cpk.programas_que_pide({"texto": "Para compilar hace falta cmake."})
ok(p and p[0]["frase"].lower().startswith("hace falta cmake"), "guarda la frase donde lo pide")

# ---------- se apunta con su título y su frase ----------
import kira_god
class Rec:
    def guardar(self, *a, **k): return 1
falso = types.SimpleNamespace(dir=T, recuerdos=Rec(), resumir_pagina=lambda p_, t_="": ("resumen " * 10, None))
pag = {"url": "https://superapp.org/instalar", "titulo": "SuperApp · Cómo instalarla",
       "texto": "Para que funcione necesitas tener ffmpeg instalado."}
kira_god.KiraGodCore.guardar_pagina(falso, pag, "superapp")
e = next(x for x in cpk.web(T) if x["fuente"] == "ffmpeg")
ok(e["titulo"] == "SuperApp · Cómo instalarla" and "necesitas tener ffmpeg" in e["desc"], "apunte con título y frase")
kira_god.KiraGodCore.guardar_pagina(falso, {"url": "https://github.com/obsproject/obs-studio",
                                            "titulo": "OBS Studio en GitHub", "texto": "OBS graba"}, "obs")

# ---------- el aviso al acabar: título y web ----------
lista = cpk.pendientes_aprobar(T)
txt = cpk.texto_aviso(lista, en_kiraos=True)
ok("SuperApp · Cómo instalarla" in txt and "https://superapp.org/instalar" in txt, "el aviso dice el título y la web")
ok("Ir a la web" in txt, "y que puedo llevarte a la web")
txt2 = cpk.texto_aviso(lista, en_kiraos=True, permiso=False)
ok("Dar permiso" in txt2, "sin permiso de admin, lo dice y dónde darlo")

# ---------- la ventana: Ir a la web + permiso ----------
f = cpk.filas(cpk.web(T), [], [], permiso=False)["web"]
ok(f[0]["texto"].startswith("Permiso de administrador: NO") and f[0]["botones"][0]["accion"] == "hacer:prog:permiso",
   "arriba: «NO lo tengo» con botón «Dar permiso»")
ff = next(x for x in f if x["texto"] == "ffmpeg")
ok([b["texto"] for b in ff["botones"]] == ["Instalar", "Ir a la web", "No, gracias"], "Instalar · Ir a la web · No, gracias")
obs = next(x for x in f if x["texto"] == "obs-studio")
ok("OBS Studio en GitHub" in obs["detalle"] and any(b["texto"] == "Ir a la web" for b in obs["botones"]),
   "los de GitHub: su título y «Ir a la web»")
f2 = cpk.filas(cpk.web(T), [], [], permiso=True)["web"]
ok(f2[0]["texto"] == "Permiso de administrador: lo tengo" and not f2[0]["botones"], "con permiso: «lo tengo», sin botón")
ok(not any("Permiso" in x["texto"] for x in cpk.filas(cpk.web(T), [], [])["web"]), "sin mirar el permiso no sale la fila")
pe = cpk.pestanas(cpk.web(T), [], [], permiso=False)
ok("2 esperan tu sí" in pe[0]["titulo"], f"la fila del permiso no cuenta como programa ({pe[0]['titulo']})")

# ---------- los botones de verdad en el escritorio ----------
import escritorio_kira as ek
class Esc(ek.EscritorioMixin):
    def __init__(self):
        self.abiertas = []
    def abrir_navegador(self, url, popen=None, which=None):
        self.abiertas.append(url)
        return {"ok": True, "texto": "abierta"}
esc = Esc()
r = esc._programas_hacer("prog:web:" + e["id"])
ok(esc.abiertas == ["https://superapp.org/instalar"], "«Ir a la web» abre la página donde lo vi")
import arreglar_app_kira as arr
arr.REGISTROS = os.path.join(T, "apps_registro")
r = esc._programas_hacer("prog:permiso")
pend = arr.tomar_pendiente()
ok(pend and "permiso" in pend["guion"] and arr.guion_valido(pend["guion"]), "«Dar permiso» abre MI terminal con el guion")
g = open(pend["guion"], encoding="utf-8").read()
ok("permiso_apps.sh" in g and "sudo" not in g.replace("permiso_apps.sh", ""), "el guion solo lanza permiso_apps.sh")
src = open(os.path.join(RAIZ, "kira_portatil", "escritorio_kira.py"), encoding="utf-8").read()
ok("aex.admin_sin_clave()" in src and "cpk.pestanas(vistos, cpk.propios(est), accesos, permiso)" in src,
   "«Mis programas» mira el permiso cada vez (si lo pierdes, sale el botón)")

print(f"\n{'TODO BIEN' if not fallos else f'{n - fallos}/{n} bien'} ({n})")
sys.exit(1 if fallos else 0)
