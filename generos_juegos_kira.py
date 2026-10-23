# -*- coding: utf-8 -*-
"""
generos_juegos_kira.py - Los GÉNEROS de juego que Kira sabe hacer bien (plantillas de nivel experto, probadas):

  esquivar     mueves al protagonista y esquivas lo que cae (el de siempre)
  carreras     carretera que avanza, 3 carriles, rivales, turbo, velocidad que sube, metros y meta
  plataformas  corre solo, toca para saltar (doble salto, salto más alto si mantienes, margen al saltar tarde),
               huecos, plataformas flotantes, enemigos que se pisan y monedas
  naves        tu nave sigue al dedo y dispara sola, oleadas con movimientos distintos, disparos enemigos,
               mejora de triple disparo y un jefe final con barra de vida
  combate      lucha 1 contra 1: botones de moverse, defensa, puñetazo y patada, golpe especial, rival con IA,
               barras de vida, rondas (gana quien gane 2) y tiempo
  retro        laberinto de comecocos con formas (sin dibujos): puntos, fantasmas que te persiguen, píldora
               de poder y niveles más rápidos

Cada uno es un PROGRAMA normal del motor de Kira (se abre en el editor, se puede leer y cambiar). Todo lo que hace
falta para jugar bien está en el código: física, IA de los rivales, curva de dificultad, efectos (chispas,
parpadeo al recibir un golpe) y choques «justos» (solo cuenta la parte central de los dibujos).
Lógica pura (sin Kivy).
"""
import re
import unicodedata

GENEROS = ("esquivar", "carreras", "plataformas", "naves", "combate", "retro")

NOMBRES = {"esquivar": "esquivar y recoger", "carreras": "carreras", "plataformas": "plataformas",
           "naves": "naves y disparos", "combate": "combate", "retro": "retro (laberinto)"}

_PALABRAS = [
    ("retro", r"\b(retro|8 ?bits|pixel(?:ad[oa])?|laberinto|comecocos|pac ?man|arcade clasico|recreativa)"),
    ("combate", r"\b(lucha|luchador|luchadores|combate|combates|pelea|peleas|boxeo|boxeador|karate|kung ?fu|"
                r"street ?fighter|mortal ?kombat|artes marciales|ninja contra|guerrero contra)"),
    ("naves", r"\b(naves?|espacial(?:es)?|marcianos|alienigenas|disparos?|dispara|shooter|aviones? de combate|"
              r"galaxia|invasores)"),
    ("carreras", r"\b(carreras?|coches?|motos?|rally|formula ?1|autos?|carros?|camiones? de carreras|"
                 r"karts?|conducir|piloto)"),
    ("plataformas", r"\b(plataformas?|saltar|salta|saltos|runner|mario|corre y salta|aventura de saltos)"),
]


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def genero_de(texto):
    """El género que pide la frase («carreras de coches» -> 'carreras'). Si no nombra ninguno: 'esquivar'."""
    t = _plano(texto)
    for g, rx in _PALABRAS:
        if re.search(rx, t):
            return g
    return "esquivar"


# Lo que se pone si la frase no lo dice (español, inglés para pintar)
DEFECTOS = {
    "carreras": {"protagonista": ("un coche de carreras rojo", "a red sports race car"),
                 "enemigo": ("coches rivales", "a blue sports car"),
                 "premio": ("bidones de turbo", "a glowing blue nitro canister"),
                 "escenario": ("una carretera junto al mar", "a coastal road with palm trees and sea")},
    "plataformas": {"protagonista": ("un aventurero", "a young adventurer with a backpack"),
                    "enemigo": ("monstruos", "a small angry green monster"),
                    "premio": ("monedas de oro", "a shiny gold coin"),
                    "escenario": ("un bosque mágico", "a magical green forest with hills"),
                    "plataforma": ("plataformas de piedra", "a floating mossy stone brick platform")},
    "naves": {"protagonista": ("una nave espacial", "a sleek white space fighter ship"),
              "enemigo": ("naves alienígenas", "a purple alien spaceship"),
              "premio": ("cristales de energía", "a glowing green energy crystal"),
              "escenario": ("el espacio profundo", "deep space with stars and a colorful nebula")},
    "combate": {"protagonista": ("un luchador de kárate", "a karate fighter in a white gi"),
                "enemigo": ("un luchador rival", "a muscular street fighter in red clothes"),
                "premio": ("", ""),
                "escenario": ("un dojo japonés", "a traditional japanese dojo interior")},
    "retro": {"protagonista": ("el comecocos", ""), "enemigo": ("fantasmas", ""), "premio": ("puntos", ""),
              "escenario": ("un laberinto", "")},
}

_QUITAR_GENERO = re.compile(
    r"^(?:juego\s+)?(?:de\s+|del\s+)?(?:(?:las?\s+)?carreras?|plataformas?|naves?(?:\s+espaciales?)?|combates?|luchas?|"
    r"peleas?|retro|laberinto|disparos?|boxeo|karate)\b\s*(?:de\s+|del\s+|con\s+|entre\s+)?", re.I)

_VEHICULOS = [(r"\bmotos?\b", ("una moto de carreras", "a racing motorbike")),
              (r"\bcamion(?:es)?\b", ("un camión de carreras", "a racing truck")),
              (r"\bkarts?\b", ("un kart", "a go-kart")),
              (r"\bformula", ("un fórmula 1", "a formula one race car")),
              (r"\b(?:coches?|autos?|carros?)\b", ("un coche de carreras", "a sports race car"))]


def tema(genero, resto):
    """De lo que queda de la frase sin el género, el protagonista (español, None si no se sabe)."""
    t = " ".join(str(resto or "").split())
    for _ in range(3):                                                         # «retro de laberinto» -> ""
        t = _QUITAR_GENERO.sub("", t).strip(" ,.:")
    if genero == "combate" and re.fullmatch(r"(?:el\s+)?(karate|kung ?fu|boxeo|judo|taekwondo|capoeira|sumo|"
                                            r"lucha libre|artes marciales)", _plano(t)):
        return "un luchador de " + t.split()[-1] if not _plano(t).startswith("artes") else "un luchador de artes marciales"
    if genero == "carreras":
        for rx, (es, _en) in _VEHICULOS:
            if re.search(rx, _plano(t)):
                return es
    return t or None


