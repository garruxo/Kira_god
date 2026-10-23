# -*- coding: utf-8 -*-
"""
tareas_kira.py - Kira hace UNA tarea larga cada vez y sabe cuánto le queda.

  - Gestor.empezar(tipo, descripción, relanzar): la tarea en marcha (programar, una mejora, un experimento, pintar,
    un juego realista, descargar o estudiar un PDF…). progreso(fracción, texto) cuando la tarea lo sabe.
  - estimacion(): % hecho y segundos que faltan. Si la tarea no dice cuánto lleva, se calcula con lo que tardaron
    las tareas de ese tipo otras veces (se aprende: media de las últimas). Nunca dice 100 % antes de acabar.
  - Si le pides otra cosa mientras trabaja, la interfaz te pregunta si la deja: interrumpir() la aparca (con lo
    necesario para volver a lanzarla) y, al terminar lo tuyo, siguiente() la devuelve para retomarla. Si dices que
    no, encolar(orden) guarda tu orden para cuando acabe.
Lógica pura (sin Kivy): se prueba en el PC. Las tareas aparcadas se guardan en disco (sobreviven a un cierre).
"""
import json
import os
import threading
import time

# lo que suele tardar cada tipo (segundos) hasta que Kira aprende lo suyo en tu móvil
DURACION_INICIAL = {"programa": 90, "mejora": 180, "experimento": 300, "juego_realista": 420, "imagen": 60,
                    "pdf": 40, "estudio": 120, "diseno": 60, "apk": 1500}
NOMBRES = {"programa": "escribir un programa", "mejora": "programar una mejora", "experimento": "un experimento",
           "juego_realista": "hacer un juego realista", "imagen": "pintar una imagen", "pdf": "un PDF",
           "estudio": "estudiar", "diseno": "un diseño", "apk": "hacer la app de un juego"}


def tiempo(seg):
    seg = max(0, int(round(seg)))
    if seg < 60:
        return f"{seg} s"
    m, s = divmod(seg, 60)
    if m < 60:
        return f"{m} min {s:02d} s" if m < 10 else f"{m} min"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min"


class Tarea:
    def __init__(self, tipo, descripcion, relanzar=None, datos=None, reloj=time.monotonic):
        self.tipo, self.descripcion = tipo, " ".join(str(descripcion or "").split())[:160]
        self.relanzar = relanzar                    # función sin parámetros que la vuelve a empezar
        self.datos = dict(datos or {})              # lo necesario para relanzarla tras un cierre (se guarda)
        self._reloj = reloj
        self.inicio = reloj()
        self.fraccion = None
        self.texto = ""
        self.interrumpida = False

    def transcurrido(self):
        return self._reloj() - self.inicio


