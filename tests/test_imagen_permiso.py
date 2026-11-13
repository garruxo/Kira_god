# -*- coding: utf-8 -*-
"""v3.33: (1) VER y LEER la imagen de un artículo web (OCR) y que esa info quede para instalar/implementar/mejorar;
(2) pedir la contraseña de admin UNA sola vez (bash permiso_apps) y luego instalar del sistema sin pedirla más."""
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATA_DIR"] = T
os.environ["KIRA_DATOS_NUCLEO"] = os.path.join(T, "kira_datos")
os.makedirs(os.environ["KIRA_DATOS_NUCLEO"], exist_ok=True)
os.environ.pop("KIRA_API_KEY", None)
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))

n = fallos = 0


def ok(c, m):
    global n, fallos
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


# ============ PARTE 2: imágenes de una página ============
import internet_kira as ik

HTML = ('<article><img src="/img/logo.png" alt="logo"><p>Instala así, como se ve en la imagen:</p>'
        '<img src="https://s/capturas/terminal-pip.png" alt="captura del terminal con pip install">'
        '<img src="data:image/png;base64,AAAA"><img src="/iconos/flecha.svg"></article>'
        '<footer><img src="/img/foto-footer.jpg"></footer>')
p = ik._html_partes(HTML)
imgs = ik.imagenes_de(p.imagenes, "https://sitio.org/guia")
urls = [i["url"] for i in imgs]
ok(any(u.endswith("terminal-pip.png") for u in urls), "saca la imagen de contenido del artículo, absoluta")
ok(not any("logo" in u or "flecha" in u or u.startswith("data:") for u in urls), "salta logos, iconos .svg y data:")
ok(not any("footer" in u for u in urls), "salta las imágenes del pie (footer)")

pag = {"url": "https://x/guia", "titulo": "instalar pip", "imagenes": [
    {"url": "https://x/otra.png", "alt": "gatito"},
    {"url": "https://x/terminal-pip.png", "alt": "captura del terminal con pip install"}]}
ok(ik.elegir_imagen(pag, "pip terminal").endswith("terminal-pip.png"), "elegir_imagen: la más relacionada con el tema")

ok(ik.MENCIONA_IMAGEN.search("como se ve en la imagen de arriba"), "detecta que el artículo remite a una imagen")
ok(not ik.MENCIONA_IMAGEN.search("esto es un texto normal sin nada"), "no se dispara con texto normal")

for s in ["lee la imagen de esta página", "qué pone en la imagen de esta web", "analiza la imagen del artículo",
          "lee la imagen", "lee la foto de aquí", "Kira, lee la imagen de esta página: https://x/art"]:
    ok(ik.es_orden_leer_imagen(s), "reconoce: " + s)
for s in ["lee la pantalla", "lee la última captura", "lee este pdf", "busca imágenes de gatos", "abre la imagen"]:
    ok(not ik.es_orden_leer_imagen(s), "NO se dispara: " + s)
ok(ik.es_orden_leer_imagen("lee la imagen de esta página: https://x/art") == "https://x/art", "saca la URL si viene")

# traer_imagen: comprueba que es una imagen por su tipo/magia
import internet_kira
net = internet_kira.Internet(os.path.join(T, "net"))
net._pedir = lambda url, maximo=0, **k: (b"\x89PNG\r\n\x1a\n" + b"x" * 50, "image/png", url)
ok(net.traer_imagen("https://x/a.png").startswith(b"\x89PNG"), "traer_imagen devuelve los bytes de una imagen")
net._pedir = lambda url, maximo=0, **k: (b"<html>no soy imagen</html>", "text/html", url)
try:
    net.traer_imagen("https://x/a")
    ok(False, "traer_imagen rechaza lo que no es imagen")
except internet_kira.InternetError:
    ok(True, "traer_imagen rechaza lo que no es imagen")

# ============ el núcleo LEE la imagen y guarda su texto ============
import kira_god

core = kira_god.KiraGodCore()


class FakeNet:
    def __init__(self):
        self.pagina = None

    def leer(self, url):
        return self.pagina

    def traer_imagen(self, url, maximo=0):
        return b"\x89PNG\r\n\x1a\n" + b"x" * 20


class FakeLector:
    recibio = []

    def leer(self, ruta):
        FakeLector.recibio.append(os.path.isfile(ruta))     # recibió un archivo de verdad
        return "pip install numpy   (texto leído de la captura)"


core.internet = FakeNet()
core.lector = FakeLector()
core._lector_listo = lambda: True