# =====================================================================================
#  LAS PLANTILLAS
# =====================================================================================
COMUN = '''
    def toca(self, a, b, margen=0.22):
        """Choque «justo»: los dibujos tienen bordes transparentes, así que se mira solo su parte central."""
        ax1, ay1, ax2, ay2 = a.caja()
        bx1, by1, bx2, by2 = b.caja()
        ma, mb = (ax2 - ax1) * margen, (bx2 - bx1) * margen
        na, nb = (ay2 - ay1) * margen, (by2 - by1) * margen
        return ax1 + ma < bx2 - mb and bx1 + mb < ax2 - ma and ay1 + na < by2 - nb and by1 + nb < ay2 - na

    def chispas(self, x, y, col="amarillo", n=10, fuerza=180):
        """Efecto de golpe o explosión: chispas que salen y se apagan."""
        for _ in range(n):
            c = self.circulo(x, y, self.azar(2, 4.5), col)
            c.vx, c.vy = self.azar(-fuerza, fuerza), self.azar(-fuerza, fuerza)
            c.datos["tipo"], c.datos["vida"] = "chispa", self.azar(0.25, 0.6)

    def mover_chispas(self, dt):
        for c in self.con_etiqueta("chispa"):
            c.datos["vida"] -= dt
            if c.datos["vida"] <= 0:
                self.borrar(c)
            else:
                r, g, b, _a = c.color
                c.color = (r, g, b, min(1.0, c.datos["vida"] * 2.5))

    def parpadeo(self, pieza, invencible):
        """Mientras dura la invencibilidad tras un golpe, la pieza parpadea."""
        r, g, b, _a = pieza.color
        pieza.color = (r, g, b, 0.35 if invencible > 0 and int(invencible * 12) % 2 == 0 else 1.0)
'''

CARRERAS = '''
    META = 5000                     # metros hasta la meta

    def preparar(self):
        self.imagen(0, 0, self.ancho, self.alto, "fondo")                     # el paisaje, a los lados
        self.x0, self.pista = 48.0, 264.0
        self.rect(self.x0 - 10, 0, self.pista + 20, self.alto, (0.9, 0.9, 0.9))
        self.rect(self.x0, 0, self.pista, self.alto, (0.17, 0.17, 0.19))      # el asfalto
        self.marcas = []
        for c in (1, 2):                                                       # las rayas de los carriles
            for k in range(7):
                self.marcas.append(self.rect(self.x0 + c * self.pista / 3 - 3, k * 110, 6, 55, (1, 1, 1, 0.8)))
        for lado in (self.x0 - 10, self.x0 + self.pista):                      # los pianos rojo y blanco
            for k in range(16):
                self.marcas.append(self.rect(lado, k * 44, 10, 22, "rojo"))
        self.carril, self.velocidad, self.metros = 1, 240.0, 0.0
        self.turbo = self.invencible = self.reloj = 0.0
        self.coche = self.imagen(self.centro(1) - 30, 60, 60, 96, "jugador")
        self.meta_puesta = False

    def centro(self, carril):
        return self.x0 + self.pista / 6 * (2 * carril + 1)

    def al_tocar(self, x, y):                       # toca a un lado del coche para cambiar de carril
        if x < self.coche.x + self.coche.w / 2:
            self.carril = max(0, self.carril - 1)
        else:
            self.carril = min(2, self.carril + 1)

    def al_deslizar(self, dx, dy):
        if abs(dx) > 30 and abs(dx) > abs(dy):
            self.carril = max(0, min(2, self.carril + (1 if dx > 0 else -1)))

    def carriles_ocupados_arriba(self):
        return {r.datos["carril"] for r in self.con_etiqueta("rival") if r.y > self.alto - 380}

    def actualizar(self, dt):
        objetivo = self.centro(self.carril) - self.coche.w / 2
        self.coche.x += (objetivo - self.coche.x) * min(1.0, dt * 12)        # cambia de carril suave
        self.turbo = max(0.0, self.turbo - dt)
        self.invencible = max(0.0, self.invencible - dt)
        self.parpadeo(self.coche, self.invencible)
        self.velocidad = min(720.0, self.velocidad + 7 * dt)                 # cada vez más rápido
        v = self.velocidad * (1.6 if self.turbo > 0 else 1.0)
        self.metros += v * dt / 8
        self.puntos = int(self.metros)
        for m in self.marcas:                                                 # la carretera avanza
            m.y -= v * dt
            if m.y < -60:
                m.y += 770 if m.w == 6 else 704
        self.reloj += dt
        hueco = max(0.45, 1.3 - self.metros / 6000)
        if self.reloj >= hueco:
            self.reloj = 0.0
            libres = [c for c in range(3) if c not in self.carriles_ocupados_arriba()]
            if len(libres) >= 2:                                              # siempre queda un carril libre
                c = libres[self.azar_entero(0, len(libres) - 1)]
                if self.azar(0, 1) < 0.8:
                    r = self.imagen(self.centro(c) - 28, self.alto + 20, 56, 92, "enemigo")
                    r.datos["tipo"], r.datos["carril"], r.datos["propia"] = "rival", c, self.azar(0.4, 0.55)
                else:
                    r = self.imagen(self.centro(c) - 22, self.alto + 20, 44, 44, "premio")
                    r.datos["tipo"], r.datos["carril"], r.datos["propia"] = "premio", c, 0.0
        for r in self.con_etiqueta("rival") + self.con_etiqueta("premio"):
            r.vy = -v * (1 - r.datos["propia"])                               # van a su marcha: tú los alcanzas
            if r.y < -120:
                self.borrar(r)
            elif self.toca(r, self.coche, 0.18):
                if r.datos["tipo"] == "premio":
                    self.borrar(r)
                    self.turbo, self.puntos = 2.5, self.puntos + 50
                    self.chispas(r.x + 22, r.y + 22, "cian", 12)
                elif self.invencible <= 0 and self.turbo <= 0:
                    self.chispas(self.coche.x + 30, self.coche.y + 80, "naranja", 18, 240)
                    self.borrar(r)
                    self.vidas -= 1
                    self.velocidad *= 0.6
                    self.invencible = 1.6
                    if self.vidas <= 0:
                        self.fin(f"¡Accidente! Recorriste {int(self.metros)} m")
                elif self.turbo > 0:                                          # con turbo, los apartas
                    self.chispas(r.x + 28, r.y + 40, "amarillo", 10)
                    self.borrar(r)
        self.mover_chispas(dt)
        if self.metros > self.META - 300 and not self.meta_puesta:            # la línea de meta a cuadros
            self.meta_puesta = True
            for i in range(12):
                for j in range(2):
                    q = self.rect(self.x0 + i * 22, self.alto + j * 22, 22, 22, "blanco" if (i + j) % 2 else "negro")
                    q.datos["tipo"] = "meta"
        for q in self.con_etiqueta("meta"):
            q.vy = -v
        if self.metros >= self.META:
            self.ganar(f"¡Has llegado a la meta! {self.vidas} vidas de sobra")

    def marcador(self):
        if self.estado != "jugando":
            return Juego.marcador(self)
        return (f"{int(self.metros)} / {self.META} m · {int(self.velocidad * (1.6 if self.turbo > 0 else 1) * 0.3)} km/h"
                f" · Vidas: {self.vidas}" + (" · ¡TURBO!" if self.turbo > 0 else ""))
'''