class Gestor:
    def __init__(self, ruta=None, reloj=time.monotonic):
        self.ruta = ruta
        self._reloj = reloj
        self._lock = threading.Lock()
        self.actual = None
        self.aparcadas = []                         # [Tarea] interrumpidas, para retomarlas (la última, primero)
        self.cola = []                              # órdenes que pediste mientras trabajaba («no, sigue»)
        self.duraciones = {}
        self.de_antes = []                          # aparcadas en otra sesión (datos), para «sigue con lo que hacías»
        if ruta:
            try:
                with open(ruta, encoding="utf-8") as f:
                    d = json.load(f)
                self.duraciones = {k: [float(x) for x in v][-5:] for k, v in (d.get("duraciones") or {}).items()
                                   if isinstance(v, list)}
                self.de_antes = [a for a in d.get("aparcadas", []) if isinstance(a, dict) and a.get("tipo")]
            except (OSError, ValueError, TypeError, AttributeError):
                pass

    def _guardar(self):
        if not self.ruta:
            return
        try:
            tmp = self.ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"duraciones": self.duraciones,
                           "aparcadas": [{"tipo": t.tipo, "descripcion": t.descripcion, "datos": t.datos}
                                         for t in self.aparcadas] + self.de_antes}, f, ensure_ascii=False)
            os.replace(tmp, self.ruta)
        except OSError:
            pass

    # ---------- la tarea en marcha ----------
    def ocupado(self):
        return self.actual is not None

    def empezar(self, tipo, descripcion, relanzar=None, datos=None):
        with self._lock:
            self.actual = Tarea(tipo, descripcion, relanzar, datos, self._reloj)
            return self.actual

    def progreso(self, fraccion=None, texto=None):
        t = self.actual
        if t is None:
            return
        if fraccion is not None:
            try:
                f = float(fraccion)
                if 0 <= f <= 1:
                    t.fraccion = max(t.fraccion or 0.0, min(f, 0.99))   # nunca hacia atrás ni 100 % antes de acabar
            except (TypeError, ValueError):
                pass
        if texto:
            t.texto = " ".join(str(texto).split())[:120]

    def duracion_tipica(self, tipo):
        v = self.duraciones.get(tipo)
        if v:
            return sum(v) / len(v)
        return float(DURACION_INICIAL.get(tipo, 120))

    def estimacion(self):
        """(fracción 0..1, segundos que faltan) de la tarea en marcha, o None."""
        t = self.actual
        if t is None:
            return None
        pasado = t.transcurrido()
        tipica = self.duracion_tipica(t.tipo)
        por_tiempo = pasado / max(1.0, tipica)
        if t.fraccion is not None and t.fraccion >= 0.05:
            f = t.fraccion
            falta = pasado * (1 - f) / f
            if por_tiempo < 1:                       # al principio, la media de antes ayuda a no dar saltos
                falta = 0.5 * falta + 0.5 * max(0.0, tipica - pasado)
        else:
            f = min(0.95, por_tiempo * 0.9)           # sin datos de la tarea: según lo que suele tardar
            falta = max(0.0, tipica - pasado)
            if pasado > tipica:                      # ya tarda más de lo normal: «casi», sin inventar
                f = min(0.97, 0.9 + 0.07 * (1 - tipica / pasado))
                falta = max(5.0, pasado * 0.1)
        return max(0.0, min(0.99, f)), max(0.0, falta)

    def texto_barra(self):
        """«Programando «X» · 45 % · quedan ~1 min 20 s · paso: probando…»."""
        t, e = self.actual, self.estimacion()
        if t is None or e is None:
            return ""
        f, falta = e
        return (f"{NOMBRES.get(t.tipo, t.tipo).capitalize()}: «{t.descripcion[:50]}» · {round(f * 100)} % · "
                f"quedan ~{tiempo(falta)}" + (f" · {t.texto}" if t.texto else ""))

    def resumen(self):
        """Para decirlo en voz alta: «estoy con X (45 %, quedan unos 2 min)»."""
        t, e = self.actual, self.estimacion()
        if t is None or e is None:
            return ""
        return f"Estoy con {NOMBRES.get(t.tipo, t.tipo)}, «{t.descripcion[:60]}» ({round(e[0] * 100)} %, quedan unos {tiempo(e[1])})"

    def terminar(self, ok=True):
        """La tarea en marcha acabó (o se canceló). Devuelve la Tarea. Si acabó bien, se aprende cuánto tardó."""
        with self._lock:
            t, self.actual = self.actual, None
        if t is not None and ok and not t.interrumpida:
            v = self.duraciones.setdefault(t.tipo, [])
            v.append(round(t.transcurrido(), 1))
            del v[:-5]
            self._guardar()
        return t

    # ---------- interrumpir y retomar ----------
    def interrumpir(self):
        """Aparca la tarea en marcha para retomarla luego. Devuelve la Tarea (o None)."""
        t = self.actual
        if t is None:
            return None
        t.interrumpida = True
        with self._lock:
            self.aparcadas.append(t)
            self._guardar()
        return t

    def encolar(self, orden):
        self.cola.append(str(orden))

    def siguiente(self):
        """Qué toca cuando queda libre: ('orden', texto) de la cola, ('retomar', Tarea) de las aparcadas, o None."""
        if self.actual is not None:
            return None
        if self.cola:
            return "orden", self.cola.pop(0)
        if self.aparcadas:
            with self._lock:
                t = self.aparcadas.pop()
                self._guardar()
            return "retomar", t
        return None

    def de_otra_vez(self):
        """Las aparcadas de la vez anterior (si Kira se cerró): lista de dicts, y se olvidan."""
        d, self.de_antes = self.de_antes, []
        self._guardar()
        return d
