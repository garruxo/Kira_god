# -*- coding: utf-8 -*-
"""
saber_avanzado_kira.py - PROGRAMACIÓN AVANZADA y DISEÑO para Kira (lógica PURA: sin red, sin Kivy, sin archivos).

  RECETAS   : técnicas escritas como MÓDULOS completos de Kira (con registrar()), igual que recetas_ingenieria_kira:
              patrones de programación avanzada (máquina de estados, eventos, ECS, corrutinas, decoradores, parsers,
              deshacer/rehacer, generadores) y DISEÑO por código (paletas armónicas, contraste accesible, escalas
              tipográficas, rejillas, curvas de animación, sistemas L, Voronoi, tramado, colapso de función de onda,
              muestreo de Poisson). Cada una trae su "prueba": tests/test_saber_avanzado.py la pasa por el
              laboratorio del móvil, el del PC y el editor seguro.
  CONCEPTOS : fichas de teoría de diseño gráfico, de interfaces (UX), de juegos, de animación, de fotografía y de
              cómo pedirle cosas al pintor, y de programación avanzada. «estudia diseño» / «estudia programación
              avanzada» las guardan en el baúl sin internet.
saber_mejoras_kira las usa como guía (la más parecida al pedido) al programar mejoras, programas y EXPERIMENTOS.
"""