PLATAFORMAS = '''
    GRAVEDAD, SALTO = 1700.0, 640.0

    def preparar(self):
        f = self.imagen(0, 0, self.ancho, self.alto, "fondo")
        f.datos["tipo"] = "fondo"
        self.velocidad, self.distancia = 170.0, 0.0
        self.vy, self.saltos, self.en_suelo = 0.0, 0, False
        self.coyote = self.buffer = self.invencible = 0.0
        self.jugador = self.imagen(70, 140, 54, 64, "jugador")
        self.ultimo = None
        self.suelo(-20, 520)                                                   # el primer tramo, largo
        while self.borde() < self.ancho + 200:
            self.tramo()

    def suelo(self, x, largo, alto=100, seguir=True):
        s = self.rect(x, 0, largo, alto, (0.42, 0.27, 0.15))
        s.datos["tipo"] = "suelo"
        c = self.rect(x, alto - 10, largo, 10, (0.25, 0.65, 0.25))           # la hierba de encima
        c.datos["tipo"] = "deco"
        if seguir:                                                             # el camino sigue desde aquí
            self.ultimo = s
        return s

    def borde(self):
        return self.ultimo.x + self.ultimo.w

    def tramo(self):
        """Lo siguiente del camino: hueco (que se puede saltar), suelo, a veces plataformas, enemigos y monedas."""
        dif = min(1.0, self.distancia / 4000)
        x = self.borde() + self.azar(60, 70 + 70 * dif)
        largo = self.azar(220 - 60 * dif, 420 - 120 * dif)
        alto = self.azar_entero(0, 2) * 30 + 70
        s = self.suelo(x, largo, alto)
        if self.azar(0, 1) < 0.5:                                              # plataforma flotante con monedas
            px = x + self.azar(20, max(30, largo - 110))
            p = self.imagen(px, alto + self.azar(110, 170), 96, 26, "plataforma")
            p.datos["tipo"] = "plataforma"
            for k in range(3):
                self.moneda(px + 14 + k * 26, p.y + 50)
        else:
            for k in range(4):                                                 # un arco de monedas
                self.moneda(x + 30 + k * 30, alto + 60 + 30 * (1 - abs(k - 1.5) / 1.5))
        if largo > 260 and self.azar(0, 1) < 0.35 + 0.4 * dif:                 # un enemigo que camina
            e = self.imagen(x + largo - 70, alto, 42, 42, "enemigo")
            e.datos.update({"tipo": "enemigo", "andar": -45.0, "suelo": s, "sitio": largo - 70})
        return s

    def moneda(self, x, y):
        m = self.imagen(x, y, 24, 24, "premio")
        m.datos["tipo"] = "moneda"

    def al_tocar(self, x, y):
        self.buffer = 0.12                                                     # el salto se recuerda un momento

    def al_soltar(self, x, y):
        if self.vy > 0:
            self.vy *= 0.5                                                     # soltar pronto = salto más bajo

    def mundo(self):
        return [p for p in self.piezas if p.viva and p is not self.jugador and p.datos.get("tipo") not in
                ("fondo", "chispa")]

    def actualizar(self, dt):
        self.velocidad = min(330.0, self.velocidad + 4 * dt)
        self.distancia += self.velocidad * dt
        self.puntos = max(self.puntos, 0)
        for p in self.mundo():                                                 # el mundo avanza hacia ti
            p.vx = -self.velocidad
            if p.datos.get("tipo") == "enemigo":                               # camina por su suelo y da la vuelta
                s, d = p.datos["suelo"], p.datos
                d["sitio"] += d["andar"] * dt
                if d["sitio"] < 0 or d["sitio"] > s.w - p.w:
                    d["andar"] = -d["andar"]
                    d["sitio"] = max(0.0, min(d["sitio"], s.w - p.w))
                p.x, p.y = s.x + d["sitio"], s.y + s.h
            if p.x + p.w < -60:
                self.borrar(p)
        while self.borde() < self.ancho + 200:
            self.tramo()
        # --- el salto (con margen al saltar tarde y doble salto) ---
        self.coyote = 0.1 if self.en_suelo else max(0.0, self.coyote - dt)
        self.buffer = max(0.0, self.buffer - dt)
        if self.buffer > 0 and (self.coyote > 0 or self.saltos < 2):
            self.vy = self.SALTO if self.coyote > 0 or self.saltos == 0 else self.SALTO * 0.85
            self.saltos = 1 if self.coyote > 0 else self.saltos + 1
            self.buffer = self.coyote = 0.0
            self.en_suelo = False
        antes = self.jugador.y
        self.vy = max(-900.0, self.vy - self.GRAVEDAD * dt)
        self.jugador.y += self.vy * dt
        self.en_suelo = False
        j = self.jugador
        pies_izq, pies_der = j.x + j.w * 0.25, j.x + j.w * 0.75
        for s in self.con_etiqueta("suelo") + self.con_etiqueta("plataforma"):
            arriba = s.y + s.h if s.datos["tipo"] == "suelo" else s.y + s.h * 0.7
            if pies_der > s.x and pies_izq < s.x + s.w:
                if self.vy <= 0 and antes >= arriba - 1 and j.y <= arriba:      # cae encima: aterriza
                    j.y, self.vy, self.en_suelo, self.saltos = arriba, 0.0, True, 0
                elif s.datos["tipo"] == "suelo" and j.y < arriba - 8 and j.x + j.w * 0.7 > s.x and j.x < s.x:
                    j.x = s.x - j.w * 0.7                                      # choca con el lado del suelo
        if j.x < 70:
            j.x = min(70.0, j.x + 60 * dt)
        # --- enemigos y monedas ---
        self.invencible = max(0.0, self.invencible - dt)
        self.parpadeo(j, self.invencible)
        for e in self.con_etiqueta("enemigo"):
            if self.toca(e, j, 0.15):
                if self.vy < 0 and antes > e.y + e.h * 0.5:                    # le caes encima: lo pisas
                    self.chispas(e.x + 21, e.y + 30, "verde", 12)
                    self.borrar(e)
                    self.vy, self.puntos = self.SALTO * 0.7, self.puntos + 50
                elif self.invencible <= 0:
                    self.herido("¡Un monstruo te ha pillado!")
        for m in self.con_etiqueta("moneda"):
            if self.toca(m, j, 0.05):
                self.borrar(m)
                self.puntos += 10
                self.chispas(m.x + 12, m.y + 12, "amarillo", 6, 120)
        if j.y < -80:                                                          # cayó por un hueco
            self.herido("¡Te has caído!")
            if self.estado == "jugando":
                self.suelo(j.x - 40, 170, 100, seguir=False)                   # un suelo para volver a empezar
                j.y, self.vy = 100, 0.0
        self.mover_chispas(dt)

    def herido(self, mensaje):
        self.vidas -= 1
        self.invencible = 1.5
        self.chispas(self.jugador.x + 27, self.jugador.y + 32, "rojo", 14)
        if self.vidas <= 0:
            self.fin(f"{mensaje} Llegaste a {int(self.distancia / 10)} m")

    def marcador(self):
        if self.estado != "jugando":
            return Juego.marcador(self)
        return f"Puntos: {self.puntos} · {int(self.distancia / 10)} m · Vidas: {self.vidas}"
'''

