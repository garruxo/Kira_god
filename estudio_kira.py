# -*- coding: utf-8 -*-
"""
estudio_kira.py - Kira ESTUDIA sola y guarda lo aprendido en su baúl de recuerdos (sin la API de Claude).

Dos fuentes, las dos solo de LECTURA (el texto se guarda, nunca se ejecuta):
  - Wikipedia en español (dominio fijo): «estudia: redes neuronales» lee los resúmenes de los artículos que mejor
    encajan y los guarda con su fuente.
  - La documentación de Python que ya trae el propio móvil (sin internet): «estudia python: json» guarda qué hace
    cada función del módulo y cómo se llama. Solo módulos de una lista segura (importarlos no hace nada raro).
Además hay un PLAN DE ESTUDIO (programación, sistemas, redes, ciberseguridad, IA…) que Kira recorre poco a poco
cuando le dices «aprende sola»: un tema cada cierto tiempo, mientras la app está abierta.
Y su SABER DE INGENIERÍA (recetas_ingenieria_kira: algoritmos, estructuras de datos, sistemas operativos, redes, bases
de datos, compiladores, seguridad defensiva, IA…): «estudia ingeniería» lo guarda en el baúl sin internet, y al
«aprender sola» lo hace la primera vez.

Lo bajado de internet no se mezcla en lo que se le pide a una IA (así una web no puede darle órdenes a Kira).
"""
import importlib
import inspect
import json
import os
import re
import threading
import time
import urllib.parse

MAX_RESUMEN = 1500
POR_TEMA = 3                    # artículos por tema del plan
INTERVALO = 10 * 60             # segundos entre temas cuando aprende sola
FUENTE_INGENIERIA = "saber de ingeniería de Kira"   # fichas propias (recetas_ingenieria_kira), sin internet

PLAN = [
    "Programación", "Python", "Algoritmo", "Estructura de datos", "Programación orientada a objetos",
    "Recursión", "Expresión regular", "JSON", "Base de datos", "SQL", "Sistema operativo", "Linux", "Android",
    "Compilador", "Git", "Control de versiones", "Red de computadoras", "Protocolo de comunicaciones",
    "Protocolo de control de transmisión", "Hypertext Transfer Protocol", "Sistema de nombres de dominio",
    "Criptografía", "Seguridad informática", "Malware", "Cortafuegos (informática)", "Phishing",
    "Autenticación de dos factores", "Inteligencia artificial", "Aprendizaje automático", "Red neuronal artificial",
    "Procesamiento de lenguajes naturales", "Modelo extenso de lenguaje", "Interfaz de usuario",
    "Prueba de software", "Depuración de programas", "Complejidad computacional", "Unicode",
    "Codificación de vídeo", "Audio digital", "FFmpeg",
]

MODULOS_PYTHON = [
    "json", "re", "math", "random", "statistics", "datetime", "time", "collections", "itertools", "functools",
    "string", "textwrap", "unicodedata", "decimal", "fractions", "heapq", "bisect", "dataclasses", "enum",
    "typing", "pathlib", "os.path", "urllib.parse", "hashlib", "hmac", "base64", "csv", "sqlite3", "struct",
    "zipfile", "threading", "queue", "logging", "copy", "pprint", "difflib", "html", "uuid", "secrets",
    "operator", "contextlib", "abc", "array", "calendar", "locale", "gzip", "io",
]