RECETAS = [
# =====================================================================================================================
#  PROGRAMACIÓN AVANZADA
# =====================================================================================================================
{
"id": "maquina_estados",
"titulo": "Máquina de estados finita (puertas, personajes, menús)",
"area": "Programación avanzada",
"temas": "maquina estados finita fsm transiciones estado puerta personaje enemigo ia juego menu flujo eventos "
         "automata patron state",
"idea": "Un objeto está siempre en UN estado y solo cambia con eventos permitidos: una tabla (estado, evento) -> "
        "nuevo estado. Así no hay combinaciones imposibles (una puerta cerrada con llave no se abre sin "
        "desbloquearla) y añadir comportamientos es añadir filas, no más «if». Es como se programan los enemigos "
        "de los juegos (patrulla, persigue, ataca, huye) y los flujos de pantallas.",
"complejidad": "cada evento O(1) (una consulta a la tabla); memoria O(transiciones)",
"codigo": r'''
class MaquinaEstados:
    """Tabla de transiciones: {(estado, evento): nuevo_estado}. Lo que no está en la tabla no se permite."""

    def __init__(self, inicial, transiciones):
        self.estado = inicial
        self.tabla = dict(transiciones)
        self.historia = [inicial]

    def permitidos(self):
        return sorted(e for (s, e) in self.tabla if s == self.estado)

    def evento(self, ev):
        nuevo = self.tabla.get((self.estado, ev))
        if nuevo is None:
            return False
        self.estado = nuevo
        self.historia.append(nuevo)
        return True


PUERTA = {("cerrada", "abrir"): "abierta", ("abierta", "cerrar"): "cerrada",
          ("cerrada", "echar llave"): "con llave", ("con llave", "quitar llave"): "cerrada"}


def registrar():
    def puerta(texto):
        # «puerta: abrir, cerrar, echar llave, abrir»
        m = MaquinaEstados("cerrada", PUERTA)
        lineas = []
        for ev in [e.strip() for e in texto.split(",") if e.strip()]:
            antes = m.estado
            if m.evento(ev):
                lineas.append(f"{ev}: {antes} -> {m.estado}")
            else:
                lineas.append(f"{ev}: NO se puede estando {antes} (se puede: {', '.join(m.permitidos())})")
        lineas.append("Estado final: " + m.estado)
        return "\n".join(lineas)
    return {"puerta": puerta}
''',
"prueba": [("puerta", "abrir, cerrar, echar llave, abrir", "abrir: NO se puede estando con llave"),
           ("puerta", "abrir, cerrar, echar llave, abrir", "Estado final: con llave")],
},
{
"id": "bus_eventos",
"titulo": "Bus de eventos (patrón observador / publicar-suscribir)",
"area": "Programación avanzada",
"temas": "bus eventos observador observer publicar suscribir pubsub desacoplar notificaciones oyentes callbacks "
         "señales mensajes patron",
"idea": "Las piezas no se llaman entre sí: publican un evento con un nombre y quien esté suscrito a ese nombre "
        "reacciona. Así el marcador de un juego no necesita conocer al enemigo, solo escuchar «enemigo_muerto». "
        "Desacopla el código: se añaden oyentes sin tocar a quien publica. Ojo con el orden y con olvidar "
        "desuscribirse.",
"complejidad": "publicar O(oyentes de ese evento); suscribir O(1)",
"codigo": r'''
class Bus:
    def __init__(self):
        self.oyentes = {}

    def suscribir(self, nombre, funcion):
        self.oyentes.setdefault(nombre, []).append(funcion)

        def quitar():                                              # para desuscribirse
            self.oyentes[nombre] = [f for f in self.oyentes[nombre] if f is not funcion]
        return quitar

    def publicar(self, nombre, **datos):
        return [f(**datos) for f in list(self.oyentes.get(nombre, []))]


def registrar():
    def partida(texto):
        # «bus eventos: 3» -> 3 enemigos derribados: el marcador, los logros y el sonido escuchan sin conocerse
        n = int(texto.strip() or "3")
        bus, estado, log = Bus(), {"puntos": 0}, []

        def marcador(puntos):
            estado["puntos"] += puntos
            return f"marcador: {estado['puntos']}"

        def logros(puntos):
            return "logro: ¡primer derribo!" if estado["puntos"] == puntos else "logros: nada nuevo"

        quitar_sonido = bus.suscribir("derribo", lambda puntos: "sonido: ¡bum!")
        bus.suscribir("derribo", marcador)
        bus.suscribir("derribo", logros)
        for i in range(n):
            if i == 1:
                quitar_sonido()                                      # se desuscribe a mitad de partida
            log.append(f"derribo {i + 1} -> " + "; ".join(bus.publicar("derribo", puntos=10)))
        log.append(f"Total: {estado['puntos']} puntos")
        return "\n".join(log)
    return {"bus eventos": partida}
''',
"prueba": [("bus eventos", "3", "derribo 1 -> sonido: ¡bum!; marcador: 10; logro: ¡primer derribo!"),
           ("bus eventos", "3", "Total: 30 puntos")],
},
{
"id": "ecs",
"titulo": "Entidad-Componente-Sistema (ECS), la arquitectura de los motores de juegos",
"area": "Programación avanzada",
"temas": "ecs entidad componente sistema arquitectura motor juegos composicion herencia datos fisica gravedad "
         "movimiento rendimiento",
"idea": "En vez de una jerarquía de clases (Enemigo hereda de Personaje…), una ENTIDAD es solo un número; sus "
        "COMPONENTES son datos sueltos (posición, velocidad, vida) y los SISTEMAS son funciones que recorren las "
        "entidades que tienen ciertos componentes. Componer en vez de heredar: un cofre con velocidad ya se mueve, "
        "sin tocar ninguna clase. Lo usan Unity DOTS, Bevy y muchos motores.",
"complejidad": "cada sistema O(entidades con sus componentes) por fotograma",
"codigo": r'''
class Mundo:
    def __init__(self):
        self.siguiente = 0
        self.comp = {}                      # nombre del componente -> {entidad: datos}

    def crear(self, **componentes):
        e = self.siguiente
        self.siguiente += 1
        for nombre, datos in componentes.items():
            self.comp.setdefault(nombre, {})[e] = dict(datos)
        return e

    def con(self, *nombres):
        """Entidades que tienen TODOS esos componentes."""
        grupos = [set(self.comp.get(n, {})) for n in nombres]
        return sorted(set.intersection(*grupos)) if grupos else []


def sistema_gravedad(m, dt):
    for e in m.con("velocidad", "peso"):
        m.comp["velocidad"][e]["vy"] -= 9.8 * dt


def sistema_movimiento(m, dt):
    for e in m.con("posicion", "velocidad"):
        p, v = m.comp["posicion"][e], m.comp["velocidad"][e]
        p["x"] += v["vx"] * dt
        p["y"] = max(0.0, p["y"] + v["vy"] * dt)


def registrar():
    def simula(texto):
        # «ecs: 10» -> 10 pasos de 0,1 s
        pasos = int(texto.strip() or "10")
        m = Mundo()
        m.crear(nombre={"n": "pelota"}, posicion={"x": 0.0, "y": 10.0}, velocidad={"vx": 2.0, "vy": 0.0}, peso={})
        m.crear(nombre={"n": "nube"}, posicion={"x": 0.0, "y": 50.0}, velocidad={"vx": 1.0, "vy": 0.0})
        m.crear(nombre={"n": "casa"}, posicion={"x": 5.0, "y": 0.0})
        for _ in range(pasos):
            sistema_gravedad(m, 0.1)
            sistema_movimiento(m, 0.1)
        lineas = []
        for e in sorted(m.comp["nombre"]):
            p = m.comp["posicion"][e]
            tiene = ", ".join(sorted(n for n in m.comp if e in m.comp[n] and n != "nombre"))
            lineas.append(f"{m.comp['nombre'][e]['n']}: x={p['x']:.1f} y={p['y']:.1f}  [{tiene}]")
        return "\n".join(lineas)
    return {"ecs": simula}
''',
"prueba": [("ecs", "10", "pelota: x=2.0 y=4.6"), ("ecs", "10", "nube: x=1.0 y=50.0"),
           ("ecs", "10", "casa: x=5.0 y=0.0  [posicion]")],
},
{
"id": "corrutinas",
"titulo": "Corrutinas con generadores: un planificador cooperativo",
"area": "Programación avanzada",
"temas": "corrutinas generadores yield planificador cooperativo tareas concurrencia asincronia asyncio bucle "
         "eventos esperar turnos",
"idea": "Un generador se PAUSA en cada yield y sigue donde se quedó. Si cada tarea cede el turno con yield, un "
        "planificador puede turnarlas sin hilos: es la idea de asyncio (async/await son corrutinas con yield por "
        "debajo). La tarea puede decir cuántos turnos quiere dormir. Cooperativo: si una tarea no cede, bloquea a "
        "todas.",
"complejidad": "cada cambio de tarea O(log n) con una cola de prioridad por «despertar»",
"codigo": r'''
import heapq


def tarea(nombre, veces, espera):
    for i in range(1, veces + 1):
        yield f"{nombre} {i}/{veces}", espera       # lo que hace y cuántos turnos duerme


def planificar(tareas):
    reloj, cola, orden, log = 0, [], 0, []
    for t in tareas:
        heapq.heappush(cola, (0, orden, t))
        orden += 1
    while cola:
        reloj, _, t = heapq.heappop(cola)
        try:
            hecho, espera = next(t)
        except StopIteration:
            continue
        log.append(f"t={reloj}: {hecho}")
        heapq.heappush(cola, (reloj + espera, orden, t))
        orden += 1
    return log


def registrar():
    def corre(texto):
        # «corrutinas: descarga 3 2, musica 4 1»: nombre, veces, turnos de espera
        tareas = []
        for trozo in texto.split(","):
            p = trozo.split()
            if len(p) == 3 and p[1].isdigit() and p[2].isdigit():
                tareas.append(tarea(p[0], int(p[1]), int(p[2])))
        if not tareas:
            raise ValueError("Uso: corrutinas: descarga 3 2, musica 4 1")
        return "\n".join(planificar(tareas))
    return {"corrutinas": corre}
''',
"prueba": [("corrutinas", "descarga 3 2, musica 4 1", "t=0: descarga 1/3\nt=0: musica 1/4\nt=1: musica 2/4"),
           ("corrutinas", "descarga 3 2, musica 4 1", "t=4: descarga 3/3")],
},
{
"id": "decoradores",
"titulo": "Decoradores: memoizar y contar llamadas sin tocar la función",
"area": "Programación avanzada",
"temas": "decoradores decorador memoizar memoizacion cache funciones orden superior wraps contar llamadas "
         "fibonacci metaprogramacion lru_cache",
"idea": "Un decorador es una función que recibe una función y devuelve otra que la envuelve: añade "
        "comportamiento (caché, medir, reintentar, comprobar permisos) sin cambiar el código de dentro. "
        "@memoizar recuerda resultados ya calculados; con Fibonacci pasa de un número exponencial de llamadas a "
        "una por valor. functools.wraps conserva el nombre de la original.",
"complejidad": "fib sin caché O(φ^n) llamadas; con caché O(n)",
"codigo": r'''
import functools


def contar(f):
    @functools.wraps(f)
    def envoltura(*a):
        envoltura.llamadas += 1
        return f(*a)
    envoltura.llamadas = 0
    return envoltura


def memoizar(f):
    guardado = {}

    @functools.wraps(f)
    def envoltura(*a):
        if a not in guardado:
            guardado[a] = f(*a)
        return guardado[a]
    return envoltura


@contar
def fib_lento(n):
    return n if n < 2 else fib_lento(n - 1) + fib_lento(n - 2)


@memoizar
@contar
def fib_rapido(n):
    return n if n < 2 else fib_rapido(n - 1) + fib_rapido(n - 2)


def registrar():
    def compara(texto):
        n = min(25, int(texto.strip() or "20"))
        fib_lento.llamadas = 0
        a = fib_lento(n)
        b = fib_rapido(n)
        llamadas = fib_rapido.__wrapped__.llamadas
        return (f"fib({n}) = {a}\nSin memoizar: {fib_lento.llamadas} llamadas\n"
                f"Memoizada: {llamadas} llamadas (resultado {b})")
    return {"decoradores": compara}
''',
"prueba": [("decoradores", "20", "fib(20) = 6765"), ("decoradores", "20", "Sin memoizar: 21891 llamadas"),
           ("decoradores", "20", "Memoizada: 21 llamadas")],
},
{
"id": "combinadores",
"titulo": "Combinadores de parsers: una calculadora con precedencia hecha de piezas",
"area": "Programación avanzada",
"temas": "parser combinadores analizador sintactico gramatica expresiones calculadora precedencia parentesis "
         "programacion funcional orden superior lenguaje",
"idea": "Un parser es una función (texto, posición) -> (valor, nueva posición) o None. Los COMBINADORES los "
        "juntan: secuencia, alternativa, repetir. Con unas pocas piezas se escribe la gramática casi como en papel: "
        "expr = término (('+'|'-') término)*, término = factor (('*'|'/') factor)*, factor = número | '(' expr ')'. "
        "Así funcionan Parsec y muchos lenguajes pequeños.",
"complejidad": "O(n) para estas gramáticas sin retroceso",
"codigo": r'''
from fractions import Fraction


def espacio(t, i):
    while i < len(t) and t[i] == " ":
        i += 1
    return i


def simbolo(c):
    def p(t, i):
        i = espacio(t, i)
        return (c, i + 1) if t.startswith(c, i) else None
    return p


def numero(t, i):
    i = espacio(t, i)
    j = i
    while j < len(t) and (t[j].isdigit() or t[j] == "."):
        j += 1
    return (Fraction(t[i:j]), j) if j > i else None


def alternativa(*ps):
    def p(t, i):
        for q in ps:
            r = q(t, i)
            if r:
                return r
        return None
    return p


def cadena(operando, operadores):
    """operando (op operando)*, aplicando de izquierda a derecha."""
    def p(t, i):
        r = operando(t, i)
        if not r:
            return None
        valor, i = r
        while True:
            o = alternativa(*[simbolo(c) for c in operadores])(t, i)
            if not o:
                return valor, i
            d = operando(t, o[1])
            if not d:
                return None
            valor = operadores[o[0]](valor, d[0])
            i = d[1]
    return p


def entre_parentesis(t, i):
    a = simbolo("(")(t, i)
    if not a:
        return None
    e = expresion(t, a[1])
    if not e:
        return None
    c = simbolo(")")(t, e[1])
    return (e[0], c[1]) if c else None


factor = alternativa(numero, entre_parentesis)
termino = cadena(factor, {"*": lambda a, b: a * b, "/": lambda a, b: a / b})


def expresion(t, i):
    return cadena(termino, {"+": lambda a, b: a + b, "-": lambda a, b: a - b})(t, i)


def registrar():
    def calcula(texto):
        r = expresion(texto, 0)
        if not r or espacio(texto, r[1]) != len(texto):
            return "No entiendo la expresión (usa números, + - * / y paréntesis)."
        v = r[0]
        return f"{texto.strip()} = {v.numerator if v.denominator == 1 else v}" + \
            ("" if v.denominator == 1 else f" ≈ {float(v):.4f}")
    return {"combinadores": calcula}
''',
"prueba": [("combinadores", "2 * (3 + 4) - 5", "= 9"), ("combinadores", "1/3 + 1/6", "= 1/2"),
           ("combinadores", "2 + * 3", "No entiendo")],
},
{
"id": "deshacer_rehacer",
"titulo": "Deshacer y rehacer (patrón comando), como en un editor",
"area": "Programación avanzada",
"temas": "deshacer rehacer undo redo comando command patron editor historial pila acciones dibujo",
"idea": "Cada acción es un objeto COMANDO que sabe hacerse y deshacerse. Una pila guarda lo hecho y otra lo "
        "deshecho: deshacer pasa el último de la primera a la segunda; rehacer, al revés; y una acción nueva vacía "
        "la de rehacer (la historia se bifurca). Es como funcionan los editores de texto y de dibujo.",
"complejidad": "deshacer y rehacer O(1) por comando; memoria O(historial)",
"codigo": r'''
class Escribir:
    def __init__(self, texto):
        self.texto = texto

    def hacer(self, doc):
        doc.append(self.texto)

    def deshacer(self, doc):
        doc.pop()


class Historial:
    def __init__(self):
        self.doc, self.hechos, self.deshechos = [], [], []

    def ejecutar(self, cmd):
        cmd.hacer(self.doc)
        self.hechos.append(cmd)
        self.deshechos.clear()

    def deshacer(self):
        if not self.hechos:
            return False
        cmd = self.hechos.pop()
        cmd.deshacer(self.doc)
        self.deshechos.append(cmd)
        return True

    def rehacer(self):
        if not self.deshechos:
            return False
        cmd = self.deshechos.pop()
        cmd.hacer(self.doc)
        self.hechos.append(cmd)
        return True


def registrar():
    def editor(texto):
        # «deshacer: escribe hola; escribe mundo; deshaz; rehaz; deshaz; escribe kira; rehaz»
        h, log = Historial(), []
        for paso in [p.strip() for p in texto.split(";") if p.strip()]:
            if paso.startswith("escribe "):
                h.ejecutar(Escribir(paso[8:]))
            elif paso == "deshaz":
                if not h.deshacer():
                    paso += " (nada que deshacer)"
            elif paso == "rehaz":
                if not h.rehacer():
                    paso += " (nada que rehacer)"
            log.append(f"{paso:30} -> {' '.join(h.doc) or '(vacío)'}")
        return "\n".join(log)
    return {"deshacer": editor}
''',
"prueba": [("deshacer", "escribe hola; escribe mundo; deshaz; rehaz; deshaz; escribe kira; rehaz",
            "rehaz (nada que rehacer)       -> hola kira")],
},
{
"id": "generadores_perezosos",
"titulo": "Tuberías perezosas con generadores (datos infinitos sin gastar memoria)",
"area": "Programación avanzada",
"temas": "generadores perezoso lazy iteradores tuberia pipeline infinito itertools islice memoria flujo datos "
         "streaming",
"idea": "Un generador produce los valores de uno en uno, cuando se piden. Encadenando generadores (filtrar, "
        "transformar, tomar los primeros) se procesa un flujo enorme o INFINITO con memoria constante: solo existe "
        "el valor que está pasando por la tubería. Es la idea de los streams y de itertools.",
"complejidad": "memoria O(1) por etapa; tiempo O(lo que se consume)",
"codigo": r'''
import itertools


def naturales(desde=2):
    n = desde
    while True:
        yield n
        n += 1


def es_primo(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def registrar():
    def tuberia(texto):
        # «perezoso: 8» -> los 8 primeros primos gemelos (p y p+2 primos), de un flujo infinito
        n = min(50, int(texto.strip() or "8"))
        primos = (p for p in naturales() if es_primo(p))
        gemelos = ((p, p + 2) for p in primos if es_primo(p + 2))
        lista = list(itertools.islice(gemelos, n))
        return f"Primeros {n} primos gemelos: " + ", ".join(f"({a},{b})" for a, b in lista)
    return {"perezoso": tuberia}
''',
"prueba": [("perezoso", "8", "(3,5), (5,7), (11,13), (17,19), (29,31), (41,43), (59,61), (71,73)")],
},
# =====================================================================================================================
#  DISEÑO POR CÓDIGO
# =====================================================================================================================
{
"id": "paleta_armonica",
"titulo": "Paletas de color armónicas (complementaria, análoga, tríada, tétrada)",
"area": "Diseño: color y tipografía",
"temas": "paleta colores armonia complementario analogos triada tetrada rueda cromatica hsl hex diseño marca web "
         "app tono saturacion",
"idea": "En la rueda de color (tono H de 0 a 360°), los colores que se llevan bien están a distancias fijas: "
        "complementario a 180°, análogos a ±30°, tríada a 120° y tétrada a 90°. Se cambia el TONO y se conservan "
        "saturación y luminosidad, así la paleta no desentona. Regla 60-30-10: 60 % color dominante, 30 % "
        "secundario, 10 % acento.",
"complejidad": "O(1) por color",
"codigo": r'''
import colorsys

ARMONIAS = {"complementaria": [0, 180], "analoga": [-30, 0, 30], "triada": [0, 120, 240],
            "tetrada": [0, 90, 180, 270], "dividida": [0, 150, 210]}


def hex_a_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError("El color va en hexadecimal: #3366cc")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb_a_hex(r, g, b):
    return "#" + "".join(f"{round(v * 255):02x}" for v in (r, g, b))


def paleta(color, armonia):
    r, g, b = hex_a_rgb(color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return [rgb_a_hex(*colorsys.hls_to_rgb((h + d / 360) % 1, l, s)) for d in ARMONIAS[armonia]]


def registrar():
    def pide(texto):
        # «paleta: #3366cc triada»
        p = texto.split()
        if not p:
            raise ValueError("Uso: paleta: #3366cc triada")
        armonia = (p[1] if len(p) > 1 else "complementaria").replace("á", "a")
        if armonia not in ARMONIAS:
            return "Armonías: " + ", ".join(ARMONIAS)
        cols = paleta(p[0], armonia)
        usos = ["dominante (60 %)", "secundario (30 %)", "acento (10 %)", "extra", "extra"]
        return f"Paleta {armonia} de {p[0]}:\n" + "\n".join(f"  {c}  {u}" for c, u in zip(cols, usos))
    return {"paleta": pide}
''',
"prueba": [("paleta", "#3366cc triada", "#3366cc  dominante"), ("paleta", "#3366cc triada", "#cc3366"),
           ("paleta", "#3366cc complementaria", "#cc9933")],
},
{
"id": "contraste_wcag",
"titulo": "Contraste accesible (WCAG): ¿se lee bien este texto?",
"area": "Diseño: color y tipografía",
"temas": "contraste accesibilidad wcag legibilidad texto fondo luminancia relativa aa aaa daltonismo colores "
         "lectura web app",
"idea": "La legibilidad depende del contraste de LUMINANCIA, no del tono. Se calcula la luminancia relativa de "
        "cada color (deshaciendo la curva sRGB) y la razón (L1 + 0,05) / (L2 + 0,05), de 1:1 a 21:1. WCAG pide "
        "4,5:1 para texto normal (AA), 3:1 para texto grande (18 pt o 14 pt en negrita) y 7:1 para AAA.",
"complejidad": "O(1)",
"codigo": r'''
def canal(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(h):
    h = h.strip().lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def razon(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def registrar():
    def mide(texto):
        # «contraste: #777777 #ffffff» (texto y fondo)
        p = texto.split()
        if len(p) != 2:
            raise ValueError("Uso: contraste: #777777 #ffffff")
        r = razon(p[0], p[1])
        notas = [("texto normal AA (4,5)", r >= 4.5), ("texto grande AA (3)", r >= 3), ("AAA (7)", r >= 7)]
        return f"Contraste {r:.2f}:1\n" + "\n".join(f"  {n}: {'sí' if v else 'NO'}" for n, v in notas)
    return {"contraste": mide}
''',
"prueba": [("contraste", "#777777 #ffffff", "Contraste 4.48:1"), ("contraste", "#777777 #ffffff", "texto normal AA (4,5): NO"),
           ("contraste", "#000000 #ffffff", "Contraste 21.00:1")],
},
{
"id": "escala_tipografica",
"titulo": "Escala tipográfica modular (tamaños de letra que combinan)",
"area": "Diseño: color y tipografía",
"temas": "tipografia escala modular tamaños letra fuente jerarquia titulos h1 h2 cuerpo proporcion tercera "
         "cuarta aurea interlineado",
"idea": "En vez de elegir tamaños a ojo, se parte de un tamaño base (el del texto) y se multiplica por una razón "
        "fija: 1,2 (tercera menor), 1,25 (tercera mayor), 1,333 (cuarta), 1,5 o 1,618 (áurea). Los títulos suben "
        "potencias y las notas bajan. La jerarquía queda clara y coherente. Interlineado: ~1,5 para cuerpo, "
        "~1,2 para títulos.",
"complejidad": "O(niveles)",
"codigo": r'''
NIVELES = [("nota", -1), ("cuerpo", 0), ("h4", 1), ("h3", 2), ("h2", 3), ("h1", 4), ("portada", 5)]


def escala(base, razon):
    return [(n, round(base * razon ** k, 1)) for n, k in NIVELES]


def registrar():
    def pide(texto):
        # «escala tipografica: 16 1.25»
        p = texto.replace(",", ".").split()
        base = float(p[0]) if p else 16.0
        razon = float(p[1]) if len(p) > 1 else 1.25
        lineas = [f"Base {base:g} px, razón {razon:g}:"]
        for n, tam in escala(base, razon):
            lineas.append(f"  {n:8} {tam:6.1f} px  interlineado {round(tam * (1.5 if n in ('nota', 'cuerpo') else 1.2))} px")
        return "\n".join(lineas)
    return {"escala tipografica": pide}
''',
"prueba": [("escala tipografica", "16 1.25", "h1         39.1 px"), ("escala tipografica", "16 1.25", "cuerpo     16.0 px  interlineado 24 px")],
},
{
"id": "rejilla",
"titulo": "Rejilla de columnas (maquetar web y apps con orden)",
"area": "Diseño: composición e interfaces",
"temas": "rejilla grid columnas maqueta layout margen medianil gutter responsive movil web app alineacion "
         "composicion diseño",
"idea": "Una rejilla reparte el ancho en columnas iguales separadas por medianiles y con márgenes a los lados; "
        "todo se alinea a ellas, y por eso el diseño se ve ordenado. Móvil: 4 columnas, márgenes y medianil de "
        "16 px; tableta: 8; escritorio: 12. Un elemento ocupa n columnas: n·col + (n−1)·medianil.",
"complejidad": "O(columnas)",
"codigo": r'''
def rejilla(ancho, columnas, medianil, margen):
    col = (ancho - 2 * margen - (columnas - 1) * medianil) / columnas
    if col <= 0:
        raise ValueError("No caben tantas columnas en ese ancho.")
    return col


def registrar():
    def pide(texto):
        # «rejilla: 360 4 16 16» -> ancho, columnas, medianil, margen
        p = [float(x) for x in texto.split()]
        ancho, columnas = p[0], int(p[1] if len(p) > 1 else 4)
        medianil = p[2] if len(p) > 2 else 16
        margen = p[3] if len(p) > 3 else medianil
        col = rejilla(ancho, columnas, medianil, margen)
        lineas = [f"{columnas} columnas de {col:.1f} px (medianil {medianil:g}, margen {margen:g})"]
        for n in range(1, columnas + 1):
            x = margen
            lineas.append(f"  ocupa {n:2}: {n * col + (n - 1) * medianil:7.1f} px (empieza en x={x:g})")
        return "\n".join(lineas)
    return {"rejilla": pide}
''',
"prueba": [("rejilla", "360 4 16 16", "4 columnas de 70.0 px"), ("rejilla", "360 4 16 16", "ocupa  4:   328.0 px")],
},
{
"id": "curvas_animacion",
"titulo": "Curvas de animación (easing): que el movimiento se sienta natural",
"area": "Diseño: animación y movimiento",
"temas": "animacion easing curvas suavizado entrada salida ease in out rebote elastico interpolar movimiento "
         "transiciones interfaz juego",
"idea": "Nada en el mundo real arranca y frena de golpe. Una curva de easing transforma el tiempo lineal t∈[0,1] "
        "en progreso: ease-in acelera (t²), ease-out frena (1−(1−t)²), ease-in-out hace las dos, y las de rebote "
        "o elásticas exageran con gracia. Para interfaces: salidas rápidas (~200 ms) con ease-out y entradas con "
        "ease-in-out.",
"complejidad": "O(1) por fotograma",
"codigo": r'''
import math

CURVAS = {
    "lineal": lambda t: t,
    "ease-in": lambda t: t * t,
    "ease-out": lambda t: 1 - (1 - t) ** 2,
    "ease-in-out": lambda t: 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2,
    "rebote": None,
    "elastica": lambda t: t if t in (0, 1) else 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1,
}


def rebote(t):
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


CURVAS["rebote"] = rebote


def registrar():
    def dibuja(texto):
        # «animacion: ease-in-out»: cómo avanza un objeto en 11 fotogramas
        nombre = texto.strip().lower() or "ease-in-out"
        if nombre not in CURVAS:
            return "Curvas: " + ", ".join(CURVAS)
        f = CURVAS[nombre]
        lineas = [f"Curva {nombre} (cada fila es un fotograma):"]
        for i in range(11):
            v = f(i / 10)
            lineas.append(f"  t={i / 10:.1f} {v:5.2f} |" + " " * max(0, round(v * 30)) + "●")
        return "\n".join(lineas)
    return {"animacion": dibuja}
''',
"prueba": [("animacion", "ease-in-out", "t=0.5  0.50"), ("animacion", "ease-out", "t=0.5  0.75"),
           ("animacion", "rebote", "t=1.0  1.00")],
},
{
"id": "sistema_l",
"titulo": "Sistemas L: plantas y fractales que crecen con reglas",
"area": "Diseño: generativo y procedural",
"temas": "sistema l lindenmayer planta arbol fractal koch copo procedural generativo reglas tortuga crecer "
         "vegetacion naturaleza",
"idea": "Se parte de una palabra (axioma) y en cada generación se reescribe cada letra con su regla. Luego una "
        "«tortuga» la lee como dibujo: F avanza, + y − giran, [ y ] guardan y recuperan la posición (ramas). Con "
        "dos reglas salen copos de Koch, helechos o árboles: así se genera la vegetación en muchos juegos.",
"complejidad": "la palabra crece exponencialmente con las generaciones (por eso pocas)",
"codigo": r'''
import math

SISTEMAS = {
    "koch": ("F", {"F": "F+F-F-F+F"}, 90),
    "planta": ("X", {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"}, 25),
    "dragon": ("FX", {"X": "X+YF+", "Y": "-FX-Y"}, 90),
}


def crecer(axioma, reglas, n):
    w = axioma
    for _ in range(n):
        w = "".join(reglas.get(c, c) for c in w)
    return w


def tortuga(palabra, angulo):
    x = y = 0.0
    a = 90.0
    pila, segmentos = [], []
    for c in palabra:
        if c == "F":
            nx, ny = x + math.cos(math.radians(a)), y + math.sin(math.radians(a))
            segmentos.append(((x, y), (nx, ny)))
            x, y = nx, ny
        elif c == "+":
            a += angulo
        elif c == "-":
            a -= angulo
        elif c == "[":
            pila.append((x, y, a))
        elif c == "]":
            x, y, a = pila.pop()
    return segmentos


def registrar():
    def genera(texto):
        # «sistema l: koch 2»
        p = texto.split()
        nombre = p[0] if p else "koch"
        n = min(6, int(p[1])) if len(p) > 1 else 2
        if nombre not in SISTEMAS:
            return "Sistemas: " + ", ".join(SISTEMAS)
        ax, reglas, ang = SISTEMAS[nombre]
        w = crecer(ax, reglas, n)
        seg = tortuga(w, ang)
        xs = [q[0] for s in seg for q in s] or [0]
        ys = [q[1] for s in seg for q in s] or [0]
        return (f"{nombre}, {n} generaciones: {len(w)} letras, {len(seg)} trazos\n"
                f"Ocupa {max(xs) - min(xs):.0f} x {max(ys) - min(ys):.0f} pasos\nPrincipio: {w[:60]}")
    return {"sistema l": genera}
''',
"prueba": [("sistema l", "koch 2", "koch, 2 generaciones: 49 letras, 25 trazos"),
           ("sistema l", "planta 3", "planta, 3 generaciones")],
},
{
"id": "voronoi",
"titulo": "Diagrama de Voronoi: regiones, mapas y texturas orgánicas",
"area": "Diseño: generativo y procedural",
"temas": "voronoi celdas regiones semillas mapa territorios textura organica piedra procedural generativo "
         "vecino mas cercano diseño",
"idea": "Se reparten unas semillas y cada punto del plano pertenece a la semilla más cercana. Salen celdas como "
        "de piedra, piel de jirafa o países de un mapa de fantasía. Cambiando la distancia (Manhattan en vez de "
        "euclídea) cambia el estilo. La distancia a la segunda semilla más cercana marca los bordes (texturas).",
"complejidad": "ingenuo O(píxeles × semillas); con Fortune, O(n log n) para el diagrama",
"codigo": r'''
import random

LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def voronoi(ancho, alto, n, semilla, manhattan=False):
    azar = random.Random(semilla)
    sem = [(azar.uniform(0, ancho), azar.uniform(0, alto)) for _ in range(n)]
    filas, cuenta = [], [0] * n
    for y in range(alto):
        fila = ""
        for x in range(ancho):
            d = [(abs(x - sx) + abs(y - sy)) if manhattan else (x - sx) ** 2 + (y - sy) ** 2 for sx, sy in sem]
            orden = sorted(range(n), key=d.__getitem__)
            a, b = d[orden[0]], d[orden[1]] if n > 1 else 1e9
            cuenta[orden[0]] += 1
            fila += "·" if n > 1 and (b - a) < (1.5 if manhattan else 12) else LETRAS[orden[0] % 26]
        filas.append(fila)
    return filas, cuenta


def registrar():
    def dibuja(texto):
        # «voronoi: 5 semilla 3» (opcional «manhattan»)
        p = texto.split()
        n = max(1, min(12, int(p[0]))) if p and p[0].isdigit() else 5
        semilla = int(p[p.index("semilla") + 1]) if "semilla" in p else 1
        filas, cuenta = voronoi(40, 16, n, semilla, "manhattan" in p)
        return "\n".join(filas) + f"\n{n} regiones; la mayor ocupa {max(cuenta)} de {40 * 16} casillas"
    return {"voronoi": dibuja}
''',
"prueba": [("voronoi", "5 semilla 3", "5 regiones; la mayor ocupa"), ("voronoi", "1", "1 regiones; la mayor ocupa 640 de 640")],
},
{
"id": "tramado",
"titulo": "Tramado Floyd-Steinberg (dithering): degradados con pocos colores",
"area": "Diseño: generativo y procedural",
"temas": "tramado dithering floyd steinberg pixel art paleta limitada degradado retro imprimir error difusion "
         "imagen blanco negro",
"idea": "Con solo blanco y negro no se puede pintar un gris… salvo que se mezclen puntos. Floyd-Steinberg "
        "redondea cada píxel al color más cercano y REPARTE el error a los vecinos aún no pintados (7/16 a la "
        "derecha, 3/16, 5/16 y 1/16 abajo). De lejos, el ojo ve el gris. Se usa en pixel art, impresión y "
        "pantallas de tinta electrónica.",
"complejidad": "O(píxeles)",
"codigo": r'''
def tramar(gris, ancho, alto):
    img = [row[:] for row in gris]
    for y in range(alto):
        for x in range(ancho):
            viejo = img[y][x]
            nuevo = 255 if viejo >= 128 else 0
            img[y][x] = nuevo
            e = viejo - nuevo
            for dx, dy, peso in ((1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)):
                if 0 <= x + dx < ancho and y + dy < alto:
                    img[y + dy][x + dx] += e * peso / 16
    return img


def registrar():
    def dibuja(texto):
        # «tramado: 48» -> un degradado de 48 de ancho tramado en blanco y negro
        ancho = max(8, min(64, int(texto.strip() or "48")))
        alto = 8
        gris = [[255 * x / (ancho - 1) for x in range(ancho)] for _ in range(alto)]
        img = tramar(gris, ancho, alto)
        filas = ["".join("█" if v == 0 else " " for v in fila) for fila in img]
        tinta = [sum(1 for y in range(alto) if img[y][x] == 0) for x in range(ancho)]
        return "\n".join(filas) + f"\nIzquierda: {tinta[0]}/{alto} puntos negros; derecha: {tinta[-1]}/{alto}"
    return {"tramado": dibuja}
''',
"prueba": [("tramado", "48", "Izquierda: 8/8 puntos negros; derecha: 0/8")],
},
{
"id": "colapso_onda",
"titulo": "Colapso de función de onda (WFC): niveles y mapas que encajan solos",
"area": "Diseño: generativo y procedural",
"temas": "wfc colapso funcion onda wave function collapse mapa nivel procedural baldosas tiles reglas vecinos "
         "terreno costa generativo juego",
"idea": "Cada casilla empieza pudiendo ser cualquier baldosa. Se elige la casilla con MENOS opciones (menor "
        "entropía), se fija una al azar y se PROPAGA: los vecinos pierden las baldosas que no pueden ir al lado. Si "
        "una casilla se queda sin opciones, se vuelve a empezar. Con reglas sencillas (agua junto a arena, arena "
        "junto a hierba, hierba junto a bosque) salen costas e islas creíbles.",
"complejidad": "O(casillas × baldosas) por propagación; reintentos si hay contradicción",
"codigo": r'''
import random

BALDOSAS = "~.,^"           # agua, arena, hierba, bosque
VECINOS = {"~": "~.", ".": "~.,", ",": ".,^", "^": ",^"}


def colapsar(ancho, alto, semilla, intentos=30):
    azar = random.Random(semilla)
    for intento in range(1, intentos + 1):
        celdas = [[set(BALDOSAS) for _ in range(ancho)] for _ in range(alto)]
        roto = False
        while not roto:
            abiertas = [(len(celdas[y][x]), y, x) for y in range(alto) for x in range(ancho) if len(celdas[y][x]) > 1]
            if not abiertas:
                break
            menor = min(a[0] for a in abiertas)
            _, y, x = azar.choice([a for a in abiertas if a[0] == menor])
            celdas[y][x] = {azar.choice(sorted(celdas[y][x]))}
            pila = [(y, x)]
            while pila and not roto:
                cy, cx = pila.pop()
                permitidas = set("".join(VECINOS[b] for b in celdas[cy][cx]))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < alto and 0 <= nx < ancho:
                        nuevo = celdas[ny][nx] & permitidas
                        if not nuevo:
                            roto = True
                            break
                        if nuevo != celdas[ny][nx]:
                            celdas[ny][nx] = nuevo
                            pila.append((ny, nx))
        if not roto:
            return ["".join(next(iter(c)) for c in fila) for fila in celdas], intento
    return None, intentos


def valido(mapa):
    for y, fila in enumerate(mapa):
        for x, b in enumerate(fila):
            if x + 1 < len(fila) and fila[x + 1] not in VECINOS[b]:
                return False
            if y + 1 < len(mapa) and mapa[y + 1][x] not in VECINOS[b]:
                return False
    return True


def registrar():
    def genera(texto):
        # «wfc: 24x8 semilla 5»
        p = texto.lower().split()
        ancho, alto = 24, 8
        if p and "x" in p[0]:
            a, b = p[0].split("x")
            ancho, alto = max(2, min(40, int(a))), max(2, min(16, int(b)))
        semilla = int(p[p.index("semilla") + 1]) if "semilla" in p else 1
        mapa, intentos = colapsar(ancho, alto, semilla)
        if mapa is None:
            return "No encajó tras muchos intentos: prueba otra semilla."
        return "\n".join(mapa) + (f"\n{ancho}x{alto}, {intentos} intento(s). Reglas respetadas: "
                                  f"{'sí' if valido(mapa) else 'NO'} (~ agua . arena , hierba ^ bosque)")
    return {"wfc": genera}
''',
"prueba": [("wfc", "24x8 semilla 5", "Reglas respetadas: sí"), ("wfc", "10x4 semilla 2", "Reglas respetadas: sí")],
},
{
"id": "poisson_disco",
"titulo": "Muestreo de disco de Poisson (Bridson): repartir cosas al azar sin amontonarlas",
"area": "Diseño: generativo y procedural",
"temas": "poisson disco bridson repartir azar natural arboles estrellas puntos distancia minima distribucion "
         "procedural generativo decorado mapa",
"idea": "El azar puro amontona (y deja huecos); una rejilla se ve artificial. El disco de Poisson pone puntos al "
        "azar pero a una distancia mínima r entre sí: parece natural, como árboles en un bosque. Bridson lo hace "
        "rápido con una rejilla de celdas de r/√2 (cabe un punto por celda) y una lista de puntos activos que "
        "prueban k candidatos en el anillo [r, 2r].",
"complejidad": "O(n) puntos con k candidatos cada uno",
"codigo": r'''
import math
import random


def poisson(ancho, alto, r, semilla, k=30):
    azar = random.Random(semilla)
    celda = r / math.sqrt(2)
    cols, filas = int(ancho / celda) + 1, int(alto / celda) + 1
    rejilla = [[None] * cols for _ in range(filas)]
    p0 = (azar.uniform(0, ancho), azar.uniform(0, alto))
    puntos, activos = [p0], [p0]
    rejilla[int(p0[1] / celda)][int(p0[0] / celda)] = p0
    while activos:
        i = azar.randrange(len(activos))
        px, py = activos[i]
        for _ in range(k):
            a, d = azar.uniform(0, 2 * math.pi), azar.uniform(r, 2 * r)
            x, y = px + d * math.cos(a), py + d * math.sin(a)
            if not (0 <= x < ancho and 0 <= y < alto):
                continue
            cx, cy = int(x / celda), int(y / celda)
            libre = True
            for yy in range(max(0, cy - 2), min(filas, cy + 3)):
                for xx in range(max(0, cx - 2), min(cols, cx + 3)):
                    q = rejilla[yy][xx]
                    if q is not None and (q[0] - x) ** 2 + (q[1] - y) ** 2 < r * r:
                        libre = False
            if libre:
                rejilla[cy][cx] = (x, y)
                puntos.append((x, y))
                activos.append((x, y))
                break
        else:
            activos.pop(i)
    return puntos


def registrar():
    def reparte(texto):
        # «poisson: 4» -> distancia mínima 4 en un campo de 60 x 20
        r = max(1.5, min(10.0, float(texto.strip() or "4")))
        pts = poisson(60, 20, r, 7)
        minima = min(math.dist(a, b) for i, a in enumerate(pts) for b in pts[i + 1:]) if len(pts) > 1 else 0
        mapa = [[" "] * 60 for _ in range(20)]
        for x, y in pts:
            mapa[int(y)][int(x)] = "♣"
        return ("\n".join("".join(f) for f in mapa) +
                f"\n{len(pts)} árboles; distancia mínima {minima:.2f} (pedida {r:g}): {'cumple' if minima >= r else 'NO cumple'}")
    return {"poisson": reparte}
''',
"prueba": [("poisson", "4", "(pedida 4): cumple")],
},
]


