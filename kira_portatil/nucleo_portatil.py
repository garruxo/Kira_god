# -*- coding: utf-8 -*-
"""
nucleo_portatil.py - La KIRA COMPLETA corriendo en el portátil (sin pantalla), para que el móvil solo le MANDE órdenes.

Pedido del dueño: «la Kira del móvil, que solo le envíe órdenes y la ejecute el portátil». Aquí corre el MISMO núcleo
de Kira que en el móvil (kira_god.KiraGodCore: estudiar, pensar, investigar, foco, programar, experimentar, baúl…),
con su carpeta de datos propia (~/kira_portatil/kira_datos) y usando como cerebro el del portátil (servidor_portatil,
127.0.0.1:8770). El móvil le manda la orden por la WiFi de casa, ve la barra de progreso y recibe la respuesta.

  POST /orden   {"orden": "estudia Python"}  -> {"id": "…"}          (una orden cada vez; si está ocupada, 409)
  GET  /tarea?id=…                          -> {"estado", "fraccion", "avance": [...], "respuesta", "codigo", "nombre"}
  POST /cancelar                            -> para lo que esté haciendo («para» en el móvil)
  POST /memoria  (cuerpo = .zip)            -> importa la memoria del móvil (memoria_kira) y reinicia el núcleo
  GET  /hola                                -> quién soy, si estoy ocupada, cuánto recuerdo
  GET  /salud                               -> {"ok": true} (sin token)

Todo pide el token del laboratorio (el mismo que el cerebro de casa). Escucha en la red de casa (puerto 8771).
SEGURIDAD: aquí NO se ejecuta código que llegue por la red: solo ÓRDENES en lenguaje normal, que el núcleo trata
igual que en el móvil (modo seguro, laboratorio, dos toques / auto-mejora con su interruptor). La memoria que llega se
valida nombre a nombre (memoria_kira) y lo que había se guarda antes.
"""
import argparse
import hmac
import json
import os
import sys
import tempfile
import threading
import time
import uuid
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PUERTO = 8771
MAX_MEMORIA = 900 * 1024 * 1024
DATOS = os.path.expanduser("~/kira_portatil/kira_datos")


# =====================================================================================
#  PREPARAR LA CARPETA DE DATOS (antes de importar el núcleo)
# =====================================================================================
def preparar_datos(datos, token, cerebro_url="http://127.0.0.1:8770", lab_url="http://127.0.0.1:8765"):
    """Deja la carpeta de datos lista y le dice al núcleo dónde está su cerebro (el del portátil) con pasarela.json.
    Tiene que ir ANTES de importar kira_god (que lee KIRA_DATA_DIR)."""
    os.makedirs(datos, exist_ok=True)
    os.environ["KIRA_DATA_DIR"] = datos
    ruta = os.path.join(datos, "pasarela.json")
    d = {}
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.update(url=lab_url, token=token, portatil_url=cerebro_url, nombre=d.get("nombre") or "portátil")
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.chmod(ruta + ".tmp", 0o600)
    os.replace(ruta + ".tmp", ruta)
    if RAIZ not in sys.path:
        sys.path.insert(0, RAIZ)
    if AQUI not in sys.path:
        sys.path.insert(0, AQUI)
    return datos


# =====================================================================================
#  QUÉ HACER CON CADA ORDEN (lo mismo que hace la pantalla del móvil, pero sin pantalla)
# =====================================================================================
def ejecutar(core, orden, paso):
    """Hace la orden con el núcleo. `paso(fraccion|None, texto)` va contando. Devuelve {texto, codigo?, nombre?}."""
    import re
    o = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(orden or ""), flags=re.I).strip() or orden
    try:
        core.registrar_actividad()
    except Exception:
        pass
    try:
        core.nueva_tarea()
    except Exception:
        pass
    import experimentos_kira as ex
    import programar_kira as pk
    import internet_kira as net
    tema = None
    try:
        tema = core.es_estudia_general(o)
    except Exception:
        tema = None
    if tema:
        paso(0.0, f"Estudio {tema}: webs oficiales y cursos completos…")
        return {"texto": core.estudiar_a_fondo(tema, al_paso=lambda fr, t: paso(fr, t))}
    exp = ex.pedido_experimento(o)
    if exp is not None:
        paso(0.0, f"Experimento con {exp}…")
        r = core.experimentar(exp, al_progreso=lambda fr, t: paso(fr, t), mejorar=ex.quiere_mejorar(o))
        return {"texto": r.get("texto", ""), "codigo": r.get("codigo") if r.get("ok") else None,
                "nombre": r.get("nombre"), "ok": bool(r.get("ok"))}
    prog = pk.pedido_programa(o)
    if prog is not None:
        paso(0.0, f"Escribo el programa: {prog}…")
        r = core.programa_acordado(prog, al_paso=lambda t: paso(None, t))
        if not r.get("ok"):
            return {"texto": str(r.get("texto", "No me salió el programa.")).split("\n")[0], "ok": False}
        return {"texto": "Programa escrito y probado en modo seguro en el portátil.", "codigo": r.get("codigo"),
                "nombre": r.get("nombre"), "ok": True}
    cod = net.pedido_aprender_codigo(o)
    if cod is not None:
        return {"texto": core.aprender_codigo(cod, al_paso=lambda t: paso(None, t))}
    paso(None, "Pensando…")
    return {"texto": core.procesar_orden(o)}


