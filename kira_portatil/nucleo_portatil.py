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
_MAQUINA = {"m": None}


def maquina():
    """La máquina virtual de Kira (v2.85), una para todo el núcleo."""
    if _MAQUINA["m"] is None:
        import maquina_kira as mq
        _MAQUINA["m"] = mq.Maquina()
    return _MAQUINA["m"]


def red_maquina():
    """v2.91: por dónde sale a internet lo de investigar (su máquina; si no puede, el portátil)."""
    if _MAQUINA.get("red") is None:
        import maquina_kira as mq
        _MAQUINA["red"] = mq.RedMaquina(maquina())
    return _MAQUINA["red"]


def enganchar_maquina(core):
    """v2.91 (lo pidió el dueño): KiraOS aprende, investiga, busca y EXPERIMENTA desde su máquina virtual. Buscar,
    leer páginas, vídeos y la Wikipedia salen DESDE la máquina (por su puerta, sin ver tu casa) y sus experimentos al
    pensar corren DENTRO, como un usuario sin permisos. Lo que lleva una clave (Claude, GitHub) o va a casa sale
    directo: una clave nunca entra en la máquina."""
    import maquina_kira as mq
    import red_kira
    red = red_maquina()
    red_kira.poner_investigar(red.abrir)
    core.probar_experimento = lambda codigo: mq.probar_en_maquina(maquina(), codigo, red=red)
    return red


def encender_maquina_al_arrancar(m=None):
    """Al encender KiraOS se enciende también su máquina (con la puerta), si está preparada y hay KVM."""
    m = m or maquina()
    try:
        if m.preparada() and m.kvm() and not m.encendida():
            m.encender(red=True)
    except Exception as e:                       # noqa: BLE001 - si no puede, investigará desde el portátil
        print(f"[núcleo] no pude encender la máquina: {e}", flush=True)


_Y_PRUEBALO = r"\s*,?\s*y\s+pru[eé]balo\s+en\s+(?:tu|la|mi)\s+m[aá]quina(?:\s+virtual)?\s*$"

# v2.87: KiraOS, cerebro central, también le cambia el ASPECTO al móvil y le prepara MEJORAS de sistema
_TEMA_MOVIL = (r"^(?:cambia|pon|ponle|cambiale)\s+(?:el\s+)?(?:aspecto|tema|color(?:es)?|estetica|estética)\s+"
               r"(?:del|al|de\s+la\s+kira\s+del)\s+m[oó]vil\s+(?:a|en)\s+(?:color\s+)?(?P<t>[\wáéíóú]+)$")
_MEJORA_MOVIL = (r"^(?:prepara|crea|hazle|haz)\s+(?:una\s+)?(?:mejora|funci[oó]n|orden\s+nueva)\s+"
                 r"(?:para\s+(?:el|la\s+kira\s+del)\s+m[oó]vil)\s*(?:que|:|para)?\s*(?P<p>.+)$")