NAVES = '''
    def preparar(self):
        self.imagen(0, 0, self.ancho, self.alto, "fondo")
        for _ in range(40):                                                    # estrellas que pasan
            e = self.circulo(self.azar(0, self.ancho), self.azar(0, self.alto), self.azar(0.6, 1.8), (1, 1, 1, 0.8))
            e.datos["tipo"], e.datos["v"] = "estrella", self.azar(40, 160)
        self.nave = self.imagen(150, 60, 62, 62, "jugador")
        self.reloj_disparo = self.reloj_oleada = self.invencible = self.triple = 0.0
        self.oleada, self.jefe, self.siguiente_jefe, self.jefes_vencidos = 0, None, 1200, 0

    def disparo(self, x, y, vx, vy, col, tipo, r=0):
        b = self.circulo(x, y, r, col) if r else self.rect(x - 2, y, 4, 16, col)
        b.vx, b.vy, b.datos["tipo"] = vx, vy, tipo
        return b

    def nueva_oleada(self):
        self.oleada += 1
        forma = self.oleada % 3
        n = min(4 + self.oleada, 9)
        for i in range(n):
            e = self.imagen(20 + i * (300 / n), self.alto + 30 + (i % 2) * 40, 46, 46, "enemigo")
            e.datos.update({"tipo": "enemigo", "vida": 1 + self.oleada // 6, "forma": forma, "t": i * 0.4,
                            "x0": e.x, "disparo": self.azar(1.0, 3.5)})
            e.vy = -70 - self.oleada * 6

    def lanzar_jefe(self):
        self.jefe = self.imagen(110, self.alto + 10, 140, 140, "enemigo")
        self.jefe.datos.update({"tipo": "jefe", "vida": 40 + self.oleada * 4, "t": 0.0, "disparo": 1.0})
        self.jefe.datos["total"] = self.jefe.datos["vida"]
        self.barra_fondo = self.rect(30, self.alto - 18, 300, 8, (0.3, 0.3, 0.3))
        self.barra = self.rect(30, self.alto - 18, 300, 8, "rojo")

    def actualizar(self, dt):
        if self.dedo:                                                          # la nave sigue a tu dedo
            self.nave.x += (self.dedo[0] - self.nave.w / 2 - self.nave.x) * min(1.0, dt * 14)
            self.nave.y += (min(self.dedo[1], 260) + 40 - self.nave.y) * min(1.0, dt * 10)
        self.limitar(self.nave)
        for e in self.con_etiqueta("estrella"):
            e.y -= e.datos["v"] * dt
            if e.y < 0:
                e.y, e.x = self.alto, self.azar(0, self.ancho)
        self.triple = max(0.0, self.triple - dt)
        self.reloj_disparo += dt
        if self.reloj_disparo >= 0.17:                                         # dispara solo
            self.reloj_disparo = 0.0
            cx, cy = self.nave.x + 31, self.nave.y + 56
            self.disparo(cx, cy, 0, 620, "cian", "bala")
            if self.triple > 0:
                self.disparo(cx - 12, cy - 6, -160, 600, "cian", "bala")
                self.disparo(cx + 12, cy - 6, 160, 600, "cian", "bala")
        if self.jefe is None and not self.con_etiqueta("enemigo"):
            self.reloj_oleada += dt
            if self.puntos >= self.siguiente_jefe:
                self.lanzar_jefe()
            elif self.reloj_oleada > 0.8:
                self.reloj_oleada = 0.0
                self.nueva_oleada()
        for e in self.con_etiqueta("enemigo"):                                 # cada oleada se mueve distinto
            d = e.datos
            d["t"] += dt
            if d["forma"] == 1:
                e.x = d["x0"] + 50 * __import_seno(d["t"] * 2.2)
            elif d["forma"] == 2 and e.y < 420 and e.vx == 0:                  # se lanza hacia ti
                e.vx = (self.nave.x - e.x) * 0.6
                e.vy = -220
            d["disparo"] -= dt
            if d["disparo"] <= 0 and e.y < self.alto - 40:
                d["disparo"] = self.azar(1.8, 3.5)
                dx, dy = self.nave.x + 31 - (e.x + 23), self.nave.y + 31 - e.y
                n = max(1.0, (dx * dx + dy * dy) ** 0.5)
                self.disparo(e.x + 23, e.y, dx / n * 230, dy / n * 230, "rojo", "bala_mala", 4)
            if e.y < -60:
                self.borrar(e)
        if self.jefe is not None:
            self.mover_jefe(dt)
        for b in self.con_etiqueta("bala"):
            if b.y > self.alto:
                self.borrar(b)
                continue
            for e in self.con_etiqueta("enemigo") + ([self.jefe] if self.jefe else []):
                if self.toca(b, e, 0.0 if e is self.jefe else 0.12):
                    self.borrar(b)
                    e.datos["vida"] -= 1
                    self.chispas(b.x, b.y + 8, "amarillo", 3, 90)
                    if e.datos["vida"] <= 0 and e is not self.jefe:
                        self.chispas(e.x + 23, e.y + 23, "naranja", 16, 220)
                        self.borrar(e)
                        self.puntos += 25 * (1 + self.oleada // 6)
                        if self.azar(0, 1) < 0.12:
                            p = self.imagen(e.x + 8, e.y, 30, 30, "premio")
                            p.vy, p.datos["tipo"] = -120, "mejora"
                    break
        self.invencible = max(0.0, self.invencible - dt)
        self.parpadeo(self.nave, self.invencible)
        for b in self.con_etiqueta("bala_mala"):
            if not self.dentro(b):
                self.borrar(b)
            elif self.invencible <= 0 and self.toca(b, self.nave, 0.3):
                self.borrar(b)
                self.herida()
        for e in self.con_etiqueta("enemigo"):
            if self.invencible <= 0 and self.toca(e, self.nave):
                self.borrar(e)
                self.herida()
        for p in self.con_etiqueta("mejora"):
            if self.toca(p, self.nave, 0.0):
                self.borrar(p)
                self.triple = 8.0
                self.chispas(p.x + 15, p.y + 15, "verde", 10)
            elif p.y < -40:
                self.borrar(p)
        self.mover_chispas(dt)

    def mover_jefe(self, dt):
        j, d = self.jefe, self.jefe.datos
        d["t"] += dt
        objetivo_y = self.alto - 210
        if j.y > objetivo_y:
            j.y -= 90 * dt
        j.x = 110 + 90 * __import_seno(d["t"] * 0.9)
        d["disparo"] -= dt
        if d["disparo"] <= 0:                                                  # ráfaga en abanico
            d["disparo"] = max(0.6, 1.4 - self.oleada * 0.05)
            for k in range(-2, 3):
                self.disparo(j.x + 70, j.y + 10, k * 70, -240, "rosa", "bala_mala", 5)
        self.barra.w = 300 * max(0, d["vida"]) / d["total"]
        if d["vida"] <= 0:
            for _ in range(4):
                self.chispas(j.x + self.azar(20, 120), j.y + self.azar(20, 120), "naranja", 14, 260)
            self.borrar(j)
            self.borrar(self.barra)
            self.borrar(self.barra_fondo)
            self.jefe = None
            self.puntos += 500
            self.jefes_vencidos += 1
            self.siguiente_jefe = self.puntos + 1200
            if self.jefes_vencidos >= 3:
                self.ganar("¡Has vencido a los 3 jefes y salvado la galaxia!")

    def herida(self):
        self.vidas -= 1
        self.invencible = 2.0
        self.triple = 0.0
        self.chispas(self.nave.x + 31, self.nave.y + 31, "rojo", 18, 220)
        if self.vidas <= 0:
            self.fin("¡Te han derribado!")
'''

