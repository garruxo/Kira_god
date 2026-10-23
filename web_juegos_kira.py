# -*- coding: utf-8 -*-
"""
web_juegos_kira.py - Tus juegos de Kira COMO APP: una página web de un solo archivo y un icono en la pantalla de inicio.

  «Kira, convierte el juego en una app»       -> las dos cosas: icono en el inicio + página web en Descargas/Kira
  «Kira, pon el juego en la pantalla de inicio» -> solo el icono (abre Kira directamente en ese juego)
  «Kira, exporta el juego a web»              -> solo la página web (funciona sin internet, en cualquier navegador,
                                                 también en el ordenador; se puede pasar a otra persona)

La página lleva DENTRO Brython (Python escrito en JavaScript, web_kira/), el motor de juegos y tu juego: el MISMO
código Python, sin traducirlo. Lógica pura (sin Kivy ni Android): se prueba en el PC.
"""
import ast
import base64
import html
import json
import os
import re
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETA_WEB = os.path.join(AQUI, "web_kira")

BASE = {"math", "random", "motor_juegos_kira"}
AMPLIADA = BASE | {"collections", "itertools", "functools", "colorsys", "json", "string", "time", "heapq", "copy",
                   "bisect", "operator"}
MAX_DIBUJOS = 3 * 1024 * 1024          # bytes de dibujos que se meten en la página


class WebError(Exception):
    pass


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# =====================================================================================
#  LA ORDEN
# =====================================================================================
_COSA = r"(?:el\s+juego|este\s+juego|mi\s+juego|el\s+juego\s+de\s+[\w\s]{1,40}?|esto|eso|lo)"
_PEDIDO = re.compile(
    r"^(?:por\s+favor\s+)?(?:"
    r"(?:convierte|conviertelo|transforma|transformalo|haz|hazme|crea|creame|pasa|pasalo)\s*(?:" + _COSA + r")?\s*"
    r"(?:en|como|a)?\s*(?:una?\s+)?(?:app|aplicacion|apk)(?:\s+de\s+(?:" + _COSA + r"|verdad|android))?"
    r"|(?:pon|ponme|ponlo|lleva|llevalo|anade|anadelo|crea)\s*(?:" + _COSA + r")?\s*(?:en|al|a)\s+(?:la\s+|mi\s+|el\s+)?"
    r"(?:pantalla\s+de\s+inicio|inicio|escritorio)"
    r"|(?:exporta|exportalo|guarda|guardalo|pasa|pasalo|convierte|conviertelo|haz|hazme)\s*(?:" + _COSA + r")?\s*"
    r"(?:a|en|como)\s+(?:una?\s+)?(?:web|pagina(?:\s+web)?|html)"
    r")\s*(?P<resto>.*)$", re.I)


def pedido_app(texto):
    """¿Pide convertir un juego en app? -> 'app' (icono + web) | 'inicio' | 'web' | 'apk' (app de verdad, por GitHub);
    si no, None. «hazme una app de recetas» NO es esto (es una maqueta de diseño): hace falta nombrar el juego."""
    t = _plano(re.sub(r"^\s*kira[\s,:]+", "", str(texto or ""), flags=re.I)).strip(" .!?¡¿")
    t = re.sub(r"\b(conviertelo|transformalo|pasalo|ponlo|llevalo|anadelo|exportalo|guardalo)\b", r"\1 lo", t)
    m = _PEDIDO.match(t)
    if not m:
        return None
    del_juego = re.search(r"\b(juego|lo|esto|eso)\b", t)
    if re.search(r"\b(apk|de verdad|android)\b", t) and del_juego:
        return "apk"
    if re.search(r"\b(web|pagina|html)\b", t):
        return "web" if del_juego else None
    if re.search(r"\b(inicio|escritorio)\b", t):
        return "inicio"
    return "app" if del_juego else None


# =====================================================================================
#  LA PÁGINA
# =====================================================================================
def importaciones(codigo):
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as e:
        raise WebError(f"El juego tiene un error de escritura (línea {e.lineno}): arréglalo antes.")
    mods = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            mods.add(n.module.split(".")[0])
    return mods


