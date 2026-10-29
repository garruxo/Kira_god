# -*- coding: utf-8 -*-
"""
defensa_juego_kira.py - El juego de PRÁCTICA DE DEFENSA de Kira (en el móvil), SOLO DEFENSIVO.

Kira entrena a reconocer amenazas con situaciones INVENTADAS (sin tocar tu red, sin internet). Es la "cabeza" del
juego del laberinto en primera persona: cada obstáculo del pasillo es una amenaza (puerta trasera, fuerza bruta,
escaneo de puertos, enlace trampa…) o tráfico sano, y Kira (o tú) decide COMBATIR o DEJAR PASAR. Gana puntos si
combate las de verdad y si NO da falsas alarmas con el tráfico sano.

Honesto y dentro de las reglas:
  - Solo defensa: cada amenaza trae CÓMO SE COMBATE (cerrar/cortar/avisar/aprender), nunca cómo se fabrica.
  - Lo que "evoluciona" al entrenar son los DATOS (los umbrales), nunca el código solo. Meter algo aprendido en los
    juegos de Kira sigue necesitando sus dos toques (eso lo hace el núcleo/interfaz, no este módulo).
  - Datos inventados y offline: aquí no hay ninguna red real.

Es LÓGICA PURA (sin Kivy): se prueba en el PC. La pantalla (laberinto Matrix) la pinta la interfaz.
"""
import json
import os
import random

# --- catálogo de amenazas: qué las delata y CÓMO las combate Kira (defensivo) ---
AMENAZAS = {
    "puerta_trasera": {
        "nombre": "puerta trasera",
        "pista": "una conexión oculta intentando entrar al núcleo sin permiso",
        "combate": ["Cierro el puerto por el que entra", "Corto la conexión oculta y la bloqueo",
                    "Te aviso y la apunto para reconocerla antes"]},
    "fuerza_bruta": {
        "nombre": "fuerza bruta",
        "pista": "muchísimos intentos de contraseña seguidos",
        "combate": ["Freno los intentos (los voy espaciando)", "Bloqueo el origen un rato",
                    "Aviso de que reforcéis esa contraseña"]},
    "escaneo_puertos": {
        "nombre": "escaneo de puertos",
        "pista": "alguien tocando muchos puertos buscando una rendija",
        "combate": ["No respondo a los puertos que no uso", "Apunto quién escanea", "Te aviso del sondeo"]},
    "enlace_trampa": {
        "nombre": "enlace trampa",
        "pista": "un enlace que quiere engañarte (phishing)",
        "combate": ["No lo abro", "Marco el enlace como peligroso", "Te aviso de la señal de engaño"]},
    "trafico_sano": {
        "nombre": "tráfico sano",
        "pista": "movimiento normal y de confianza",
        "combate": ["Lo dejo pasar: no es una amenaza"]},
}
ORDEN = ["puerta_trasera", "fuerza_bruta", "escaneo_puertos", "enlace_trampa", "trafico_sano"]

UMBRALES_INICIO = {"trafico": 2.5, "logins": 25, "puertos": 20}   # a propósito flojos: al entrenar se afinan
LIMITES = {"trafico": (1.4, 4.0), "logins": (6, 60), "puertos": (5, 50)}
PASO = {"trafico": 0.2, "logins": 3, "puertos": 3}


def _clamp(v, lim):
    return max(lim[0], min(lim[1], v))


class Defensa:
    """La 'cabeza' de Kira para defender: sus umbrales (los DATOS que aprende). Se guardan en disco."""

    def __init__(self, ruta=None, umbrales=None):
        self.ruta = ruta
        self.umbrales = dict(UMBRALES_INICIO)
        self.partidas = 0
        if umbrales:
            self.umbrales.update({k: float(v) for k, v in umbrales.items() if k in self.umbrales})
        if ruta and os.path.exists(ruta):
            try:
                with open(ruta, encoding="utf-8") as f:
                    d = json.load(f)
                self.umbrales.update({k: float(v) for k, v in (d.get("umbrales") or {}).items() if k in self.umbrales})
                self.partidas = int(d.get("partidas", 0))
            except (OSError, ValueError, TypeError):
                pass

    def guardar(self):
        if not self.ruta:
            return
        try:
            tmp = self.ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"umbrales": self.umbrales, "partidas": self.partidas}, f)
            os.replace(tmp, self.ruta)
            try:
                os.chmod(self.ruta, 0o600)
            except OSError:
                pass
        except OSError:
            pass


def generar(semilla):
    """Una situación inventada (un obstáculo del pasillo): o una amenaza o tráfico sano, con algo de ruido para que
    no sea trivial (así entrenar sirve de algo)."""
    r = random.Random(semilla if isinstance(semilla, (int, float, str, bytes)) else repr(semilla))
    tipo = r.choice(ORDEN)
    esc = {"trafico": round(r.uniform(0.3, 1.5), 2), "logins": r.randint(0, 8), "puertos": r.randint(0, 6),
           "oculto": False, "enlace": False}
    if tipo == "puerta_trasera":
        esc.update(oculto=True, trafico=round(r.uniform(1.6, 5.0), 2), logins=r.randint(10, 60))
    elif tipo == "fuerza_bruta":
        esc.update(logins=r.randint(16, 90), trafico=round(r.uniform(1.0, 2.5), 2))
    elif tipo == "escaneo_puertos":
        esc.update(puertos=r.randint(12, 60), trafico=round(r.uniform(0.8, 2.0), 2))
    elif tipo == "enlace_trampa":
        esc.update(enlace=True)
    esc["tipo"] = tipo
    esc["ataque"] = tipo != "trafico_sano"
    return esc


