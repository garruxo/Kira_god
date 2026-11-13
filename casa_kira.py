# -*- coding: utf-8 -*-
"""
casa_kira.py - El móvil usa el CEREBRO DE CASA (el portátil) cuando está en la WiFi (VA EN EL APK; solo estándar).

Cuando Kira y el portátil están en la misma red, Kira le pasa lo pesado (charla, programar, experimentar, estudiar
y pintar) a su cerebro grande; fuera de casa sigue con su cerebro del móvil. El portátil corre
kira_portatil/servidor_portatil.py (puerto 8770, faro UDP 8767); se empareja con el MISMO código de 6 cifras que el
laboratorio (comparten token). La dirección se guarda en pasarela.json (clave «portatil_url»); si el portátil cambia
de dirección, Kira lo vuelve a buscar solo.

  Casa().disponible()                 -> True si el portátil responde con nuestro token (cache 20 s)
  Casa().chat(msgs, grande=…, …)      -> respuesta del cerebro de casa (rápido o grande); puede ir a trozos
  Casa().pintar(prompt, …)            -> los bytes del PNG que pinta el portátil
  Casa.buscar()                       -> portátiles que hay en la WiFi [{'url','ip','nombre'}]

v2.84 — el MÓVIL COMO MANDO: en el portátil corre también la Kira completa (kira_portatil/nucleo_portatil.py, puerto
8771). El móvil le manda la orden y ve cómo va:
  Casa().nucleo_disponible()          -> True si la Kira completa del portátil responde
  Casa().orden("estudia Python", al_paso=…, parar=…) -> la tarea final {estado, respuesta, codigo, nombre}
  Casa().enviar_memoria("memoria.zip") -> le pasa la memoria del móvil (memoria_kira)
"""
import json
import socket
import threading
import time
import urllib.error
import urllib.request

import pasarela_cliente as pc

PUERTO_HTTP = 8770
PUERTO_NUCLEO = 8771
PUERTO_FARO = 8767
PREGUNTA = b"KIRA_BUSCA_PORTATIL 1"


class CasaError(RuntimeError):
    pass


class Cancelada(RuntimeError):
    pass


# =====================================================================================
#  BUSCARLO EN LA WIFI (igual que el laboratorio, pero su faro y su pregunta)
# =====================================================================================
def buscar(espera=1.5):
    """Portátiles (cerebro de casa) que hay en la WiFi: [{'url','ip','nombre'}]."""
    import enlace_lab_kira as el
    ip = el.ip_local()
    return _preguntar(el.destinos_faro(ip), espera) or _desde_lab()


def _preguntar(destinos, espera):
    out = {}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        return []
    with s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError:
            pass
        for d in destinos:
            try:
                s.sendto(PREGUNTA, (d, PUERTO_FARO))
            except OSError:
                continue
        fin = time.monotonic() + espera
        while True:
            queda = fin - time.monotonic()
            if queda <= 0:
                break
            s.settimeout(queda)
            try:
                datos, (ip, _p) = s.recvfrom(1024)
            except (socket.timeout, OSError):
                break
            try:
                r = json.loads(datos.decode("utf-8"))
                puerto = int(r.get("puerto", PUERTO_HTTP))
            except (ValueError, TypeError, AttributeError):
                continue
            if r.get("kira_portatil") != 1 or not 0 < puerto < 65536:
                continue
            nombre = str(r.get("nombre") or ip)[:40]
            out[(nombre, puerto)] = {"url": f"http://{ip}:{puerto}", "ip": ip, "nombre": nombre}
    return list(out.values())


def _desde_lab():
    """Si no contesta el faro, prueba en la MISMA dirección del laboratorio pero en el puerto del portátil."""
    url = str(pc.leer_config().get("url") or "")
    if not url:
        return []
    try:
        ip = url.split("//", 1)[1].split(":", 1)[0]
    except IndexError:
        return []
    prueba = f"http://{ip}:{PUERTO_HTTP}"
    return [{"url": prueba, "ip": ip, "nombre": pc.leer_config().get("nombre") or ip}] if _salud(prueba) else []


