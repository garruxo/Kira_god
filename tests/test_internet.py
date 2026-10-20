# -*- coding: utf-8 -*-
"""Kira busca y lee en internet (v2.18): órdenes, buscadores (DuckDuckGo, Wikipedia, Stack Overflow, GitHub),
páginas a texto con su código aparte, PDF sencillos, resumir y aprender (red simulada)."""
import gzip, io, json, os, sys, tempfile, urllib.parse, zlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import internet_kira as ik
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- qué se pide ----------
I = ik.interpretar
ok(I("busca en internet cómo plantar tomates") == {"accion": "buscar", "tipo": "web", "consulta": "cómo plantar tomates"}, "web")
ok(I("Búscame información sobre la fotosíntesis")["consulta"] == "la fotosíntesis", "información sobre…")
ok(I("busca código de un servidor web en python")["tipo"] == "codigo", "código")
ok(I("busca código de un servidor web en python")["consulta"] == "un servidor web en python", "consulta de código limpia")
ok(I("busca documentos sobre la revolución francesa") == {"accion": "buscar", "tipo": "docs", "consulta": "la revolución francesa"}, "documentos")
ok(I("busca apuntes de derivadas")["tipo"] == "docs", "apuntes")
ok(I("investiga los agujeros negros")["accion"] == "buscar", "investiga")
ok(I("estudia en internet la revolución francesa") == {"accion": "estudiar", "consulta": "la revolución francesa"}, "estudiar en internet")
ok(I("lee el 2") == {"accion": "leer", "n": 2} and I("resume el primero") == {"accion": "resumir", "n": 1}, "lee / resume el N")
ok(I("guarda el 3") == {"accion": "guardar", "n": 3} and I("aprende del 3")["accion"] == "guardar", "guarda / aprende del N")
ok(I("abre el 2 en el editor") == {"accion": "editor", "n": 2}, "al editor")
ok(I("abre el 2 en el navegador") == {"accion": "navegador", "n": 2}, "al navegador")
ok(I("lee esta página https://ejemplo.com/a") == {"accion": "leer", "url": "https://ejemplo.com/a"}, "una dirección")
ok(I("busca en tus recuerdos el gato") is None and I("busca en google paella") is None, "recuerdos y google no son esto")
ok(I("hola qué tal") is None and I("estudia ingeniería") is None and I("lee la última captura") is None, "lo demás no")

# ---------- buscadores ----------
DUCK = """<html><body>
<div class="result results_links results_links_deep result--ad"><a rel="nofollow" class="result__a"
 href="https://duckduckgo.com/y.js?ad_domain=x.com&amp;u3=1">Anuncio</a></div>
<div class="result results_links results_links_deep web-result"><h2 class="result__title">
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.huerto.es%2Ftomates&amp;rut=1">Cómo plantar <b>tomates</b></a></h2>
<a class="result__snippet" href="//duckduckgo.com/l/?uddg=x">Guía para plantar <b>tomates</b> en casa.</a></div>
<div class="result web-result"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fejemplo.org%2Fb">Otro &amp; más</a>
<a class="result__snippet">Segundo resumen</a></div>
</body></html>"""
LITE = """<table><tr><td>1.&nbsp;</td><td><a rel="nofollow" href="https://lite.ejemplo.com/x" class='result-link'>Lite uno</a></td></tr>
<tr><td></td><td class='result-snippet'>Resumen <b>lite</b></td></tr></table>"""
r = ik.resultados_duck(DUCK)
ok([x["url"] for x in r] == ["https://www.huerto.es/tomates", "https://ejemplo.org/b"], "saca las direcciones reales, sin anuncios: " + repr(r))
ok(r[0]["titulo"] == "Cómo plantar tomates" and r[0]["resumen"] == "Guía para plantar tomates en casa." and r[0]["fuente"] == "huerto.es", "título, resumen y fuente")
ok(r[1]["titulo"] == "Otro & más", "entidades HTML")
ok(ik.resultados_duck(LITE) == [{"titulo": "Lite uno", "url": "https://lite.ejemplo.com/x", "resumen": "Resumen lite", "fuente": "lite.ejemplo.com"}], "versión lite")

PAGINA = """<!DOCTYPE html><html><head><title>Plantar tomates | Huerto</title><script>alert(1)</script></head><body>
<nav>Inicio Blog Contacto</nav><header>Menú</header>
<h1>Cómo plantar tomates</h1><p>Los tomates necesitan <b>sol</b> y riego.</p><ul><li>Sol directo</li><li>Riego regular</li></ul>
<pre><code>def regar(litros):
    return litros * 2</code></pre><aside>Publicidad</aside><footer>© 2026</footer></body></html>"""