def mejora_para_movil(core, pedido, paso):
    """KiraOS escribe una mejora de sistema para el móvil, la prueba en SU laboratorio y la deja lista para la
    próxima sincronía. El móvil la vuelve a probar en el suyo y espera los dos toques del dueño."""
    import laboratorio_movil_kira as lab
    import sincronia_kira as sc
    paso(0.1, "Escribo la mejora para el móvil…")
    nombre, codigo = core.generar_mejora(pedido)
    paso(0.6, f"La pruebo en mi laboratorio ({nombre})…")
    res = lab.LaboratorioMovil().probar(nombre, codigo)
    if not res.get("ok"):
        mal = next((e for e in res.get("etapas", []) if not e.get("ok")), {})
        return {"texto": f"[x] La mejora «{nombre}» no pasa mi laboratorio ({mal.get('nombre', '?')}: "
                         f"{mal.get('detalle', '')}). No se la mando al móvil.", "ok": False}
    sc.guardar_para_movil(core.dir, nombre, codigo, descripcion=pedido, prueba=res)
    return {"texto": f"Mejora «{nombre}» lista y probada en mi laboratorio. Se la daré al móvil en la próxima "
                     "sincronía; allí la volverá a probar y esperará tus dos toques.", "codigo": codigo,
            "nombre": nombre, "ok": True}


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
    import maquina_kira as mq
    import wifi_kira as wk
    import sentidos_portatil as sp
    if wk.orden_wifi(o) is not None:              # v2.88: la WiFi del portátil (la clave, solo en el portátil)
        paso(0.2, "Miro la WiFi del portátil…")
        return {"texto": wk.responder(o)}
    so = sp.es_orden(o)                           # v2.93: los SENTIDOS del portátil (cámara y pantalla, con OCR)
    if so:
        tipo, describir = so
        paso(0.3, "Miro con mi cámara…" if tipo == "camara" else "Leo la pantalla…")
        return {"texto": sp.hacer(tipo, describir)}
    om = mq.orden_maquina(o)                      # v2.85: su MÁQUINA VIRTUAL (Linux ligero)
    if om:
        accion, carga = om
        paso(0.0, f"Mi máquina: {accion}…")
        rec = getattr(core, "recuerdos", None)
        guardar = (lambda tema, texto: rec.guardar(texto, tema=tema, fuente="mi máquina virtual")) if rec else None
        try:
            return mq.hacer(maquina(), accion, carga, al_paso=lambda fr, t: paso(fr, t), guardar_ficha=guardar)
        except mq.MaquinaError as e:
            return {"texto": f"[x] {e}", "ok": False}
    o_limpia = o.rstrip(" .!¡?¿")
    m_t = re.match(_TEMA_MOVIL, o_limpia, flags=re.I)
    if m_t:
        import sincronia_kira as sc
        try:
            tema = sc.poner_tema_movil(core.dir, m_t.group("t"))
        except ValueError as e:
            return {"texto": f"[x] {e}", "ok": False}
        return {"texto": f"Hecho: el móvil se verá en «{tema['nombre']}» después de la próxima sincronía "
                         "(al volver a abrir la app)."}
    m_m = re.match(_MEJORA_MOVIL, o_limpia, flags=re.I)
    if m_m:
        return mejora_para_movil(core, m_m.group("p").strip(), paso)
    en_maquina = bool(re.search(_Y_PRUEBALO, o, flags=re.I))
    if en_maquina:
        o = re.sub(_Y_PRUEBALO, "", o, flags=re.I).strip()
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
        if r.get("ok") and r.get("codigo"):
            maquina().ultimo_codigo = r.get("codigo")
        return {"texto": r.get("texto", ""), "codigo": r.get("codigo") if r.get("ok") else None,
                "nombre": r.get("nombre"), "ok": bool(r.get("ok"))}
    prog = pk.pedido_programa(o)
    if prog is not None:
        paso(0.0, f"Escribo el programa: {prog}…")
        r = core.programa_acordado(prog, al_paso=lambda t: paso(None, t))
        if not r.get("ok"):
            return {"texto": str(r.get("texto", "No me salió el programa.")).split("\n")[0], "ok": False}
        maquina().ultimo_codigo = r.get("codigo")
        texto = "Programa escrito y probado en modo seguro en el portátil."
        if en_maquina:
            try:
                c, salida = maquina().probar_python(r.get("codigo") or "")
                texto += (" Y en mi máquina " + ("funciona" if c == 0 else f"falló (código {c})") + ":\n"
                          + (salida.strip() or "(sin salida)"))
            except mq.MaquinaError as e:
                texto += f" En mi máquina no pude probarlo: {e}"
        return {"texto": texto, "codigo": r.get("codigo"), "nombre": r.get("nombre"), "ok": True}
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
    def __init__(self, datos, crear=None, con_maquina=False):
        self.datos = datos
        self._crear = crear or self._crear_real
        self.con_maquina = con_maquina
        self.core = self._crear()
        self._enganchar()
        self.trabajos = Trabajos(lambda orden, paso: ejecutar(self.core, orden, paso))
        self._lock_sinc = threading.Lock()

    @staticmethod
    def _crear_real():
        import kira_god
        return kira_god.KiraGodCore()

    def _enganchar(self):
        if self.con_maquina:
            try:
                enganchar_maquina(self.core)
            except Exception as e:                   # noqa: BLE001
                print(f"[núcleo] sin máquina para investigar: {e}", flush=True)

    def reiniciar(self):
        try:
            self.core.pensar_sola(False)
        except Exception:
            pass
        self.core = self._crear()
        self._enganchar()
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
                "ocupada": self.trabajos.ocupado(), "haciendo": (t or {}).get("orden", "") if self.trabajos.ocupado() else "",
                "actividad": actividad(self.core), "equipo": equipo_corto(), "sincronia": sincronia_corta(self.datos)}

    def sincronizar(self, paquete):
        """v2.87: lo nuevo del móvil entra en KiraOS (se suma, no se borra) y le devuelve lo nuevo de KiraOS."""
        import sincronia_kira as sc
        with self._lock_sinc:
            return sc.aplicar_en_kiraos(self.datos, self.core.recuerdos, paquete)


def es_local(ip):
    """¿La petición viene de este mismo portátil (la ventana o la consola de Kira)?"""
    return str(ip or "") in ("127.0.0.1", "::1", "localhost") or str(ip or "").startswith("127.")


