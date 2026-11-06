# -*- coding: utf-8 -*-
"""v2.93: los SENTIDOS de KiraOS en el portátil (cámara + pantalla, leídas con OCR). El oído ya iba (v2.90).
Aquí NO se abre la cámara de verdad: `_which` y `correr` son de mentira; se comprueba la lógica, que la imagen se
BORRA tras leerla, y los mensajes honestos cuando falta una herramienta."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import sentidos_portatil as sp  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


# ---------- reconocer la orden ----------
for frase, esp in (
        ("Kira, mira con tu cámara", ("camara", False)),
        ("hazme una foto", ("camara", False)),
        ("saca una foto", ("camara", False)),
        ("¿qué tengo delante?", ("camara", True)),
        ("qué ves", ("camara", True)),
        ("describe lo que ves", ("camara", True)),
        ("usa la webcam", ("camara", False)),
        ("lee la pantalla", ("pantalla", True)),
        ("¿qué pone en la pantalla?", ("pantalla", True)),
        ("mira la pantalla", ("pantalla", True)),
        ("lee la última captura", ("pantalla", True)),
        ("qué hay en la captura", ("pantalla", True)),
):
    ok(sp.es_orden(frase) == esp, f"«{frase}» → {esp}")

for frase in ("hola Kira", "mira a ver si puedes", "busca recetas de tortilla", "piensa", "qué tiempo hace",
              "investiga la fotosíntesis", "pon una foto de perfil"):
    ok(sp.es_orden(frase) is None, f"«{frase}» no es un sentido (va a Kira como siempre)")

# ---------- órdenes de sistema (puras) ----------
ok(sp.orden_foto("fswebcam", "/tmp/f.jpg", "/dev/video0")[0] == "fswebcam" and "/tmp/f.jpg" in sp.orden_foto("fswebcam", "/tmp/f.jpg"),
   "la orden de la webcam con fswebcam")
ok(sp.orden_foto("ffmpeg", "/tmp/f.jpg")[0] == "ffmpeg" and "v4l2" in sp.orden_foto("ffmpeg", "/tmp/f.jpg"),
   "la orden de la webcam con ffmpeg")
ok(sp.orden_pantalla("scrot", "/tmp/p.png") == ["scrot", "-o", "/tmp/p.png"], "captura con scrot")
ok(sp.orden_pantalla("import", "/tmp/p.png")[:3] == ["import", "-window", "root"], "captura con import (ImageMagick)")
ok(sp.orden_pantalla("grim", "/tmp/p.png") == ["grim", "/tmp/p.png"], "captura con grim (Wayland)")
ok(sp.orden_ocr("/tmp/f.jpg") == ["tesseract", "/tmp/f.jpg", "stdout", "-l", "spa+eng"], "OCR con tesseract a stdout")


# ---------- Sentidos de mentira ----------
class Falso:
    """Un portátil de mentira: dice qué herramientas hay y, al «sacar la foto», crea el archivo; el OCR devuelve texto."""
    def __init__(self, hay=("fswebcam", "scrot", "tesseract"), texto="HOLA MUNDO\nesto es una prueba", crea=True, cod=0):
        self.hay, self.texto, self.crea, self.cod = set(hay), texto, crea, cod
        self.corridas = []

    def which(self, nombre):
        return ("/usr/bin/" + nombre) if nombre in self.hay else None

    def correr(self, args, timeout=30):
        self.corridas.append(args)
        if args[0] == "tesseract":
            return (self.cod, self.texto)
        # foto/captura: crea el archivo destino (último argumento) si toca
        destino = args[-1]
        if self.crea:
            with open(destino, "wb") as f:
                f.write(b"\xff\xd8imagen")
        return (self.cod, "")


TMP = tempfile.mkdtemp(prefix="kira_sent_")


def sent(f):
    return sp.Sentidos(which=f.which, correr=f.correr, carpeta_tmp=TMP)


f = Falso()
s = sent(f)
ok(s.estado() == {"camara": "fswebcam", "pantalla": "scrot", "ocr": True}, "estado: qué sentidos hay")
r = s.foto()
ok("Con la cámara leo" in r and "HOLA MUNDO" in r, "la foto se saca y se LEE su texto")
ok(not os.path.isfile(os.path.join(TMP, "kira_foto.jpg")), "la foto se BORRA tras leerla (privacidad)")
ok(["tesseract", os.path.join(TMP, "kira_foto.jpg"), "stdout", "-l", "spa+eng"] in f.corridas, "usó el OCR sobre la foto")

r = s.foto(describir=True)
ok("mis ojos" in r and "móvil" in r, "si pides que DESCRIBA, avisa honesto de que en el portátil solo lee letras")

r = s.pantalla()
ok("En la pantalla leo" in r and "prueba" in r, "captura la pantalla y lee su texto")
ok(not os.path.isfile(os.path.join(TMP, "kira_pantalla.png")), "la captura también se borra tras leerla")

# sin cámara
f2 = Falso(hay=("scrot", "tesseract"))
r = sp.hacer("camara", False, sent(f2))
ok(r.startswith("[x]") and "fswebcam" in r, "sin cámara: lo dice claro y cómo instalarla")

# sin lector (tesseract): la foto se hace pero no se lee, y se borra igual
f3 = Falso(hay=("fswebcam", "scrot"))
s3 = sent(f3)
r = s3.foto()
ok("He hecho la foto" in r and "tesseract" in r, "sin lector: hizo la foto pero avisa de que falta el OCR")
ok(not os.path.isfile(os.path.join(TMP, "kira_foto.jpg")), "y aun sin leerla, la borra")

# la foto no sale (herramienta falla)
f4 = Falso(crea=False, cod=1)
r = sp.hacer("camara", False, sent(f4))
ok(r.startswith("[x]") and "foto" in r.lower(), "si la webcam falla, lo dice sin reventar")

# OCR que no encuentra letras
f5 = Falso(texto="")
r = sent(f5).pantalla()
ok("No he leído ninguna letra" in r, "pantalla sin texto: lo dice, no inventa")

ok("cámara" in sp.texto_estado(sent(Falso())) and "oído" in sp.texto_estado(sent(Falso())),
   "texto_estado resume los sentidos del portátil")

# ---------- cableado en el núcleo del portátil ----------
src = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("import sentidos_portatil as sp" in src and "sp.es_orden(o)" in src and "sp.hacer(tipo, describir)" in src,
   "el núcleo del portátil atiende los sentidos (cámara/pantalla) en «ejecutar»")
ipos, wpos = src.index("sp.es_orden(o)"), src.index("mq.orden_maquina(o)")
ok(ipos < wpos, "los sentidos se miran ANTES que la máquina virtual")

inst = open(os.path.join(RAIZ, "kira_portatil", "instalar_portatil.sh"), encoding="utf-8").read()
ok("fswebcam" in inst and "scrot" in inst and "tesseract-ocr-spa" in inst,
   "el instalador pone cámara, captura y lector en el portátil")

import shutil  # noqa: E402
shutil.rmtree(TMP, ignore_errors=True)
print("\nTODO BIEN", n)