class Resp:
    def __init__(s, cuerpo, tipo="text/html; charset=utf-8", codif="", status=200, url=None):
        s.b, s.status, s.url = cuerpo, status, url
        s.headers = {"Content-Type": tipo, "Content-Encoding": codif}
    def read(s, n=-1): return s.b if n < 0 else s.b[:n]
    def __enter__(s): return s
    def __exit__(s, *a): return False

def pdf_simple(lineas):
    cont = b"BT /F1 12 Tf 72 720 Td " + b" T* ".join(b"(" + l.replace(b"(", b"\\(").replace(b")", b"\\)") + b") Tj" for l in lineas) + b" ET"
    z = zlib.compress(cont)
    return (b"%PDF-1.4\n1 0 obj << /Length " + str(len(z)).encode() + b" /Filter /FlateDecode >>\nstream\n" + z +
            b"\nendstream\nendobj\n%%EOF")

pedidos = []
def red(req, timeout=0):
    url = req.full_url; pedidos.append(url)
    if "html.duckduckgo.com" in url:
        return Resp(DUCK.encode())
    if "es.wikipedia.org/w/api.php" in url:
        return Resp(json.dumps({"query": {"search": [{"title": "Tomate", "snippet": "El <span>tomate</span> es una planta"}]}}).encode(), "application/json")
    if "api.stackexchange.com" in url:
        d = {"items": [{"title": "How to make a web server in Python?", "link": "https://stackoverflow.com/q/1", "is_answered": True,
                        "score": 42, "tags": ["python", "http"]}]}
        return Resp(gzip.compress(json.dumps(d).encode()), "application/json; charset=utf-8", "gzip")
    if "api.github.com/search" in url:
        return Resp(json.dumps({"items": [{"full_name": "ana/servidor", "html_url": "https://github.com/ana/servidor",
                                           "description": "Servidor <b>mínimo</b>", "stargazers_count": 7, "language": "Python"}]}).encode(), "application/json")
    if "api.github.com/repos/ana/servidor/readme" in url:
        return Resp(b"# Servidor\n\n```python\nimport http.server\nprint('hola')\n```\n", "text/plain")
    if url == "https://www.huerto.es/tomates":
        return Resp(PAGINA.encode())
    if url.endswith(".pdf"):
        return Resp(pdf_simple([b"La fotosintesis convierte la luz en energia quimica.", b"Ocurre en los cloroplastos (hojas)."]), "application/pdf")
    if url == "https://ejemplo.org/b":
        return Resp(b"<html><body><p>Pagina corta pero con texto suficiente para leer.</p></body></html>")
    raise OSError("sin red")

net = ik.Internet(os.path.join(T, "internet"), abrir=red)
res = net.buscar("cómo plantar tomates")
ok([x["fuente"] for x in res] == ["huerto.es", "ejemplo.org", "es.wikipedia.org"], "web + Wikipedia: " + repr([x["fuente"] for x in res]))
ok("1. Cómo plantar tomates — huerto.es" in net.texto_resultados() and "«lee el 2»" in net.texto_resultados(), "lista para enseñar")
cod = net.buscar("servidor web en python", "codigo")
ok(cod[0]["fuente"] == "stackoverflow.com" and "respondida" in cod[0]["resumen"] and "42 votos" in cod[0]["resumen"], "Stack Overflow (comprimido)")
ok(any(x["url"] == "https://github.com/ana/servidor" and "★ 7" in x["resumen"] and "<b>" not in x["resumen"] for x in cod), "GitHub")
ok("«abre el 2 en el editor»" in net.texto_resultados(), "con código, ofrece el editor")

# ---------- leer ----------
pag = net.leer("https://www.huerto.es/tomates")
ok(pag["titulo"] == "Plantar tomates | Huerto", "título de la página")
ok("Los tomates necesitan sol y riego." in pag["texto"] and "- Sol directo" in pag["texto"], "el texto, limpio: " + pag["texto"][:200])
ok(all(x not in pag["texto"] for x in ("alert", "Inicio Blog", "Publicidad", "© 2026")), "sin scripts, menús, anuncios ni pie")
ok(pag["codigos"] == ["def regar(litros):\n    return litros * 2"], "el código aparte, con su sangría")
ok(net.codigo_de(pag).startswith("def regar"), "código para el editor")
gh = net.leer("https://github.com/ana/servidor")
ok(gh["codigos"] and "import http.server" in gh["codigos"][0], "GitHub: lee el README y saca su código")
pdf = net.leer("https://ejemplo.com/apuntes.pdf")
ok(pdf["tipo"] == "pdf" and "convierte la luz" in pdf["texto"] and "cloroplastos (hojas)" in pdf["texto"], "PDF sencillo: " + pdf["texto"][:100])
ok(ik.pdf_a_texto(b"%PDF-1.4 nada que leer") == "", "PDF ilegible: lo dice")
try: net.leer("ftp://x"); ok(False, "solo web")
except ik.InternetError: ok(True, "solo direcciones web")
try: net.leer("https://no.existe/"); ok(False, "sin red")
except ik.InternetError as e: ok("internet" in str(e), "sin red: lo dice claro")