# =====================================================================================
#  LAS TAREAS (una cada vez; el móvil pregunta cómo va)
# =====================================================================================
class Trabajos:
    def __init__(self, hacer, guardar=20):
        self._hacer = hacer            # hacer(orden, paso) -> dict
        self._lock = threading.Lock()
        self.tareas = {}
        self.actual = None
        self._guardar = guardar

    def ocupado(self):
        t = self.tareas.get(self.actual) if self.actual else None
        return bool(t and t["estado"] == "en curso")

    def empezar(self, orden):
        with self._lock:
            if self.ocupado():
                return None
            tid = uuid.uuid4().hex[:12]
            t = {"id": tid, "orden": str(orden)[:500], "estado": "en curso", "fraccion": 0.0, "avance": [],
                 "respuesta": "", "codigo": None, "nombre": None, "inicio": time.time()}
            self.tareas[tid] = t
            self.actual = tid
            for viejo in sorted(self.tareas, key=lambda k: self.tareas[k]["inicio"])[:-self._guardar]:
                self.tareas.pop(viejo, None)

        def paso(fr, texto):
            if fr is not None:
                try:
                    t["fraccion"] = max(0.0, min(1.0, float(fr)))
                except (TypeError, ValueError):
                    pass
            if texto:
                t["avance"] = (t["avance"] + [str(texto)[:300]])[-40:]

        def correr():
            try:
                r = self._hacer(t["orden"], paso) or {}
                t.update(respuesta=str(r.get("texto") or ""), codigo=r.get("codigo"), nombre=r.get("nombre"),
                         estado="hecho", fraccion=1.0)
            except Exception as e:
                cancel = type(e).__name__ == "Cancelada"
                t.update(estado="cancelado" if cancel else "error",
                         respuesta="Parado." if cancel else f"[x] {e}")
        threading.Thread(target=correr, daemon=True).start()
        return tid

    def ver(self, tid):
        t = self.tareas.get(tid)
        if not t:
            return None
        return {k: t[k] for k in ("id", "orden", "estado", "fraccion", "avance", "respuesta", "codigo", "nombre")}


# =====================================================================================
#  EL NÚCLEO (se puede reiniciar tras importar la memoria)
# =====================================================================================
class Nucleo:
    def __init__(self, datos, crear=None):
        self.datos = datos
        self._crear = crear or self._crear_real
        self.core = self._crear()
        self.trabajos = Trabajos(lambda orden, paso: ejecutar(self.core, orden, paso))

    @staticmethod
    def _crear_real():
        import kira_god
        return kira_god.KiraGodCore()

    def reiniciar(self):
        try:
            self.core.pensar_sola(False)
        except Exception:
            pass
        self.core = self._crear()
        try:
            self.core.reanudar_pensar()
        except Exception:
            pass

    def importar_memoria(self, zip_ruta):
        if self.trabajos.ocupado():
            raise RuntimeError("Estoy haciendo algo; cuando acabe, mándame la memoria.")
        import memoria_kira as mk
        r = mk.importar(zip_ruta, self.datos)
        try:                                          # su nacimiento sigue siendo su primer recuerdo
            import nacimiento_kira as nk
            p = nk.cargar()
            if p:
                nk.primer_recuerdo(p, os.path.join(self.datos, "recuerdos"))
        except Exception:
            pass
        self.reiniciar()
        return r

    def hola(self):
        rec = getattr(self.core, "recuerdos", None)
        try:
            n = rec.total() if rec is not None else 0
        except Exception:
            n = 0
        try:
            import version_kira as vk
            ver = vk.VERSION
        except Exception:
            ver = "?"
        llamar = ""
        try:
            import nacimiento_kira as nk
            llamar = (nk.cargar() or {}).get("llamar", "")
        except Exception:
            pass
        t = self.trabajos.tareas.get(self.trabajos.actual) if self.trabajos.actual else None
        return {"kira_nucleo": 1, "version": ver, "recuerdos": n, "llamar": llamar,
                "ocupada": self.trabajos.ocupado(), "haciendo": (t or {}).get("orden", "") if self.trabajos.ocupado() else ""}


