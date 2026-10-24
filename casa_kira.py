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
"""
import json
import socket
import threading
import time
import urllib.error
import urllib.request

import pasarela_cliente as pc

PUERTO_HTTP = 8770
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
    def chat(self, system, mensajes, grande=False, max_tokens=1024, timeout=600, al_trozo=None, parar=None):
        import cerebro_ia_kira as ci
        if parar is not None and al_trozo is None:
            al_trozo = lambda _t: None
        if parar is not None and parar():
            raise Cancelada("Cancelado.")
        msgs = ([{"role": "system", "content": str(system)}] if system else []) + [
            {"role": m["role"], "content": m["content"] if isinstance(m["content"], list) else str(m["content"])}
            for m in mensajes]
        cuerpo = json.dumps({"messages": msgs, "max_tokens": int(max_tokens), "temperature": 0.6,
                             "stream": bool(al_trozo), "cache_prompt": True,
                             "kira_cerebro": "grande" if grande else "rapido",
                             "chat_template_kwargs": {"enable_thinking": False}}).encode("utf-8")
        req = urllib.request.Request(self.url + "/v1/chat/completions", data=cuerpo, method="POST",
                                     headers={"Content-Type": "application/json", "X-Kira-Token": self.token})
        try:
            with self._abrir(req, timeout=timeout) as r:
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
        except ci.Cancelada:
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
