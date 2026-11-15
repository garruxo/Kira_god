"""v3.89: lo que Kira ESTUDIÓ (o está estudiando) de un programa en internet le sirve luego para instalarlo y
arrancarlo (pasos, programa puente…), aunque su carpeta no traiga README."""
import os, sys, tempfile
RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path[:0] = [RAIZ, os.path.join(RAIZ, "kira_portatil")]
T = tempfile.mkdtemp()
os.environ["HOME"] = T
DATOS = os.path.join(T, "datos"); os.makedirs(DATOS)
os.environ["KIRA_DATOS_NUCLEO"] = DATOS
import catalogo_programas_kira as cpk
import accesos_kira as ak
import arreglar_app_kira as ar
ar.DATOS = DATOS
ar.REGISTROS = os.path.join(T, "reg")

ok = mal = 0
def mira(c, t):
    global ok, mal
    if c: ok += 1; print("  ok ", t)
    else: mal += 1; print("FALLA", t)

# Kira estudia el repositorio y su wiki (la página de instalación)
pag_repo = {"url": "https://github.com/ana/chatcito", "titulo": "ana/chatcito", "tipo": "texto",
            "texto": "# Chatcito\n\nUn chat por terminal, sencillo y ligero, para la red de casa.\n"}
pag_wiki = {"url": "https://github.com/ana/chatcito/wiki/Instalar", "titulo": "Instalar", "tipo": "web",
            "texto": "## Instalar\n\nPrimero arranca el servidor en otra terminal y déjalo abierto:\n\n```\n"
                     "python3 server.py\n```\n\nLuego, en esta terminal:\n\n```\npython3 cliente.py\n```\n"}
mira(cpk.anotar_web(DATOS, pag_repo) is not None, "el repositorio queda apuntado en Mis programas")
mira(cpk.guardar_guia(DATOS, pag_repo) is not None, "guarda lo que dice el repositorio")
mira(cpk.guardar_guia(DATOS, pag_wiki) is not None, "su wiki se guarda con el mismo programa")
mira(cpk.guardar_guia(DATOS, pag_wiki) is not None and
     cpk.guia_de(DATOS, "https://github.com/ana/chatcito").count("página: https://github.com/ana/chatcito/wiki") == 1,
     "la misma página no se guarda dos veces")
g = cpk.guia_de(DATOS, "https://github.com/ana/chatcito")
mira("python3 server.py" in g and "otra terminal" in g, "se guarda TAL CUAL, con las órdenes (sin resumir)")

# web propia: sus páginas de documentación van con el programa
web = {"url": "https://www.programa-x.org/descargas", "titulo": "Programa X - Descargas", "tipo": "web",
       "texto": "Descarga Programa X para Linux", "descargas": [{"url": "https://www.programa-x.org/x.AppImage",
                                                                 "archivo": "x.AppImage"}]}
cpk.anotar_web(DATOS, web)
doc = {"url": "https://www.programa-x.org/docs/arrancar", "titulo": "Arrancar", "tipo": "web",
       "texto": "Para arrancarlo:\n\n```\n./x.AppImage --sin-sonido\n```\n"}
mira(cpk.guardar_guia(DATOS, doc) == cpk._id("https://www.programa-x.org/descargas"),
     "una página de documentación de su misma web va con ese programa")
mira(cpk.guardar_guia(DATOS, {"url": "https://otra.com/receta", "texto": "x" * 100}) is None,
     "una página que no es de ningún programa no se guarda como guía")

# lo instala: su carpeta NO trae README, pero lo estudiado sí dice cómo arrancarlo
app = os.path.join(T, "apps", "chatcito"); os.makedirs(app)
open(os.path.join(app, "server.py"), "w").write("print('srv')\n")
open(os.path.join(app, "cliente.py"), "w").write("input('?')\n")
iid = ak.anadir_externa(DATOS, "chatcito", ["python3", os.path.join(app, "cliente.py")], app)
a = ak.uno(DATOS, iid)
a_f = dict(a, fuente="https://github.com/ana/chatcito")
# apuntamos la fuente como lo hace el instalador
import json
lista = json.load(open(os.path.join(DATOS, "accesos.json")))
for e in (lista if isinstance(lista, list) else lista.get("accesos", [])):
    if e.get("id") == iid:
        e["fuente"] = "https://github.com/ana/chatcito"
json.dump(lista, open(os.path.join(DATOS, "accesos.json"), "w"))
a = ak.uno(DATOS, iid)
mira(a.get("fuente") == "https://github.com/ana/chatcito", "el icono sabe de dónde vino")
mira("otra terminal" in ar.leer_readme(app), "al leer «su README» también lee lo que estudió")
mira(ar.leer_readme(app, con_estudio=False) == "", "su carpeta, sola, no trae README")
pasos = ar.pasos_terminal(a)
mira(any(ar.es_puente_linea(b) and "server.py" in b for _t, b in pasos),
     f"gracias a lo estudiado sabe que necesita el puente: {[t for t, _ in pasos]}")
mira(ar.es_de_terminal(a), "y lo abre en la terminal")

# sin nada estudiado, todo como antes
otra = os.path.join(T, "apps", "otra"); os.makedirs(otra)
mira(ar.guia_estudiada(otra) == "", "si no estudió nada de ese programa, no inventa")

print(f"test_guia_estudiada: {ok} bien, {mal} mal")
sys.exit(1 if mal else 0)
