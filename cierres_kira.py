# -*- coding: utf-8 -*-
"""
cierres_kira.py - Por qué se cerró Kira y qué estaba haciendo (para no perder el trabajo).

  - motivo_android(cadena): Android 11+ apunta por qué cerró cada app (ServicioKira.ultimoCierre). Aquí se traduce
    a algo entendible («le faltaba memoria», «la cerró el ahorro de batería del fabricante»…) con qué hacer.
  - Trabajo: lo que Kira está haciendo (programar, experimentar, una mejora, un juego realista) se apunta en disco
    al empezar y se borra al terminar. Si al arrancar sigue ahí, es que la cerraron a mitad: Kira lo dice y con
    «sigue con lo que hacías» lo retoma.
Lógica pura (sin Kivy ni Android): se prueba en el PC.
"""
import json
import os
import re
import time

# ApplicationExitInfo.REASON_*  ->  (qué pasó, qué hacer)
MOTIVOS = {
    1: ("se cerró ella misma", ""),
    2: ("la paró el sistema de golpe (suele ser el ahorro de batería del fabricante o un «limpiador»)",
        "En Ajustes › Aplicaciones › Kira › Batería elige «Sin restricciones», y si tu móvil tiene «Apps en reposo» o "
        "«Optimización automática», saca a Kira de ahí."),
    3: ("Android la cerró porque le faltaba MEMORIA",
        "Mi cerebro ocupa mucha memoria: con otras apps grandes abiertas, Android cierra la que más gasta. Usa el "
        "cerebro ligero (2B) en Menú › Cerebro y oído, o cierra apps que no uses."),
    4: ("tuvo un fallo de Python", "Mira el aviso de la portada y mándaselo a Claude."),
    5: ("tuvo un fallo de una librería (cerebro, oído, pintor…)", "Mándale este aviso a Claude."),
    6: ("se quedó colgada y Android la cerró", "Mándale este aviso a Claude."),
    7: ("falló al arrancar", "Mándale este aviso a Claude."),
    8: ("se le quitó un permiso", "Vuelve a darle el permiso cuando lo pida."),
    9: ("gastaba demasiada batería o procesador en segundo plano y Android la cortó",
        "Ponle «Sin restricciones» en Ajustes › Aplicaciones › Kira › Batería."),
    10: ("la cerraste tú (o una app de limpieza)", "Si no fuiste tú, quita a Kira de las apps de limpieza."),
    11: ("se forzó su detención desde Ajustes", ""),
    12: ("se cerró algo de lo que dependía", ""),
    13: ("Android la cerró por otro motivo", "Ponle «Sin restricciones» en Ajustes › Aplicaciones › Kira › Batería."),
    14: ("Android la congeló en segundo plano", "Ponle «Sin restricciones» en Ajustes › Aplicaciones › Kira › Batería."),
    16: ("se actualizó", ""),
}
NORMALES = {1, 10, 11, 16}          # cierres que no son un problema (no se avisa de ellos)


def motivo_android(cadena, visto_ms=0):
    """(texto_para_el_usuario, instante_ms) del último cierre si es NUEVO (posterior a visto_ms) y es un problema;
    (None, instante_ms) si no hay que avisar. cadena = «motivo|detalle|instante|memoria_kb|importancia»."""
    partes = str(cadena or "").split("|")
    if len(partes) < 3 or not partes[0].strip().lstrip("-").isdigit():
        return None, visto_ms
    motivo, detalle = int(partes[0]), partes[1].strip()
    try:
        instante = int(partes[2])
    except ValueError:
        return None, visto_ms
    if instante <= visto_ms:
        return None, visto_ms
    if motivo in NORMALES:
        return None, instante
    que, hacer = MOTIVOS.get(motivo, ("Android la cerró", ""))
    memoria = ""
    try:
        kb = int(partes[3]) if len(partes) > 3 else 0
        if kb > 0:
            memoria = f" (estaba usando {kb / 1024 / 1024:.1f} GB de memoria)" if kb > 1024 * 1024 else \
                f" (estaba usando {kb / 1024:.0f} MB de memoria)"
    except ValueError:
        pass
    cuando = time.strftime("%d/%m %H:%M", time.localtime(instante / 1000.0))
    texto = f"La última vez ({cuando}) {que}{memoria}."
    if detalle:
        texto += f" Android dice: «{detalle[:160]}»."
    if hacer:
        texto += " " + hacer
    return texto, instante


