# -*- coding: utf-8 -*-
"""
juegos_kira.py - Juegos de Kira escritos con su motor (motor_juegos_kira). Cada juego es un PROGRAMA de verdad:
puedes abrirlo en el editor, ver cómo está hecho, cambiarlo y guardarlo como tuyo.
"""

ROMPELADRILLOS = '''from motor_juegos_kira import Juego


class Rompeladrillos(Juego):
    titulo = "Rompeladrillos"
    instrucciones = "Mueve la pala con el dedo. Rompe todos los ladrillos sin que caiga la bola."

    def preparar(self):
        self.pala = self.rect(140, 40, 80, 14, "azul")
        self.nueva_bola()
        colores = ["rojo", "naranja", "amarillo", "verde", "cian"]
        for fila in range(5):
            for col in range(6):
                l = self.rect(12 + col * 57, 500 - fila * 26, 51, 20, colores[fila])
                l.datos["tipo"] = "ladrillo"

    def nueva_bola(self):
        self.bola = self.circulo(180, 120, 8, "negro")
        self.bola.vx, self.bola.vy = self.azar(-160, 160), 260

    def actualizar(self, dt):
        if self.dedo:
            self.pala.x = self.dedo[0] - self.pala.w / 2
            self.limitar(self.pala)
        b = self.bola
        if self.rebotar_en_bordes(b, suelo=False) == "abajo" or b.y < -20:
            self.vidas -= 1
            b.viva = False
            if self.vidas <= 0:
                self.fin("Se acabaron las bolas")
            else:
                self.nueva_bola()
            return
        if self.chocan(b, self.pala) and b.vy < 0:
            b.vy = -b.vy * 1.02
            b.vx += (b.x - self.pala.centro[0]) * 4     # según dónde pegue, sale más torcida
        for l in self.con_etiqueta("ladrillo"):
            if self.chocan(b, l):
                l.viva = False
                b.vy = -b.vy
                self.puntos += 10
                break
        if not self.con_etiqueta("ladrillo"):
            self.ganar("¡Todos los ladrillos rotos!")
'''

SERPIENTE = '''from motor_juegos_kira import Juego

CASILLA = 24


class Serpiente(Juego):
    titulo = "Serpiente"
    instrucciones = "Desliza el dedo para girar. Come las manzanas y no te muerdas la cola."

    def preparar(self):
        self.columnas, self.filas = self.ancho // CASILLA, self.alto // CASILLA - 2
        self.cuerpo = [(7, 12), (6, 12), (5, 12)]
        self.direccion = (1, 0)
        self.siguiente = (1, 0)
        self.reloj = 0.0
        self.manzana = None
        self.poner_manzana()

    def poner_manzana(self):
        while True:
            m = (self.azar_entero(0, self.columnas - 1), self.azar_entero(0, self.filas - 1))
            if m not in self.cuerpo:
                self.manzana = m
                return

    def al_deslizar(self, dx, dy):
        if abs(dx) > abs(dy):
            d = (1, 0) if dx > 0 else (-1, 0)
        else:
            d = (0, 1) if dy > 0 else (0, -1)
        if (d[0] + self.direccion[0], d[1] + self.direccion[1]) != (0, 0):   # no se puede dar media vuelta
            self.siguiente = d

    def actualizar(self, dt):
        self.reloj += dt
        if self.reloj < max(0.07, 0.16 - len(self.cuerpo) * 0.003):
            return
        self.reloj = 0.0
        self.direccion = self.siguiente
        cx, cy = self.cuerpo[0]
        cabeza = (cx + self.direccion[0], cy + self.direccion[1])
        if not (0 <= cabeza[0] < self.columnas and 0 <= cabeza[1] < self.filas) or cabeza in self.cuerpo:
            self.fin("¡Choque!")
            return
        self.cuerpo.insert(0, cabeza)
        if cabeza == self.manzana:
            self.puntos += 1
            self.poner_manzana()
        else:
            self.cuerpo.pop()
        self.dibujar_tablero()

    def dibujar_tablero(self):
        for p in self.piezas:
            p.viva = False
        self.rect(0, 0, self.columnas * CASILLA, self.filas * CASILLA, (0.92, 0.95, 0.92))
        mx, my = self.manzana
        self.circulo(mx * CASILLA + CASILLA / 2, my * CASILLA + CASILLA / 2, CASILLA / 2 - 2, "rojo")
        for i, (x, y) in enumerate(self.cuerpo):
            self.rect(x * CASILLA + 1, y * CASILLA + 1, CASILLA - 2, CASILLA - 2, "verde" if i else (0.1, 0.5, 0.25))
'''

