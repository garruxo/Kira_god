# -*- coding: utf-8 -*-
"""
master_brain.py - Cerebro auxiliar (NO va en el APK; lo usa pasarela_extra.py en el PC o Termux)

Cambios respecto a la versión anterior:
- Sin __getattr__ "mágico": un método que no existe ahora da error, no se convierte en una orden.
- Las acciones de sensores (foto, vídeo, captura de pantalla, GPS) están DESACTIVADAS por defecto:
  hay que crear KiraMasterBrain(permitir_sensores=True) a mano, nunca desde la pasarela.
- La voz está desactivada por defecto (antes leía en voz alta cada respuesta, incluida la ubicación).
- Los archivos (memoria, fotos...) van a KIRA_DATA_DIR, no a la carpeta del proyecto (no acaban en el APK).
- Escritura atómica de JSON. generar_programa / sintetizar_audio ya no fingen hacer algo que no hacen.
"""
import json
import os
import subprocess
import threading
from datetime import datetime


def _dir_datos():
    d = os.environ.get("KIRA_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".kira")
    os.makedirs(d, exist_ok=True)
    return d


class KiraMasterBrain:
    def __init__(self, permitir_sensores=False, voz=False):
        self.permitir_sensores, self.voz = bool(permitir_sensores), bool(voz)
        self.dir = _dir_datos()
        self.f_memoria = os.path.join(self.dir, "kira_memoria.json")
        self.f_vocab = os.path.join(self.dir, "kira_vocabulario_aprendido.json")
        self.f_diseno = os.path.join(self.dir, "kira_diseno_conocimiento.json")
        self.memoria = self._leer(self.f_memoria, [])
        self.vocabulario = self._leer(self.f_vocab, {})
        self.conocimiento_diseno = self._leer(self.f_diseno, {
            "teoria_color": "Uso armónico de colores para transmitir emociones y jerarquía visual.",
            "tipografia": "Técnica de organizar la letra para asegurar legibilidad.",
            "composicion": "Distribución de elementos guiando la mirada."})
        self.diccionario_base = {
            "algoritmo": "Conjunto ordenado y finito de operaciones para hallar una solución.",
            "efímero": "Que dura por un período muy corto de tiempo.",
            "resiliencia": "Capacidad de adaptación frente a situaciones adversas."}

    # ---------- persistencia ----------
    @staticmethod
    def _leer(ruta, defecto):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            return datos if isinstance(datos, type(defecto)) else defecto
        except (OSError, ValueError):
            return defecto

    def _guardar(self, ruta, datos):
        try:
            tmp = ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            os.replace(tmp, ruta)
        except OSError as e:
            print(f"[!] No se pudo guardar {os.path.basename(ruta)}: {e}")

    # ---------- utilidades del dispositivo (Termux-API; solo si existen) ----------
    def _termux(self, args, timeout=8):
        try:
            return subprocess.check_output(args, timeout=timeout, stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except Exception:
            return None

    def hablar(self, texto):
        if not self.voz:
            return
        threading.Thread(target=lambda: self._termux(["termux-tts-speak", "-l", "es", str(texto)[:500]]), daemon=True).start()

    def obtener_bateria(self):
        out = self._termux(["termux-battery-status"])
        try:
            return f"Batería al {json.loads(out).get('percentage')}%."
        except Exception:
            return "[x] No pude leer la batería (hace falta Termux-API)."

    def obtener_espacio_disco(self):
        try:
            st = os.statvfs(self.dir)
            return f"Quedan {(st.f_bavail * st.f_frsize) / 1024 ** 3:.2f} GB libres en almacenamiento."
        except Exception:
            return "[x] No pude medir el espacio libre."

    def _sensor(self, nombre, args, destino=None):
        if not self.permitir_sensores:
            return f"[x] '{nombre}' está desactivado. Se activa solo creando el cerebro con permitir_sensores=True, en local."
        if destino:
            os.makedirs(os.path.join(self.dir, "media"), exist_ok=True)
            ruta = os.path.join(self.dir, "media", f"kira_{nombre}_{datetime.now():%Y%m%d_%H%M%S}{destino}")
            args = [a if a != "{ruta}" else ruta for a in args]
        out = self._termux(args, timeout=30)
        return f"[OK] {nombre} realizado." + (f" Guardado en {ruta}" if destino else "") if out is not None else f"[x] {nombre} falló (¿Termux-API?)."

    def tomar_foto(self, camara="0"):
        return self._sensor("foto", ["termux-camera-photo", "-c", str(camara) if str(camara) in ("0", "1") else "0", "{ruta}"], ".jpg")

    def grabar_video(self, camara="0"):
        return self._sensor("video", ["termux-camera-record", "-c", str(camara) if str(camara) in ("0", "1") else "0", "-f", "{ruta}"], ".mp4")

    def ver_pantalla(self):
        return self._sensor("pantalla", ["termux-screenshot", "{ruta}"], ".jpg")

    def obtener_ubicacion(self):
        if not self.permitir_sensores:
            return "[x] 'ubicación' está desactivada. Se activa solo con permitir_sensores=True, en local."
        out = self._termux(["termux-location", "-p", "gps"])
        try:
            d = json.loads(out)
            return f"Ubicación GPS: {d.get('latitude')}, {d.get('longitude')}."
        except Exception:
            return "[x] No pude obtener la ubicación (hace falta Termux-API)."

    # ---------- conversación básica ----------
    def procesar_inteligencia_propia(self, prompt):
        p = prompt.lower()
        for palabra, definicion in {**self.diccionario_base, **self.vocabulario}.items():
            if palabra in p and any(k in p for k in ("significa", "define", "busca")):
                return f"'{palabra}': {definicion}"
        if "aprende la palabra" in p or "define la palabra" in p:
            partes = prompt.split("'")
            if len(partes) >= 4:
                self.vocabulario[partes[1].strip().lower()] = partes[3].strip()[:500]
                self._guardar(self.f_vocab, self.vocabulario)
                return f"Palabra aprendida: '{partes[1].strip().lower()}'."
            return "Usa el formato: Aprende la palabra 'palabra' que significa 'definición'."
        for prefijo in ("acuérdate de ", "acuerdate de ", "recuerda "):
            if p.startswith(prefijo):
                recuerdo = prompt[len(prefijo):].strip()[:500]
                self.memoria.append({"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "texto": recuerdo})
                self.memoria = self.memoria[-500:]
                self._guardar(self.f_memoria, self.memoria)
                return f"Guardado en memoria: '{recuerdo}'."
        if any(k in p for k in ("qué recuerdas", "que recuerdas", "mis notas")):
            return "Últimos recuerdos:\n" + "\n".join(f"- {m['texto']}" for m in self.memoria[-5:]) if self.memoria else "Memoria vacía."
        if any(s in p.split() for s in ("hola", "buenas", "hey")):
            return "¡Hola! Soy Kira."
        return "[i] No entiendo esa orden todavía. Para crear funciones nuevas usa 'mejorar ...' en el panel."

    def process_universal_order(self, prompt=""):
        p = str(prompt).lower()
        if "batería" in p or "bateria" in p:
            r = self.obtener_bateria()
        elif any(k in p for k in ("espacio", "disco", "almacenamiento")):
            r = self.obtener_espacio_disco()
        elif any(k in p for k in ("ubicación", "ubicacion", "gps")):
            r = self.obtener_ubicacion()
        elif "grabar video" in p or "video trasero" in p:
            r = self.grabar_video("0")
        elif "foto" in p or "selfie" in p:
            r = self.tomar_foto("1" if ("delantera" in p or "selfie" in p) else "0")
        elif "pantalla" in p:
            r = self.ver_pantalla()
        else:
            r = self.procesar_inteligencia_propia(str(prompt))
        self.hablar(r)
        return r

    def generar_programa(self, prompt=""):
        return "[x] Este cerebro no genera programas. Usa 'mejorar <orden>' en el panel: la IA lo escribe y el laboratorio lo prueba."

    def sintetizar_audio(self, prompt=""):
        return "[x] La síntesis de audio no está implementada todavía."

    def procesar_diseno(self, prompt=""):
        p = str(prompt).lower()
        for concepto, teoria in self.conocimiento_diseno.items():
            if concepto in p or concepto.replace("_", " ") in p:
                return f"Sobre {concepto.replace('_', ' ')}: {teoria}"
        return "[i] Solo tengo apuntes de teoría del color, tipografía y composición."

    def procesar(self, prompt=""):
        return self.process_universal_order(prompt)

    procesar_orden = procesar