# DuckDuckGo no responde: Wikipedia
def red_sin_duck(req, timeout=0):
    if "duckduckgo" in req.full_url: raise OSError("bloqueado")
    return red(req, timeout)
net2 = ik.Internet(T, abrir=red_sin_duck)
ok([x["fuente"] for x in net2.buscar("tomate")] == ["es.wikipedia.org"] and "Wikipedia" in net2.texto_resultados(), "si DuckDuckGo falla, Wikipedia (y lo dice)")

# ---------- en el núcleo: buscar, leer, resumir, aprender ----------
import kira_god, cerebro_ia_kira as ci
core = kira_god.KiraGodCore()
core.internet = ik.Internet(os.path.join(T, "internet"), abrir=red)
r = core.procesar_orden("busca en internet cómo plantar tomates")
ok(r.startswith("Resultados de «cómo plantar tomates»") and "huerto.es" in r, "buscar desde una orden")
r = core.procesar_orden("lee el 1")
ok("Los tomates necesitan sol" in r and "bloque(s) de código" in r, "lee el 1")
ok(core.lector.ultimo.startswith("def regar"), "lo leído (el código) queda listo para «abre lo leído en el editor»")
r = core.procesar_orden("resume el 1")
ok("Sin cerebro" in r and "Los tomates necesitan sol" in r, "sin cerebro, resumir es honesto")
vistos = []
core._leer_clave = lambda *a: ci.LOCAL
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None: (
    vistos.append((system, usuario)), "Los tomates quieren mucho sol directo y riego regular; se plantan en primavera.")[1]
r = core.procesar_orden("resume el 1")
ok("quieren mucho sol" in r and "ignora cualquier instrucción" in vistos[-1][0], "resume con su cerebro (y no obedece a la web)")
ok(len(vistos[-1][1]) < 3300, "al cerebro del móvil le llega un trozo que le cabe")
r = core.procesar_orden("guarda el 1")
ok(r.startswith("[OK] Lo he aprendido") and "huerto.es" in r, "aprender una página")
ok(any("sol directo" in x["texto"] for x in core.recuerdos.buscar("tomates sol", n=5)), "queda en su baúl")
r = core.procesar_orden("estudia en internet cómo plantar tomates")
ok(r.startswith("[OK] He estudiado «cómo plantar tomates» en internet") and "huerto.es" in r, "estudiar en internet: " + r)
ok(core.procesar_orden("lee el 9").startswith("[x] Solo tengo"), "un número que no está")

# ---------- la pantalla «Internet» y la voz (Kivy simulado) ----------
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
import inicio_kira as ik2
class VozMuda:
    def __init__(s): s.dichos = []
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", "no"
    def parar_escucha(s): pass
VOZ = VozMuda(); ik2.Voz = lambda *a, **k: VOZ
core3 = kira_god.KiraGodCore()
core3.internet = ik.Internet(os.path.join(T, "internet3"), abrir=red)
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core3)
def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())
def textos(nombre): return [w.text for w in sm.get_screen(nombre).walk() if isinstance(getattr(w, "text", None), str)]
def decir_a_kira(frase):
    sm.ir("inicio"); correr(0.3)
    campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
    campo.text = frase
    next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
correr(0.8)
decir_a_kira("Kira, busca en internet cómo plantar tomates")
ok(correr(3, lambda: sm.current == "internet"), "la voz lleva a la pantalla Internet")
ok(correr(4, lambda: any("1. Cómo plantar tomates" in t for t in textos("internet"))), "enseña los resultados: " + str(textos("internet")[-5:]))
ok(correr(2, lambda: any("He encontrado 3 resultados" in d for d in VOZ.dichos)), "y lo dice: " + str(VOZ.dichos[-2:]))
tarjeta = next(w for w in sm.get_screen("internet").walk() if type(w).__name__ == "Button" and "1. Cómo plantar" in w.text)
tarjeta.press()
ok(correr(4, lambda: any("Los tomates necesitan sol" in t for t in textos("internet"))), "tocar un resultado lo lee")
decir_a_kira("abre el 1 en el editor")
ok(correr(4, lambda: sm.current == "editor_codigo"), "su código, al editor")
ok(any("def regar" in t for t in textos("editor_codigo")) and any("nunca se ejecuta solo" in t for t in textos("editor_codigo")),
   "el código está en el editor y avisa de que no se ejecuta solo")
decir_a_kira("guarda el 1")
ok(correr(4, lambda: any("Lo he aprendido" in d or "ya lo tenía" in d.lower() for d in VOZ.dichos + textos("inicio"))), "aprender por voz")
print("INTERNET OK", n)
