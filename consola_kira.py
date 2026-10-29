# -*- coding: utf-8 -*-
"""
consola_kira.py - La CONSOLA DE TRABAJO EN VIVO de Kira (lo que se ve en la terminal de la Sala Hacker).

Cuando Kira hace una tarea de las gordas (escribir un programa, un experimento, entrenar sus defensas…), va contando
aquí lo que hace: los pasos, el código tal y como lo va escribiendo (letra a letra), cada intento con su resultado de
las pruebas (✓ pasó / ✗ falló) y, al final, el resumen. La interfaz lee esto cada poco y lo pinta.

Es LÓGICA PURA (sin Kivy): se prueba en el PC. La interfaz (Kivy) solo lee `texto()` y mira `version()` para saber si
hay algo nuevo que pintar. Guardar las correcciones del dueño para que Kira mejore NO es cosa de aquí (eso lo hace el
núcleo en el baúl): aquí solo se MUESTRAN.

  c = Consola()
  c.empezar("escribir un programa que ordene una lista", pedido="ordena una lista")
  c.linea("Pensando el programa…")
  c.codigo_vivo("def ordena(x):\n    retu")        # va saliendo según lo escribe el cerebro
  c.intento("def ordena(x):\n    return sorted(x)", ok=True, motivo="")   # intento probado
  c.terminar("Programa listo y probado.")
"""
import threading
import time

MAX_LINEAS = 400              # no crecer sin fin: solo las últimas líneas
MAX_CODIGO = 20000            # tope del código que se muestra (para no reventar la pantalla)
MAX_INTENTOS = 30


class Consola:
    def __init__(self, reloj=time.monotonic):
        self._lock = threading.RLock()
        self._reloj = reloj
        self.titulo = ""
        self.pedido = ""              # lo que pidió el dueño (para que «Corregir» sepa a qué pedido atar la lección)
        self.activa = False
        self.lineas = []              # [(instante, texto)]
        self.codigo_vivo_txt = ""     # el código tal cual lo va escribiendo el cerebro (letra a letra)
        self.intentos = []            # [{"n", "codigo", "ok", "motivo"}]
        self.fin = ""
        self.detener_pedido = False   # el dueño tocó «Detener / Borrar proceso» (aviso visual; el corte real lo hace el núcleo)
        self._cambio = 0

    # ---- escribir (lo llama el núcleo/interfaz mientras trabaja) ----
    def empezar(self, titulo, pedido=""):
        with self._lock:
            self.titulo = " ".join(str(titulo or "").split())[:140]
            self.pedido = " ".join(str(pedido or "").split())[:200]
            self.activa = True
            self.lineas = []
            self.codigo_vivo_txt = ""
            self.intentos = []
            self.fin = ""
            self.detener_pedido = False
            self._cambio += 1
        self.linea("▶ " + (self.titulo or "trabajando"))
        return self

    def linea(self, texto):
        texto = " ".join(str(texto or "").split())
        if not texto:
            return
        with self._lock:
            if self.lineas and self.lineas[-1][1] == texto:   # no repitas la misma línea seguida
                return
            self.lineas.append((self._reloj(), texto))
            if len(self.lineas) > MAX_LINEAS:
                del self.lineas[:-MAX_LINEAS]
            self._cambio += 1

    def codigo_vivo(self, parcial):
        """El código según se va escribiendo (lo que el cerebro lleva hasta ahora)."""
        with self._lock:
            self.codigo_vivo_txt = str(parcial or "")[-MAX_CODIGO:]
            self._cambio += 1

    def intento(self, codigo, ok, motivo=""):
        """Un intento ya probado: su código y si pasó o falló (con el motivo)."""
        with self._lock:
            n = len(self.intentos) + 1
            self.intentos.append({"n": n, "codigo": str(codigo or "").rstrip()[:MAX_CODIGO],
                                  "ok": bool(ok), "motivo": " ".join(str(motivo or "").split())})
            if len(self.intentos) > MAX_INTENTOS:
                del self.intentos[:-MAX_INTENTOS]
            self.codigo_vivo_txt = ""
            self._cambio += 1
        self.linea(f"Intento {n}: " + ("✓ pasó las pruebas" if ok else "✗ falló" + (f": {motivo}" if motivo else "")))

    def terminar(self, texto=""):
        with self._lock:
            self.activa = False
            self.fin = " ".join(str(texto or "").split())
            self._cambio += 1
        if texto:
            self.linea("■ " + self.fin)

    def pedir_detener(self):
        """El dueño tocó Detener/Borrar: marca visual inmediata (el corte de verdad lo hace el núcleo con cancelar())."""
        with self._lock:
            self.detener_pedido = True
            self._cambio += 1
        self.linea("⏹ Me pediste parar…")

    # ---- leer (lo llama la interfaz para pintar) ----
    def version(self):
        """Sube cada vez que hay algo nuevo: la interfaz solo repinta si cambió."""
        with self._lock:
            return self._cambio

    def ultimo_codigo(self):
        """El código que toca enseñar ahora: lo que se está escribiendo, o el del último intento."""
        with self._lock:
            if self.codigo_vivo_txt:
                return self.codigo_vivo_txt
            return self.intentos[-1]["codigo"] if self.intentos else ""

    def ultimo_intento(self):
        with self._lock:
            return dict(self.intentos[-1]) if self.intentos else None

    def texto(self, explicacion=""):
        """Lo que se pinta en la terminal. `explicacion` (técnica, de la interfaz) va bajo el último código."""
        with self._lock:
            cab = ("KIRA//TRABAJO · " + self.titulo) if self.titulo else "KIRA//TRABAJO"
            partes = [cab, ""]
            partes.append("\n".join(t for _, t in self.lineas))
            cod = self.codigo_vivo_txt or (self.intentos[-1]["codigo"] if self.intentos else "")
            escribiendo = bool(self.codigo_vivo_txt)
            if cod:
                partes.append("")
                partes.append("——— CÓDIGO " + ("(escribiendo…)" if escribiendo else "———"))
                partes.append(cod + ("▌" if escribiendo else ""))
                if explicacion and not escribiendo:
                    partes.append("")
                    partes.append("——— CÓMO FUNCIONA (técnico) ———")
                    partes.append(str(explicacion))
            return "\n".join(partes).strip()
