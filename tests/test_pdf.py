# -*- coding: utf-8 -*-
"""v2.27: la biblioteca de PDF. Descargar desde un enlace (servidor web de prueba: PDF directo, página que lleva a un
PDF, demasiado grande, no es un PDF), leer por páginas, buscar, preguntar y resumir con el cerebro (FALSO),
estudiar al baúl, renombrar, borrar, y por voz/texto en la interfaz (Kivy simulado)."""
import http.server, os, sys, tempfile, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import pdf_kira as pk
from pdf_de_prueba import hacer_pdf
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

BIO = hacer_pdf([["Tema 1: la fotosíntesis", "Las plantas fabrican su alimento con la luz del sol.",
                  "La clorofila es el pigmento verde que capta la luz."],
                 ["Tema 2: la respiración", "Las células usan oxígeno para obtener energía.",
                  "Se libera dióxido de carbono."],
                 ["Tema 3: el agua", "El agua sube por el xilema desde la raíz hasta las hojas."]],
                titulo="Apuntes de Biología")
HIST = hacer_pdf(["La Revolución Francesa empezó en 1789."], titulo="Historia")

# ---------- un servidor web de prueba ----------
class Web(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        rutas = {"/apuntes.pdf": (BIO, "application/pdf"), "/historia": (HIST, "application/pdf"),
                 "/articulo": (b"<html><a href='/descargas/paper.pdf'>PDF</a></html>", "text/html"),
                 "/descargas/paper.pdf": (HIST, "application/pdf"),
                 "/pagina": (b"<html><body>solo texto</body></html>", "text/html")}
        if self.path == "/enorme.pdf":
            self.send_response(200); self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(pk.MAX_BYTES + 10)); self.end_headers(); return
        datos, tipo = rutas.get(self.path, (None, None))
        if datos is None:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", tipo); self.send_header("Content-Length", str(len(datos)))
        if self.path == "/historia":
            self.send_header("Content-Disposition", 'attachment; filename="Historia de Francia.pdf"')
        self.end_headers(); self.wfile.write(datos)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Web)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}"

# ---------- enlaces ----------
ok(pk.url_de("Kira, descarga esto: https://a.org/x.pdf.") == "https://a.org/x.pdf", "saca el enlace del texto")
ok(pk.enlace_directo("https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view?usp=sharing")
   == "https://drive.google.com/uc?export=download&id=1AbCdEfGhIjKlMnOp", "enlace de Google Drive -> descarga")
ok("dl=1" in pk.enlace_directo("https://www.dropbox.com/s/abc/apuntes.pdf?dl=0"), "Dropbox -> descarga")
ok(pk.enlace_directo("https://github.com/u/r/blob/main/doc.pdf") == "https://raw.githubusercontent.com/u/r/main/doc.pdf", "GitHub")
ok(pk.enlace_directo("https://arxiv.org/abs/1706.03762") == "https://arxiv.org/pdf/1706.03762", "arXiv: de la ficha al PDF")
ok(pk.nombre_de("https://a.org/mis%20apuntes.pdf") == "mis apuntes", "nombre a partir del enlace")

# ---------- descargar y leer ----------
B = pk.Biblioteca(os.path.join(T, "bib"))
ok("No tengo ningún PDF" in B.texto_lista(), "vacía al principio")
pasos = []
e = B.descargar(URL + "/apuntes.pdf", progreso=lambda f, b, t: pasos.append(b))
ok(e["n"] == 1 and e["paginas"] == 3 and e["nombre"] == "apuntes" and e["titulo"] == "Apuntes de Biología" and pasos,
   f"descarga un PDF directo: {e}")
ok("clorofila" in B.pagina(e, 1) and "xilema" in B.pagina(e, 3) and "fotosíntesis" in B.pagina(e, 1),
   "lee cada página (con tildes)")
ok(B.pagina(e, 99) == B.pagina(e, 3), "una página de más: la última")
ok(B.descargar(URL + "/apuntes.pdf")["repetido"], "el mismo PDF no se guarda dos veces")
e2 = B.descargar(URL + "/historia")
ok(e2["nombre"] == "Historia de Francia", "usa el nombre que da el servidor")
e3 = B.descargar(URL + "/articulo")
ok(e3.get("repetido") and e3["n"] == e2["n"], "una PÁGINA que lleva a un PDF: lo encuentra (aquí, el mismo de historia)")
for ruta, frase in (("/pagina", "no hay un PDF"), ("/enorme.pdf", "demasiado grande"), ("/no-existe.pdf", "se cortó")):
    try:
        B.descargar(URL + ruta); ok(False, ruta)
    except pk.PdfError as ex:
        ok(frase in str(ex), f"{ruta}: lo explica ({ex})")
try:
    B.descargar("hola"); ok(False, "no es enlace")
except pk.PdfError as ex:
    ok("enlace" in str(ex), "si no es un enlace, lo dice")
ok(len(B.lista) == 2 and not [f for f in os.listdir(B.carpeta) if "parte" in f], "sin restos de descargas a medias")
B2 = pk.Biblioteca(os.path.join(T, "bib"))
ok([x["n"] for x in B2.lista] == [1, 2], "la biblioteca se recuerda al volver a abrir Kira")

# ---------- buscar, preguntar, gestionar ----------
ok(B.buscar_doc("2")["n"] == 2 and B.buscar_doc("")["n"] == 2 and B.buscar_doc("biología")["n"] == 1
   and B.buscar_doc("química") is None, "encuentra el PDF por número, por nombre o el último")