# =====================================================================================================================
#  FICHAS DE TEORÍA (al baúl con «estudia diseño» / «estudia programación avanzada»)
# =====================================================================================================================
CONCEPTOS = [
# ---------- diseño gráfico ----------
{"id": "teoria_color", "area": "Diseño gráfico", "titulo": "Teoría del color para diseñar",
 "temas": "color teoria rueda cromatica tono saturacion luminosidad calidos frios armonia 60 30 10 psicologia",
 "texto": "Un color se describe por TONO (dónde está en la rueda), SATURACIÓN (lo puro o grisáceo) y LUMINOSIDAD. "
          "Cálidos (rojo, naranja) avanzan y activan; fríos (azul, verde) retroceden y calman. Armonías: "
          "complementarios (opuestos, mucho contraste), análogos (vecinos, tranquilos), tríada (a 120°, viva pero "
          "equilibrada). Regla 60-30-10: un dominante, un secundario y un acento para lo importante (el botón de "
          "acción). Mejor pocos colores bien usados que muchos. Para fondos, colores poco saturados; la saturación "
          "fuerte se reserva para llamar la atención. Kira tiene la receta «paleta»."},
{"id": "tipografia", "area": "Diseño gráfico", "titulo": "Tipografía: elegir y combinar letras",
 "temas": "tipografia fuentes letra serif sans palo seco legibilidad interlineado tracking jerarquia combinar google fonts",
 "texto": "Con serifa (Georgia, Merriweather): clásica, buena para leer textos largos impresos. Palo seco (Roboto, "
          "Inter): limpia, ideal en pantallas. Display o manuscritas: solo para títulos cortos. Combina como mucho "
          "dos familias (una para títulos y otra para texto) o una sola con varios pesos. Texto en móvil de 16 px "
          "o más, líneas de 45 a 75 caracteres, interlineado de ~1,5 en el cuerpo y de ~1,2 en títulos. Jerarquía "
          "con tamaño, peso y color, no con subrayados ni MAYÚSCULAS largas. Una escala modular (receta «escala "
          "tipografica») da tamaños que combinan."},
{"id": "jerarquia_visual", "area": "Diseño gráfico", "titulo": "Jerarquía visual: qué se ve primero",
 "temas": "jerarquia visual atencion tamaño contraste peso color posicion lectura f z patron foco",
 "texto": "El ojo va primero a lo más GRANDE, lo de más CONTRASTE, lo más saturado y lo que está aislado. Ordena la "
          "información de más a menos importante y hazlo visible: un solo protagonista por pantalla. En webs se lee "
          "en forma de F (texto) o de Z (páginas con poco texto): lo clave arriba a la izquierda y la acción al "
          "final del recorrido. Prueba del entrecerrar los ojos: si al ver borroso no distingues lo importante, la "
          "jerarquía falla."},
{"id": "gestalt", "area": "Diseño gráfico", "titulo": "Principios de la Gestalt (cómo agrupa el cerebro)",
 "temas": "gestalt proximidad semejanza continuidad cierre figura fondo region comun agrupar percepcion",
 "texto": "PROXIMIDAD: lo que está cerca parece un grupo (el espacio separa mejor que las líneas). SEMEJANZA: lo que "
          "se parece (color, forma) parece relacionado: todos los botones del mismo tipo, iguales. CONTINUIDAD: el "
          "ojo sigue líneas y curvas. CIERRE: completamos formas incompletas (logotipos). FIGURA-FONDO: separamos "
          "el objeto del fondo; si dudan, el diseño confunde. REGIÓN COMÚN: lo que comparte un recuadro o tarjeta "
          "va junto. Usarlos hace que una interfaz se entienda sin explicarla."},
{"id": "composicion", "area": "Diseño gráfico", "titulo": "Composición: tercios, equilibrio y espacio en blanco",
 "temas": "composicion regla tercios equilibrio simetria asimetria espacio blanco negativo proporcion aurea foco encuadre",
 "texto": "Regla de los tercios: divide el cuadro en 3x3 y pon lo importante en las líneas o sus cruces, no en el "
          "centro exacto (más dinamismo). Equilibrio: simétrico (formal, estable) o asimétrico (un elemento grande "
          "compensado por varios pequeños). El ESPACIO EN BLANCO no es espacio perdido: da aire, separa grupos y "
          "hace que lo importante respire. Las líneas que guían la mirada (caminos, miradas de personajes) llevan "
          "al foco. La proporción áurea (1,618) aparece en rejillas y escalas, pero la claridad importa más."},
{"id": "logotipos_marca", "area": "Diseño gráfico", "titulo": "Logotipos e identidad de marca",
 "temas": "logotipo logo marca identidad imagotipo isotipo simbolo escalable vectorial manual marca",
 "texto": "Un buen logo es SIMPLE (se reconoce a 16 px), memorable, atemporal y funciona en un solo color y en "
          "negativo. Tipos: logotipo (solo letras), isotipo (solo símbolo), imagotipo (los dos). Se diseña en "
          "vectorial (escala sin perder calidad) y se prueba en tamaños pequeños, sobre fondos claros y oscuros. La "
          "identidad completa (manual de marca) fija colores exactos, tipografías, márgenes de seguridad y usos "
          "prohibidos. No copies marcas existentes: inspírate en la idea, no en la forma."},
# ---------- interfaces y experiencia de usuario ----------
{"id": "heuristicas_nielsen", "area": "Diseño de interfaces (UX)", "titulo": "Las 10 heurísticas de usabilidad de Nielsen",
 "temas": "heuristicas nielsen usabilidad ux interfaz estado sistema errores consistencia control usuario ayuda",
 "texto": "1) Muestra el estado del sistema (barras de progreso). 2) Habla el idioma del usuario. 3) Control y "
          "libertad: deshacer, cancelar, atrás. 4) Consistencia: lo mismo se ve y funciona igual. 5) Prevén errores "
          "(confirma lo que no se puede deshacer). 6) Reconocer mejor que recordar: opciones a la vista. 7) "
          "Flexibilidad: atajos para expertos (la voz de Kira). 8) Diseño minimalista: nada que sobre. 9) Errores "
          "con mensajes claros que digan cómo arreglarlo. 10) Ayuda y documentación fáciles de encontrar."},
{"id": "leyes_ux", "area": "Diseño de interfaces (UX)", "titulo": "Ley de Fitts, ley de Hick y ley de Jakob (experiencia de usuario)",
 "temas": "ley fitts hick jakob miller ux botones tamaño distancia opciones decision carga cognitiva",
 "texto": "FITTS: el tiempo para tocar algo crece con la distancia y baja con el tamaño: botones importantes "
          "grandes y cerca del pulgar (abajo en el móvil). HICK: cuantas más opciones, más se tarda en decidir: "
          "menús cortos y agrupados. JAKOB: la gente pasa casi todo su tiempo en OTRAS apps, así que espera que la "
          "tuya funcione igual (no reinventes los gestos). MILLER: la memoria de trabajo guarda unas pocas cosas a "
          "la vez: trocea la información. Umbral de Doherty: respuestas en menos de 0,4 s mantienen la atención."},
{"id": "diseno_movil", "area": "Diseño de interfaces (UX)", "titulo": "Diseñar para el móvil",
 "temas": "movil android pulgar zona toque 48dp dedo gestos pantalla pequeña responsive modo oscuro material",
 "texto": "Objetivos táctiles de al menos 48 dp (unos 9 mm) y separados 8 dp. La zona cómoda del pulgar es la "
          "parte baja y central: ahí las acciones frecuentes; arriba, lo que se consulta. Una tarea principal por "
          "pantalla. Texto de 16 sp o más. Contempla el modo oscuro (no negro puro: #121212) y la letra grande del "
          "sistema. Feedback inmediato a cada toque (cambio de color, vibración leve). Material Design (Android) "
          "da medidas, componentes y movimientos probados."},
{"id": "accesibilidad", "area": "Diseño de interfaces (UX)", "titulo": "Accesibilidad: que lo pueda usar todo el mundo",
 "temas": "accesibilidad wcag contraste lector pantalla talkback daltonismo alternativo subtitulos tamaño letra inclusivo",
 "texto": "Contraste de texto de 4,5:1 como mínimo (receta «contraste»). No transmitas información solo con color "
          "(1 de cada 12 hombres distingue mal rojo y verde): añade iconos o texto. Todo botón con una etiqueta que "
          "lea el lector de pantalla (TalkBack). Que la app aguante la letra grande del sistema. Subtítulos en los "
          "vídeos, textos alternativos en las imágenes, y nada que parpadee más de 3 veces por segundo. Lo "
          "accesible suele ser mejor para todos (la voz de Kira es un ejemplo)."},
{"id": "sistemas_diseno", "area": "Diseño de interfaces (UX)", "titulo": "Sistemas de diseño y tokens",
 "temas": "sistema diseño tokens componentes biblioteca coherencia espaciado 8 puntos variables tema material",
 "texto": "Un sistema de diseño es el conjunto de reglas y piezas reutilizables de un producto: TOKENS (variables "
          "con nombre para colores, tamaños de letra, espaciados, radios y sombras), COMPONENTES (botón, tarjeta, "
          "campo) y pautas de uso. Espaciado en múltiplos de 8 (o 4): 8, 16, 24, 32… Cambiar un token cambia toda la "
          "app de golpe (temas claro/oscuro). En Kira, estilo_kira.py hace de pequeño sistema de diseño: tamaños con "
          "tope, fondo redondeado y la misma letra en todas las pantallas."},
{"id": "diseno_web", "area": "Diseño de interfaces (UX)", "titulo": "Diseño web: estructura que funciona",
 "temas": "web pagina landing estructura cabecera heroe llamada accion cta secciones responsive css flexbox grid",
 "texto": "Una página de presentación clásica: cabecera con logo y menú; HÉROE con un titular claro (qué es y para "
          "quién), una frase de apoyo y UNA llamada a la acción; después beneficios (3 en columnas), prueba social, "
          "detalles y un pie con contacto. Diseña primero para móvil y amplía. En CSS, Flexbox para filas o "
          "columnas y Grid para rejillas de dos dimensiones. Imágenes optimizadas y texto real (no texto dentro de "
          "imágenes). Velocidad: cada segundo de carga hace que se vaya gente."},
# ---------- animación, juegos, imagen ----------
{"id": "principios_animacion", "area": "Animación y movimiento", "titulo": "Los 12 principios de la animación (Disney)",
 "temas": "animacion principios disney estirar encoger anticipacion puesta escena entrada salida arcos exageracion timing",
 "texto": "Estirar y encoger (da peso y elasticidad), anticipación (preparar el movimiento: agacharse antes de "
          "saltar), puesta en escena (que se entienda la acción), animación directa o pose a pose, acción "
          "continuada y superpuesta (el pelo sigue moviéndose al parar), entrada y salida lentas (easing), arcos "
          "(lo vivo se mueve en curvas), acción secundaria, ritmo (timing), exageración, dibujo sólido y atractivo. "
          "En juegos e interfaces, aplicar easing, anticipación y exageración ya hace que todo se sienta vivo."},
{"id": "diseno_juegos", "area": "Diseño de juegos", "titulo": "Diseño de juegos: bucle central, dificultad y «jugo»",
 "temas": "diseño juegos bucle central core loop dificultad flujo curva recompensa feedback juice game feel mecanica",
 "texto": "BUCLE CENTRAL: la acción que se repite cada pocos segundos (saltar, esquivar, disparar) tiene que ser "
          "divertida por sí sola. FLUJO: el reto debe crecer con la habilidad (ni aburrido ni frustrante): sube la "
          "dificultad poco a poco y da respiros. RECOMPENSAS claras y frecuentes. «JUGO» (game feel): que cada "
          "acción responda con sonido, partículas, vibración de pantalla, pequeñas pausas al golpear y animaciones "
          "con easing. Enseña jugando, sin textos largos: el primer nivel es el tutorial. Prueba con gente y mira "
          "dónde se atasca."},
{"id": "diseno_niveles", "area": "Diseño de juegos", "titulo": "Diseño de niveles y generación procedural",
 "temas": "niveles diseño procedural generacion mapas ritmo tension calma puntos referencia semilla wfc ruido",
 "texto": "Un buen nivel enseña una idea, la pone a prueba y luego la complica (introducir, practicar, dominar). "
          "Alterna tensión y calma, y usa puntos de referencia visibles para orientarse. La generación PROCEDURAL "
          "crea contenido con reglas y azar: ruido (terrenos), colapso de función de onda (mapas de baldosas que "
          "encajan), disco de Poisson (repartir objetos), sistemas L (vegetación), Voronoi (regiones). Con una "
          "SEMILLA fija, el mismo mundo sale igual siempre (útil para compartir y probar). Kira tiene recetas de "
          "todas."},
{"id": "pixel_art_sprites", "area": "Diseño de juegos", "titulo": "Sprites y pixel art",
 "temas": "sprites pixel art paleta limitada silueta legible animacion fotogramas transparencia hoja sprites contorno",
 "texto": "Un sprite tiene que leerse por su SILUETA (prueba a verlo en negro). Paleta limitada y coherente para "
          "todo el juego, con sombras que tiran a frío y luces a cálido en vez de solo oscurecer. Personajes con "
          "contorno o con contraste respecto al fondo, y fondos más apagados que los personajes. Animaciones de "
          "pocos fotogramas (4-8) bien elegidos. Fondo transparente (PNG) para que se superpongan: los personajes "
          "realistas que pinta Kira se recortan así. El tramado (receta «tramado») simula más colores."},
{"id": "luz_fotografia", "area": "Imagen y fotografía", "titulo": "Luz y fotografía: lo que hace real una imagen",
 "temas": "luz fotografia iluminacion tres puntos hora dorada contraluz sombras objetivo focal profundidad campo bokeh",
 "texto": "La LUZ hace la foto. Hora dorada (al amanecer y al atardecer): luz cálida, baja y suave. Luz de tres "
          "puntos: principal, de relleno (suaviza sombras) y contraluz (separa del fondo). Luz dura = sombras "
          "marcadas y dramáticas; suave (nublado, ventana) = favorecedora. Focal: 24-35 mm para paisajes y "
          "escenas, 50 mm natural, 85-135 mm para retratos; poca profundidad de campo (f/1.8) desenfoca el fondo "
          "(bokeh). Saber esto ayuda a describir fotos realistas."},
{"id": "prompts_pintor", "area": "Imagen y fotografía", "titulo": "Cómo pedirle una buena imagen al pintor (prompts)",
 "temas": "prompt pintor imagen ia stable diffusion descripcion sujeto estilo luz encuadre negativo semilla pasos",
 "texto": "Un buen pedido sigue un orden: SUJETO concreto (quién o qué, cómo es), ACCIÓN o pose, ENTORNO, LUZ "
          "(golden hour, soft light), ENCUADRE (close-up, wide shot, 85mm), ESTILO (realistic photo, watercolor, "
          "pixel art) y calidad (highly detailed). Concreto mejor que abstracto («un faro blanco sobre rocas al "
          "atardecer» y no «algo bonito»). El prompt NEGATIVO quita lo que no quieres (text, blurry, extra "
          "fingers). La SEMILLA repite una imagen; cambiarla da variaciones. Los modelos pequeños del móvil "
          "entienden mejor frases cortas en inglés: Kira traduce sola."},
# ---------- programación avanzada ----------
{"id": "programacion_funcional", "area": "Programación avanzada", "titulo": "Programación funcional en Python",
 "temas": "funcional funciones puras inmutabilidad map filter reduce lambda composicion efectos secundarios",
 "texto": "Una función PURA devuelve siempre lo mismo para lo mismo y no cambia nada de fuera: se prueba y se "
          "entiende sola. INMUTABILIDAD: en vez de modificar datos, crear otros nuevos (tuplas, frozenset, "
          "dataclass(frozen=True)), lo que evita errores al compartirlos. Funciones de orden superior: reciben o "
          "devuelven funciones (map, filter, sorted con key, functools.reduce, partial). COMPOSICIÓN: programas como "
          "tuberías de pasos pequeños (receta «perezoso»). Separa el núcleo puro de los bordes con efectos (archivos, "
          "red, pantalla): así está hecho Kira, con la lógica pura probada en el PC."},
{"id": "metaprogramacion", "area": "Programación avanzada", "titulo": "Metaprogramación: decoradores, descriptores y metaclases",
 "temas": "metaprogramacion decoradores descriptores property metaclases introspeccion dunder magic methods dataclass",
 "texto": "Código que trabaja con código. DECORADORES: envuelven funciones o clases para añadir comportamiento (receta "
          "«decoradores»; @property, @staticmethod, @dataclass y @functools.lru_cache son decoradores). Los métodos "
          "especiales (__len__, __iter__, __eq__, __add__) hacen que tus objetos funcionen con la sintaxis de Python. "
          "DESCRIPTORES: objetos que controlan el acceso a un atributo (así funciona property). METACLASES: la clase "
          "de una clase, para modificar cómo se crean (casi nunca hacen falta: un decorador de clase suele bastar). "
          "Úsalo con moderación: lo explícito es más fácil de leer."},
{"id": "tipado", "area": "Programación avanzada", "titulo": "Tipado gradual en Python (typing)",
 "temas": "tipos typing anotaciones mypy optional union generics protocol typeddict comprobacion estatica",
 "texto": "Las anotaciones (def area(r: float) -> float) no cambian cómo corre Python, pero documentan y dejan que "
          "una herramienta (mypy, pyright) encuentre errores antes de ejecutar. Básicos: list[int], dict[str, "
          "float], Optional[X] o X | None, Union. Protocol describe «lo que tiene que saber hacer» un objeto (tipado "
          "estructural, como los patos); TypedDict, diccionarios con claves fijas; Generic y TypeVar, funciones que "
          "conservan el tipo. Empieza anotando las funciones públicas: es donde más ayuda."},
{"id": "manejo_errores", "area": "Programación avanzada", "titulo": "Errores bien manejados",
 "temas": "errores excepciones try except finally raise contexto with gestor recursos fallar pronto mensajes",
 "texto": "Falla pronto y con un mensaje que diga qué pasó y cómo arreglarlo. Captura solo las excepciones que sabes "
          "tratar (except ValueError, no un except: desnudo que oculta fallos). Libera recursos con «with» (gestores "
          "de contexto) o finally. Crea tus propias excepciones para los errores de tu dominio (Kira tiene "
          "DescargaError, PintorError…). En la frontera con el usuario, convierte la excepción en un mensaje amable; "
          "por dentro, deja que suba. Y apunta lo inesperado en un registro (la caja negra de Kira) para poder "
          "arreglarlo."},
{"id": "bucle_juego", "area": "Programación avanzada", "titulo": "El bucle de un juego: tiempo fijo y delta time",
 "temas": "bucle juego game loop delta time fotogramas fps paso fijo fisica interpolacion actualizar dibujar",
 "texto": "Todo juego repite: leer la entrada, actualizar el mundo y dibujar. Si se mueve «5 px por fotograma», va "
          "más rápido en móviles potentes: hay que multiplicar por el tiempo transcurrido (dt): x += v·dt. Para la "
          "física, mejor un PASO FIJO (por ejemplo 1/60 s) acumulando el tiempo real y haciendo tantos pasos como "
          "quepan: así las colisiones son estables y reproducibles; el dibujo puede interpolar entre pasos. Limitar "
          "dt evita «saltos» tras una pausa. El motor de juegos de Kira llama a actualizar(dt) con este cuidado."},
{"id": "concurrencia_python", "area": "Programación avanzada", "titulo": "Concurrencia en Python: hilos, procesos y asyncio",
 "temas": "concurrencia hilos threading procesos multiprocessing asyncio gil bloqueo cpu io paralelismo",
 "texto": "El GIL de CPython deja ejecutar código Python a un solo hilo a la vez: los HILOS sirven para esperar "
          "(red, disco, el cerebro de Kira) sin congelar la pantalla, pero no aceleran cálculos. Para cálculo "
          "pesado en paralelo: PROCESOS (multiprocessing) o librerías nativas que sueltan el GIL. ASYNCIO: muchas "
          "esperas a la vez en un solo hilo con async/await (receta «corrutinas»). En apps con interfaz (Kivy), lo "
          "lento va en un hilo y el resultado se devuelve al hilo principal (Clock.schedule_once), que es el único "
          "que puede tocar la pantalla."},
]