def _limpio(t, maximo):
    t = re.sub(r"<[^>]{0,200}>", "", str(t or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= maximo else t[:maximo].rsplit(" ", 1)[0] + "…"


def _pedir_wikipedia(url, timeout=10):
    """JSON de la Wikipedia en español (solo ese dominio)."""
    if not url.startswith("https://es.wikipedia.org/"):
        raise ValueError("dominio no permitido")
    import urllib.request
    import red_kira
    req = urllib.request.Request(url, headers={"User-Agent": "KiraApp/1.0 (asistente personal)",
                                               "Accept": "application/json"})
    with red_kira.abrir(req, timeout=timeout) as r:
        return json.loads(r.read(400_000).decode("utf-8"))


class Estudiante:
    def __init__(self, recuerdos, ruta_estado, pedir=_pedir_wikipedia, reloj=time.time):
        self.recuerdos = recuerdos
        self.ruta = ruta_estado
        self._pedir = pedir
        self._reloj = reloj
        self._lock = threading.Lock()
        self._hilo = None
        self._parar = threading.Event()
        self.ultimo_error = ""
        try:
            with open(ruta_estado, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        d = d if isinstance(d, dict) else {}
        self.sola = bool(d.get("sola", False))
        self.indice = int(d.get("indice", 0)) if str(d.get("indice", 0)).isdigit() else 0
        self.aprendidos = int(d.get("aprendidos", 0)) if str(d.get("aprendidos", 0)).isdigit() else 0
        self.ultimo = str(d.get("ultimo", ""))[:120]
        self.ingenieria = int(d.get("ingenieria", 0)) if str(d.get("ingenieria", 0)).isdigit() else 0

    def _guardar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"sola": self.sola, "indice": self.indice, "aprendidos": self.aprendidos,
                       "ultimo": self.ultimo, "ingenieria": self.ingenieria}, f, ensure_ascii=False)
        os.replace(tmp, self.ruta)

    # ---------- Wikipedia ----------
    def estudiar(self, tema, n=5):
        """Lee los resúmenes de los n artículos que mejor encajan con 'tema' y los guarda. Devuelve los títulos."""
        tema = _limpio(tema, 100)
        if len(tema) < 2:
            raise ValueError("Dime qué quieres que estudie.")
        q = urllib.parse.quote(tema)
        res = self._pedir("https://es.wikipedia.org/w/api.php?action=query&list=search&format=json"
                          f"&srlimit={int(n)}&srsearch={q}")
        titulos = [str(x.get("title", "")) for x in (res.get("query", {}) or {}).get("search", []) if x.get("title")]
        aprendidos = []
        for titulo in titulos[:n]:
            try:
                s = self._pedir("https://es.wikipedia.org/api/rest_v1/page/summary/"
                                + urllib.parse.quote(titulo.replace(" ", "_"), safe=""))
            except Exception:
                continue
            if s.get("type") == "disambiguation":
                continue
            texto = _limpio(s.get("extract", ""), MAX_RESUMEN)
            if len(texto) < 40:
                continue
            fuente = "https://es.wikipedia.org/wiki/" + urllib.parse.quote(titulo.replace(" ", "_"), safe="")
            antes = self.recuerdos.total()
            if self.recuerdos.guardar(texto, tema=titulo, fuente=fuente) and self.recuerdos.total() > antes:
                aprendidos.append(titulo)
        with self._lock:
            self.aprendidos += len(aprendidos)
            self.ultimo = tema
            self._guardar()
        return aprendidos

    # ---------- documentación de Python (sin internet) ----------
    def estudiar_python(self, nombre=None):
        """Guarda la documentación de un módulo de la lista segura (o de todos si nombre es None).
        Devuelve cuántas fichas nuevas guardó."""
        nombres = MODULOS_PYTHON if nombre is None else [str(nombre).strip().lower()]
        for m in nombres:
            if m not in MODULOS_PYTHON:
                raise ValueError(f"«{m}» no está en mi lista de módulos seguros. Puedo estudiar: "
                                 + ", ".join(MODULOS_PYTHON[:12]) + "…")
        nuevas = 0
        for m in nombres:
            try:
                mod = importlib.import_module(m)
            except Exception:
                continue
            doc = inspect.getdoc(mod) or ""
            if doc:
                nuevas += self._ficha(f"python {m}", f"Módulo {m} de Python: " + doc.split("\n\n")[0])
            for nom, obj in sorted(vars(mod).items()):
                if nom.startswith("_") or not (inspect.isfunction(obj) or inspect.isbuiltin(obj) or inspect.isclass(obj)):
                    continue
                om = getattr(obj, "__module__", None) or mod.__name__
                if om not in (m, mod.__name__, "_" + m, "_" + mod.__name__):
                    continue                               # lo que el módulo importa de otros, no
                d = inspect.getdoc(obj) or ""
                if not d:
                    continue
                try:
                    firma = str(inspect.signature(obj))
                except (TypeError, ValueError):
                    firma = "(…)"
                tipo = "clase" if inspect.isclass(obj) else "función"
                nuevas += self._ficha(f"python {m}.{nom}",
                                      f"{m}.{nom}{firma} ({tipo} de Python): " + d.split("\n\n")[0])
        with self._lock:
            self.aprendidos += nuevas
            self.ultimo = "python " + (nombre or "(todo)")
            self._guardar()
        return nuevas

    def _ficha(self, tema, texto, fuente="documentación de Python"):
        antes = self.recuerdos.total()
        self.recuerdos.guardar(_limpio(texto, MAX_RESUMEN), tema=tema, fuente=fuente)
        return 1 if self.recuerdos.total() > antes else 0

    # ---------- ingeniería informática (saber propio de Kira, sin internet) ----------
    def estudiar_ingenieria(self):
        """Guarda en el baúl las fichas de recetas_ingenieria_kira (algoritmos, estructuras de datos, sistemas,
        redes, bases de datos, compiladores, seguridad defensiva, IA…). Devuelve (fichas nuevas, total de fichas).
        Es texto escrito y revisado a mano en el proyecto: no viene de internet."""
        import recetas_ingenieria_kira as ri
        fichas = ri.fichas()
        nuevas = sum(self._ficha(tema, texto, fuente=FUENTE_INGENIERIA) for tema, texto in fichas)
        with self._lock:
            self.aprendidos += nuevas
            self.ingenieria = len(fichas)
            self.ultimo = "ingeniería informática"
            self._guardar()
        return nuevas, len(fichas)

    def ingenieria_pendiente(self):
        try:
            import recetas_ingenieria_kira as ri
            return self.ingenieria < len(ri.fichas())
        except ImportError:
            return False

    # ---------- plan de estudio ----------
    def paso(self):
        """Estudia el siguiente tema del plan. Devuelve (tema, títulos aprendidos)."""
        with self._lock:
            tema = PLAN[self.indice % len(PLAN)]
            self.indice += 1
            self._guardar()
        return tema, self.estudiar(tema, n=POR_TEMA)

    def poner_sola(self, activo, intervalo=INTERVALO):
        self.sola = bool(activo)
        self._guardar()
        if self.sola:
            self.arrancar(intervalo)
        else:
            self._parar.set()

    def arrancar(self, intervalo=INTERVALO):
        """Hilo de fondo: un tema del plan cada 'intervalo' segundos mientras la app esté abierta."""
        if not self.sola or (self._hilo and self._hilo.is_alive()):
            return
        self._parar = threading.Event()

        def bucle(parar=self._parar):
            try:
                if self.ingenieria_pendiente():          # lo propio primero: no necesita internet
                    self.estudiar_ingenieria()
            except Exception as e:
                self.ultimo_error = str(e)[:200]
            while not parar.is_set() and self.sola:
                try:
                    self.paso()
                    self.ultimo_error = ""
                except Exception as e:                  # sin internet, etc.: lo intenta en la siguiente vuelta
                    self.ultimo_error = str(e)[:200]
                parar.wait(intervalo)
        self._hilo = threading.Thread(target=bucle, daemon=True, name="kira-estudia")
        self._hilo.start()

    def estado_texto(self):
        hecho = min(self.indice, len(PLAN))
        return (f"Estudio: {self.aprendidos} ficha(s) aprendidas por mi cuenta. Plan: {hecho} de {len(PLAN)} temas"
                f"{' (vuelta ' + str(self.indice // len(PLAN) + 1) + ')' if self.indice >= len(PLAN) else ''}.\n"
                f"Aprender sola: {'SÍ, un tema cada ' + str(INTERVALO // 60) + ' min mientras la app está abierta' if self.sola else 'no'}."
                + (f"\nIngeniería informática: {self.ingenieria} fichas en el baúl." if self.ingenieria else
                   "\nIngeniería informática: aún no la he guardado («estudia ingeniería»).")
                + (f"\nÚltimo: {self.ultimo}." if self.ultimo else "")
                + (f"\nÚltimo problema: {self.ultimo_error}" if self.ultimo_error else "")
                + "\nÓrdenes: «estudia: tema», «estudia python: json», «estudia python», «estudia ingeniería», "
                  "«aprende sola», «deja de aprender», «plan de estudio».")

    def texto_plan(self):
        lineas = []
        for i, t in enumerate(PLAN):
            marca = "[hecho]" if i < self.indice else ("[ahora]" if i == self.indice % len(PLAN) else "       ")
            lineas.append(f"{marca} {t}")
        return "Plan de estudio:\n" + "\n".join(lineas)