def biblioteca_para(codigo):
    """'stdlib_base.js' o 'stdlib_ampliada.js' según lo que importe el juego (o WebError si usa algo que no va)."""
    mods = importaciones(codigo)
    raros = sorted(mods - AMPLIADA)
    if raros:
        raise WebError("El juego usa " + ", ".join(f"«{r}»" for r in raros) + ", que todavía no funciona en la versión "
                       "web. Los juegos web pueden usar: " + ", ".join(sorted(AMPLIADA - {"motor_juegos_kira"})) + ".")
    return "stdlib_base.js" if mods <= BASE else "stdlib_ampliada.js"


def titulo_de(codigo):
    m = re.search(r"^\s+titulo\s*=\s*(['\"])(.{1,80}?)\1", codigo, re.M)
    return m.group(2).strip() if m else "Juego de Kira"


def nombre_archivo(titulo):
    t = re.sub(r"[^a-z0-9]+", "_", _plano(titulo)).strip("_")[:40]
    return (t or "juego") + ".html"


def _leer(nombre):
    with open(os.path.join(CARPETA_WEB, nombre), encoding="utf-8") as f:
        return f.read()


def _js(texto):
    """Que nada dentro de un <script> lo cierre antes de tiempo."""
    return texto.replace("</", "<\\/")


def dibujos_png(carpeta_sprites):
    """{nombre: bytes} de los dibujos pintados del juego (los .png de su carpeta)."""
    sal, total = {}, 0
    if not carpeta_sprites or not os.path.isdir(carpeta_sprites):
        return sal
    for f in sorted(os.listdir(carpeta_sprites)):
        if not f.lower().endswith(".png"):
            continue
        try:
            with open(os.path.join(carpeta_sprites, f), "rb") as fh:
                datos = fh.read()
        except OSError:
            continue
        if total + len(datos) > MAX_DIBUJOS:
            break
        total += len(datos)
        sal[f[:-4]] = datos
    return sal


def fuente_motor():
    """El texto del motor de juegos. En el APK los .py van compilados (.pyc) y el original no está: entonces sale
    de motor_fuente_kira.py (generado por herramientas_pc/generar_motor_fuente.py)."""
    try:
        with open(os.path.join(AQUI, "motor_juegos_kira.py"), encoding="utf-8") as f:
            return f.read()
    except OSError:
        import motor_fuente_kira
        return motor_fuente_kira.MOTOR


def html_juego(codigo, dibujos=None, titulo=None):
    """La página completa (un solo archivo .html, sin internet) que juega a ESTE juego."""
    if "Juego" not in codigo or "class " not in codigo:
        raise WebError("Eso no es un juego de Kira (una clase que herede de Juego).")
    lib = biblioteca_para(codigo)
    titulo = titulo or titulo_de(codigo)
    motor = fuente_motor()
    modulos = {"$timestamp": 1, "motor_juegos_kira": [".py", motor, ["math", "random"]],
               "juego_kira": [".py", codigo, sorted(importaciones(codigo))]}
    imgs = {n: "data:image/png;base64," + base64.b64encode(b).decode("ascii") for n, b in (dibujos or {}).items()}
    return (PLANTILLA
            .replace("@@TITULO@@", html.escape(titulo))
            .replace("@@BRYTHON@@", (_js(_leer("brython.js"))))
            .replace("@@STDLIB@@", (_js(_leer(lib))))
            .replace("@@MODULOS@@", (_js(json.dumps(modulos, ensure_ascii=False))))
            .replace("@@DIBUJOS@@", (_js(json.dumps(imgs)))))


PLANTILLA = r"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0f172a">
<title>@@TITULO@@</title>
<style>
html,body{margin:0;height:100%;background:#0f172a;color:#e2e8f0;font-family:Roboto,system-ui,sans-serif;
  overflow:hidden;touch-action:none;user-select:none;-webkit-user-select:none}
#arriba{height:44px;display:flex;align-items:center;gap:8px;padding:0 10px;box-sizing:border-box}
#marcador{flex:1;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
button{background:#334155;color:#fff;border:0;border-radius:8px;padding:8px 12px;font-size:14px}
#lienzo{display:block;width:100vw;height:calc(100vh - 44px)}
#aviso{position:fixed;left:12px;right:12px;bottom:12px;background:#7f1d1d;color:#fff;padding:12px;border-radius:10px;
  display:none;font-size:14px;white-space:pre-wrap}