# las REDES NEURONALES (y algo más de programación avanzada) van en su propio archivo y se suman aquí
for _nombre in ("saber_redes_kira", "saber_pln_kira"):   # redes neuronales; lenguaje natural, RAG, ML y ajuste fino
    try:
        _m = __import__(_nombre)
        RECETAS = RECETAS + _m.RECETAS
        CONCEPTOS = CONCEPTOS + _m.CONCEPTOS
    except ImportError:
        pass


# =====================================================================================================================
#  AYUDAS
# =====================================================================================================================
def tipo_de(area):
    """'redes' | 'programación' | 'diseño' (para «estudia redes neuronales / programación avanzada / diseño»)."""
    if area.startswith(("Redes", "IA")):
        return "redes"
    return "programación" if area.startswith("Programación") else "diseño"


def areas():
    orden = {}
    for r in RECETAS:
        orden.setdefault(r["area"], []).append(r)
    return list(orden.items())


def demo(r):
    import recetas_ingenieria_kira as ri
    return ri.demo(r)


def leccion(r):
    return {"id": "av_" + r["id"], "titulo": r["titulo"], "nivel": "avanzado y diseño",
            "texto": f"{r['idea']} Coste: {r['complejidad']}.", "codigo": demo(r)}


def fichas(tipo=None):
    """(tema, texto) para el baúl. tipo: 'diseño' (diseño, UX, juegos, imagen), 'programación', 'redes' (redes
    neuronales) o None (todo)."""
    res = []
    for r in RECETAS:
        if tipo is None or tipo_de(r["area"]) == tipo:
            res.append((r["titulo"], f"{r['titulo']} ({r['area']}): {r['idea']} Coste: {r['complejidad']}. "
                                     f"Kira tiene una receta probada: «receta {r['id'].replace('_', ' ')}»."))
    for c in CONCEPTOS:
        if tipo is None or tipo_de(c["area"]) == tipo:
            res.append((c["titulo"], f"{c['titulo']}: {c['texto']}"))
    return res
