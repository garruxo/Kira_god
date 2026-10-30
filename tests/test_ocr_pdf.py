# -*- coding: utf-8 -*-
"""OCR de PDF escaneados (pdf_kira.texto_ocr + Biblioteca.ocr): un PDF que es una IMAGEN (sin capa de texto) se lee
sacando la imagen de cada página y pasándola por un lector (en el móvil, el Tesseract de Kira; aquí, uno de mentira
que comprueba que lo que recibe es una imagen de verdad). pypdf y PIL están en el contenedor."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import pdf_kira as pk

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


def pdf_escaneado(ruta, paginas=3):
    """Un PDF que es solo imágenes (como un escaneo): sin capa de texto."""
    from PIL import Image, ImageDraw
    imgs = []
    for i in range(paginas):
        im = Image.new("RGB", (480, 640), (245, 245, 245))
        d = ImageDraw.Draw(im)
        d.rectangle([20, 20, 460, 620], outline=(0, 0, 0), width=3)
        d.text((40, 300), f"PAGINA {i + 1}", fill=(0, 0, 0))
        imgs.append(im)
    imgs[0].save(ruta, "PDF", save_all=True, append_images=imgs[1:])


tmp = tempfile.mkdtemp()
ruta = os.path.join(tmp, "escaneado.pdf")
pdf_escaneado(ruta, 3)

# sin OCR, pypdf no saca texto (es una imagen): con_texto sería falso
textos_txt, info = pk.paginas_de(ruta)
ok(sum(len(t) for t in textos_txt) <= 40, "un PDF escaneado no tiene capa de texto (pypdf no saca casi nada)")

# el lector de mentira: comprueba que lo que le pasan es una IMAGEN válida y devuelve texto
leidas = []


def leer_imagen(p):
    from PIL import Image
    Image.open(p).verify()                 # peta si no es una imagen de verdad
    leidas.append(p)
    return "TEXTO OCR DE LA PAGINA"


pasos = []
textos = pk.texto_ocr(ruta, leer_imagen, al_progreso=lambda f, t: pasos.append(t), max_paginas=10)
ok(len(textos) == 3, "hace OCR de las 3 páginas")
ok(all("TEXTO OCR" in t for t in textos), "cada página sale con el texto del OCR")
ok(len(leidas) >= 3, "extrae una imagen por página y la pasa al lector")
ok(pasos and "OCR" in pasos[0], "avisa del progreso del OCR")

# tope de páginas
t2 = pk.texto_ocr(ruta, leer_imagen, max_paginas=1)
ok(len(t2) == 1, "respeta el tope de páginas (OCR es lento)")

# cancelar a mitad
t3 = pk.texto_ocr(ruta, leer_imagen, cancelado=lambda: True)
ok(t3 == [], "si cancelas, para en seco")

# --- Biblioteca.ocr: guarda lo que saca (no repite) ---
bib = pk.Biblioteca(os.path.join(tmp, "biblio"))
e = bib.anadir_archivo(ruta, nombre="escaneado")
ok(not e.get("con_texto", True), "la ficha marca que el PDF no tiene texto (escaneado)")
textos_bib = bib.ocr(e, leer_imagen)
ok(textos_bib and e.get("con_texto") and e.get("ocr"), "ocr() saca texto y marca la ficha como leída por OCR")
ok("TEXTO OCR" in bib.pagina(e, 1), "tras el OCR, leer la página 1 ya da texto")
# y queda guardado: textos() lo devuelve sin volver a hacer OCR
ok("TEXTO OCR" in "".join(bib.textos(e)), "el texto del OCR queda guardado para la próxima")

# --- texto_util: distingue texto bueno de basura de escaneo (capa de texto rota) ---
ok(pk.texto_util(["El hacking ético busca vulnerabilidades con permiso para corregirlas antes que un atacante."]),
   "texto de verdad: útil")
ok(not pk.texto_util(["A" * 400]), "una página llena de «AAAA» no es texto útil (es escaneo roto)")
ok(not pk.texto_util([]) and not pk.texto_util(["xx"]), "vacío o casi vacío: no es útil")
# un PDF cuyo «texto» es basura se marca como escaneado (con_texto False) -> hará OCR
import io
import tempfile as _tf
# reusar el escaneado de antes: su ficha ya marcó con_texto False
ok(not e.get("con_texto", True) or e.get("ocr"), "el PDF de imágenes se marca para OCR (no como texto bueno)")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