pag_img = {"url": "https://x/art", "titulo": "guía", "imagenes": [{"url": "https://x/captura.png", "alt": "captura"}]}
t = core.texto_de_imagen(pag_img)
ok("numpy" in t and FakeLector.recibio and FakeLector.recibio[0], "texto_de_imagen: OCR de la imagen (con un archivo real)")
ok(not os.path.exists(os.path.join(tempfile.gettempdir(), "kira_img_%d.png" % (abs(hash("https://x/captura.png")) % 10 ** 9))),
   "la imagen se borra tras leerla (privacidad)")

core.internet.pagina = pag_img
r = core.leer_imagen_pagina()
ok("numpy" in r, "«lee la imagen de esta página» muestra el texto de la imagen")

# el texto de la imagen entra en el resumen (para que QUEDE para aprender/mejorar)
core._clave_para = lambda tarea: ""                          # sin cerebro → resumen = principio del texto
pag2 = {"url": "https://x/b", "titulo": "g", "texto": "Instálalo, como se ve en la imagen.",
        "imagenes": [{"url": "https://x/c.png", "alt": ""}]}
res, _con = core.resumir_pagina(pag2)
ok("numpy" in res, "resumir_pagina: si el artículo remite a una imagen, su texto entra en lo que aprende")

# cableado
src_nuc = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("es_orden_leer_imagen" in src_nuc and "leer_imagen_pagina" in src_nuc, "el núcleo (KiraOS) enruta «lee la imagen»")
src_html = open(os.path.join(RAIZ, "kira_portatil", "kiraos_web", "escritorio.html"), encoding="utf-8").read()
ok("busImagen" in src_html and "lee la imagen de esta página" in src_html, "el Buscador tiene el botón «Leer la imagen»")

# ============ PARTE 1: permiso de admin una sola vez ============
import apps_externas_kira as aex

BASE = os.path.join(T, "apps")


def correr_con_permiso(args, cwd=None, timeout=0):
    return 0, "ok"                                           # sudo -n true → 0 (hay permiso); apt/dpkg → 0


def correr_sin_permiso(args, cwd=None, timeout=0):
    if args[:3] == ["sudo", "-n", "true"]:
        return 1, ""                                         # no hay permiso
    return 0, "ok"


ok(aex.admin_sin_clave(correr_con_permiso) is True, "admin_sin_clave: con permiso → True")
ok(aex.admin_sin_clave(correr_sin_permiso) is False, "admin_sin_clave: sin permiso → False")
ok(aex.admin_sin_clave(lambda *a, **k: (_ for _ in ()).throw(OSError())) is False, "sin sudo → False (no revienta)")

r = aex.instalar("vlc", base=BASE, correr=correr_con_permiso)
ok(r["ok"] and r["lanzar"] == ["vlc"] and "con el permiso" in r["mensaje"],
   "con el permiso dado, instala un programa del sistema (apt) sin pedir la contraseña")
r = aex.instalar("vlc", base=BASE, correr=correr_sin_permiso)
ok(not r["ok"] and r.get("admin") and "permiso_apps" in r["mensaje"],
   "sin permiso: lo explica y ofrece darlo UNA vez (bash permiso_apps)")


def bajar_deb(u, dst):
    open(dst, "wb").write(b"x")
    return 1


r = aex.instalar("https://x/foo_1_amd64.deb", base=BASE, correr=correr_con_permiso, bajar=bajar_deb)
ok(r["ok"] and "del sistema" in r["mensaje"], ".deb con permiso: lo instala en el sistema (dpkg -i, sin contraseña)")


def correr_sin_dpkg(args, cwd=None, timeout=0):
    if args[:3] == ["sudo", "-n", "true"]:
        return 1, ""
    raise FileNotFoundError("no dpkg-deb")


r = aex.instalar("https://x/bar_1_amd64.deb", base=BASE, correr=correr_sin_dpkg, bajar=bajar_deb)
ok(not r["ok"] and "permiso_apps" in r["mensaje"], ".deb sin permiso ni dpkg-deb: ofrece el permiso una vez")

# el guion de permiso, de verdad, sobre una raíz falsa
raiz_sis = os.path.join(T, "sis")
env = dict(os.environ, KIRA_RAIZ_SIS=raiz_sis, KIRA_USUARIO="papi")
subprocess.run(["bash", os.path.join(RAIZ, "kira_portatil", "permiso_apps.sh")], env=env, capture_output=True, timeout=30)
sudoers = os.path.join(raiz_sis, "etc", "sudoers.d", "50-kira-apps")
ok(os.path.isfile(sudoers) and "NOPASSWD" in open(sudoers).read() and "apt-get" in open(sudoers).read(),
   "permiso_apps da el permiso (NOPASSWD para apt-get/apt/dpkg, limitado)")
subprocess.run(["bash", os.path.join(RAIZ, "kira_portatil", "permiso_apps.sh"), "--quitar"], env=env, capture_output=True, timeout=30)
ok(not os.path.isfile(sudoers), "permiso_apps --quitar lo quita")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