def actividad(core):
    """Qué está haciendo la Kira del portátil (para el panel del móvil)."""
    d = {"pensando": bool(getattr(core, "_pensar_on", False)), "estudiando": bool(getattr(core, "_estudiando", False)),
         "foco": "", "pensamientos": 0, "soluciones": 0, "maquina": False}
    try:
        foco = json.load(open(os.path.join(core.dir, "foco.json"), encoding="utf-8"))
        if foco.get("activo"):
            d["foco"] = str(foco.get("tema", ""))[:80]
    except (OSError, ValueError, AttributeError):
        pass
    try:
        import pensador_kira as pn
        est = pn.cargar(os.path.join(core.dir, "pensamientos.json"))
        d["pensamientos"], d["soluciones"] = len(est.get("notas", [])), len(est.get("soluciones", {}))
    except Exception:
        pass
    m = _MAQUINA.get("m")
    try:
        d["maquina"] = bool(m and m.encendida())
    except Exception:
        pass
    r = _MAQUINA.get("red")
    if r is not None:
        d["internet"] = r.estado()
    try:
        import wifi_kira as wk
        d["wifi"] = wk.resumen_corto()
    except Exception:
        pass
    return d


def equipo_corto():
    try:
        import nacimiento_kira as nk
        e = nk.equipo()
        try:
            import shutil as _sh
            e["disco_libre_gb"] = _sh.disk_usage("/").free // (1000 ** 3)
        except OSError:
            pass
        try:
            with open("/proc/loadavg") as f:
                e["carga"] = f.read().split()[0]
        except OSError:
            pass
        try:
            with open("/proc/uptime") as f:
                e["encendido_h"] = round(float(f.read().split()[0]) / 3600, 1)
        except (OSError, ValueError):
            pass
        return e
    except Exception:
        return {}


def sincronia_corta(datos):
    try:
        import sincronia_kira as sc
        est = sc.estado_kiraos(datos)
        return {"ultima": est.get("ultima", 0), "recibidos": est.get("recibidos_total", 0)}
    except Exception:
        return {}


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
                if not es_local(self.client_address[0]):     # v2.88: desde el móvil, la WiFi con cuidado
                    import wifi_kira as wk
                    vale, porque = wk.permitida_remota(orden)
                    if not vale:
                        return self._json(403, {"error": porque})
                tid = nucleo.trabajos.empezar(orden)
                if tid is None:
                    return self._json(409, {"error": "ocupada", **nucleo.hola()})
                return self._json(200, {"id": tid})
            if u.path == "/sincronizar":
                d = self._cuerpo_json(maximo=40_000_000)
                try:
                    resumen, respuesta = nucleo.sincronizar(d.get("paquete") or {})
                except (ValueError, TypeError) as e:
                    return self._json(400, {"error": str(e)})
                return self._json(200, {"ok": True, "resumen": resumen, "respuesta": respuesta})
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
        """Manda la orden y espera el resultado contando los pasos. Devuelve la tarea final (dict).
        v2.94: si está ocupada (409), lo dice con buenas palabras en vez de soltar «HTTP Error 409»."""
        import urllib.error
        try:
            tid = self._pedir("/orden", {"orden": texto})["id"]
        except urllib.error.HTTPError as e:
            if e.code == 409:                        # el núcleo solo hace una cosa a la vez
                hago = ""
                try:
                    d = json.loads((e.read() or b"{}").decode("utf-8"))
                    act = [k for k, v in (d.get("actividad") or {}).items() if v]
                    hago = (" (estoy con: " + ", ".join(act) + ")") if act else ""
                except Exception:
                    pass
                return {"estado": "ocupada",
                        "respuesta": "Estoy ocupada terminando lo anterior" + hago +
                                     ". Dame un momento y vuelve a pedírmelo."}
            raise
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
    ap.add_argument("--sin-wifi", action="store_true", help="no vigilar la WiFi")
    ap.add_argument("--sin-maquina", action="store_true", help="investigar desde el portátil, no desde su máquina")
    a = ap.parse_args(argv)
    sys.path.insert(0, AQUI)
    import servidor_portatil as sp
    token = sp.leer_token(a.token)
    if len(token) < 16:
        sys.exit("No encuentro el token del laboratorio (arranca antes el laboratorio una vez: lo crea él).")
    preparar_datos(a.datos, token)
    os.environ.setdefault("KIRA_BAUL_PORTATIL", os.path.join(a.datos, "recuerdos"))
    nucleo = Nucleo(a.datos, con_maquina=not a.sin_maquina)
    if not a.sin_maquina:                       # v2.91: su máquina se enciende con ella (investiga desde ahí)
        threading.Thread(target=encender_maquina_al_arrancar, daemon=True).start()
    try:
        nucleo.core.reanudar_pensar()
    except Exception:
        pass
    if not a.sin_wifi:                          # v2.88: si la WiFi se cae, vuelve a conectar sola (redes guardadas)
        import wifi_kira as wk
        threading.Thread(target=wk.vigilar, daemon=True).start()
    srv = crear_servidor(a.host, a.puerto, token, nucleo)
    print(f"[núcleo] Kira completa escuchando en {a.host}:{a.puerto} (datos en {a.datos}).", flush=True)
    try:
        srv.serve_forever()
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
