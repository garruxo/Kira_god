# -*- coding: utf-8 -*-
"""
saber_redes_kira.py - REDES NEURONALES (y algo más de programación avanzada) para Kira, en Python PURO.

En el móvil no hay numpy ni PyTorch dentro del modo seguro, así que todo está escrito a mano y pequeño: así se ve
CÓMO funcionan por dentro y se puede ejecutar, cambiar e instalar como mejora.
  RECETAS   : autodiferenciación (lo que hace PyTorch), red multicapa con softmax, red convolucional, red recurrente
              que aprende a escribir, atención (el corazón de los transformers), optimizadores (SGD, momento, Adam),
              aprendizaje por refuerzo (Q-learning), mini-Prolog con unificación y pruebas de propiedades.
              Cada una trae su "prueba": tests/test_saber_avanzado.py las pasa por los dos laboratorios y el editor.
  CONCEPTOS : fichas de teoría (neurona, retropropagación, pérdidas, sobreajuste, CNN, RNN/LSTM, transformers,
              embeddings, refuerzo, difusión —cómo pinta el pintor—, entrenar en el móvil, evaluar un modelo).
saber_avanzado_kira las suma a las suyas: «estudia redes neuronales», «recetas de redes neuronales».
"""

RECETAS = [
{
"id": "autograd",
"titulo": "Autodiferenciación: el «backward()» de PyTorch hecho a mano",
"area": "Redes neuronales",
"temas": "autograd autodiferenciacion derivadas gradiente backward pytorch grafo computo regla cadena retropropagacion "
         "micrograd red neuronal neurona entrenar",
"idea": "Cada operación (sumar, multiplicar, tanh…) crea un nodo que recuerda de dónde viene y cómo derivarse. Al "
        "final, backward() recorre el grafo AL REVÉS (orden topológico) aplicando la regla de la cadena: el "
        "gradiente de cada nodo es la suma de lo que le llega de sus hijos. Así entrenan todas las redes neuronales "
        "modernas. Se comprueba contra la derivada numérica (f(x+h) − f(x−h)) / 2h.",
"complejidad": "backward cuesta lo mismo que la pasada hacia delante: O(nodos del grafo)",
"codigo": r'''
import math


class Valor:
    """Un número que recuerda cómo se calculó, para poder derivar hacia atrás."""

    def __init__(self, dato, hijos=(), op=""):
        self.dato, self.grad = float(dato), 0.0
        self.hijos, self.op = hijos, op
        self._atras = lambda: None

    def __add__(self, otro):
        otro = otro if isinstance(otro, Valor) else Valor(otro)
        sal = Valor(self.dato + otro.dato, (self, otro), "+")

        def atras():
            self.grad += sal.grad
            otro.grad += sal.grad
        sal._atras = atras
        return sal

    def __mul__(self, otro):
        otro = otro if isinstance(otro, Valor) else Valor(otro)
        sal = Valor(self.dato * otro.dato, (self, otro), "*")

        def atras():
            self.grad += otro.dato * sal.grad
            otro.grad += self.dato * sal.grad
        sal._atras = atras
        return sal

    def __pow__(self, k):
        sal = Valor(self.dato ** k, (self,), f"**{k}")

        def atras():
            self.grad += k * self.dato ** (k - 1) * sal.grad
        sal._atras = atras
        return sal

    def tanh(self):
        t = math.tanh(self.dato)
        sal = Valor(t, (self,), "tanh")

        def atras():
            self.grad += (1 - t * t) * sal.grad
        sal._atras = atras
        return sal

    __radd__ = __add__
    __rmul__ = __mul__

    def __neg__(self):
        return self * -1

    def __sub__(self, otro):
        return self + (-otro if isinstance(otro, Valor) else -otro)

    def backward(self):
        orden, vistos = [], set()

        def visitar(v):
            if id(v) not in vistos:
                vistos.add(id(v))
                for h in v.hijos:
                    visitar(h)
                orden.append(v)
        visitar(self)
        self.grad = 1.0
        for v in reversed(orden):
            v._atras()


def funcion(a, b):
    return (a * b + b ** 2).tanh() * 3 + a


def registrar():
    def deriva(texto):
        # «autograd: 0.5 -0.3» -> f(a, b) = 3·tanh(a·b + b²) + a, sus derivadas y una neurona que aprende
        p = [float(x) for x in texto.replace(",", " ").split()] or [0.5, -0.3]
        a, b = Valor(p[0]), Valor(p[1] if len(p) > 1 else -0.3)
        f = funcion(a, b)
        f.backward()
        h = 1e-6
        na = (funcion(Valor(a.dato + h), Valor(b.dato)).dato - funcion(Valor(a.dato - h), Valor(b.dato)).dato) / (2 * h)
        nb = (funcion(Valor(a.dato), Valor(b.dato + h)).dato - funcion(Valor(a.dato), Valor(b.dato - h)).dato) / (2 * h)
        bien = abs(na - a.grad) < 1e-4 and abs(nb - b.grad) < 1e-4
        # una neurona aprende y = 2x - 1 con el mismo autograd
        w, c = Valor(0.0), Valor(0.0)
        for _ in range(60):
            perdida = Valor(0.0)
            for x in (-1.0, 0.0, 1.0, 2.0):
                perdida = perdida + (w * x + c - (2 * x - 1)) ** 2
            w.grad = c.grad = 0.0
            perdida.backward()
            w.dato -= 0.05 * w.grad
            c.dato -= 0.05 * c.grad
        return (f"f = {f.dato:.4f}\ndf/da = {a.grad:.4f} (numérica {na:.4f})\ndf/db = {b.grad:.4f} (numérica {nb:.4f})\n"
                f"Coinciden con la derivada numérica: {'sí' if bien else 'NO'}\n"
                f"Una neurona aprende y = 2x - 1: w = {w.dato:.2f}, b = {c.dato:.2f}")
    return {"autograd": deriva}
''',
"prueba": [("autograd", "0.5 -0.3", "Coinciden con la derivada numérica: sí"),
           ("autograd", "0.5 -0.3", "w = 2.00, b = -1.00")],
},
{
"id": "mlp_softmax",
"titulo": "Red neuronal multicapa con softmax: clasificar en varias clases",
"area": "Redes neuronales",
"temas": "red neuronal multicapa mlp perceptron softmax entropia cruzada clasificar clases capas ocultas relu "
         "minilotes entrenamiento prueba precision sobreajuste deep learning",
"idea": "Entrada → capa oculta (ReLU) → capa de salida con SOFTMAX, que convierte las puntuaciones en probabilidades "
        "que suman 1. La pérdida es la entropía cruzada (−log de la probabilidad de la clase correcta); su "
        "gradiente en la salida es simplemente (probabilidades − respuesta correcta). Se entrena por minilotes y se "
        "mide la precisión en datos de PRUEBA que la red no ha visto, para saber si generaliza.",
"complejidad": "por ejemplo y época: O(entradas·ocultas + ocultas·clases)",
"codigo": r'''
import math
import random


def datos(n, semilla):
    """Tres nubes de puntos (clases 0, 1 y 2)."""
    rnd = random.Random(semilla)
    centros = [(-1.0, -1.0), (1.2, 0.0), (-0.6, 1.4)]
    return [((cx + rnd.gauss(0, 0.45), cy + rnd.gauss(0, 0.45)), k) for _ in range(n) for k, (cx, cy) in enumerate(centros)]


def softmax(z):
    m = max(z)
    e = [math.exp(v - m) for v in z]
    s = sum(e)
    return [v / s for v in e]


class Red:
    def __init__(self, entradas, ocultas, clases, rnd):
        esc = math.sqrt(2 / entradas)                        # inicialización de He (va bien con ReLU)
        self.W1 = [[rnd.gauss(0, esc) for _ in range(entradas)] for _ in range(ocultas)]
        self.b1 = [0.0] * ocultas
        self.W2 = [[rnd.gauss(0, math.sqrt(1 / ocultas)) for _ in range(ocultas)] for _ in range(clases)]
        self.b2 = [0.0] * clases

    def adelante(self, x):
        h = [max(0.0, sum(w * xi for w, xi in zip(fila, x)) + b) for fila, b in zip(self.W1, self.b1)]
        return h, softmax([sum(w * hi for w, hi in zip(fila, h)) + b for fila, b in zip(self.W2, self.b2)])

    def entrenar_lote(self, lote, ritmo):
        perdida = 0.0
        for x, y in lote:
            h, p = self.adelante(x)
            perdida -= math.log(max(p[y], 1e-12))
            dz = [pk - (1.0 if k == y else 0.0) for k, pk in enumerate(p)]       # softmax + entropía cruzada
            dh = [sum(self.W2[k][j] * dz[k] for k in range(len(dz))) * (1.0 if h[j] > 0 else 0.0)
                  for j in range(len(h))]
            for k in range(len(dz)):
                for j in range(len(h)):
                    self.W2[k][j] -= ritmo * dz[k] * h[j] / len(lote)
                self.b2[k] -= ritmo * dz[k] / len(lote)
            for j in range(len(h)):
                for i in range(len(x)):
                    self.W1[j][i] -= ritmo * dh[j] * x[i] / len(lote)
                self.b1[j] -= ritmo * dh[j] / len(lote)
        return perdida / len(lote)

    def precision(self, ejemplos):
        bien = 0
        for x, y in ejemplos:
            p = self.adelante(x)[1]
            bien += max(range(len(p)), key=p.__getitem__) == y
        return bien / len(ejemplos)


def registrar():
    def clasifica(texto):
        # «red multicapa: 8 40» -> 8 neuronas ocultas, 40 épocas
        p = [int(v) for v in texto.split() if v.isdigit()]
        ocultas, epocas = (p + [8, 40])[:2]
        rnd = random.Random(1)
        entreno, prueba = datos(30, 2), datos(10, 3)
        red = Red(2, max(2, min(32, ocultas)), 3, rnd)
        lineas = []
        for e in range(1, min(200, epocas) + 1):
            rnd.shuffle(entreno)
            perdidas = [red.entrenar_lote(entreno[i:i + 10], 0.5) for i in range(0, len(entreno), 10)]
            if e in (1, epocas // 2, epocas):
                lineas.append(f"época {e:3}: pérdida {sum(perdidas) / len(perdidas):.3f}")
        ac_e, ac_p = red.precision(entreno), red.precision(prueba)
        lineas.append(f"Precisión en entrenamiento: {ac_e:.0%}; en PRUEBA (datos nuevos): {ac_p:.0%}")
        lineas.append("Generaliza bien" if ac_p >= 0.85 else "Generaliza poco: más datos, más épocas o otra arquitectura")
        return "\n".join(lineas)
    return {"red multicapa": clasifica}
''',
"prueba": [("red multicapa", "8 40", "Generaliza bien")],
},
{
"id": "convolucional",
"titulo": "Red convolucional (CNN): reconocer formas en imágenes",
"area": "Redes neuronales",
"temas": "convolucional cnn convolucion filtros kernel imagen reconocer formas vision artificial pooling relu "
         "caracteristicas bordes pixeles clasificar imagenes",
"idea": "Un FILTRO pequeño (3×3) se desliza por la imagen y en cada sitio multiplica y suma: responde fuerte donde "
        "encuentra su patrón (un borde, una línea). Los mismos pesos sirven en toda la imagen, así que hay pocos "
        "parámetros y da igual dónde esté la forma. Tras la ReLU, el «max pooling» se queda con la respuesta más "
        "fuerte y una capa final decide la clase. Los filtros NO se programan: se aprenden con retropropagación.",
"complejidad": "por imagen: O(filtros · píxeles · tamaño del filtro)",
"codigo": r'''
import math
import random

FORMAS = ["vertical", "horizontal", "diagonal", "cruz"]


def dibujar(forma, rnd):
    img = [[0.0] * 6 for _ in range(6)]
    f, c = rnd.randint(1, 4), rnd.randint(1, 4)
    for k in range(-1, 2):
        if forma in ("vertical", "cruz"):
            img[f + k][c] = 1.0
        if forma in ("horizontal", "cruz"):
            img[f][c + k] = 1.0
        if forma == "diagonal":
            img[f + k][c + k] = 1.0
    for _ in range(2):                                        # un poco de ruido
        img[rnd.randrange(6)][rnd.randrange(6)] += 0.3
    return img


def convolucionar(img, filtro):
    return [[sum(filtro[a][b] * img[i + a][j + b] for a in range(3) for b in range(3)) for j in range(4)] for i in range(4)]


class CNN:
    def __init__(self, n_filtros, rnd):
        self.F = [[[rnd.gauss(0, 0.4) for _ in range(3)] for _ in range(3)] for _ in range(n_filtros)]
        self.W = [[rnd.gauss(0, 0.4) for _ in range(n_filtros)] for _ in range(len(FORMAS))]
        self.b = [0.0] * len(FORMAS)

    def adelante(self, img):
        mapas, maximos, donde = [], [], []
        for f in self.F:
            m = convolucionar(img, f)
            i, j = max(((i, j) for i in range(4) for j in range(4)), key=lambda p: m[p[0]][p[1]])
            mapas.append(m)
            maximos.append(max(0.0, m[i][j]))                 # ReLU + max pooling global
            donde.append((i, j))
        z = [sum(w * v for w, v in zip(fila, maximos)) + b for fila, b in zip(self.W, self.b)]
        mz = max(z)
        e = [math.exp(v - mz) for v in z]
        return maximos, donde, [v / sum(e) for v in e]

    def aprender(self, img, y, ritmo):
        maximos, donde, p = self.adelante(img)
        dz = [pk - (1.0 if k == y else 0.0) for k, pk in enumerate(p)]
        for f in range(len(self.F)):
            dmax = sum(self.W[k][f] * dz[k] for k in range(len(dz))) if maximos[f] > 0 else 0.0
            i, j = donde[f]
            for a in range(3):
                for b in range(3):
                    self.F[f][a][b] -= ritmo * dmax * img[i + a][j + b]    # solo el sitio ganador recibe gradiente
        for k in range(len(dz)):
            for f in range(len(self.F)):
                self.W[k][f] -= ritmo * dz[k] * maximos[f]
            self.b[k] -= ritmo * dz[k]
        return -math.log(max(p[y], 1e-12))


def registrar():
    def entrena(texto):
        # «red convolucional: 6» -> 6 filtros
        n = max(2, min(8, int(texto.strip() or "6")))
        rnd = random.Random(4)
        red = CNN(n, rnd)
        for _ in range(500):
            k = rnd.randrange(len(FORMAS))
            red.aprender(dibujar(FORMAS[k], rnd), k, 0.1)
        prueba = [(dibujar(FORMAS[k], rnd), k) for k in range(len(FORMAS)) for _ in range(10)]
        bien = 0
        for img, y in prueba:
            p = red.adelante(img)[2]
            bien += max(range(len(p)), key=p.__getitem__) == y
        f = max(red.F, key=lambda m: sum(abs(v) for fila in m for v in fila))
        dibujo = "\n".join("  " + " ".join("█" if v > 0.3 else ("·" if v > -0.3 else " ") for v in fila) for fila in f)
        return (f"{n} filtros 3×3, 500 imágenes de entrenamiento.\nAcierta {bien} de {len(prueba)} imágenes NUEVAS "
                f"({bien / len(prueba):.0%})\nUno de los filtros que ha aprendido sola:\n{dibujo}")
    return {"red convolucional": entrena}
''',
"prueba": [("red convolucional", "6", "imágenes NUEVAS (")],
},
{
"id": "recurrente",
"titulo": "Red recurrente (RNN): aprende a escribir letra a letra",
"area": "Redes neuronales",
"temas": "recurrente rnn secuencias texto letras caracteres memoria estado oculto lstm generar escribir predecir "
         "siguiente bptt lenguaje",
"idea": "Una red RECURRENTE lee una secuencia paso a paso y guarda un ESTADO OCULTO que resume lo leído: h = "
        "tanh(Wx·x + Wh·h_anterior). En cada paso predice la siguiente letra. Se entrena «desenrollándola» en el "
        "tiempo y retropropagando por todos los pasos (BPTT). Después, dándole una letra y realimentando lo que "
        "predice, ESCRIBE. Las LSTM y GRU añaden puertas para recordar más tiempo.",
"complejidad": "por paso: O(oculto² + oculto·vocabulario)",
"codigo": r'''
import math
import random

TEXTO = "hola kira. hola mundo. "


class RNN:
    def __init__(self, vocab, oculto, rnd):
        self.V, self.H = vocab, oculto
        g = lambda f, c, e: [[rnd.gauss(0, e) for _ in range(c)] for _ in range(f)]
        self.Wx, self.Wh, self.Wy = g(oculto, vocab, 0.3), g(oculto, oculto, 0.1), g(vocab, oculto, 0.3)
        self.bh, self.by = [0.0] * oculto, [0.0] * vocab

    def paso(self, x, h):
        nh = [math.tanh(self.Wx[i][x] + sum(self.Wh[i][j] * h[j] for j in range(self.H)) + self.bh[i])
              for i in range(self.H)]
        z = [sum(self.Wy[k][i] * nh[i] for i in range(self.H)) + self.by[k] for k in range(self.V)]
        m = max(z)
        e = [math.exp(v - m) for v in z]
        s = sum(e)
        return nh, [v / s for v in e]

    def entrenar(self, xs, ys, ritmo):
        hs, ps = [[0.0] * self.H], []
        for x in xs:
            h, p = self.paso(x, hs[-1])
            hs.append(h)
            ps.append(p)
        perdida = -sum(math.log(max(p[y], 1e-12)) for p, y in zip(ps, ys)) / len(xs)
        dWx = [[0.0] * self.V for _ in range(self.H)]
        dWh = [[0.0] * self.H for _ in range(self.H)]
        dWy = [[0.0] * self.H for _ in range(self.V)]
        dbh, dby, dh_sig = [0.0] * self.H, [0.0] * self.V, [0.0] * self.H
        for t in reversed(range(len(xs))):                      # retropropagación A TRAVÉS DEL TIEMPO
            dz = list(ps[t])
            dz[ys[t]] -= 1.0
            h, hp = hs[t + 1], hs[t]
            for k in range(self.V):
                dby[k] += dz[k]
                for i in range(self.H):
                    dWy[k][i] += dz[k] * h[i]
            dh = [sum(self.Wy[k][i] * dz[k] for k in range(self.V)) + dh_sig[i] for i in range(self.H)]
            dr = [dh[i] * (1 - h[i] * h[i]) for i in range(self.H)]
            for i in range(self.H):
                dbh[i] += dr[i]
                dWx[i][xs[t]] += dr[i]
                for j in range(self.H):
                    dWh[i][j] += dr[i] * hp[j]
            dh_sig = [sum(self.Wh[i][j] * dr[i] for i in range(self.H)) for j in range(self.H)]
        for M, dM in ((self.Wx, dWx), (self.Wh, dWh), (self.Wy, dWy)):
            for fila, dfila in zip(M, dM):
                for j in range(len(fila)):
                    fila[j] -= ritmo * max(-5.0, min(5.0, dfila[j]))   # recorte del gradiente (evita explosiones)
        for v, dv in ((self.bh, dbh), (self.by, dby)):
            for j in range(len(v)):
                v[j] -= ritmo * max(-5.0, min(5.0, dv[j]))
        return perdida


def registrar():
    def escribe(texto):
        # «red recurrente: 200» -> 200 pasos de entrenamiento con el texto de ejemplo
        vueltas = max(50, min(600, int(texto.strip() or "200")))
        letras = sorted(set(TEXTO))
        idx = {c: i for i, c in enumerate(letras)}
        rnd = random.Random(5)
        red = RNN(len(letras), 10, rnd)
        datos = [idx[c] for c in TEXTO * 2]
        primera = ultima = None
        for v in range(vueltas):
            i = (v * 7) % len(TEXTO)
            p = red.entrenar(datos[i:i + 8], datos[i + 1:i + 9], 0.1)
            primera = p if primera is None else primera
            ultima = p
        h, x, sale = [0.0] * red.H, idx["h"], "h"
        for _ in range(22):                                     # escribe eligiendo la letra más probable
            h, p = red.paso(x, h)
            x = max(range(len(p)), key=p.__getitem__)
            sale += letras[x]
        return (f"Pérdida al empezar {primera:.2f} y al acabar {ultima:.2f} ({'aprende' if ultima < primera / 3 else 'aprende poco'})\n"
                f"Escribe empezando por «h»: {sale}")
    return {"red recurrente": escribe}
''',
"prueba": [("red recurrente", "200", "(aprende)"), ("red recurrente", "200", "Escribe empezando por «h»: hola mundo.")],
},
{
"id": "atencion",
"titulo": "Atención: el corazón de los transformers (como el cerebro de Kira)",
"area": "Redes neuronales",
"temas": "atencion transformer autoatencion self attention consultas claves valores qkv softmax mascara causal "
         "llm gpt qwen modelo lenguaje embeddings cabezas",
"idea": "Cada palabra lanza una CONSULTA (Q) y todas ofrecen una CLAVE (K) y un VALOR (V). La similitud Q·K "
        "(dividida por √d para que no se dispare) pasa por softmax y da cuánto atiende cada palabra a cada otra; el "
        "resultado es la mezcla de los VALORES con esos pesos. La MÁSCARA CAUSAL impide mirar al futuro: así "
        "escriben los modelos de lenguaje palabra a palabra. Varias «cabezas» en paralelo atienden a cosas distintas.",
"complejidad": "O(n² · d) para n palabras: por eso el contexto largo sale caro",
"codigo": r'''
import math

# embeddings de juguete (en un modelo real se aprenden): [es animal, es acción, es comida, es artículo]
EMB = {"el": [0, 0, 0, 1], "gato": [1, 0, 0.2, 0], "come": [0.2, 1, 0.3, 0], "pescado": [0.6, 0, 1, 0],
       "perro": [1, 0, 0.1, 0], "bebe": [0.1, 1, 0.2, 0], "agua": [0, 0, 0.8, 0], "la": [0, 0, 0, 1]}


def matmul(A, B):
    return [[sum(a * b for a, b in zip(fila, col)) for col in zip(*B)] for fila in A]


def softmax(fila):
    m = max(fila)
    e = [math.exp(v - m) for v in fila]
    return [v / sum(e) for v in e]


def atencion(X, causal):
    d = len(X[0])
    Wq = [[1 if i == j else 0.2 for j in range(d)] for i in range(d)]      # pesos fijos de ejemplo
    Wk = [[1 if i == (j + 1) % d else 0.1 for j in range(d)] for i in range(d)]
    Q, K, V = matmul(X, Wq), matmul(X, Wk), X
    pesos = []
    for i, q in enumerate(Q):
        punt = [sum(a * b for a, b in zip(q, k)) / math.sqrt(d) for k in K]
        if causal:
            punt = [p if j <= i else -1e9 for j, p in enumerate(punt)]        # no puede mirar al futuro
        pesos.append(softmax(punt))
    return pesos, matmul(pesos, V)


def registrar():
    def atiende(texto):
        # «atencion: el gato come pescado»  (añade «causal» para la máscara de los modelos de lenguaje)
        palabras = [p for p in texto.lower().split() if p in EMB] or ["el", "gato", "come", "pescado"]
        causal = "causal" in texto.lower()
        pesos, _ = atencion([EMB[p] for p in palabras], causal)
        ancho = max(len(p) for p in palabras) + 1
        lineas = [" " * ancho + " ".join(f"{p[:6]:>6}" for p in palabras)]
        for p, fila in zip(palabras, pesos):
            lineas.append(f"{p:<{ancho}}" + " ".join(f"{v:6.2f}" for v in fila))
        sumas = all(abs(sum(f) - 1) < 1e-9 for f in pesos)
        futuro = all(v < 1e-6 for i, f in enumerate(pesos) for j, v in enumerate(f) if j > i)
        lineas.append(f"Cada fila suma 1.00: {'sí' if sumas else 'NO'}"
                      + (f"; nadie mira al futuro: {'sí' if futuro else 'NO'}" if causal else ""))
        return "\n".join(lineas)
    return {"atencion": atiende}
''',
"prueba": [("atencion", "el gato come pescado", "Cada fila suma 1.00: sí"),
           ("atencion", "el gato come pescado causal", "nadie mira al futuro: sí")],
},
{
"id": "optimizadores",
"titulo": "Optimizadores: SGD, momento, RMSprop y Adam (cómo baja una red hacia el error mínimo)",
"area": "Redes neuronales",
"temas": "optimizadores sgd descenso gradiente momento momentum rmsprop adam ritmo aprendizaje learning rate "
         "convergencia valle rosenbrock entrenar",
"idea": "El descenso de gradiente da pasos cuesta abajo: θ ← θ − ritmo·∇. En valles alargados zigzaguea y va lento. "
        "MOMENTO acumula velocidad (como una bola que rueda). RMSprop divide cada paso por el tamaño típico de su "
        "gradiente (cada peso con su propio ritmo). ADAM combina las dos ideas y corrige el sesgo del principio: "
        "por eso es el optimizador por defecto para entrenar redes.",
"complejidad": "O(parámetros) por paso; Adam guarda 2 números más por parámetro",
"codigo": r'''
import math


def valle(x, y):
    """Un valle muy alargado (10 veces más empinado en y): el caso difícil."""
    return x * x + 10 * y * y, (2 * x, 20 * y)


def optimizar(nombre, ritmo, pasos=500):
    x, y = -4.0, 1.5
    vx = vy = sx = sy = 0.0
    for t in range(1, pasos + 1):
        f, (gx, gy) = valle(x, y)
        if f < 1e-4:
            return t, f
        if nombre == "sgd":
            dx, dy = gx, gy
        elif nombre == "momento":
            vx, vy = 0.9 * vx + gx, 0.9 * vy + gy
            dx, dy = vx, vy
        elif nombre == "rmsprop":
            sx, sy = 0.9 * sx + 0.1 * gx * gx, 0.9 * sy + 0.1 * gy * gy
            dx, dy = gx / (math.sqrt(sx) + 1e-8), gy / (math.sqrt(sy) + 1e-8)
        else:                                                    # adam
            vx, vy = 0.9 * vx + 0.1 * gx, 0.9 * vy + 0.1 * gy
            sx, sy = 0.999 * sx + 0.001 * gx * gx, 0.999 * sy + 0.001 * gy * gy
            cv, cs = 1 - 0.9 ** t, 1 - 0.999 ** t                # corrección del sesgo inicial
            dx = (vx / cv) / (math.sqrt(sx / cs) + 1e-8)
            dy = (vy / cv) / (math.sqrt(sy / cs) + 1e-8)
        x, y = x - ritmo * dx, y - ritmo * dy
    return pasos, valle(x, y)[0]


def registrar():
    def compara(texto):
        ritmos = {"sgd": 0.04, "momento": 0.01, "rmsprop": 0.05, "adam": 0.3}
        res = {n: optimizar(n, r) for n, r in ritmos.items()}
        lineas = [f"{n:8} (ritmo {ritmos[n]}): {p:4} pasos, error final {f:.1e}" for n, (p, f) in res.items()]
        mejor = min(res, key=lambda n: res[n][0])
        lineas.append(f"Llega antes al fondo del valle: {mejor}")
        lineas.append(f"SGD necesita {res['sgd'][0]} pasos; momento, {res['momento'][0]}")
        return "\n".join(lineas)
    return {"optimizadores": compara}
''',
"prueba": [("optimizadores", "", "Llega antes al fondo del valle:")],
},
{
"id": "q_learning",
"titulo": "Aprendizaje por refuerzo (Q-learning): un agente aprende jugando",
"area": "Redes neuronales",
"temas": "refuerzo q learning agente recompensa castigo politica explorar explotar epsilon juego laberinto ia "
         "aprender jugando bellman jugar juega sola solo entrenar agente juegos",
"idea": "Nadie le dice al agente qué hacer: prueba acciones y recibe premios o castigos. Guarda en una tabla Q(estado, "
        "acción) lo bueno que espera que sea cada acción y la mejora con la ecuación de Bellman: Q ← Q + α·(premio + "
        "γ·max Q(siguiente) − Q). Al principio EXPLORA al azar (ε) y poco a poco EXPLOTA lo aprendido. Con una red "
        "neuronal en vez de la tabla es el «Deep Q-learning» que aprendió a jugar a Atari.",
"complejidad": "por paso O(acciones); la tabla ocupa estados × acciones",
"codigo": r'''
import random

MAPA = ["S...",
        ".#.X",
        "...#",
        "X..M"]                       # S salida, M meta (+10), X trampa (−10), # muro
ACCIONES = {"↑": (-1, 0), "↓": (1, 0), "←": (0, -1), "→": (0, 1)}


def mover(f, c, a):
    df, dc = ACCIONES[a]
    nf, nc = f + df, c + dc
    if not (0 <= nf < 4 and 0 <= nc < 4) or MAPA[nf][nc] == "#":
        return f, c, -1.0, False                          # choca: se queda y le cuesta
    casilla = MAPA[nf][nc]
    if casilla == "M":
        return nf, nc, 10.0, True
    if casilla == "X":
        return nf, nc, -10.0, True
    return nf, nc, -0.1, False                            # cada paso cuesta un poco: así busca el camino corto


def aprender(episodios, rnd, alfa=0.5, gamma=0.9):
    Q = {(f, c): {a: 0.0 for a in ACCIONES} for f in range(4) for c in range(4)}
    for e in range(episodios):
        eps = max(0.05, 1 - e / (episodios * 0.7))
        f, c = 0, 0
        for _ in range(50):
            a = rnd.choice(list(ACCIONES)) if rnd.random() < eps else max(Q[(f, c)], key=Q[(f, c)].get)
            nf, nc, premio, fin = mover(f, c, a)
            objetivo = premio + (0 if fin else gamma * max(Q[(nf, nc)].values()))
            Q[(f, c)][a] += alfa * (objetivo - Q[(f, c)][a])
            f, c = nf, nc
            if fin:
                break
    return Q


def registrar():
    def juega(texto):
        # «q learning: 300» -> episodios de práctica
        episodios = max(20, min(2000, int(texto.strip() or "300")))
        Q = aprender(episodios, random.Random(7))
        filas = []
        for f in range(4):
            fila = ""
            for c in range(4):
                fila += MAPA[f][c] if MAPA[f][c] in "#XM" else max(Q[(f, c)], key=Q[(f, c)].get)
            filas.append("  " + " ".join(fila))
        f, c, pasos, fin, premio = 0, 0, 0, False, 0.0
        while not fin and pasos < 20:
            f, c, premio, fin = mover(f, c, max(Q[(f, c)], key=Q[(f, c)].get))
            pasos += 1
        llega = fin and premio > 0
        return (f"Tras {episodios} partidas de práctica, lo que haría en cada casilla:\n" + "\n".join(filas) +
                (f"\nLlega a la meta en {pasos} pasos" if llega else "\nTodavía no llega a la meta: necesita más práctica"))
    return {"q learning": juega}
''',
"prueba": [("q learning", "300", "Llega a la meta en 6 pasos")],
},
{
"id": "mini_prolog",
"titulo": "Mini-Prolog: unificación y búsqueda hacia atrás (programación lógica)",
"area": "Programación avanzada",
"temas": "prolog logica unificacion resolucion backtracking hechos reglas consultas variables inferencia "
         "programacion declarativa sistema experto familia",
"idea": "En vez de decir CÓMO, se dicen hechos («padre(juan, ana)») y reglas («abuelo(X, Z) si padre(X, Y) y "
        "padre(Y, Z)»). Para responder una consulta, se UNIFICA con cada hecho o cabeza de regla (se buscan valores "
        "para las variables que hagan iguales los dos términos) y, si hay que probar varias cosas, se prueba una a "
        "una dando marcha atrás cuando algo falla. Así funcionan Prolog, los sistemas expertos y los comprobadores "
        "de tipos.",
"complejidad": "exponencial en el peor caso (búsqueda); con hechos simples, lineal en su número",
"codigo": r'''
import itertools

CONTADOR = itertools.count()
HECHOS = [("padre", "juan", "ana"), ("padre", "juan", "pedro"), ("padre", "ana", "luis"),
          ("madre", "rosa", "ana"), ("padre", "pedro", "eva")]
REGLAS = [  # (cabeza, [cuerpo])
    (("progenitor", "X", "Y"), [("padre", "X", "Y")]),
    (("progenitor", "X", "Y"), [("madre", "X", "Y")]),
    (("abuelo", "X", "Z"), [("progenitor", "X", "Y"), ("progenitor", "Y", "Z")]),
    (("hermano", "X", "Y"), [("padre", "P", "X"), ("padre", "P", "Y"), ("distinto", "X", "Y")]),
]


def es_var(t):
    return isinstance(t, str) and t[:1].isupper()


def valor(t, s):
    while es_var(t) and t in s:
        t = s[t]
    return t


def unificar(a, b, s):
    if len(a) != len(b):
        return None
    s = dict(s)
    for x, y in zip(a, b):
        x, y = valor(x, s), valor(y, s)
        if x == y:
            continue
        if es_var(x):
            s[x] = y
        elif es_var(y):
            s[y] = x
        else:
            return None
    return s


def renombrar(t, n):
    return tuple(f"{x}_{n}" if es_var(x) else x for x in t)


def resolver(metas, s):
    if not metas:
        yield s
        return
    meta, resto = metas[0], metas[1:]
    if meta[0] == "distinto":
        if valor(meta[1], s) != valor(meta[2], s):
            yield from resolver(resto, s)
        return
    for h in HECHOS:
        s2 = unificar(meta, h, s)
        if s2 is not None:
            yield from resolver(resto, s2)
    for cabeza, cuerpo in REGLAS:
        n = next(CONTADOR)
        s2 = unificar(meta, renombrar(cabeza, n), s)
        if s2 is not None:
            yield from resolver([renombrar(c, n) for c in cuerpo] + resto, s2)


def registrar():
    def consulta(texto):
        # «prolog: abuelo(X, luis)»   «prolog: hermano(ana, Y)»   «prolog: abuelo(juan, Z)»
        t = texto.strip().replace(" ", "")
        if "(" not in t or not t.endswith(")"):
            return "Uso: prolog: abuelo(X, luis)"
        nombre, args = t[:-1].split("(", 1)
        meta = tuple([nombre] + args.split(","))
        variables = [a for a in meta[1:] if es_var(a)]
        vistas = []
        for s in resolver([meta], {}):
            r = ", ".join(f"{v} = {valor(v, s)}" for v in variables) or "sí"
            if r not in vistas:
                vistas.append(r)
        return "\n".join(vistas) if vistas else "no"
    return {"prolog": consulta}
''',
"prueba": [("prolog", "abuelo(X, luis)", "X = juan"), ("prolog", "hermano(ana, Y)", "Y = pedro"),
           ("prolog", "abuelo(rosa, Z)", "Z = luis"), ("prolog", "abuelo(luis, juan)", "no")],
},
{
"id": "pruebas_propiedades",
"titulo": "Pruebas de propiedades con reducción (como Hypothesis / QuickCheck)",
"area": "Programación avanzada",
"temas": "pruebas propiedades property based testing hypothesis quickcheck aleatorio contraejemplo reducir shrinking "
         "fallos errores ordenar tests",
"idea": "En vez de escribir ejemplos a mano, se escribe una PROPIEDAD que siempre debe cumplirse («ordenar no cambia "
        "los elementos y deja cada uno ≤ el siguiente») y se prueba con cientos de entradas al azar. Cuando falla, "
        "se REDUCE el contraejemplo (quitar elementos, acercar números a 0) hasta el caso más pequeño que sigue "
        "fallando: así se ve el error de un vistazo.",
"complejidad": "O(pruebas × coste de la función) + la reducción",
"codigo": r'''
import random


def ordenar_con_fallo(lista):
    """Un «ordenar» con un error escondido: pierde los repetidos."""
    return sorted(set(lista))


def propiedad(f, lista):
    r = f(list(lista))
    return sorted(r) == sorted(lista) and all(a <= b for a, b in zip(r, r[1:]))


def reducir(f, caso):
    cambio = True
    while cambio:
        cambio = False
        candidatos = [caso[:i] + caso[i + 1:] for i in range(len(caso))]
        candidatos += [caso[:i] + [v // 2] + caso[i + 1:] for i, v in enumerate(caso) if v != 0]
        candidatos += [[w // 2 if w == v else w for w in caso] for v in set(caso) if v != 0]   # los iguales, a la vez
        for c in candidatos:
            if not propiedad(f, c):
                caso, cambio = c, True
                break
    return caso


def registrar():
    def prueba(texto):
        rnd = random.Random(3)
        for n in range(1, 301):
            caso = [rnd.randint(-20, 20) for _ in range(rnd.randint(0, 8))]
            if not propiedad(ordenar_con_fallo, caso):
                minimo = reducir(ordenar_con_fallo, caso)
                return (f"Falla en la prueba {n} con {caso}\nContraejemplo mínimo: {minimo}\n"
                        f"Con él se ve el error: ordenar({minimo}) da {ordenar_con_fallo(minimo)}")
        return "La propiedad se cumple en 300 pruebas"
    return {"propiedades": prueba}
''',
"prueba": [("propiedades", "", "Contraejemplo mínimo: [0, 0]")],
},
]