def decidir(defensa, esc):
    """Qué ve Kira con sus umbrales de AHORA: si es amenaza, de qué tipo, por qué, y cómo la combatiría."""
    u = defensa.umbrales
    motivos = []
    tipo = None
    if esc.get("enlace"):
        tipo = tipo or "enlace_trampa"
        motivos.append("un enlace sospechoso")
    if esc.get("oculto") and esc.get("trafico", 0) >= 1.5:
        tipo = tipo or "puerta_trasera"
        motivos.append("una conexión oculta")
    if esc.get("logins", 0) >= u["logins"]:
        tipo = tipo or "fuerza_bruta"
        motivos.append(f"{esc['logins']} intentos de contraseña")
    if esc.get("puertos", 0) >= u["puertos"]:
        tipo = tipo or "escaneo_puertos"
        motivos.append(f"{esc['puertos']} puertos tocados")
    if esc.get("trafico", 0) >= u["trafico"]:
        tipo = tipo or "puerta_trasera"
        motivos.append(f"tráfico x{esc['trafico']}")
    es_amenaza = bool(motivos)
    tipo = tipo if es_amenaza else "trafico_sano"
    info = AMENAZAS[tipo]
    return {"es_amenaza": es_amenaza, "tipo": tipo, "nombre": info["nombre"], "pista": info["pista"],
            "motivo": " + ".join(motivos) if motivos else "todo normal",
            "combate": list(info["combate"])}


def jugar(defensa, rondas=8, semilla=0):
    """Una partida: `rondas` obstáculos. Por cada uno: qué era, qué decidió Kira y si acertó.
    Devuelve (resultados, totales). No cambia los umbrales (eso lo hace aprender())."""
    resultados = []
    aciertos = fallos = falsas = 0
    for i in range(rondas):
        esc = generar((semilla, i))
        d = decidir(defensa, esc)
        combatio = d["es_amenaza"]
        if esc["ataque"] and combatio:
            res, aciertos = "acierto", aciertos + 1
        elif esc["ataque"] and not combatio:
            res, fallos = "se_escapo", fallos + 1
        elif (not esc["ataque"]) and combatio:
            res, falsas = "falsa_alarma", falsas + 1
        else:
            res, aciertos = "acierto", aciertos + 1
        resultados.append({"esc": esc, "decision": d, "resultado": res})
    totales = {"rondas": rondas, "aciertos": aciertos, "fallos": fallos, "falsas": falsas,
               "puntos": aciertos * 10 - fallos * 8 - falsas * 4}
    return resultados, totales


def aprender(defensa, resultados):
    """Afina los umbrales (los DATOS) con lo que salió mal: lo que se escapó -> baja el listón; las falsas alarmas ->
    súbelo. Pasos pequeños y con tope. Devuelve la lista de cambios (texto) para contarlos en la consola."""
    u = defensa.umbrales
    cambios = []
    for r in resultados:
        esc, res = r["esc"], r["resultado"]
        if res == "se_escapo":                       # una amenaza se coló: baja el umbral que la habría pillado
            for k in ("trafico", "logins", "puertos"):
                if esc.get(k, 0) > 0 and esc[k] < u[k]:
                    antes = u[k]
                    u[k] = _clamp(u[k] - PASO[k], LIMITES[k])
                    if u[k] != antes:
                        cambios.append(f"bajo el umbral de {k} {antes:g} → {u[k]:g} (se me escapaba)")
                        break
        elif res == "falsa_alarma":                  # paré tráfico sano: sube el umbral que saltó de más
            for k in ("trafico", "logins", "puertos"):
                if esc.get(k, 0) >= u[k]:
                    antes = u[k]
                    u[k] = _clamp(u[k] + PASO[k], LIMITES[k])
                    if u[k] != antes:
                        cambios.append(f"subo el umbral de {k} {antes:g} → {u[k]:g} (era falsa alarma)")
                        break
    defensa.partidas += 1
    return cambios


def codigo_detector(defensa):
    """El 'detector' de Kira como CÓDIGO (lo que ha aprendido), para enseñarlo en la consola y para poder meterlo en
    sus juegos (con los dos toques). Es una función de defensa, nunca de ataque."""
    u = defensa.umbrales
    return (
        "def es_amenaza(evento):\n"
        "    \"\"\"Defensa de Kira: True si el evento parece un ataque. Umbrales aprendidos entrenando.\"\"\"\n"
        f"    if evento.get('enlace'):            # enlace trampa (phishing)\n"
        "        return True\n"
        "    if evento.get('oculto') and evento.get('trafico', 0) >= 1.5:   # puerta trasera\n"
        "        return True\n"
        f"    if evento.get('logins', 0) >= {u['logins']:g}:   # fuerza bruta\n"
        "        return True\n"
        f"    if evento.get('puertos', 0) >= {u['puertos']:g}:  # escaneo de puertos\n"
        "        return True\n"
        f"    if evento.get('trafico', 0) >= {u['trafico']:g}:  # pico de tráfico\n"
        "        return True\n"
        "    return False\n")


_PAL = ("defensa", "defender", "defiende", "defenderse", "defiéndete", "amenaza", "amenazas", "laberinto",
        "intruso", "intrusos", "ataque", "ataques")


def es_orden(texto):
    """¿Es un «entrena/juega a defenderte», «juego de defensa», «laberinto de defensa»…? (para el enrutado)."""
    t = " " + str(texto or "").lower() + " "
    if not any(p in t for p in _PAL):
        return False
    return any(v in t for v in ("entrena", "entréna", "juega", "juego", "practica", "práctica", "defien", "defén",
                                "defens", "laberinto"))