def _es_tailscale(ip):
    """¿Es una dirección de Tailscale (100.64.0.0/10)? Solo esas se aceptan como «dirección de fuera»."""
    import ipaddress
    try:
        d = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return False
    return d.version == 4 and d in ipaddress.ip_network("100.64.0.0/10")


def _salud(url, timeout=0.6):
    try:
        with urllib.request.urlopen(url + "/salud", timeout=timeout) as r:
            return json.loads(r.read(200).decode("utf-8")).get("ok") is True
    except Exception:
        return False


# =====================================================================================
#  EL CLIENTE
# =====================================================================================
class Casa:
    """url del portátil = pasarela.json['portatil_url'] (o se busca); token = el de la pasarela (compartido)."""

    def __init__(self, abrir=None, reloj=time.monotonic):
        self._abrir = abrir or urllib.request.urlopen
        self._reloj = reloj
        self._cache = (0.0, None)          # (instante, disponible)
        self._url_cache = None

    @property
    def url(self):
        return str(pc.leer_config().get("portatil_url") or "").rstrip("/")

    @property
    def token(self):
        return str(pc.leer_config().get("token") or "") or ""

    def _guardar_url(self, url):
        pc.guardar_config(pc.leer_config().get("url"), self.token,
                          portatil_url=str(url or "").rstrip("/"), nombre=pc.leer_config().get("nombre"))
        self._cache = (0.0, None)

    def reubicar(self):
        """Busca el portátil en la WiFi (mismo token) y guarda su dirección nueva. True si lo encontró."""
        for p in buscar():
            if self._comprueba(p["url"]):
                self._guardar_url(p["url"])
                return True
        return False

    def _comprueba(self, url):
        """¿Responde este portátil a NUESTRO token? (GET /hola)."""
        if not url or not self.token:
            return False
        try:
            req = urllib.request.Request(url + "/hola", method="GET", headers={"X-Kira-Token": self.token})
            with self._abrir(req, timeout=2) as r:
                return 200 <= getattr(r, "status", 200) < 300
        except Exception:
            return False

    def disponible(self, forzar=False):
        """True si el portátil está en la WiFi y acepta nuestro token (lo busca si cambió de dirección)."""
        t, ok = self._cache
        if not forzar and ok is not None and self._reloj() - t < 20:
            return ok
        ok = bool(self.url) and bool(self.token) and self._comprueba(self.url)
        if not ok and self.token:
            ok = self.reubicar()
        self._cache = (self._reloj(), ok)
        return ok

    def info(self):
        """Lo que hay en el portátil (cerebros, pintor, cargado), o None."""
        if not self.url or not self.token:
            return None
        try:
            req = urllib.request.Request(self.url + "/hola", method="GET", headers={"X-Kira-Token": self.token})
            with self._abrir(req, timeout=3) as r:
                return json.loads(r.read(20000).decode("utf-8"))
        except Exception:
            return None

    # ---- hablar con el cerebro de casa (mismo formato que llama-server, con token y «kira_cerebro») ----
    def chat(self, system, mensajes, grande=False, max_tokens=1024, timeout=600, al_trozo=None, parar=None, codigo=False):
        import cerebro_ia_kira as ci
        if parar is not None and al_trozo is None:
            al_trozo = lambda _t: None
        if parar is not None and parar():
            raise Cancelada("Cancelado.")
        msgs = ([{"role": "system", "content": str(system)}] if system else []) + [
            {"role": m["role"], "content": m["content"] if isinstance(m["content"], list) else str(m["content"])}
            for m in mensajes]
        afinado = ({"temperature": 0.78, "top_p": 0.95} if codigo else {"temperature": 0.6})  # v3.24: programar, más suave
        cuerpo = json.dumps({"messages": msgs, "max_tokens": int(max_tokens),
                             "stream": bool(al_trozo), "cache_prompt": True,
                             "kira_cerebro": "grande" if grande else "rapido",
                             "chat_template_kwargs": {"enable_thinking": False}, **afinado}).encode("utf-8")
        req = urllib.request.Request(self.url + "/v1/chat/completions", data=cuerpo, method="POST",
                                     headers={"Content-Type": "application/json", "X-Kira-Token": self.token})
        vigia = None
        if parar is not None and self._abrir is urllib.request.urlopen and self.url.startswith("http://"):
            abrir = lambda rq, timeout: self._abrir_cortable(rq, timeout, parar)   # noqa: E731  v3.18
        else:
            abrir = self._abrir
        try:
            with abrir(req, timeout=timeout) as r:
                if al_trozo:
                    crudo = []
                    texto = ci.leer_sse(r, lambda d: (d["choices"][0].get("delta") or {}).get("content") or "",
                                        al_trozo, parar=parar, crudo=crudo)
                    if not texto and crudo:
                        try:
                            texto = json.loads("\n".join(crudo))["choices"][0]["message"]["content"]
                        except (ValueError, KeyError, IndexError, TypeError):
                            texto = ""
                else:
                    datos = json.loads(r.read(4_000_000).decode("utf-8"))
                    texto = datos["choices"][0]["message"]["content"]
        except (ci.Cancelada, Cancelada):
            raise Cancelada("Cancelado.")
        except urllib.error.HTTPError as e:
            self._cache = (0.0, None)
            raise CasaError(f"El cerebro de casa respondió {e.code}.")
        except (KeyError, IndexError, TypeError):
            raise CasaError("El cerebro de casa devolvió una respuesta sin texto.")
        except Exception as e:
            self._cache = (0.0, None)
            raise CasaError(f"No se pudo hablar con el cerebro de casa: {e}")
        texto = ci.limpiar_respuesta(texto)
        if not texto:
            raise CasaError("El cerebro de casa no llegó a responder.")
        return texto

    def _abrir_cortable(self, req, timeout, parar):
        """v3.18: como urlopen, pero «Parar» corta YA aunque el cerebro aún esté LEYENDO el pedido (minutos sin decir
        nada en el Packard Bell): un vigía mira `parar()` cada 0,3 s y, si toca, cierra la conexión → el cerebro de
        casa lo nota y deja de trabajar en ello. Lanza Cancelada."""
        import http.client
        import urllib.parse
        u = urllib.parse.urlsplit(req.full_url)
        conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=timeout)
        listo = threading.Event()
        cortado = []

        def vigia():
            while not listo.wait(0.3):
                try:
                    if parar():
                        cortado.append(1)
                        if conn.sock is not None:
                            conn.sock.shutdown(socket.SHUT_RDWR)
                        return
                except Exception:
                    return
        cabeceras = {k: v for k, v in req.header_items()}
        try:
            conn.request(req.get_method(), u.path + (("?" + u.query) if u.query else ""), body=req.data,
                         headers=cabeceras)
            threading.Thread(target=vigia, daemon=True).start()
            r = conn.getresponse()
        except Exception:
            listo.set()
            conn.close()
            if cortado or parar():
                raise Cancelada("Cancelado.")
            raise
        if r.status >= 400:
            listo.set()
            cuerpo = r.read()
            conn.close()
            raise urllib.error.HTTPError(req.full_url, r.status, r.reason, r.headers, None)

        class _Resp:
            def __init__(self):
                self.status = r.status

            def __enter__(self):
                return self

            def __exit__(self, *a):
                listo.set()
                conn.close()

            def readline(self, *a):
                try:
                    return r.readline(*a)
                except Exception:
                    if cortado or parar():
                        raise Cancelada("Cancelado.")
                    raise

            def read(self, *a):
                try:
                    return r.read(*a)
                except Exception:
                    if cortado or parar():
                        raise Cancelada("Cancelado.")
                    raise
        return _Resp()

    def pintar(self, prompt, negativo="", ancho=None, alto=None, semilla=None, timeout=900):
        """Los bytes del PNG que pinta el portátil. Lanza CasaError."""
        cuerpo = json.dumps({"prompt": str(prompt)[:1500], "negativo": str(negativo)[:600],
                             "ancho": ancho, "alto": alto, "semilla": semilla}).encode("utf-8")
        req = urllib.request.Request(self.url + "/pintar", data=cuerpo, method="POST",
                                     headers={"Content-Type": "application/json", "X-Kira-Token": self.token})
        try:
            with self._abrir(req, timeout=timeout) as r:
                datos = r.read(30_000_000)
                if r.getheader("Content-Type", "").startswith("image/"):
                    return datos
                raise CasaError(json.loads(datos.decode("utf-8")).get("error", "el pintor de casa falló"))
        except urllib.error.HTTPError as e:
            raise CasaError(f"El pintor de casa respondió {e.code}.")
        except CasaError:
            raise
        except Exception as e:
            raise CasaError(f"No se pudo pintar en casa: {e}")

    # ---- v2.84: la Kira COMPLETA del portátil (el móvil solo le manda órdenes) ----
    # ---- v3.00: fuera de casa, por Tailscale (solo sincronía y ver qué hace KiraOS) ----
    @property
    def url_fuera(self):
        """La dirección del portátil en Tailscale (100.x.y.z), que KiraOS le dio al móvil estando en casa."""
        return str(pc.leer_config().get("portatil_fuera") or "").rstrip("/")

    @property
    def via(self):
        """Por dónde se llegó a KiraOS la última vez: «casa» (la WiFi), «fuera» (Tailscale) o None."""
        return getattr(self, "_via", None)

    def _aprender_fuera(self, hola):
        """En casa, KiraOS dice su dirección de Tailscale: me la guardo para encontrarla luego fuera."""
        ip = str((hola or {}).get("fuera_ip") or "").strip()
        if not _es_tailscale(ip):
            return
        url = f"http://{ip}:{PUERTO_HTTP}"
        if url != self.url_fuera:
            try:
                pc.guardar_config(pc.leer_config().get("url"), self.token, portatil_fuera=url)
            except OSError:
                pass

    @property
    def nucleo_url(self):
        u = self.url_fuera if getattr(self, "_via", None) == "fuera" else self.url
        if not u:
            return ""
        try:
            esquema, resto = u.split("//", 1)
            host = resto.split("/", 1)[0].rsplit(":", 1)[0]
            return f"{esquema}//{host}:{PUERTO_NUCLEO}"
        except (ValueError, IndexError):
            return ""

    def _nucleo(self, ruta, datos=None, timeout=10, crudo=None, tipo="application/json", maximo=4_000_000, base=None):
        base = base or self.nucleo_url
        if not base or not self.token:
            raise CasaError("No sé dónde está el portátil.")
        cuerpo = crudo if crudo is not None else (None if datos is None else json.dumps(datos).encode("utf-8"))
        req = urllib.request.Request(base + ruta, data=cuerpo, method="GET" if cuerpo is None else "POST",
                                     headers={"X-Kira-Token": self.token, "Content-Type": tipo})
        try:
            with self._abrir(req, timeout=timeout) as r:
                return json.loads(r.read(maximo).decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                d = json.loads(e.read(20000).decode("utf-8"))
            except Exception:
                d = {}
            if e.code == 409:
                raise CasaError("El portátil está ocupado con: " + (d.get("haciendo") or "otra cosa") + ".")
            raise CasaError(d.get("error") or f"El portátil respondió {e.code}.")
        except CasaError:
            raise
        except Exception as e:
            raise CasaError(f"No llego al portátil: {e}")

    def nucleo_disponible(self, fuera=False):
        """¿Está la Kira completa del portátil? (cache 20 s, como el cerebro). Por defecto SOLO en la WiFi de casa (para
        las órdenes de trabajo y el cerebro, como siempre). Con fuera=True (sincronía y ver qué hace), si no está en
        casa la busca también por Tailscale. `via` dice por dónde se llegó."""
        t, ok = getattr(self, "_cache_nucleo", (0.0, None))
        if ok is None or self._reloj() - t >= 20:
            ok = False
            if self.disponible():
                try:
                    h = self._nucleo("/hola", timeout=2, base=self._base_casa())
                    ok = h.get("kira_nucleo") == 1
                    if ok:
                        self._via = "casa"
                        self._aprender_fuera(h)
                except CasaError:
                    ok = False
            self._cache_nucleo = (self._reloj(), ok)
        if ok:
            self._via = "casa"
            return True
        if not fuera or not self.url_fuera:
            return False
        t, okf = getattr(self, "_cache_fuera", (0.0, None))
        if okf is None or self._reloj() - t >= 20:
            okf = False
            try:
                okf = self._nucleo("/hola", timeout=4, base=self._base_fuera()).get("kira_nucleo") == 1
            except CasaError:
                okf = False
            self._cache_fuera = (self._reloj(), okf)
        if okf:
            self._via = "fuera"
        return okf

    def _base(self, u):
        try:
            esquema, resto = u.split("//", 1)
            host = resto.split("/", 1)[0].rsplit(":", 1)[0]
            return f"{esquema}//{host}:{PUERTO_NUCLEO}"
        except (ValueError, IndexError):
            return ""

    def _base_casa(self):
        return self._base(self.url) if self.url else ""

    def _base_fuera(self):
        return self._base(self.url_fuera) if self.url_fuera else ""

    def estado_nucleo(self):
        """v3.00: lo que hace KiraOS ahora (ocupada, en cola, en pausa…), o None."""
        try:
            return self._nucleo("/estado", timeout=4)
        except CasaError:
            return None

    def pausar_nucleo(self, si=True):
        """v3.00: los botones Pausar / Seguir del panel. Devuelve True si KiraOS lo recibió."""
        try:
            r = self._nucleo("/pausar" if si else "/seguir", {"si": bool(si)} if si else {})
            return bool(r.get("pausada")) == bool(si)
        except CasaError:
            return False

    def nucleo_hola(self):
        try:
            return self._nucleo("/hola", timeout=3)
        except CasaError:
            return None

    def orden(self, texto, al_paso=None, parar=None, cada=1.0, espera_max=6 * 3600, dormir=time.sleep, al_id=None):
        """Manda la orden a la Kira del portátil y espera: al_paso(fraccion, texto) con cada paso; parar() -> True
        la cancela allí. Devuelve la tarea final {estado, respuesta, codigo, nombre}. Lanza CasaError.
        v2.89: al_id(tid) nada más empezar, para apuntarlo (si se cierra la app, el resultado se recoge luego)."""
        tid = self._nucleo("/orden", {"orden": str(texto)})["id"]
        if al_id:
            try:
                al_id(tid)
            except Exception:
                pass
        vistos, fin, cancelada = 0, self._reloj() + espera_max, False
        while self._reloj() < fin:
            t = self._nucleo("/tarea?id=" + tid)
            av = t.get("avance") or []
            for linea in av[vistos:]:
                if al_paso:
                    al_paso(t.get("fraccion"), linea)
            vistos = len(av)
            if t.get("estado") not in ("en curso", "en cola"):     # v2.95: KiraOS encola; «en cola» = esperar
                return t
            if parar is not None and not cancelada and parar():
                cancelada = True
                try:
                    self._nucleo("/cancelar", {})
                except CasaError:
                    pass
            dormir(cada)
        return {"estado": "error", "respuesta": "El portátil ha tardado demasiado."}

    def orden_empezar(self, texto):
        """v2.87: manda la orden y NO espera (para las órdenes que el móvil apuntó fuera de casa). Devuelve el id."""
        return self._nucleo("/orden", {"orden": str(texto)})["id"]

    def tarea(self, tid):
        """Cómo va una orden mandada antes: {estado, fraccion, avance, respuesta, codigo…}."""
        return self._nucleo("/tarea?id=" + str(tid))

    def sincronizar(self, paquete, timeout=300):
        """v2.87: le da a KiraOS lo nuevo del móvil y recibe lo nuevo de KiraOS. Devuelve (resumen, respuesta)."""
        r = self._nucleo("/sincronizar", {"paquete": paquete}, timeout=timeout, maximo=40_000_000)
        if not r.get("ok"):
            raise CasaError(r.get("error") or "KiraOS no pudo sincronizar.")
        return r.get("resumen") or {}, r.get("respuesta") or {}

    def cancelar_nucleo(self):
        try:
            self._nucleo("/cancelar", {})
            return True
        except CasaError:
            return False

    def enviar_memoria(self, ruta_zip, timeout=1800):
        """Le pasa al portátil el paquete de memoria (.zip). Devuelve el texto de lo que recibió."""
        with open(ruta_zip, "rb") as f:
            datos = f.read()
        r = self._nucleo("/memoria", crudo=datos, timeout=timeout, tipo="application/zip")
        if not r.get("ok"):
            raise CasaError(r.get("error") or "El portátil no pudo guardar la memoria.")
        return r.get("texto") or "Memoria recibida."