COMBATE = '''
    SUELO = 120.0
    BOTONES = (("<", "izq"), (">", "der"), ("DEF", "defensa"), ("PUÑO", "puno"), ("PATADA", "patada"))
    GOLPES = {"puno": (0.07, 0.10, 0.20, 7, 78), "patada": (0.14, 0.12, 0.32, 11, 100),
              "especial": (0.20, 0.20, 0.40, 24, 125)}      # (preparar, activo, recuperar, daño, alcance)

    def preparar(self):
        self.imagen(0, self.SUELO - 30, self.ancho, self.alto - self.SUELO + 30, "fondo")
        self.rect(0, 0, self.ancho, self.SUELO - 30, (0.12, 0.1, 0.1))
        self.botones = []
        for i, (texto, accion) in enumerate(self.BOTONES):                    # los botones de abajo
            b = self.rect(4 + i * 71.2, 8, 66, 66, (0.25, 0.25, 0.3, 0.9))
            b.datos["accion"] = accion
            tam = 18 if len(texto) <= 4 else 14
            self.texto(b.x + 33 - len(texto) * tam * 0.31, 30, texto, tam, "blanco")
            self.botones.append(b)
        self.ronda, self.victorias = 1, [0, 0]
        self.p1 = self.luchador(50, "jugador", 1)
        self.p2 = self.luchador(200, "enemigo", -1)
        self.barras = []
        for i, x in enumerate((12, 192)):
            self.rect(x, self.alto - 34, 156, 14, (0.3, 0.3, 0.3))
            self.barras.append(self.rect(x, self.alto - 34, 156, 14, "verde"))
        self.carga = self.rect(12, self.alto - 46, 0, 6, "cian")              # la barra del golpe especial
        self.aviso = self.texto(95, self.alto - 80, "", 30, "blanco")
        self.empezar_ronda()

    def luchador(self, x, dibujo, mira):
        p = self.imagen(x, self.SUELO, 110, 160, dibujo)
        p.datos.update({"vida": 100.0, "mira": mira, "golpe": None, "t": 0.0, "aturdido": 0.0, "defensa": False,
                        "carga": 0.0, "pensar": 0.0})
        return p

    def empezar_ronda(self):
        for p, x in ((self.p1, 50.0), (self.p2, 200.0)):
            p.x, p.datos["vida"], p.datos["golpe"], p.datos["aturdido"] = x, 100.0, None, 0.0
        self.tiempo_ronda, self.pausa = 60.0, 1.2
        self.aviso.texto = f"RONDA {self.ronda}"

    def boton_en(self, x, y):
        for b in self.botones:
            if b.x <= x <= b.x + b.w and b.y <= y <= b.y + b.h:
                return b.datos["accion"]
        return None

    def al_tocar(self, x, y):
        accion = self.boton_en(x, y)
        if accion in ("puno", "patada"):
            if accion == "patada" and self.p1.datos["carga"] >= 100:
                accion = "especial"
                self.p1.datos["carga"] = 0.0
            self.atacar(self.p1, accion)

    def al_deslizar(self, dx, dy):
        if dy > 40 and self.p1.datos["carga"] >= 100:                          # desliza hacia arriba: especial
            self.p1.datos["carga"] = 0.0
            self.atacar(self.p1, "especial")

    def atacar(self, p, tipo):
        d = p.datos
        if d["golpe"] is None and d["aturdido"] <= 0 and self.pausa <= 0:
            d["golpe"], d["t"], d["acerto"] = tipo, 0.0, False

    def distancia(self):
        return abs((self.p2.x + 55) - (self.p1.x + 55))

    def actualizar(self, dt):
        self.mover_chispas(dt)
        if self.pausa > 0:
            self.pausa -= dt
            if self.pausa <= 0:
                self.aviso.texto = ""
            return
        self.tiempo_ronda -= dt
        accion = self.boton_en(*self.dedo) if self.dedo else None              # botones que se mantienen
        d1 = self.p1.datos
        d1["defensa"] = accion == "defensa" and d1["golpe"] is None
        if d1["golpe"] is None and d1["aturdido"] <= 0 and not d1["defensa"]:
            if accion == "izq":
                self.p1.x -= 170 * dt
            elif accion == "der":
                self.p1.x += 170 * dt
        self.cerebro_rival(dt)
        for a, b in ((self.p1, self.p2), (self.p2, self.p1)):
            self.mover_golpe(a, b, dt)
        self.p1.x = max(0.0, min(self.p1.x, self.p2.x - 60))                  # no se atraviesan
        self.p2.x = min(self.ancho - 110.0, max(self.p2.x, self.p1.x + 60))
        for barra, p in zip(self.barras, (self.p1, self.p2)):
            barra.w = 156 * max(0.0, p.datos["vida"]) / 100
            barra.color = (0.2, 0.78, 0.45, 1) if p.datos["vida"] > 30 else (0.92, 0.26, 0.3, 1)
        self.carga.w = 156 * min(100.0, d1["carga"]) / 100
        self.puntos = self.victorias[0]
        if self.p1.datos["vida"] <= 0 or self.p2.datos["vida"] <= 0 or self.tiempo_ronda <= 0:
            self.fin_ronda()

    def cerebro_rival(self, dt):
        """La IA del rival: se acerca, guarda la distancia, ataca, se defiende si le vas a dar y se retira."""
        d = self.p2.datos
        d["pensar"] -= dt
        nivel = min(1.0, 0.45 + 0.2 * (self.ronda - 1))
        if d["golpe"] is not None or d["aturdido"] > 0:
            return
        g1 = self.p1.datos["golpe"]
        if g1 is not None and self.distancia() < 130 and self.azar(0, 1) < 0.04 * nivel * 60 * dt:
            d["defensa"] = True
            d["pensar"] = 0.35
        if d["pensar"] > 0:
            return
        d["defensa"] = False
        dist = self.distancia()
        if dist > 72:                                                          # se acerca hasta tenerte a mano
            self.p2.x -= 130 * dt
        elif d["vida"] < 30 and self.azar(0, 1) < 0.25:                         # con poca vida, a veces recula
            self.p2.x += 120 * dt
        elif self.azar(0, 1) < 2.2 * nivel * dt * 4:
            tipo = "especial" if d["carga"] >= 100 else ("patada" if self.azar(0, 1) < 0.4 else "puno")
            if tipo == "especial":
                d["carga"] = 0.0
            self.atacar(self.p2, tipo)
            d["pensar"] = self.azar(0.2, 0.7) / nivel

    def mover_golpe(self, a, b, dt):
        d = a.datos
        d["aturdido"] = max(0.0, d["aturdido"] - dt)
        r, g, bb, _x = a.color
        a.color = (r, g, bb, 0.45 if d["aturdido"] > 0 and int(d["aturdido"] * 20) % 2 else 1.0)
        if d["golpe"] is None:
            return
        prep, activo, recup, dano, alcance = self.GOLPES[d["golpe"]]
        d["t"] += dt
        t = d["t"]
        a.y = self.SUELO + (14 if prep <= t < prep + activo else 0)
        if prep <= t < prep + activo and not d["acerto"]:
            if self.distancia() <= alcance:
                d["acerto"] = True
                db = b.datos
                pega = dano * (0.2 if db["defensa"] else 1.0)
                db["vida"] -= pega
                d["carga"] = min(100.0, d["carga"] + pega * 2.2)
                db["carga"] = min(100.0, db["carga"] + pega)
                if not db["defensa"]:
                    db["aturdido"], db["golpe"] = 0.25 + dano / 60, None
                b.x += 18 * d["mira"] * (0.3 if db["defensa"] else 1.0)
                cx = (a.x + b.x) / 2 + 55
                self.chispas(cx, self.SUELO + 110, "cian" if db["defensa"] else "amarillo", 8 + int(dano), 160)
        if t >= prep + activo + recup:
            d["golpe"], a.y = None, self.SUELO

    def fin_ronda(self):
        v1, v2 = self.p1.datos["vida"], self.p2.datos["vida"]
        if abs(v1 - v2) < 0.5:                                                 # empate: se repite la ronda
            self.aviso.texto = "¡EMPATE!"
            self.empezar_ronda()
            self.pausa = 2.0
            return
        gana = 0 if v1 > v2 else 1
        self.victorias[gana] += 1
        self.aviso.texto = "¡K.O.!" if min(v1, v2) <= 0 else "¡TIEMPO!"
        self.chispas(self.p2.x + 55 if gana == 0 else self.p1.x + 55, self.SUELO + 90, "rojo", 24, 260)
        if self.victorias[0] == 2:
            self.ganar(f"¡Has ganado el combate {self.victorias[0]}-{self.victorias[1]}!")
        elif self.victorias[1] == 2:
            self.fin(f"Has perdido el combate {self.victorias[0]}-{self.victorias[1]}")
        else:
            self.ronda += 1
            self.empezar_ronda()
            self.pausa = 2.0

    def marcador(self):
        if self.estado != "jugando":
            return Juego.marcador(self)
        return (f"Ronda {self.ronda} · {max(0, int(self.tiempo_ronda))} s · Tú {self.victorias[0]} - "
                f"{self.victorias[1]} Rival" + (" · ¡ESPECIAL listo! (patada)" if self.p1.datos["carga"] >= 100 else ""))
'''