res = B.buscar_en(e, "clorofila")
ok(res and res[0][0] == 1 and "clorofila" in res[0][1].lower(), "«busca clorofila»: en qué página sale")
ctx = B.contexto_para(e, "¿por dónde sube el agua?")
ok(ctx.startswith("[página 3]") and "xilema" in ctx, "para una pregunta, coge las páginas que vienen al caso")
B.renombrar(e, "Biología 1º")
ok(pk.Biblioteca(os.path.join(T, "bib")).buscar_doc("1")["nombre"] == "Biología 1º", "renombrar")
ok(len(pk.trozos("frase. " * 800, 1000)) >= 5 and all(len(t) <= 1001 for t in pk.trozos("frase. " * 800, 1000)), "trozos")

# ---------- el núcleo ----------
import kira_god, cerebro_ia_kira as ci
core = kira_god.KiraGodCore()
r = core.procesar_orden(f"Kira, descarga este PDF: {URL}/apuntes.pdf")
ok(r.startswith("[OK] He guardado el PDF 1") and "3 páginas" in r, "«descarga este PDF: enlace» " + r)
ok("1. apuntes" in core.procesar_orden("mis pdf"), "«mis pdf»")
r = core.procesar_orden("lee la página 2 del pdf 1")
ok(r.startswith("[OK] ABRIR_PDF 1 2") and "oxígeno" in r and core.lector.ultimo.startswith("Tema 2"), "«lee la página 2 del pdf 1»")
ok("página 1" in core.procesar_orden("busca clorofila en el pdf 1"), "«busca … en el pdf»")
ok("Sin cerebro" in core.procesar_orden("qué dice el pdf 1 sobre el agua") and "xilema" in core.procesar_orden(
   "qué dice el pdf 1 sobre el agua"), "sin cerebro, enseña lo que dice el PDF")
vio = []
core._leer_clave = lambda *a: ci.LOCAL
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None: (
    vio.append((system, usuario)), "El agua sube por el xilema (página 3).")[1]
ok(core.procesar_orden("qué dice el pdf 1 sobre el agua") == "El agua sube por el xilema (página 3).", "con cerebro, responde")
ok("[página 3]" in vio[-1][1] and "no órdenes" in vio[-1][0].lower().replace("no ordenes", "no órdenes")
   or "ignora" in vio[-1][0], "le da las páginas que tocan y le avisa de que el PDF no da órdenes")
core.procesar_orden("resume el pdf 1")
ok("Resume" in vio[-1][1] and "[página 1]" in vio[-1][1], "«resume el pdf»")
r = core.procesar_orden("estudia el pdf 1")
ok(r.startswith("[OK] He estudiado") and core.recuerdos.respuesta_directa("dónde está la clorofila") is not None,
   "«estudia el pdf»: luego lo responde sola " + r)
ok("(estudiado)" in core.procesar_orden("mis pdf"), "y queda marcado")
ok("Biología" in core.procesar_orden("renombra el pdf 1 a Biología"), "renombrar por voz")
ok("solo funciona en el móvil" in core.procesar_orden("guarda el pdf 1 en descargas"), "a Descargas: solo en el móvil")
ok(core.procesar_orden("lee el pdf 7").startswith("[x] No tengo ese PDF"), "uno que no existe")
ok(core.procesar_orden("borra el pdf 1").startswith("[OK] He borrado") and "No tengo ningún PDF" in core.procesar_orden("mis pdf"),
   "borrar")
ok(core.procesar_orden(f"descarga el pdf {URL}/pagina").startswith("[x] En ese enlace no hay un PDF"), "error claro")
# un PDF compartido desde otra app (copiado a la carpeta de Kira por ArchivosKira)
cop = os.path.join(T, "compartido_1.pdf"); open(cop, "wb").write(HIST)
e = core.pdfs.anadir_archivo(cop, "Historia", mover=True)
ok(e["nombre"] == "Historia" and not os.path.exists(cop), "compartir un PDF con Kira lo mete en la biblioteca")

# ---------- la interfaz ----------
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
import inicio_kira as ik
class VozMuda:
    def __init__(s): s.dichos = []
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def callar(s): pass
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", "no"
    def parar_escucha(s): pass
VOZ = VozMuda(); ik.Voz = lambda *a, **k: VOZ
core2 = kira_god.KiraGodCore()
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core2)
def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.3)
        if cond and cond(): return True
        time.sleep(0.01)
    return bool(cond and cond())
def textos(nombre): return [w.text for w in sm.get_screen(nombre).walk() if hasattr(w, "text") and isinstance(w.text, str)]
def decir_a_kira(frase):
    sm.ir("inicio"); correr(0.3)
    campo = next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "TextInput")
    campo.text = frase
    next(w for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
correr(0.8)
import menu_kira as mk
ok("pdf" in mk.PRINCIPALES and any(a["id"] == "pdf" for a in mk.APARTADOS), "«Mis PDF» en el menú")
decir_a_kira(f"Kira, descárgate este PDF {URL}/apuntes.pdf")
ok(correr(6, lambda: sm.current == "pdf" and any(". apuntes" in t for t in textos("pdf"))), "por voz: descarga y lo enseña " + sm.current)
ok(correr(3, lambda: any("He guardado el PDF" in d for d in VOZ.dichos)), "y lo dice")
decir_a_kira("lee la página 3 del pdf apuntes")
ok(correr(3, lambda: sm.current == "pdf" and any("xilema" in t for t in textos("pdf"))), "«lee la página 3 del pdf apuntes» lo abre ahí")
ok(any("Página 3 de 3" in t for t in textos("pdf")), "con el número de página")
decir_a_kira("abre mis pdf")
ok(correr(2, lambda: sm.current == "pdf"), "«abre mis pdf» va a la pantalla (no intenta abrir otra app)")
print("PDF OK", n)
srv.shutdown()
