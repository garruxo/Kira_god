# -*- coding: utf-8 -*-
"""
cerebro_ia_kira.py - De dónde saca Kira sus respuestas de IA: un MODELO LOCAL o la API de Claude (solo librería estándar).

  local  : un modelo pequeño (2-4B parámetros) corriendo con llama.cpp («llama-server») en el MISMO móvil (Termux) o en
           otro equipo de casa. Kira le habla por http://127.0.0.1:8080 con el formato OpenAI (/v1/chat/completions).
           Sin internet y sin pagar API. Más lento y menos listo que Claude.
  claude : la API de Claude (necesita clave e internet).
  auto   : (por defecto) usa el local si está encendido; si no, Claude si hay clave.

Configuración en <datos>/cerebro.json: {"motor": "auto"|"local"|"claude", "url": "http://127.0.0.1:8080"}.
Se cambia con las órdenes «cerebro local», «cerebro claude», «cerebro auto», «cerebro url: …» y «cerebro» (estado).
Lo que hace la IA no cambia: el modelo local también pasa por las mismas reglas (las mejoras se prueban en el
laboratorio y solo se aplican con tu doble confirmación).
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

LOCAL = "\x00cerebro-local\x00"          # marca interna que se pasa en lugar de la clave cuando responde el modelo local
MOTORES = ("auto", "local", "claude")
URL_DEFECTO = "http://127.0.0.1:8080"
MAX_TOKENS_LOCAL = 1024                  # un modelo de móvil va a ~3-10 palabras/s: respuestas largas tardarían minutos
_URL_OK = re.compile(r"^https?://[A-Za-z0-9.\-]+(:\d{1,5})?/?$")
_PENSAMIENTO = re.compile(r"<think>.*?</think>\s*", re.S | re.I)


class CerebroError(RuntimeError):
    pass


def visible_parcial(texto):
    """Lo que se puede enseñar YA de una respuesta a medias: sin el razonamiento <think>… (ni el que aún no se cerró)."""
    t = _PENSAMIENTO.sub("", str(texto or ""))
    i = t.lower().find("<think>")
    return (t[:i] if i >= 0 else t).lstrip()


def leer_sse(respuesta, extraer, al_trozo, tope=2_000_000):
    """Lee un flujo «data: …» línea a línea. extraer(dict) -> trocito de texto. Llama al_trozo(texto_visible)."""
    total, visto, leidos = "", "", 0
    while True:
        linea = respuesta.readline()
        if not linea:
            break
        leidos += len(linea)
        if leidos > tope:
            break
        linea = linea.decode("utf-8", "replace").strip()
        if not linea.startswith("data:"):
            continue
        dato = linea[5:].strip()
        if dato == "[DONE]":
            break
        try:
            trozo = extraer(json.loads(dato))
        except (ValueError, KeyError, IndexError, TypeError):
            continue
        if trozo:
            total += trozo
            v = visible_parcial(total)
            if v != visto:
                visto = v
                try:
                    al_trozo(v)
                except Exception:
                    pass
    return total


def limpiar_respuesta(texto):
    """Quita el «razonamiento» que algunos modelos (Qwen y similares) escriben entre <think>…</think>."""
    t = _PENSAMIENTO.sub("", str(texto or ""))
    if "<think>" in t.lower():                     # se cortó a mitad del razonamiento: no hay respuesta útil
        t = t[: t.lower().index("<think>")]
    return t.strip()


class Cerebro:
    def __init__(self, dir_datos, abrir=None, reloj=time.monotonic):
        self.ruta = os.path.join(dir_datos, "cerebro.json")
        self._abrir = abrir or urllib.request.urlopen
        self._reloj = reloj
        self._cache = (0.0, None)                  # (instante, disponible)
        d = {}
        try:
            with open(self.ruta, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        d = d if isinstance(d, dict) else {}
        self.motor = d.get("motor") if d.get("motor") in MOTORES else "auto"
        # para PROGRAMAR mejoras: en «auto» se prefiere Claude (escribe mejor código) si hay clave; si no, el local
        self.codigo = d.get("codigo") if d.get("codigo") in MOTORES else "auto"
        self.url = d.get("url") if isinstance(d.get("url"), str) and _URL_OK.match(d.get("url", "")) else URL_DEFECTO

    def _guardar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"motor": self.motor, "url": self.url, "codigo": self.codigo}, f, ensure_ascii=False)
        os.replace(tmp, self.ruta)

    def poner_motor(self, motor):
        if motor not in MOTORES:
            raise CerebroError(f"Motor desconocido: {motor}. Usa: {', '.join(MOTORES)}.")
        self.motor = motor
        self._guardar()

    def poner_codigo(self, motor):
        if motor not in MOTORES:
            raise CerebroError(f"Motor desconocido: {motor}. Usa: {', '.join(MOTORES)}.")
        self.codigo = motor
        self._guardar()

    def poner_url(self, url):
        url = str(url).strip().rstrip("/")
        if not _URL_OK.match(url):
            raise CerebroError("Dirección no válida. Ejemplo: http://127.0.0.1:8080")
        self.url = url
        self._cache = (0.0, None)
        self._guardar()

    # ---- ¿está encendido el modelo local? ----
    def local_disponible(self, forzar=False):
        t, ok = self._cache
        if not forzar and ok is not None and self._reloj() - t < 20:
            return ok
        ok = False
        for ruta in ("/health", "/v1/models"):
            try:
                with self._abrir(urllib.request.Request(self.url + ruta, method="GET"), timeout=2) as r:
                    if 200 <= getattr(r, "status", 200) < 300:
                        cuerpo = r.read(20000).decode("utf-8", "replace")
                        ok = ruta == "/v1/models" or '"ok"' in cuerpo or "ok" in cuerpo.lower()
                        if ok:
                            break
            except Exception:
                continue
        self._cache = (self._reloj(), ok)
        return ok

    def elegir(self, clave_api, tarea="general"):
        """'local' | 'claude' | None según el motor configurado, la tarea, lo que esté encendido y si hay clave.
        tarea='codigo' (programar mejoras): en modo «auto» se prefiere Claude si hay clave, porque un modelo pequeño
        se equivoca más programando; «cerebro mejoras local|claude» lo fija. «cerebro local» manda siempre."""
        if tarea == "codigo" and self.motor == "auto":
            if self.codigo == "claude" or (self.codigo == "auto" and clave_api):
                if clave_api:
                    return "claude"
                if self.codigo == "claude":
                    return None
            if self.codigo == "local":
                return "local" if self.local_disponible() else None
        if self.motor == "claude":
            return "claude" if clave_api else None
        if self.local_disponible():
            return "local"
        if self.motor == "local":
            return None
        return "claude" if clave_api else None

    def motivo_sin_cerebro(self, clave_api):
        if self.motor == "local":
            return (f"El cerebro local no responde en {self.url}. Arráncalo en Termux (llama-server) o di «cerebro auto».")
        if self.motor == "claude":
            return "Falta la clave de la API. Usa: config clave: TU_CLAVE (o di «cerebro auto» para usar el modelo local)."
        return ("No hay cerebro de IA: ni el modelo local está encendido ni hay clave de la API. Arranca llama-server en "
                "el móvil (ver «cómo cerebro local») o pon la clave con «config clave: …».")

    # ---- hablar con el modelo local (formato OpenAI de llama-server) ----
    def chat_local(self, system, mensajes, max_tokens=512, timeout=300, al_trozo=None):
        """Respuesta del modelo local. Con al_trozo(texto_hasta_ahora) la respuesta va llegando palabra a palabra."""
        msgs = ([{"role": "system", "content": str(system)}] if system else []) + [
            {"role": m["role"], "content": m["content"] if isinstance(m["content"], list) else str(m["content"])}
            for m in mensajes]
        cuerpo = json.dumps({"messages": msgs, "max_tokens": int(min(max_tokens, MAX_TOKENS_LOCAL)),
                             "temperature": 0.6, "stream": bool(al_trozo)}).encode("utf-8")
        req = urllib.request.Request(self.url + "/v1/chat/completions", data=cuerpo, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with self._abrir(req, timeout=timeout) as r:
                if al_trozo:
                    texto = leer_sse(r, lambda d: (d["choices"][0].get("delta") or {}).get("content") or "", al_trozo)
                    datos = None
                else:
                    datos = json.loads(r.read(2_000_000).decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise CerebroError(f"El modelo local respondió {e.code}.")
        except Exception as e:
            self._cache = (0.0, None)
            raise CerebroError(f"No se pudo hablar con el modelo local: {e}")
        if datos is not None:
            try:
                texto = datos["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise CerebroError("El modelo local devolvió una respuesta sin texto.")
        texto = limpiar_respuesta(texto)
        if not texto:
            raise CerebroError("El modelo local no llegó a responder (respuesta vacía).")
        return texto

    def ver_imagen(self, ruta, pregunta, max_tokens=400, timeout=300, al_trozo=None):
        """Los OJOS: el modelo local mira una imagen (necesita el cerebro encendido con sus ojos, --mmproj)."""
        import base64
        try:
            with open(ruta, "rb") as f:
                datos = f.read(12_000_000)
        except OSError as e:
            raise CerebroError(f"No encuentro la imagen: {e}")
        tipo = "image/png" if datos[:4] == b"\x89PNG" else "image/jpeg"
        url = f"data:{tipo};base64," + base64.b64encode(datos).decode("ascii")
        contenido = [{"type": "image_url", "image_url": {"url": url}}, {"type": "text", "text": str(pregunta)}]
        return self.chat_local("Eres Kira. Responde en español, claro y breve.",
                               [{"role": "user", "content": contenido}], max_tokens=max_tokens, timeout=timeout,
                               al_trozo=al_trozo)

    def estado_texto(self, clave_api):
        local = self.local_disponible(forzar=True)
        uso = self.elegir(clave_api)
        return (f"Cerebro de IA: modo «{self.motor}».\n"
                f"  Modelo local ({self.url}): {'ENCENDIDO' if local else 'apagado'}\n"
                f"  API de Claude: {'clave guardada' if clave_api else 'sin clave'}\n"
                f"  Ahora mismo respondería: {({'local': 'el modelo local (sin internet)', 'claude': 'Claude (API)'}).get(uso, 'nadie')}\n"
                f"  Para programar mejoras: {({'local': 'el modelo local', 'claude': 'Claude (API)'}).get(self.elegir(clave_api, 'codigo'), 'nadie')} "
                f"(preferencia «{self.codigo}»)\n"
                "Órdenes: «cerebro local», «cerebro claude», «cerebro auto», «cerebro url: http://IP:8080», "
                "«cerebro mejoras auto|local|claude».")