def resumen_cierre(anterior):
    """Aviso CORTO y claro si la vez anterior la app se cerró de golpe (un fallo grave/nativo). Devuelve '' si no
    hubo cierre así. NO enseña el registro técnico entero (esa lista de módulos de Kivy, rutas, etc.): eso se queda
    en kira_cierre.log. Como mucho, saca UNA línea con el motivo de verdad (el error), si la encuentra."""
    texto = str(anterior or "")
    if "Fatal Python error" not in texto and "Segmentation fault" not in texto:
        return ""
    motivo = ""
    _SALTA = ("File ", "Current thread", "Thread ", "Extension modules", "Stack ", "  ")
    for linea in reversed(texto.splitlines()):
        l = linea.strip()
        if not l or l.startswith(_SALTA) or "kivy" in l.lower() or l.lower().startswith("0x"):
            continue
        if re.search(r"(Fatal Python error|Segmentation fault|[A-Za-z_]+Error\b|[A-Za-z_]+Exception\b|Killed)", l):
            motivo = l[:140]
            break
    aviso = "La vez anterior me cerré sola de golpe, pero ya he vuelto. Si te vuelve a pasar, dímelo."
    if motivo:
        aviso += f"\n(motivo técnico: {motivo})"
    return aviso


class Visto:
    """Hasta qué cierre ya se avisó (para no repetirlo en cada arranque)."""

    def __init__(self, ruta):
        self.ruta = ruta
        try:
            with open(ruta, encoding="utf-8") as f:
                self.ms = int(f.read().strip() or 0)
        except (OSError, ValueError):
            self.ms = 0

    def guardar(self, ms):
        self.ms = int(ms)
        try:
            with open(self.ruta, "w", encoding="utf-8") as f:
                f.write(str(self.ms))
        except OSError:
            pass


# =====================================================================================
#  TRABAJO EN CURSO
# =====================================================================================
NOMBRES = {"programa": "escribir un programa", "experimento": "un experimento", "mejora": "programar una mejora",
           "juego_realista": "hacer un juego realista"}
_SIGUE = re.compile(r"^(?:kira[\s,]+)?(?:sigue|contin[uú]a|retoma|reanuda)(?:\s+con)?(?:\s+lo\s+que\s+(?:hac[ií]as|"
                    r"estabas\s+haciendo)|\s+(?:el|la|lo)\s+(?:de\s+antes|trabajo|programa|experimento|mejora))?\s*[.!]*$",
                    re.I)


def pide_seguir(frase):
    return bool(_SIGUE.match(" ".join(str(frase or "").split())))


class Trabajo:
    def __init__(self, ruta):
        self.ruta = ruta
        self.interrumpido = None
        try:
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and d.get("tipo") in NOMBRES and str(d.get("pedido") or "").strip():
                self.interrumpido = {"tipo": d["tipo"], "pedido": str(d["pedido"])[:3000],
                                     "t": float(d.get("t") or 0)}
        except (OSError, ValueError, TypeError):
            pass
        self._borrar()                 # lo de la vez anterior queda en memoria (interrumpido), no en disco

    def _borrar(self):
        try:
            os.remove(self.ruta)
        except OSError:
            pass

    def empezar(self, tipo, pedido):
        try:
            tmp = self.ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"tipo": tipo, "pedido": str(pedido)[:3000], "t": time.time()}, f, ensure_ascii=False)
            os.replace(tmp, self.ruta)
        except OSError:
            pass

    def terminar(self):
        self._borrar()

    def aviso(self):
        """Lo que dice Kira al arrancar si la cerraron a mitad de algo; '' si no."""
        i = self.interrumpido
        if not i:
            return ""
        que = NOMBRES.get(i["tipo"], "algo")
        pedido = " ".join(i["pedido"].split("\n")[0].split())[:90]
        return (f"Me cerraron mientras estaba con {que} («{pedido}»). Dime «sigue con lo que hacías» y lo retomo.")

    def retomar(self):
        """El trabajo interrumpido (y se olvida), o None."""
        i, self.interrumpido = self.interrumpido, None
        return i