# =====================================================================================
#  EL SERVIDOR
# =====================================================================================
def crear_servidor(host, puerto, token, nucleo):
    class Manejador(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "KiraNucleo/1"

        def log_message(self, *a):
            pass

        def _json(self, codigo, d):
            cuerpo = json.dumps(d, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _ok_token(self):
            t = self.headers.get("X-Kira-Token", "")
            if token and t and hmac.compare_digest(t.encode(), token.encode()):
                return True
            self._json(401, {"error": "token"})
            return False

        def _cuerpo_json(self, maximo=200_000):
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > maximo:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode("utf-8"))
            except ValueError:
                return {}

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if u.path == "/salud":
                return self._json(200, {"ok": True})
            if not self._ok_token():
                return
            if u.path == "/hola":
                return self._json(200, nucleo.hola())
            if u.path == "/tarea":
                tid = (urllib.parse.parse_qs(u.query).get("id") or [""])[0]
                t = nucleo.trabajos.ver(tid)
                return self._json(200, t) if t else self._json(404, {"error": "no existe esa tarea"})
            self._json(404, {"error": "no existe"})

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if not self._ok_token():
                return
            if u.path == "/orden":
                orden = str(self._cuerpo_json().get("orden") or "").strip()
                if not orden:
                    return self._json(400, {"error": "falta la orden"})
                tid = nucleo.trabajos.empezar(orden)
                if tid is None:
                    return self._json(409, {"error": "ocupada", **nucleo.hola()})
                return self._json(200, {"id": tid})
            if u.path == "/cancelar":
                try:
                    nucleo.core.cancelar()
                except Exception:
                    pass
                return self._json(200, {"ok": True})
            if u.path == "/memoria":
                n = int(self.headers.get("Content-Length") or 0)
                if n <= 0 or n > MAX_MEMORIA:
                    return self._json(413, {"error": "el paquete de memoria no vale (vacío o enorme)"})
                fd, tmp = tempfile.mkstemp(suffix=".zip")
                try:
                    with os.fdopen(fd, "wb") as f:
                        quedan = n
                        while quedan > 0:
                            trozo = self.rfile.read(min(1 << 20, quedan))
                            if not trozo:
                                break
                            f.write(trozo)
                            quedan -= len(trozo)
                    import memoria_kira as mk
                    r = nucleo.importar_memoria(tmp)
                    return self._json(200, {"ok": True, "texto": mk.texto_resumen(r, "recibido"), **{
                        k: r.get(k) for k in ("archivos", "origen")}})
                except Exception as e:
                    return self._json(400, {"ok": False, "error": str(e)})
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            self._json(404, {"error": "no existe"})

    return ThreadingHTTPServer((host, puerto), Manejador)


# =====================================================================================
#  CLIENTE (lo usa la ventana del portátil; el móvil usa casa_kira)
# =====================================================================================
class ClienteNucleo:
    def __init__(self, url, token, abrir=None):
        import urllib.request
        self.url, self.token = url.rstrip("/"), token
        self._abrir = abrir or urllib.request.urlopen

    def _pedir(self, ruta, datos=None, timeout=10):
        import urllib.request
        req = urllib.request.Request(self.url + ruta, data=None if datos is None else json.dumps(datos).encode(),
                                     method="GET" if datos is None else "POST",
                                     headers={"X-Kira-Token": self.token, "Content-Type": "application/json"})
        with self._abrir(req, timeout=timeout) as r:
            return json.loads(r.read(4_000_000).decode("utf-8"))

    def disponible(self):
        try:
            return self._pedir("/hola", timeout=2).get("kira_nucleo") == 1
        except Exception:
            return False

    def orden(self, texto, al_paso=None, cada=1.0, parar=None, espera_max=6 * 3600):
        """Manda la orden y espera el resultado contando los pasos. Devuelve la tarea final (dict)."""
        tid = self._pedir("/orden", {"orden": texto})["id"]
        vistos, fin = 0, time.time() + espera_max
        while time.time() < fin:
            t = self._pedir("/tarea?id=" + tid)
            for linea in t.get("avance", [])[vistos:]:
                if al_paso:
                    al_paso(t.get("fraccion"), linea)
            vistos = len(t.get("avance", []))
            if t.get("estado") != "en curso":
                return t
            if parar and parar():
                self._pedir("/cancelar", {})
            time.sleep(cada)
        return {"estado": "error", "respuesta": "Ha tardado demasiado."}


def main(argv=None):
    ap = argparse.ArgumentParser(description="La Kira completa en el portátil (el móvil le manda órdenes)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--puerto", type=int, default=PUERTO)
    ap.add_argument("--datos", default=DATOS)
    ap.add_argument("--token", default=os.path.join(RAIZ, "kira_laboratorio", "token_lab.txt"))
    a = ap.parse_args(argv)
    sys.path.insert(0, AQUI)
    import servidor_portatil as sp
    token = sp.leer_token(a.token)
    if len(token) < 16:
        sys.exit("No encuentro el token del laboratorio (arranca antes el laboratorio una vez: lo crea él).")
    preparar_datos(a.datos, token)
    os.environ.setdefault("KIRA_BAUL_PORTATIL", os.path.join(a.datos, "recuerdos"))
    nucleo = Nucleo(a.datos)
    try:
        nucleo.core.reanudar_pensar()
    except Exception:
        pass
    srv = crear_servidor(a.host, a.puerto, token, nucleo)
    print(f"[núcleo] Kira completa escuchando en {a.host}:{a.puerto} (datos en {a.datos}).", flush=True)
    try:
        srv.serve_forever()
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
