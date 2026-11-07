# -*- coding: utf-8 -*-
"""v3.04: Kira estudia FOROS: lee todas las páginas de un hilo (2, 3, «siguiente»…), se salta el ruido del foro
(responder, citar, votar, denunciar, perfiles, editar), lee Reddit en su versión clásica y guarda lo aprendido
avisando de que son opiniones de usuarios."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["HOME"] = T
import internet_kira as ik  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


for u in ("https://www.reddit.com/r/learnpython/comments/abc/hola/", "https://stackoverflow.com/questions/1/x",
          "https://foro.elhacker.net/x", "https://forum.ubuntu.com/viewtopic.php?t=3", "https://discourse.org/t/tema/123",
          "https://www.forocoches.com/foro/showthread.php?t=1"):
    ok(ik.es_foro(u), f"es un foro: {u}")
for u in ("https://docs.python.org/es/3/tutorial/", "https://es.wikipedia.org/wiki/Python",
          "https://academia.es/curso/tema/3"):
    ok(not ik.es_foro(u), f"no es un foro: {u}")
ok(ik.reescribir("https://www.reddit.com/r/python/comments/1/x/?a=1") ==
   "https://old.reddit.com/r/python/comments/1/x/?a=1", "Reddit se lee en su versión clásica (sin JavaScript)")
ok(ik.reescribir("https://docs.python.org/x") == "https://docs.python.org/x", "lo demás, igual")
for u, t in (("https://f.es/hilo?page=2", ""), ("https://f.es/hilo/page-3", ""), ("https://f.es/t?p=2", "2"),
             ("https://f.es/x", "Siguiente"), ("https://f.es/x", "»"), ("https://f.es/x", "Página 4")):
    ok(ik.es_paginacion(u, t), f"paginación: {u} «{t}»")
ok(not ik.es_paginacion("https://f.es/articulo-sobre-python", "Leer más sobre Python"), "un enlace normal no lo es")

HILO1 = """<html><head><title>¿Cómo leer un CSV en Python?</title></head><body><main>
<div class="post"><p>Pregunta: quiero leer un CSV en Python y no sé cómo.</p>
<a href="/hilo/123/reply">Responder</a> <a href="/hilo/123/quote/5">Citar</a> <a href="/report/5">Denunciar</a>
<a href="/members/pepe.9/">pepe</a> <a href="/users/77/juan">juan</a> <a href="/posts/5/edit">Editar</a>
<a href="/vote/up/5">+1</a></div>
<div class="post"><p>Respuesta: usa el módulo csv con csv.reader, y mira <a href="https://docs.python.org/es/3/library/csv.html">la documentación del módulo csv</a>.</p></div>
<div class="paginas"><a href="/hilo/123?page=2">2</a> <a href="/hilo/123?page=3">3</a> <a href="/hilo/123?page=2">Siguiente</a></div>
</main></body></html>"""
BASE = "https://foro.ejemplo.es/hilo/123"
p = ik._html_partes(HILO1)
enl = [e["url"] for e in ik.enlaces_de(p.enlaces, BASE)]
ok(not any(x in u for u in enl for x in ("reply", "quote", "report", "members", "users", "edit", "vote")),
   "se salta el ruido del foro (responder, citar, denunciar, perfiles, editar, votar)")
ok("https://foro.ejemplo.es/hilo/123?page=2" in enl and "https://docs.python.org/es/3/library/csv.html" in enl,
   "y se queda con las páginas del hilo y lo que enlazan las respuestas")
pag = {"url": BASE, "titulo": "¿Cómo leer un CSV en Python?", "enlaces": ik.enlaces_de(p.enlaces, BASE)}
ok(any("page=2" in e["url"] for e in ik.elegir_enlaces(pag, "csv", n=10)),
   "al estudiar por tema, la página 2 del hilo también cuenta")

# núcleo: estudio completo de un hilo de 4 páginas -> las lee TODAS, en orden, y guarda avisando de que es un foro
import kira_god  # noqa: E402


def pagina_hilo(k):
    sig = f'<a href="/hilo/123?page={k + 1}">Siguiente</a>' if k < 4 else ""
    return {"url": f"{BASE}?page={k}", "titulo": f"Hilo página {k}",
            "texto": f"Respuestas de la página {k} sobre leer CSV en Python. " * 3,
            "enlaces": ik.enlaces_de(ik._html_partes(f"<main><p>x</p>{sig}</main>").enlaces, f"{BASE}?page={k}")}


leidas = []


class Net:
    pagina = None

    def es_orden(self, t):
        return ik.interpretar(t) is not None

    def leer(self, url):
        leidas.append(url)
        if url == BASE:
            return dict(pag, texto="Pregunta y respuestas sobre CSV en Python. " * 3)
        if "page=" in url:
            return pagina_hilo(int(url.rsplit("=", 1)[1]))
        return {"url": url, "titulo": "csv", "texto": "Documentación del módulo csv de Python. " * 3}


core = kira_god.KiraGodCore()
core.dir = os.path.join(T, "k")
os.makedirs(core.dir)
core.internet = Net()
core.resumir_pagina = lambda pg, tema="": (pg.get("texto", "")[:300], True)
guardado = []


class Baul:
    def guardar(self, texto, tema="", fuente=""):
        guardado.append((texto, fuente))
        return 1


core.recuerdos = Baul()
r = core.estudiar_pagina(BASE)
ok(r.startswith("[OK]") and "Estudio completo" in r, "estudio completo del hilo: " + r[:80])
paginas = [u for u in leidas if "page=" in u]
ok(paginas == [f"{BASE}?page={k}" for k in (2, 3, 4)], "lee TODAS las páginas del hilo, en orden: " + str(paginas))
ok(any("csv.html" in u for u in leidas), "y lo que enlazan las respuestas (la documentación)")
foro = [t for t, f in guardado if "foro.ejemplo.es" in f]
ok(foro and all(t.startswith("Según un foro") for t in foro), "lo del foro se guarda avisando: son opiniones")
ok(all(not t.startswith("Según un foro") for t, f in guardado if "docs.python.org" in f),
   "la documentación oficial, sin ese aviso")
print("\nTODO BIEN", n)