ESQUIVA = '''from motor_juegos_kira import Juego


class Esquiva(Juego):
    titulo = "Esquiva meteoritos"
    instrucciones = "Arrastra la nave con el dedo y esquiva los meteoritos. Cuanto más aguantes, más puntos."

    def preparar(self):
        self.fondo = (0.06, 0.07, 0.14)
        self.nave = self.rect(165, 50, 30, 30, "cian")
        self.siguiente = 0.0
        for _ in range(40):                       # estrellas de fondo
            e = self.circulo(self.azar(0, self.ancho), self.azar(0, self.alto), self.azar(0.5, 1.6), (1, 1, 1, 0.6))
            e.vy = -self.azar(20, 60)
            e.datos["tipo"] = "estrella"

    def actualizar(self, dt):
        if self.dedo:
            self.nave.x += (self.dedo[0] - 15 - self.nave.x) * min(1, dt * 12)
            self.limitar(self.nave)
        for e in self.con_etiqueta("estrella"):
            if e.y < 0:
                e.y = self.alto
        self.siguiente -= dt
        if self.siguiente <= 0:
            self.siguiente = max(0.18, 0.9 - self.tiempo * 0.02)
            m = self.circulo(self.azar(10, self.ancho - 10), self.alto + 20, self.azar(10, 24), "naranja")
            m.vy = -self.azar(160, 260) - self.tiempo * 4
            m.datos["tipo"] = "meteorito"
        for m in self.con_etiqueta("meteorito"):
            if self.chocan(m, self.nave):
                self.fin("¡Impacto!")
            elif m.y < -30:
                m.viva = False
                self.puntos += 1
'''

SALTARIN = '''from motor_juegos_kira import Juego


class Saltarin(Juego):
    titulo = "Saltarín"
    instrucciones = "Toca para saltar y pasa por los huecos de las columnas."

    def preparar(self):
        self.gravedad = 900
        self.pajaro = self.circulo(90, 320, 14, "amarillo")
        self.pajaro.cae = True
        self.siguiente = 0.0

    def al_tocar(self, x, y):
        self.pajaro.vy = 330

    def actualizar(self, dt):
        self.siguiente -= dt
        if self.siguiente <= 0:
            self.siguiente = 1.6
            hueco = self.azar(160, 470)
            for y, h in ((0, hueco - 75), (hueco + 75, self.alto - hueco - 75)):
                c = self.rect(self.ancho, y, 50, h, "verde")
                c.vx = -140
                c.datos["tipo"] = "columna"
        p = self.pajaro
        if p.y < 0 or p.y > self.alto:
            self.fin("¡Te has caído!")
        for c in self.con_etiqueta("columna"):
            if self.chocan(p, c):
                self.fin("¡Choque!")
            if c.x + c.w < 0:
                c.viva = False
                if c.y == 0:
                    self.puntos += 1
'''