</style>
<script>window.__BRYTHON__ = {brython_path: location.href.split("#")[0].split("?")[0].replace(/[^\/]*$/, "")};</script>
<script>@@BRYTHON@@</script>
<script>@@STDLIB@@</script>
<script>__BRYTHON__.update_VFS(@@MODULOS@@);</script>
</head><body>
<div id="arriba"><div id="marcador">Cargando…</div>
<button id="b_pausa">Pausa</button><button id="b_otra">Otra vez</button></div>
<canvas id="lienzo"></canvas><div id="aviso"></div>
<script>
(function(){
  var DIBUJOS = @@DIBUJOS@@, IMGS = {};
  for (var n in DIBUJOS){ var im = new Image(); im.src = DIBUJOS[n]; IMGS[n] = im; }
  var cv = document.getElementById('lienzo'), ctx = cv.getContext('2d');
  var mar = document.getElementById('marcador'), aviso = document.getElementById('aviso');
  var W = 360, H = 640, esc = 1, ox = 0, oy = 0, dpr = 1, previo = null, antes = 0, vivo = true;
  function ajustar(){
    dpr = window.devicePixelRatio || 1;
    cv.width = Math.round(cv.clientWidth * dpr); cv.height = Math.round(cv.clientHeight * dpr);
    esc = Math.min(cv.width / W, cv.height / H); ox = (cv.width - W * esc) / 2; oy = (cv.height - H * esc) / 2;
  }
  function col(c){ return 'rgba(' + Math.round(c[0]*255) + ',' + Math.round(c[1]*255) + ',' + Math.round(c[2]*255) + ',' + c[3] + ')'; }
  function px(x){ return ox + x * esc; }
  function py(y){ return cv.height - oy - y * esc; }        // en el juego (0,0) está ABAJO a la izquierda
  function pintar(d, fondo){
    ctx.fillStyle = '#0f172a'; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.save(); ctx.beginPath(); ctx.rect(ox, oy, W * esc, H * esc); ctx.clip();   // nada fuera del campo
    ctx.fillStyle = col(fondo); ctx.fillRect(ox, oy, W * esc, H * esc);
    for (var i = 0; i < d.length; i++){
      var p = d[i], f = p[0], x = p[1], y = p[2], w = p[3], h = p[4], c = p[5], t = p[6], tam = p[7], pts = p[8];
      ctx.fillStyle = col(c); ctx.strokeStyle = col(c);
      if (f == 'rect') ctx.fillRect(px(x), py(y + h), w * esc, h * esc);
      else if (f == 'circulo'){ ctx.beginPath(); ctx.ellipse(px(x), py(y), w*esc/2, h*esc/2, 0, 0, 2*Math.PI); ctx.fill(); }
      else if (f == 'linea' && pts.length >= 2){
        ctx.lineWidth = Math.max(1, tam * esc); ctx.lineCap = 'round'; ctx.beginPath();
        ctx.moveTo(px(pts[0][0]), py(pts[0][1]));
        for (var k = 1; k < pts.length; k++) ctx.lineTo(px(pts[k][0]), py(pts[k][1]));
        ctx.stroke();
      } else if (f == 'poligono' && pts.length >= 3){
        ctx.beginPath(); ctx.moveTo(px(pts[0][0]), py(pts[0][1]));
        for (var k = 1; k < pts.length; k++) ctx.lineTo(px(pts[k][0]), py(pts[k][1]));
        ctx.closePath(); ctx.fill();
      } else if (f == 'imagen'){
        var im = IMGS[t];
        if (im && im.complete && im.naturalWidth){ ctx.globalAlpha = c[3]; ctx.drawImage(im, px(x), py(y + h), w*esc, h*esc); ctx.globalAlpha = 1; }
        else { ctx.fillStyle = 'rgba(' + Math.round(c[0]*153) + ',' + Math.round(c[1]*178) + ',' + Math.round(c[2]*204) + ',0.5)';
               ctx.fillRect(px(x), py(y + h), w * esc, h * esc); }
      } else if (f == 'texto' && t){
        ctx.font = Math.max(8, Math.round(tam * esc)) + 'px Roboto, system-ui, sans-serif';
        ctx.textBaseline = 'bottom'; ctx.fillText(t, px(x), py(y));
      }
    }
    ctx.restore();
  }
  function fallo(e){ vivo = false; aviso.style.display = 'block';
    aviso.textContent = 'Error en el juego: ' + (typeof e == 'string' ? e : (e && e.message) || String(e)); }
  function cuadro(ahora){
    if (!vivo) return;
    var dt = antes ? (ahora - antes) / 1000 : 0; antes = ahora;
    try { var r = window.kira_paso(dt); if (!vivo || !r || !r.length) return; pintar(r[0], r[2]); mar.textContent = r[1]; }
    catch (e) { fallo(e); return; }
    requestAnimationFrame(cuadro);
  }
  function aJuego(ev){ var b = cv.getBoundingClientRect();
    return [((ev.clientX - b.left) * dpr - ox) / esc, (cv.height - (ev.clientY - b.top) * dpr - oy) / esc]; }
  cv.addEventListener('pointerdown', function(ev){ ev.preventDefault(); cv.setPointerCapture(ev.pointerId);
    previo = aJuego(ev); try { window.kira_tocar(previo[0], previo[1]); } catch (e) { fallo(e); } });
  cv.addEventListener('pointermove', function(ev){ if (!previo) return; var q = aJuego(ev);
    try { window.kira_mover(q[0], q[1], q[0] - previo[0], q[1] - previo[1]); } catch (e) { fallo(e); }
    if (Math.abs(q[0] - previo[0]) + Math.abs(q[1] - previo[1]) > 25) previo = q; });
  function suelta(ev){ if (!previo) return; previo = null; var q = aJuego(ev);
    try { window.kira_soltar(q[0], q[1]); } catch (e) { fallo(e); } }
  cv.addEventListener('pointerup', suelta); cv.addEventListener('pointercancel', suelta);
  document.getElementById('b_pausa').onclick = function(){ window.kira_pausa(); };
  document.getElementById('b_otra').onclick = function(){ window.kira_otra(); };
  window.addEventListener('resize', ajustar);
  window.kira_empezar = function(ancho, alto, titulo){ W = ancho; H = alto; document.title = titulo; ajustar();
    requestAnimationFrame(cuadro); };
  window.kira_error = function(texto){ fallo(texto); };
  window.addEventListener('load', function(){ try { brython({debug: 0}); } catch (e) { fallo(e); } });
})();
</script>
<script type="text/python">
from browser import window
import motor_juegos_kira as mj
try:
    import juego_kira
    clase = mj.buscar_juego(juego_kira.__dict__)
    if clase is None:
        raise RuntimeError("el programa no define ningún juego (una clase que herede de Juego)")
    g = clase()