RETRO = '''
    MAPA = [
        "###############",
        "#o.....#.....o#",
        "#.###.##.###..#",
        "#.............#",
        "#.##.#.#.#.##.#",
        "#....#...#....#",
        "####.##.##.####",
        "   #.#   #.#   ",
        "####.# # #.####",
        "#......P......#",
        "####.#####.####",
        "   #.......#   ",
        "####.#####.####",
        "#......#......#",
        "#.##.#.#.#.##.#",
        "#o.#...G...#.o#",
        "##.#.#####.#.##",
        "#....G...G....#",
        "#.###..#..###.#",
        "#......#......#",
        "###############",
    ]
    CASILLA = 24.0
    COLORES_FANTASMA = ["rojo", "rosa", "cian", "naranja"]
    fondo = (0.02, 0.02, 0.06)

    def preparar(self):
        self.nivel = getattr_nivel = 1
        self.montar()

    def montar(self):
        self.y0 = 70.0
        self.paredes, self.puntos_mapa = set(), {}
        for p in list(self.piezas):
            self.borrar(p)
        for fila, linea in enumerate(self.MAPA):
            for col, c in enumerate(linea):
                x, y = col * self.CASILLA, self.y0 + (len(self.MAPA) - 1 - fila) * self.CASILLA
                if c == "#":
                    self.paredes.add((col, fila))
                    self.rect(x + 2, y + 2, self.CASILLA - 4, self.CASILLA - 4, (0.1, 0.2, 0.9))
                elif c in ".o":
                    r = 6.0 if c == "o" else 2.5
                    self.puntos_mapa[(col, fila)] = self.circulo(x + 12, y + 12, r, (1, 0.85, 0.7))
                    self.puntos_mapa[(col, fila)].datos["grande"] = c == "o"
                elif c == "P":
                    self.salida_p = (col, fila)
                elif c == "G":
                    self.salida_g = getattr_g = (col, fila)
        self.salidas_g = [(c, f) for f, linea in enumerate(self.MAPA) for c, ch in enumerate(linea) if ch == "G"]
        self.come = self.poligono([(0, 0), (1, 0), (0, 1)], "amarillo")
        self.pac = {"pos": list(self.centro(*self.salida_p)), "dir": (0, 0), "quiere": (-1, 0), "boca": 0.0}
        self.fantasmas = []
        for i in range(4):
            col, fila = self.salidas_g[i % len(self.salidas_g)]
            cuerpo = self.circulo(0, 0, 10, self.COLORES_FANTASMA[i])
            ojo1, ojo2 = self.circulo(0, 0, 3, "blanco"), self.circulo(0, 0, 3, "blanco")
            self.fantasmas.append({"pos": list(self.centro(col, fila)), "dir": (0, 1), "cuerpo": cuerpo,
                                   "ojos": (ojo1, ojo2), "color": self.COLORES_FANTASMA[i], "casa": (col, fila),
                                   "espera": i * 2.0})
        self.asustados = 0.0
        self.velocidad = 82.0 + 12 * self.nivel
        self.texto(10, 20, f"NIVEL {self.nivel}", 18, "amarillo")

    def centro(self, col, fila):
        return (col * self.CASILLA + 12, self.y0 + (len(self.MAPA) - 1 - fila) * self.CASILLA + 12)

    def casilla(self, pos):
        col = int(pos[0] // self.CASILLA)
        fila = len(self.MAPA) - 1 - int((pos[1] - self.y0) // self.CASILLA)
        return col, fila

    def libre(self, col, fila):
        if fila < 0 or fila >= len(self.MAPA) or col < 0 or col >= len(self.MAPA[0]):
            return False
        return (col, fila) not in self.paredes

    def al_deslizar(self, dx, dy):
        if abs(dx) > abs(dy):
            self.pac["quiere"] = (1 if dx > 0 else -1, 0)
        else:
            self.pac["quiere"] = (0, 1 if dy > 0 else -1)

    def al_tocar(self, x, y):                                                  # tocar hacia donde quieres ir
        px, py = self.pac["pos"]
        dx, dy = x - px, y - py
        if max(abs(dx), abs(dy)) > 20:
            self.al_deslizar(dx, dy)

    def avanzar(self, ente, quiere, velocidad, dt):
        """Movimiento por casillas: solo se gira en el centro de una casilla y no se atraviesan paredes."""
        x, y = ente["pos"]
        col, fila = self.casilla((x, y))
        cx, cy = self.centro(col, fila)
        en_centro = abs(x - cx) < velocidad * dt + 0.5 and abs(y - cy) < velocidad * dt + 0.5
        if en_centro:
            if quiere != ente["dir"] and self.libre(col + quiere[0], fila - quiere[1]):
                ente["dir"] = quiere
                x, y = cx, cy
            if not self.libre(col + ente["dir"][0], fila - ente["dir"][1]):
                ente["pos"] = [cx, cy]
                return True
        ente["pos"] = [x + ente["dir"][0] * velocidad * dt, y + ente["dir"][1] * velocidad * dt]
        return en_centro

    def elegir(self, f, col, fila, objetivo):
        """IA de los fantasmas: en cada cruce eligen el camino que más les acerca a su objetivo (sin dar la vuelta)."""
        opciones = []
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if d == (-f["dir"][0], -f["dir"][1]) or not self.libre(col + d[0], fila - d[1]):
                continue
            nx, ny = col + d[0], fila - d[1]
            opciones.append(((nx - objetivo[0]) ** 2 + (ny - objetivo[1]) ** 2, d))
        if not opciones:
            return (-f["dir"][0], -f["dir"][1])
        if self.asustados > 0:
            return opciones[self.azar_entero(0, len(opciones) - 1)][1]
        return min(opciones)[1]

    def actualizar(self, dt):
        self.avanzar(self.pac, self.pac["quiere"], self.velocidad, dt)
        pc = self.casilla(self.pac["pos"])
        p = self.puntos_mapa.get(pc)
        if p is not None and p.viva:
            self.borrar(p)
            del self.puntos_mapa[pc]
            self.puntos += 50 if p.datos["grande"] else 10
            if p.datos["grande"]:
                self.asustados = 7.0
        self.pintar_pac(dt)
        self.asustados = max(0.0, self.asustados - dt)
        for i, f in enumerate(self.fantasmas):
            if f["espera"] > 0:                                                # espera en su sitio antes de salir
                f["espera"] -= dt
                self.pintar_fantasma(f)
                continue
            col, fila = self.casilla(f["pos"])
            v = self.velocidad * (0.55 if self.asustados > 0 else 0.92)
            if i == 0 or self.asustados > 0:
                objetivo = pc
            elif i == 1:                                                       # se adelanta a donde vas
                objetivo = (pc[0] + 4 * self.pac["dir"][0], pc[1] - 4 * self.pac["dir"][1])
            elif i == 2:
                objetivo = (2 * pc[0] - self.casilla(self.fantasmas[0]["pos"])[0],
                            2 * pc[1] - self.casilla(self.fantasmas[0]["pos"])[1])
            else:                                                              # se asusta si está cerca
                objetivo = pc if abs(col - pc[0]) + abs(fila - pc[1]) > 6 else (0, len(self.MAPA))
            cx, cy = self.centro(col, fila)
            cerca = abs(f["pos"][0] - cx) < v * dt + 0.5 and abs(f["pos"][1] - cy) < v * dt + 0.5
            if cerca and (col, fila) != f.get("ultima"):                       # en cada casilla decide una vez
                f["ultima"] = (col, fila)
                f["pos"] = [cx, cy]
                f["dir"] = self.elegir(f, col, fila, objetivo)
            self.avanzar(f, f["dir"], v, dt)
            self.pintar_fantasma(f)
            fx, fy = f["pos"]
            px, py = self.pac["pos"]
            if (fx - px) ** 2 + (fy - py) ** 2 < 15 ** 2:
                if self.asustados > 0:                                         # te lo comes
                    self.puntos += 200
                    f["pos"], f["espera"], f["ultima"] = list(self.centro(*f["casa"])), 3.0, None
                    f["dir"] = (0, 1)
                else:
                    self.vidas -= 1
                    if self.vidas <= 0:
                        self.fin("¡Te han atrapado los fantasmas!")
                        return
                    self.pac["pos"], self.pac["dir"] = list(self.centro(*self.salida_p)), (0, 0)
                    for k, g in enumerate(self.fantasmas):
                        g["pos"], g["espera"], g["ultima"] = list(self.centro(*g["casa"])), k * 1.5, None
                    return
        if not self.puntos_mapa:
            if self.nivel >= 3:
                self.ganar("¡Has limpiado los 3 laberintos!")
            else:
                self.nivel += 1
                self.montar()

    def pintar_pac(self, dt):
        self.pac["boca"] = (self.pac["boca"] + dt * 8) % 6.283
        abre = 0.08 + 0.32 * abs(__import_seno(self.pac["boca"]))
        dx, dy = self.pac["dir"] if self.pac["dir"] != (0, 0) else (1, 0)
        base = __import_angulo(dy, dx)
        x, y = self.pac["pos"]
        pts = [(x, y)]
        for k in range(13):
            a = base + abre + (6.283 - 2 * abre) * k / 12
            pts.append((x + 10 * __import_coseno(a), y + 10 * __import_seno(a)))
        self.poner_puntos(self.come, pts)

    def pintar_fantasma(self, f):
        x, y = f["pos"]
        f["cuerpo"].x, f["cuerpo"].y = x, y
        asustado = self.asustados > 0
        f["cuerpo"].color = ((0.2, 0.3, 1, 1) if not (asustado and self.asustados < 2 and int(self.asustados * 6) % 2)
                             else (1, 1, 1, 1)) if asustado else self.colores(f["color"])
        for k, o in enumerate(f["ojos"]):
            o.x, o.y = x - 4 + 8 * k + 1.5 * f["dir"][0], y + 3 + 1.5 * f["dir"][1]

    def colores(self, nombre):
        return {"rojo": (0.92, 0.26, 0.3, 1), "rosa": (1, 0.55, 0.85, 1), "cian": (0, 0.85, 1, 1),
                "naranja": (1, 0.6, 0.2, 1)}[nombre]
'''