CONCEPTOS = [
{"id": "neurona", "area": "Redes neuronales", "titulo": "La neurona artificial y las funciones de activación",
 "temas": "neurona artificial pesos sesgo activacion relu sigmoide tanh softmax gelu perceptron capa",
 "texto": "Una neurona multiplica cada entrada por un PESO, suma todo más un SESGO y pasa el resultado por una "
          "función de ACTIVACIÓN no lineal. Sin activación, apilar capas sería como tener una sola. ReLU (max(0, z)) "
          "es la más usada en capas ocultas: barata y sin «saturarse» por arriba. Sigmoide (de 0 a 1) para una "
          "probabilidad de sí/no; tanh (de −1 a 1) en redes recurrentes; SOFTMAX en la salida para varias clases "
          "(probabilidades que suman 1); GELU en los transformers. Una CAPA son muchas neuronas a la vez: una "
          "multiplicación de matrices. Kira tiene la receta «red multicapa»."},
{"id": "retropropagacion", "area": "Redes neuronales", "titulo": "Retropropagación y descenso de gradiente",
 "temas": "retropropagacion backpropagation gradiente descenso regla cadena derivada ritmo aprendizaje learning rate epoca lote",
 "texto": "Entrenar es ajustar los pesos para que baje el ERROR (la pérdida). La RETROPROPAGACIÓN calcula, con la "
          "regla de la cadena y yendo de la salida hacia la entrada, cuánto cambia la pérdida al mover cada peso (el "
          "gradiente). Después, cada peso da un pasito en contra: w ← w − ritmo·gradiente. Ritmo muy grande: diverge; "
          "muy pequeño: no avanza. Se entrena por MINILOTES (unos pocos ejemplos cada vez) y una ÉPOCA es pasar una "
          "vez por todos los datos. PyTorch y compañía lo hacen solos (autodiferenciación: receta «autograd»)."},
{"id": "perdidas", "area": "Redes neuronales", "titulo": "Funciones de pérdida: qué se le pide a la red",
 "temas": "perdida loss error cuadratico medio entropia cruzada clasificacion regresion huber objetivo",
 "texto": "La pérdida mide lo lejos que está la red de la respuesta. REGRESIÓN (predecir números): error cuadrático "
          "medio (castiga mucho los errores grandes) o Huber (más tolerante con datos raros). CLASIFICACIÓN: "
          "ENTROPÍA CRUZADA, −log(probabilidad dada a la clase correcta): estar seguro y equivocado cuesta mucho. "
          "Combinada con softmax, su gradiente es simplemente probabilidades − respuesta correcta. Elegir bien la "
          "pérdida es decirle a la red qué es «hacerlo bien»: si no coincide con lo que de verdad quieres, aprenderá "
          "otra cosa."},
{"id": "sobreajuste_regularizacion", "area": "Redes neuronales", "titulo": "Sobreajuste y regularización",
 "temas": "sobreajuste overfitting regularizacion dropout l2 weight decay parada temprana early stopping validacion aumento datos",
 "texto": "Una red grande puede MEMORIZAR los ejemplos en vez de aprender la regla: acierta todo en entrenamiento y "
          "falla con datos nuevos (sobreajuste). Se detecta separando datos de VALIDACIÓN que no se usan para "
          "entrenar. Remedios: más datos (o AUMENTARLOS: girar, recortar, añadir ruido), L2 / weight decay (pesos "
          "pequeños), DROPOUT (apagar neuronas al azar al entrenar, para que no dependan unas de otras), PARADA "
          "TEMPRANA (parar cuando la validación deja de mejorar) y modelos más pequeños. El caso contrario, "
          "subajuste, es una red demasiado simple o poco entrenada."},
{"id": "inicializacion_normalizacion", "area": "Redes neuronales", "titulo": "Inicialización, normalización y gradientes que explotan",
 "temas": "inicializacion he xavier normalizacion batchnorm layernorm gradiente desvanece explota residual recorte",
 "texto": "Si los pesos empiezan muy grandes o muy pequeños, la señal crece o se apaga al atravesar muchas capas y "
          "los gradientes EXPLOTAN o se DESVANECEN. Inicialización de He (para ReLU) o Xavier (para tanh) los ponen "
          "a la escala justa. La NORMALIZACIÓN por lotes (BatchNorm) o por capa (LayerNorm, la de los transformers) "
          "recentra las activaciones en cada paso. Las conexiones RESIDUALES (sumar la entrada a la salida de un "
          "bloque) dejan pasar el gradiente aunque haya cientos de capas. Y el RECORTE de gradiente evita saltos "
          "enormes (lo usa la receta «red recurrente»)."},
{"id": "cnn", "area": "Redes neuronales", "titulo": "Redes convolucionales (CNN) para imágenes",
 "temas": "convolucional cnn imagen filtros kernel pooling stride padding vision resnet caracteristicas",
 "texto": "Una imagen tiene millones de píxeles: conectar todos con todos sería imposible. Una CONVOLUCIÓN usa "
          "filtros pequeños (3×3) que se deslizan por la imagen con los MISMOS pesos: detectan bordes y texturas "
          "estén donde estén. Las primeras capas ven bordes; las siguientes, formas; las últimas, objetos. El "
          "POOLING reduce el tamaño quedándose con lo más fuerte. Arquitecturas famosas: LeNet, AlexNet, VGG, "
          "ResNet (con conexiones residuales). Hoy compiten con los transformers de visión (ViT). Receta: «red "
          "convolucional»."},
{"id": "rnn_lstm", "area": "Redes neuronales", "titulo": "Redes recurrentes, LSTM y GRU",
 "temas": "recurrente rnn lstm gru secuencias memoria estado oculto puertas tiempo texto audio series",
 "texto": "Para SECUENCIAS (texto, audio, series de datos) una red recurrente procesa un elemento cada vez y lleva "
          "un ESTADO OCULTO que resume lo anterior. El problema: al retropropagar por muchos pasos, el gradiente se "
          "desvanece y olvida lo lejano. La LSTM añade una «cinta» de memoria con PUERTAS (olvidar, entrar, salir) "
          "que deciden qué guardar; la GRU es una versión más sencilla. Fueron lo mejor para traducir y reconocer "
          "voz hasta que llegaron los transformers; siguen siendo útiles en dispositivos pequeños. Receta: «red "
          "recurrente»."},
{"id": "transformers", "area": "Redes neuronales", "titulo": "Transformers y atención, por dentro",
 "temas": "transformer atencion multicabeza qkv posicional embeddings feed forward capas decodificador gpt bert",
 "texto": "Un transformer es una pila de bloques iguales. Cada bloque: ATENCIÓN multicabeza (cada token mezcla "
          "información de los demás según la similitud consulta·clave, receta «atencion»), luego una pequeña red "
          "por token (feed-forward), con normalización y conexiones residuales alrededor de cada parte. Como la "
          "atención no sabe de orden, se añade la POSICIÓN a cada token (sinusoidal o RoPE). Los modelos que "
          "escriben (GPT, Qwen, Claude) son solo-decodificador con máscara causal; BERT es solo-codificador. Todo se "
          "entrena prediciendo la siguiente ficha con muchísimo texto."},
{"id": "embeddings", "area": "Redes neuronales", "titulo": "Embeddings: convertir palabras en números con significado",
 "temas": "embeddings vectores palabras significado similitud coseno word2vec busqueda semantica rag",
 "texto": "Un EMBEDDING es una lista de números que representa una palabra, una frase o una imagen, aprendida para "
          "que cosas parecidas queden CERCA (rey − hombre + mujer ≈ reina, en word2vec). La cercanía se mide con la "
          "similitud del coseno. Sirven para buscar por significado y no por palabras exactas (búsqueda semántica) "
          "y para RAG: buscar los trozos de documentos más parecidos a la pregunta y dárselos al modelo de lenguaje "
          "para que responda con ellos, como hace Kira con su baúl (aunque Kira busca por raíces de palabras)."},
{"id": "refuerzo", "area": "Redes neuronales", "titulo": "Aprendizaje por refuerzo",
 "temas": "refuerzo agente entorno recompensa politica q learning exploracion explotacion rlhf juegos alphago",
 "texto": "Un AGENTE actúa en un ENTORNO y recibe RECOMPENSAS; aprende una POLÍTICA (qué hacer en cada situación) "
          "que maximice la recompensa total a largo plazo. El dilema central es EXPLORAR (probar cosas nuevas) frente "
          "a EXPLOTAR (repetir lo que funciona). Q-learning aprende el valor de cada acción (receta «q learning»); "
          "con redes neuronales aprendió a jugar a Atari (DQN) y, con búsqueda, a ganar al Go (AlphaGo). RLHF "
          "(refuerzo con preferencias humanas) es una de las técnicas para que los modelos de lenguaje sean útiles."},
{"id": "difusion", "area": "Redes neuronales", "titulo": "Modelos de difusión: cómo pinta el pintor de Kira",
 "temas": "difusion stable diffusion ruido quitar ruido latente vae unet texto imagen pasos cfg gan generativo",
 "texto": "Un modelo de DIFUSIÓN aprende a QUITAR RUIDO: en el entrenamiento se ensucian fotos poco a poco y la red "
          "aprende a deshacer cada paso. Para pintar, se parte de puro ruido y se limpia en varios pasos, guiándose "
          "por el texto (que un codificador como CLIP convierte en números). Stable Diffusion trabaja en un espacio "
          "LATENTE pequeño y un VAE (o el TAESD, más rápido) lo convierte en imagen al final. La «guía» (CFG) dice "
          "cuánto obedecer al texto. Los modelos «turbo» y SDXS están destilados para pintar en 1-4 pasos: por eso el "
          "móvil puede. Antes se usaban GAN (un generador contra un discriminador)."},
{"id": "entrenar_en_movil", "area": "Redes neuronales", "titulo": "Entrenar en el móvil: qué se puede y qué no",
 "temas": "entrenar movil inferencia ajuste fino lora cuantizacion memoria gpu limites numpy python puro",
 "texto": "USAR un modelo (inferencia) cabe en el móvil: el cerebro de Kira (2-4 mil millones de parámetros "
          "cuantizados) y el pintor. ENTRENAR uno grande, no: hace falta guardar gradientes y estados del "
          "optimizador (3-4 veces la memoria) y semanas de tarjetas gráficas. Lo que sí: redes PEQUEÑAS en Python "
          "puro (las recetas de Kira entrenan en segundos), y en un ordenador con GPU, AJUSTE FINO con LoRA (se "
          "entrenan solo unas matrices pequeñas añadidas, un 1 % de los pesos) para enseñar un estilo o un tema a un "
          "modelo ya hecho. Para datos de verdad, numpy/PyTorch en el PC: Python puro es cien veces más lento."},
{"id": "evaluar_modelo", "area": "Redes neuronales", "titulo": "Cómo saber si un modelo funciona",
 "temas": "evaluar metricas precision recall f1 matriz confusion validacion cruzada prueba sesgo datos fuga",
 "texto": "Separa los datos en ENTRENAMIENTO, VALIDACIÓN (para elegir hiperparámetros) y PRUEBA (solo al final, una "
          "vez). Con pocos datos, validación cruzada. La exactitud engaña si una clase es rara: mira la MATRIZ DE "
          "CONFUSIÓN, la precisión (de lo que dijo «sí», cuánto lo era), la exhaustividad o recall (de lo que era "
          "«sí», cuánto encontró) y F1. Cuidado con la FUGA de datos (que algo de la prueba se cuele en el "
          "entrenamiento) y con los SESGOS: un modelo aprende también los defectos de sus datos. Compara siempre con "
          "una línea base sencilla."},
]