except Exception as e:
    g = None
    window.kira_error(f"{type(e).__name__}: {e}")


def avisar(e):
    linea, tb = "", getattr(e, "__traceback__", None)
    while tb is not None:                               # la línea de TU juego donde falló
        try:
            if "juego_kira" in str(tb.tb_frame.f_code.co_filename):
                linea = f" (línea {tb.tb_lineno} del juego)"
        except Exception:
            pass
        tb = getattr(tb, "tb_next", None)
    window.kira_error(f"{type(e).__name__}: {e}{linea}")


def seguro(f):
    def envuelta(*a):
        try:
            return f(*a)
        except Exception as e:
            avisar(e)
            return None
    return envuelta


@seguro
def paso(dt):
    g.paso(dt)
    return [[[f, x, y, w, h, list(c), t, tam, [list(p) for p in pts]]
             for f, x, y, w, h, c, t, tam, pts in g.dibujo()], g.marcador(), list(mj.color(g.fondo))]


@seguro
def otra(*_):
    g.reiniciar()
    g.estado = "jugando"


if g is not None:
    window.kira_paso = paso
    window.kira_tocar = seguro(lambda x, y: g.tocar(x, y))
    window.kira_mover = seguro(lambda x, y, dx, dy: g.mover_dedo(x, y, dx, dy))
    window.kira_soltar = seguro(lambda x, y: g.soltar(x, y))
    window.kira_pausa = seguro(lambda *_: g.pausar())
    window.kira_otra = otra
    window.kira_empezar(g.ancho, g.alto, g.titulo)
</script>
</body></html>
"""