def _limpio(t, n=80):
    return re.sub(r"[\"'\\{}<>\[\]\n\r]", "", str(t or ""))[:n]


def instrucciones(plan):
    g = plan.get("tipo") or "esquivar"
    if g == "esquivar":
        return f"Mueve a {plan['protagonista']} con el dedo: esquiva {plan['enemigo']} y recoge {plan['premio']}."
    return {
        "carreras": f"Toca a un lado de tu coche (o desliza) para cambiar de carril. Esquiva {plan['enemigo']} y "
                    f"recoge {plan['premio']}: turbo que aparta a los rivales.",
        "plataformas": f"Corre solo: toca para saltar (otra vez en el aire = doble salto; suelta pronto para saltar "
                       f"menos). Pisa {plan['enemigo']} y recoge {plan['premio']}.",
        "naves": f"Mueve la nave con el dedo: dispara sola. Recoge {plan['premio']} para el triple disparo.",
        "combate": "Mantén < y > para moverte y DEF para defenderte; PUÑO y PATADA para atacar. Con la barra azul "
                   "llena, la patada es un golpe ESPECIAL. Gana 2 rondas.",
        "retro": "Desliza (o toca hacia donde quieras ir) para guiar al comecocos. Come todos los puntos; las bolas "
                 "grandes asustan a los fantasmas.",
    }[g]


