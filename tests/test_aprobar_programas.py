# -*- coding: utf-8 -*-
"""v3.90: lo que Kira ve que hace falta instalar MIENTRAS ESTUDIA queda esperando tu aprobación en «Mis programas»
y, al ACABAR de estudiar, te lo pregunta. Nunca instala nada sola."""
import os, sys, tempfile, types, json

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_NACIMIENTO"] = os.path.join(T, "nac.json")
os.environ["KIRA_DATOS_NUCLEO"] = T
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

# ---------- qué pide instalar una página ----------
pag = {"url": "https://ejemplo.org/instalar", "titulo": "SuperApp - Instalación",
       "texto": "Primero instala lo necesario:\n$ sudo apt install -y ffmpeg libsdl2-dev and then run make\n"
                "Opcional: flatpak install flathub org.videolan.VLC\nNada más.",
       "codigos": ["sudo apt-get install --no-install-recommends python3-tk git\n./configure"]}
p = cpk.programas_que_pide(pag)
nombres = [x["fuente"] for x in p]
ok(nombres == ["ffmpeg", "libsdl2-dev", "flatpak org.videolan.VLC", "python3-tk", "git"], f"saca los paquetes ({nombres})")
ok("and" not in nombres and "run" not in nombres and "make" not in nombres, "se para en el texto normal")
ok(cpk.programas_que_pide({"texto": "apt es el gestor de paquetes"}) == [], "hablar de apt no es pedir nada")
ok(cpk.programas_que_pide({"texto": "sudo apt install $(cat lista) ; rm -rf /"}) == [], "nada raro como paquete")

# ---------- se apunta al estudiar, esperando ----------
import kira_god
class Rec:
    def guardar(self, *a, **k): return 1
falso = types.SimpleNamespace(dir=T, recuerdos=Rec(), resumir_pagina=lambda p_, t_="": ("resumen " * 10, None))
kira_god.KiraGodCore.guardar_pagina(falso, pag, "superapp")
kira_god.KiraGodCore.guardar_pagina(falso, pag, "superapp")
kira_god.KiraGodCore.guardar_pagina(falso, {"url": "https://github.com/obsproject/obs-studio", "texto": "OBS graba"}, "obs")
pend = cpk.pendientes_aprobar(T)
ok(len(pend) == 6 and all(e["espera"] for e in pend), f"6 esperando tu aprobación, sin repetir ({len(pend)})")

# ---------- la ventana «Mis programas» ----------
pest = cpk.pestanas(cpk.web(T), [], [])
web = pest[0]
ok("esperan tu sí" in web["titulo"], "la pestaña dice cuántos esperan")
ok(web["secciones"][0][0] == "espera" and "aprobación" in web["secciones"][0][1], "sección «Esperan tu aprobación» arriba")
esp = [f for f in web["filas"] if f["seccion"] == "espera"]
ok(len(esp) == 6, "todas en la sección de espera")
ff = next(f for f in esp if f["texto"] == "ffmpeg")
ok([b["texto"] for b in ff["botones"]] == ["Instalar", "Ir a la web", "No, gracias"] and ff["botones"][0]["accion"] == "decir:instala ffmpeg",
   "Instalar = «instala ffmpeg» (tu sí, por el camino de siempre)")
ok("SuperApp" in ff["detalle"], "dice quién lo pide")

# ---------- tu sí / tu no ----------
ok(cpk.aprobar(T, "ffmpeg"), "«instala ffmpeg» lo aprueba")
ok(not any(e["fuente"] == "ffmpeg" for e in cpk.pendientes_aprobar(T)), "ya no espera")
ok(not any(f["texto"] == "ffmpeg" for f in cpk.pestanas(cpk.web(T), [], [])[0]["filas"]), "y sale de la lista")
gid = next(e["id"] for e in cpk.web(T) if e["fuente"] == "git")
cpk.quitar_web(T, gid)
ok(not any(e["fuente"] == "git" for e in cpk.web(T)), "«No, gracias» la quita")

# ---------- al ACABAR de estudiar te pregunta ----------
import time
class Nucleo:
    dir = T
    es_kiraos = True
    _estudio_con_aviso = kira_god.KiraGodCore._estudio_con_aviso
    _avisar_programas_vistos = kira_god.KiraGodCore._avisar_programas_vistos
    estudiar_en_internet = kira_god.KiraGodCore.estudiar_en_internet
    estudiar_a_fondo = kira_god.KiraGodCore.estudiar_a_fondo
    def _estudiar_en_internet_(self, consulta, paginas=3, al_paso=None, enlaces=4):
        kira_god.KiraGodCore.guardar_pagina(falso, {"url": "https://x.org/i", "titulo": "Cosa",
                                                    "texto": "sudo apt install cmake"}, consulta)
        return "[OK] He estudiado internet."
    def _estudiar_a_fondo_(self, tema, al_paso=None):
        return self.estudiar_en_internet(tema) + " Y vídeos."

r = Nucleo().estudiar_a_fondo("cosa")
ok(r.count("Mientras estudiaba") == 1, "pregunta UNA vez al acabar (no en el estudio de dentro)")
ok("cmake" in r and "ffmpeg" not in r and "Mis programas" in r, "solo lo nuevo de este estudio, y dónde está")
ok("No he instalado nada" in r, "dice que no instaló nada")
av = json.load(open(os.environ["KIRA_AVISOS"]))
ok(any("cmake" in a["texto"] for a in av), "en KiraOS deja un aviso prioritario")
r2 = Nucleo().estudiar_a_fondo("cosa")
ok("Mientras estudiaba" not in r2, "si no hay nada nuevo, no pregunta")
m = Nucleo(); m.es_kiraos = False
txt = cpk.texto_aviso([{"nombre": "x", "fuente": "x", "tipo": "sistema"}], en_kiraos=False)
ok("KiraOS" in txt, "en el móvil explica que «Mis programas» está en KiraOS")

# ---------- KiraOS: «instala X» aprueba ----------
src = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("cpk.aprobar(core.dir, fuente)" in src, "el núcleo aprueba al instalar por tu orden")

print(f"\n{'TODO BIEN' if not fallos else f'{n - fallos}/{n} bien'} ({n})")
sys.exit(1 if fallos else 0)