PONG = '''from motor_juegos_kira import Juego


class Pong(Juego):
    titulo = "Pong contra Kira"
    instrucciones = "Mueve tu pala (abajo) con el dedo. Gana quien llegue a 5."

    def preparar(self):
        self.tu = self.rect(140, 30, 80, 14, "azul")
        self.kira = self.rect(140, 596, 80, 14, "rosa")
        self.kira_puntos = 0
        self.saque(1)

    def saque(self, hacia):
        self.bola = self.circulo(180, 320, 9, "negro")
        self.bola.vx, self.bola.vy = self.azar(-120, 120), 240 * hacia

    def actualizar(self, dt):
        if self.dedo:
            self.tu.x = self.dedo[0] - self.tu.w / 2
            self.limitar(self.tu)
        b = self.bola
        objetivo = b.x - self.kira.w / 2                 # la «IA» de Kira sigue la bola, sin ser perfecta
        self.kira.x += max(-200 * dt, min(200 * dt, objetivo - self.kira.x))
        self.limitar(self.kira)
        if b.x - b.r < 0 or b.x + b.r > self.ancho:
            b.vx = -b.vx
        for pala, sentido in ((self.tu, 1), (self.kira, -1)):
            if self.chocan(b, pala) and b.vy * sentido < 0:
                b.vy = -b.vy * 1.05
                b.vx += (b.x - pala.centro[0]) * 5
        if b.y < 0 or b.y > self.alto:
            if b.y < 0:
                self.kira_puntos += 1
            else:
                self.puntos += 1
            b.viva = False
            if self.puntos >= 5:
                self.ganar("¡Le has ganado a Kira!")
            elif self.kira_puntos >= 5:
                self.fin("Ha ganado Kira")
            else:
                self.saque(1 if b.y > self.alto else -1)

    def marcador(self):
        if self.estado == "jugando":
            return f"Tú {self.puntos} - {self.kira_puntos} Kira"
        return super().marcador()
'''

PLANTILLA = '''from motor_juegos_kira import Juego


class MiJuego(Juego):
    titulo = "Mi juego"
    instrucciones = "Toca la pantalla para atrapar las estrellas."

    def preparar(self):
        # aquí creas las piezas del principio
        self.siguiente = 0.0

    def actualizar(self, dt):
        # esto se ejecuta 60 veces por segundo
        self.siguiente -= dt
        if self.siguiente <= 0:
            self.siguiente = 0.8
            e = self.circulo(self.azar(20, self.ancho - 20), self.alto, 16, "amarillo")
            e.vy = -150
            e.datos["tipo"] = "estrella"
        for e in self.con_etiqueta("estrella"):
            if e.y < 0:
                e.viva = False
                self.vidas -= 1
                if self.vidas <= 0:
                    self.fin("Se escaparon demasiadas")

    def al_tocar(self, x, y):
        for e in self.con_etiqueta("estrella"):
            if abs(e.x - x) < 30 and abs(e.y - y) < 30:
                e.viva = False
                self.puntos += 1
'''

JUEGOS = [
    {"id": "rompeladrillos", "titulo": "Rompeladrillos", "codigo": ROMPELADRILLOS},
    {"id": "serpiente", "titulo": "Serpiente", "codigo": SERPIENTE},
    {"id": "esquiva", "titulo": "Esquiva meteoritos", "codigo": ESQUIVA},
    {"id": "saltarin", "titulo": "Saltarín", "codigo": SALTARIN},
    {"id": "pong", "titulo": "Pong contra Kira", "codigo": PONG},
]


def buscar(id_):
    return next((j for j in JUEGOS if j["id"] == id_), None)


def cargar(codigo, semilla=None):
    """Ejecuta el programa en modo seguro y devuelve (juego, None) o (None, motivo)."""
    import ejecutor_kira as ej
    import motor_juegos_kira as mj
    r = ej.ejecutar(codigo, limite=3)
    if not r["ok"]:
        return None, r["error"]
    clase = mj.buscar_juego(r["globales"])
    if clase is None:
        return None, "El programa no define ningún juego (una clase que herede de Juego)."
    try:
        return ej.con_limite(clase, 1.0, semilla), None
    except Exception as e:
        return None, f"Error al preparar el juego: {type(e).__name__}: {e}"