def codigo(plan, dibujos):
    """El programa completo del juego del género del plan."""
    g = plan.get("tipo") or "esquivar"
    cuerpo = {"carreras": CARRERAS, "plataformas": PLATAFORMAS, "naves": NAVES, "combate": COMBATE,
              "retro": RETRO}[g]
    instr = instrucciones(plan)
    lineas = "\n".join(f"        {k!r}: {v!r}," for k, v in dibujos.items())
    cabecera = (f"class Juego{g.capitalize()}(Juego):\n"
                f"    titulo = {_limpio(plan['titulo'], 40)!r}\n"
                f"    instrucciones = {_limpio(instr, 300)!r}\n"
                f"    sprites = {plan['carpeta'] if dibujos else ''!r}\n"
                f"    dibujos = {{\n{lineas}\n    }}\n")
    cuerpo = (cuerpo.replace("__import_seno", "math.sin").replace("__import_coseno", "math.cos")
              .replace("__import_angulo", "math.atan2")
              .replace("self.nivel = getattr_nivel = 1", "self.nivel = 1")
              .replace("self.salida_g = getattr_g = (col, fila)", "self.salida_g = (col, fila)"))
    return ("import math\n\nfrom motor_juegos_kira import Juego\n\n"
            f"# Juego de {NOMBRES[g].upper()} hecho por Kira (plantilla de nivel experto). Los dibujos los pinta su pintor\n"
            "# y se guardan en la carpeta «sprites»; para cambiar uno, cambia su descripción en «dibujos» y dile\n"
            "# «pinta los dibujos del juego». Todo lo demás (física, IA, dificultad) está aquí: cámbialo a tu gusto.\n\n\n"
            + cabecera + COMUN + cuerpo)
