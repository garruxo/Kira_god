# -*- coding: utf-8 -*-
"""
recetas_ingenieria_kira.py - INGENIERÍA INFORMÁTICA avanzada para Kira (lógica PURA: sin red, sin Kivy, sin archivos).

  RECETAS   : algoritmos y estructuras de datos avanzados escritos como MÓDULOS completos de Kira (con registrar()).
              Cada una trae su "prueba": tests/test_saber.py la instala, la ejecuta y comprueba la respuesta, y
              tests/test_ingenieria.py la ejecuta también en el editor seguro. Si algo no funciona, las pruebas fallan.
              saber_mejoras_kira las usa como guía cuando Kira programa una mejora (la más parecida al pedido).
  CONCEPTOS : fichas de teoría (complejidad, sistemas operativos, redes, bases de datos, compiladores, sistemas
              distribuidos, arquitectura, seguridad DEFENSIVA, IA…). «estudia ingeniería» las guarda en el baúl de
              recuerdos sin internet, y desde ahí Kira las responde sola y se las pasa al cerebro cuando programa.

Formato de una receta: id, titulo, area, temas (palabras para encontrarla), idea, complejidad, codigo, prueba
[(orden, texto, lo que debe aparecer en la respuesta)].
Nada de aquí ejecuta, descarga ni ataca nada: es saber para aprender y para programar mejor.
"""

RECETAS = [
# =====================================================================================================================
#  ESTRUCTURAS DE DATOS
# =====================================================================================================================
{
"id": "union_find",
"titulo": "Conjuntos disjuntos (Union-Find) con compresión de caminos",
"area": "Estructuras de datos",
"temas": "union find conjuntos disjuntos grupos componentes conectados unir juntar amigos redes ciclo kruskal dsu "
         "particion clases equivalencia",
"idea": "Cada grupo es un árbol y su raíz lo representa. hallar(x) sube hasta la raíz y, de paso, hace que todos "
        "apunten directo a ella (compresión de caminos); unir(a, b) cuelga la raíz del árbol bajo de la del alto "
        "(unión por rango). Si dos ya tienen la misma raíz, unirlos cerraría un ciclo.",
"complejidad": "casi O(1) por operación: O(α(n)), la inversa de Ackermann (menos de 5 en la práctica)",
"codigo": r'''
class UnionFind:
    """Conjuntos disjuntos: hallar() y unir() en casi O(1) gracias a la compresión de caminos y la unión por rango."""

    def __init__(self):
        self.padre = {}
        self.rango = {}

    def hallar(self, x):
        if x not in self.padre:
            self.padre[x] = x
            self.rango[x] = 0
        raiz = x
        while self.padre[raiz] != raiz:
            raiz = self.padre[raiz]
        while self.padre[x] != raiz:                 # compresión: todo el camino apunta directo a la raíz
            self.padre[x], x = raiz, self.padre[x]
        return raiz

    def unir(self, a, b):
        ra, rb = self.hallar(a), self.hallar(b)
        if ra == rb:
            return False                             # ya estaban juntos: esta unión cerraría un ciclo
        if self.rango[ra] < self.rango[rb]:          # unión por rango: el árbol bajo cuelga del alto
            ra, rb = rb, ra
        self.padre[rb] = ra
        if self.rango[ra] == self.rango[rb]:
            self.rango[ra] += 1
        return True

    def grupos(self):
        g = {}
        for x in list(self.padre):
            g.setdefault(self.hallar(x), []).append(x)
        return sorted(sorted(v) for v in g.values())


def registrar():
    def grupos(texto):
        # «grupos a-b b-c d-e»: cada pareja dice que esas dos cosas van en el mismo grupo
        pares = []
        for t in texto.replace(",", " ").split():
            a, _, b = t.partition("-")
            if not a or not b:
                raise ValueError(f"No entiendo «{t}». Uso: grupos a-b b-c d-e")
            pares.append((a, b))
        if not pares:
            raise ValueError("Uso: grupos a-b b-c d-e (cada pareja une dos cosas)")
        uf = UnionFind()
        ciclos = [f"{a}-{b}" for a, b in pares if not uf.unir(a, b)]
        gs = uf.grupos()
        lineas = [f"{len(gs)} grupos:"] + ["- " + ", ".join(g) for g in gs]
        if ciclos:
            lineas.append("Uniones que cerraban un ciclo (ya estaban en el mismo grupo): " + ", ".join(ciclos))
        return "\n".join(lineas)
    return {"grupos": grupos}
''',
"prueba": [("grupos", "a-b b-c d-e c-a", "2 grupos"), ("grupos", "a-b b-c d-e c-a", "ciclo")],
},
{
"id": "trie",
"titulo": "Árbol de prefijos (trie) para autocompletar",
"area": "Estructuras de datos",
"temas": "trie arbol prefijos prefijo autocompletar autocompletado sugerencias teclado palabras diccionario buscador "
         "completar escribir",
"idea": "Cada nodo es una letra y el camino desde la raíz forma la palabra. Para autocompletar se baja por las "
        "letras del prefijo y se recorre solo ese subárbol, ordenando por lo usada que es cada palabra.",
"complejidad": "insertar y buscar un prefijo: O(L), el largo de la palabra, da igual cuántas haya guardadas",
"codigo": r'''
VOCABULARIO = ("programa programa programa programar programador proceso proceso procesador protocolo proyecto "
               "proyecto prueba prueba python python python pila puntero paquete codigo codigo compilador compilar "
               "cola clase clase cache ciclo cifrado algoritmo algoritmo arbol arbol arreglo asincrono grafo grafo "
               "hilo hash memoria memoria monticulo matriz modulo nodo objeto red recursion socket sistema servidor "
               "tabla tipo variable vector kira kira kivy")


class NodoTrie:
    __slots__ = ("hijos", "fin", "peso")

    def __init__(self):
        self.hijos = {}
        self.fin = False
        self.peso = 0


class Trie:
    """Árbol de prefijos: buscar un prefijo cuesta lo que mide el prefijo, no lo que mide el diccionario."""

    def __init__(self):
        self.raiz = NodoTrie()

    def insertar(self, palabra, peso=1):
        nodo = self.raiz
        for c in palabra:
            nodo = nodo.hijos.setdefault(c, NodoTrie())
        nodo.fin = True
        nodo.peso += peso

    def con_prefijo(self, prefijo, maximo=8):
        nodo = self.raiz
        for c in prefijo:
            nodo = nodo.hijos.get(c)
            if nodo is None:
                return []
        hallados, pila = [], [(nodo, prefijo)]
        while pila:                                  # recorrido en profundidad del subárbol del prefijo
            n, palabra = pila.pop()
            if n.fin:
                hallados.append((-n.peso, palabra))
            for c, hijo in n.hijos.items():
                pila.append((hijo, palabra + c))
        return [p for _, p in sorted(hallados)[:maximo]]


def registrar():
    def autocompleta(texto):
        # «autocompleta pro» (vocabulario de Kira) o «autocompleta ca: casa cama coche casa» (tus palabras)
        prefijo, _, palabras = texto.lower().partition(":")
        prefijo = prefijo.strip()
        if not prefijo:
            raise ValueError("Uso: autocompleta pro   o   autocompleta ca: casa cama coche")
        t = Trie()
        for p in (palabras if palabras.strip() else VOCABULARIO).split():
            t.insertar(p)
        r = t.con_prefijo(prefijo)
        if not r:
            return f"Ninguna palabra empieza por «{prefijo}»."
        return f"Empiezan por «{prefijo}» (las más usadas primero): " + ", ".join(r)
    return {"autocompleta": autocompleta}
''',
"prueba": [("autocompleta", "pro", "programa"), ("autocompleta", "ca: casa cama coche casa", "casa, cama")],
},
{
"id": "monticulo",
"titulo": "Montículo binario (cola de prioridad) hecho a mano: top-k y heapsort",
"area": "Estructuras de datos",
"temas": "monticulo heap cola prioridad prioridades top mayores menores mejores altas altos ranking notas "
         "puntuaciones heapsort urgente binario flotar hundir",
"idea": "Un árbol binario completo guardado en una lista: los hijos de i están en 2i+1 y 2i+2. Al meter, el valor "
        "FLOTA mientras sea menor que su padre; al sacar el mínimo, el último pasa arriba y se HUNDE hacia el hijo "
        "menor. Para los k mayores basta un montículo de tamaño k.",
"complejidad": "meter y sacar O(log n); mínimo O(1); top-k O(n log k); heapsort O(n log n) sin memoria extra",
"codigo": r'''
class Monticulo:
    """Montículo binario de MÍNIMOS en una lista."""

    def __init__(self):
        self.a = []

    def __len__(self):
        return len(self.a)

    def minimo(self):
        return self.a[0]

    def meter(self, x):
        a = self.a
        a.append(x)
        i = len(a) - 1
        while i > 0:                                 # flotar: sube mientras sea menor que su padre
            p = (i - 1) // 2
            if a[p] <= a[i]:
                break
            a[p], a[i] = a[i], a[p]
            i = p

    def sacar(self):
        a = self.a
        if not a:
            raise IndexError("el montículo está vacío")
        tope, ultimo = a[0], a.pop()
        if a:
            a[0] = ultimo
            i, n = 0, len(a)
            while True:                              # hundir: baja hacia el hijo menor
                h = 2 * i + 1
                if h >= n:
                    break
                if h + 1 < n and a[h + 1] < a[h]:
                    h += 1
                if a[i] <= a[h]:
                    break
                a[i], a[h] = a[h], a[i]
                i = h
        return tope


def numeros(texto):
    try:
        return [float(x) if "." in x else int(x) for x in texto.replace(",", " ").split()]
    except ValueError:
        raise ValueError("Escribe solo números separados por espacios.")


def bonito(x):
    return f"{x:g}" if isinstance(x, float) else str(x)


def registrar():
    def mayores(texto):
        # «mayores 3 de 5 1 9 7 3 8»: los k mayores con un montículo de tamaño k
        k_txt, _, resto = texto.partition(" de ")
        if not resto.strip() or not k_txt.strip().isdigit() or int(k_txt) < 1:
            raise ValueError("Uso: mayores 3 de 5 1 9 7 3 8")
        k, datos = int(k_txt), numeros(resto)
        m = Monticulo()
        for x in datos:
            if len(m) < k:
                m.meter(x)
            elif x > m.minimo():                     # el más pequeño de los k mejores sale
                m.sacar()
                m.meter(x)
        top = sorted((m.sacar() for _ in range(len(m))), reverse=True)
        return f"Los {len(top)} mayores: " + ", ".join(bonito(x) for x in top) + f" (montículo de tamaño {k}: O(n log k))"

    def heapsort(texto):
        m = Monticulo()
        for x in numeros(texto):
            m.meter(x)
        return "Ordenado con un montículo: " + ", ".join(bonito(m.sacar()) for _ in range(len(m)))
    return {"mayores": mayores, "heapsort": heapsort}
''',
"prueba": [("mayores", "3 de 5 1 9 7 3 8", "9, 8, 7"), ("heapsort", "5 1 9 7 3", "1, 3, 5, 7, 9")],
},
{
"id": "cache_lru",
"titulo": "Caché LRU en O(1): diccionario + lista doblemente enlazada",
"area": "Estructuras de datos",
"temas": "cache lru memoria reciente ultimo usado recordar expulsar eviccion lista enlazada doble diccionario "
         "aciertos fallos navegador rendimiento memoizar",
"idea": "El diccionario encuentra cada clave en O(1) y la lista doblemente enlazada mantiene el orden de uso: lo "
        "usado pasa al frente y, si la caché está llena, se expulsa el del final (el usado hace más tiempo). Los "
        "nodos centinela evitan casos especiales en los extremos.",
"complejidad": "leer y poner O(1); memoria O(capacidad)",
"codigo": r'''
class Nodo:
    __slots__ = ("clave", "valor", "ant", "sig")

    def __init__(self, clave=None, valor=None):
        self.clave, self.valor, self.ant, self.sig = clave, valor, None, None


class CacheLRU:
    """Al llenarse expulsa lo usado hace MÁS tiempo (Least Recently Used)."""

    def __init__(self, capacidad):
        if capacidad < 1:
            raise ValueError("La capacidad debe ser al menos 1.")
        self.capacidad = capacidad
        self.mapa = {}
        self.cabeza, self.cola = Nodo(), Nodo()      # centinelas: cabeza.sig es el más reciente
        self.cabeza.sig, self.cola.ant = self.cola, self.cabeza

    def _desenganchar(self, n):
        n.ant.sig, n.sig.ant = n.sig, n.ant

    def _al_frente(self, n):
        n.ant, n.sig = self.cabeza, self.cabeza.sig
        self.cabeza.sig.ant = n
        self.cabeza.sig = n

    def leer(self, clave):
        n = self.mapa.get(clave)
        if n is None:
            return None
        self._desenganchar(n)
        self._al_frente(n)
        return n.valor

    def poner(self, clave, valor):
        """Guarda el valor y devuelve la clave expulsada (o None)."""
        n = self.mapa.get(clave)
        if n is not None:
            n.valor = valor
            self._desenganchar(n)
            self._al_frente(n)
            return None
        expulsada = None
        if len(self.mapa) >= self.capacidad:
            viejo = self.cola.ant
            self._desenganchar(viejo)
            del self.mapa[viejo.clave]
            expulsada = viejo.clave
        n = Nodo(clave, valor)
        self.mapa[clave] = n
        self._al_frente(n)
        return expulsada

    def orden(self):
        res, n = [], self.cabeza.sig
        while n is not self.cola:
            res.append(n.clave)
            n = n.sig
        return res


def registrar():
    def simula(texto):
        # «cache lru 2: a b a c b a»: capacidad 2 y la secuencia de peticiones
        cap, _, pedidos = texto.partition(":")
        if not pedidos.split() or not cap.strip().isdigit():
            raise ValueError("Uso: cache lru 2: a b a c b a")
        c = CacheLRU(int(cap))
        aciertos, lineas = 0, []
        for p in pedidos.split():
            if c.leer(p) is not None:
                aciertos += 1
                que = "acierto"
            else:
                fuera = c.poner(p, True)
                que = "fallo" + (f", expulsa {fuera}" if fuera else "")
            lineas.append(f"{p}: {que:18} -> [{' '.join(c.orden())}]")
        total = len(pedidos.split())
        lineas.append(f"Aciertos: {aciertos}, fallos: {total - aciertos} (tasa de acierto {round(100 * aciertos / total)} %)")
        return "\n".join(lineas)
    return {"cache lru": simula}
''',
"prueba": [("cache lru", "2: a b a c b a", "Aciertos: 1, fallos: 5")],
},
{
"id": "fenwick",
"titulo": "Árbol de Fenwick: sumas por tramos con cambios en O(log n)",
"area": "Estructuras de datos",
"temas": "fenwick bit arbol indices binarios suma sumas tramo rango rangos prefijo acumulada actualizar consulta "
         "estadisticas ventas",
"idea": "La casilla i guarda la suma de los últimos (i & -i) elementos hasta i; i & -i es el bit más bajo de i. "
        "Para sumar un prefijo se va quitando ese bit; para cambiar un valor se va sumando. Una suma de tramo es "
        "la resta de dos prefijos.",
"complejidad": "construir O(n log n); suma de tramo y cambio O(log n); memoria O(n)",
"codigo": r'''
class Fenwick:
    """Árbol de Fenwick (Binary Indexed Tree). Posiciones desde 1."""

    def __init__(self, valores):
        self.n = len(valores)
        self.t = [0] * (self.n + 1)
        for i, v in enumerate(valores, 1):
            self.sumar(i, v)

    def sumar(self, i, delta):
        while i <= self.n:
            self.t[i] += delta
            i += i & -i                              # siguiente casilla que también cubre a i

    def prefijo(self, i):
        s = 0
        while i > 0:
            s += self.t[i]
            i -= i & -i                              # quita el bit más bajo
        return s

    def tramo(self, a, b):
        return self.prefijo(b) - self.prefijo(a - 1)


def registrar():
    def suma_rango(texto):
        # «suma rango 3 1 4 1 5 9 | 2 5»: suma de la posición 2 a la 5;  «... | 2 5 | 3=10»: tras cambiar la 3ª a 10
        partes = [p.strip() for p in texto.split("|")]
        if len(partes) < 2 or len(partes[1].split()) < 2:
            raise ValueError("Uso: suma rango 3 1 4 1 5 9 | 2 5   (y si quieres | 3=10 para cambiar un valor)")
        valores = [int(x) for x in partes[0].split()]
        a, b = (int(x) for x in partes[1].split()[:2])
        if not 1 <= a <= b <= len(valores):
            raise ValueError(f"El tramo debe ir de 1 a {len(valores)}.")
        f = Fenwick(valores)
        res = [f"Suma de las posiciones {a} a {b}: {f.tramo(a, b)}"]
        for cambio in partes[2:]:
            for c in cambio.split():
                i, _, v = c.partition("=")
                i, v = int(i), int(v)
                if not 1 <= i <= len(valores):
                    raise ValueError(f"La posición {i} no existe.")
                f.sumar(i, v - valores[i - 1])
                valores[i - 1] = v
            res.append(f"Tras cambiar ({cambio}): {f.tramo(a, b)}")
        return "\n".join(res)
    return {"suma rango": suma_rango}
''',
"prueba": [("suma rango", "3 1 4 1 5 9 2 6 | 2 5", "Suma de las posiciones 2 a 5: 11"),
           ("suma rango", "3 1 4 1 5 9 2 6 | 2 5 | 3=10", "Tras cambiar (3=10): 17")],
},
{
"id": "arbol_segmentos",
"titulo": "Árbol de segmentos: mínimo, máximo y suma de un tramo en O(log n)",
"area": "Estructuras de datos",
"temas": "arbol segmentos segment tree minimo maximo suma tramo rango consulta actualizar intervalo rmq "
         "asociativa",
"idea": "Las hojas son los datos y cada nodo guarda la operación (mínimo, máximo o suma) de sus dos hijos. Un tramo "
        "se responde combinando O(log n) nodos; cambiar un dato solo recalcula su camino hasta la raíz. Vale para "
        "cualquier operación asociativa.",
"complejidad": "construir O(n); consulta y cambio O(log n); memoria 2n",
"codigo": r'''
class ArbolSegmentos:
    """Versión compacta de abajo arriba: las hojas en t[n..2n), el nodo i combina t[2i] y t[2i+1]."""

    def __init__(self, datos, op, neutro):
        self.n, self.op, self.neutro = len(datos), op, neutro
        self.t = [neutro] * self.n + list(datos)
        for i in range(self.n - 1, 0, -1):
            self.t[i] = op(self.t[2 * i], self.t[2 * i + 1])

    def cambiar(self, i, valor):                     # posición desde 0
        i += self.n
        self.t[i] = valor
        while i > 1:
            i //= 2
            self.t[i] = self.op(self.t[2 * i], self.t[2 * i + 1])

    def consultar(self, a, b):                       # tramo [a, b) desde 0
        izq = der = self.neutro
        a += self.n
        b += self.n
        while a < b:
            if a & 1:
                izq = self.op(izq, self.t[a])
                a += 1
            if b & 1:
                b -= 1
                der = self.op(self.t[b], der)
            a //= 2
            b //= 2
        return self.op(izq, der)


def suma(a, b):
    return a + b


def registrar():
    def tramo(texto):
        # «minimo rango 5 2 8 1 9 3 | 2 4» (posiciones 2 a 4)  y opcional «| 4=7» para cambiar la 4ª
        partes = [p.strip() for p in texto.split("|")]
        if len(partes) < 2 or len(partes[1].split()) < 2:
            raise ValueError("Uso: minimo rango 5 2 8 1 9 3 | 2 4   (y si quieres | 4=7)")
        datos = [int(x) for x in partes[0].split()]
        a, b = (int(x) for x in partes[1].split()[:2])
        if not 1 <= a <= b <= len(datos):
            raise ValueError(f"El tramo debe ir de 1 a {len(datos)}.")
        arboles = [("mínimo", ArbolSegmentos(datos, min, float("inf"))),
                   ("máximo", ArbolSegmentos(datos, max, float("-inf"))),
                   ("suma", ArbolSegmentos(datos, suma, 0))]

        def informe(cabecera):
            return cabecera + ", ".join(f"{nombre} {arbol.consultar(a - 1, b)}" for nombre, arbol in arboles)
        res = [informe(f"Tramo {a}..{b}: ")]
        for cambio in partes[2:]:
            for c in cambio.split():
                i, _, v = c.partition("=")
                if not 1 <= int(i) <= len(datos):
                    raise ValueError(f"La posición {i} no existe.")
                for _, arbol in arboles:
                    arbol.cambiar(int(i) - 1, int(v))
            res.append(informe(f"Tras cambiar ({cambio}): "))
        return "\n".join(res)
    return {"minimo rango": tramo, "mínimo rango": tramo}
''',
"prueba": [("minimo rango", "5 2 8 1 9 3 | 2 4", "mínimo 1, máximo 8, suma 11"),
           ("minimo rango", "5 2 8 1 9 3 | 2 4 | 4=7", "Tras cambiar (4=7): mínimo 2")],
},
{
"id": "filtro_bloom",
"titulo": "Filtro de Bloom: ¿lo he visto ya? con muy poca memoria",
"area": "Estructuras de datos",
"temas": "bloom filtro probabilistico pertenencia conjunto visto duplicados falsos positivos bits hash memoria "
         "spam cache base datos",
"idea": "Una fila de m bits y k funciones hash. Añadir enciende k bits; preguntar mira si los k están encendidos. Si "
        "alguno está apagado, SEGURO que no está; si todos están encendidos, PROBABLEMENTE sí (falso positivo "
        "posible, falso negativo nunca). Con doble hash bastan 2 cálculos para k posiciones.",
"complejidad": "añadir y consultar O(k); memoria m bits; falso positivo ≈ (1 - e^(-kn/m))^k, k óptimo = (m/n)·ln 2",
"codigo": r'''
import hashlib
import math


class FiltroBloom:
    def __init__(self, bits=512, k=4):
        self.m, self.k = bits, k
        self.bits = bytearray((bits + 7) // 8)
        self.n = 0

    def _posiciones(self, x):
        h = hashlib.sha256(str(x).encode("utf-8")).digest()
        h1 = int.from_bytes(h[:8], "big")
        h2 = int.from_bytes(h[8:16], "big") | 1
        return [(h1 + i * h2) % self.m for i in range(self.k)]    # doble hash: k posiciones con 2 cálculos

    def anadir(self, x):
        for p in self._posiciones(x):
            self.bits[p // 8] |= 1 << (p % 8)
        self.n += 1

    def quizas(self, x):
        return all(self.bits[p // 8] >> (p % 8) & 1 for p in self._posiciones(x))

    def prob_falso_positivo(self):
        return (1 - math.exp(-self.k * self.n / self.m)) ** self.k


def registrar():
    def bloom(texto):
        # «filtro bloom kira python java | rust python»: guarda las primeras y pregunta por las segundas
        guardar, _, preguntar = texto.lower().partition("|")
        if not guardar.split() or not preguntar.split():
            raise ValueError("Uso: filtro bloom kira python java | rust python")
        f = FiltroBloom()
        for w in guardar.split():
            f.anadir(w)
        res = [f"{w}: probablemente sí (podría ser un falso positivo)" if f.quizas(w) else f"{w}: seguro que no"
               for w in preguntar.split()]
        m_1 = math.ceil(-f.n * math.log(0.01) / math.log(2) ** 2)      # bits para un 1 % de falsos positivos
        res.append(f"Falso positivo ahora: {f.prob_falso_positivo():.2e} ({f.m} bits, k={f.k}, {len(f.bits)} bytes). "
                   f"Para {f.n} elementos con un 1 % bastarían {m_1} bits y k={max(1, round(m_1 / f.n * math.log(2)))}.")
        return "\n".join(res)
    return {"filtro bloom": bloom}
''',
"prueba": [("filtro bloom", "kira python java | rust python", "rust: seguro que no"),
           ("filtro bloom", "kira python java | rust python", "python: probablemente sí")],
},
{
"id": "arbol_avl",
"titulo": "Árbol AVL: árbol de búsqueda que se equilibra solo con giros",
"area": "Estructuras de datos",
"temas": "avl arbol busqueda binario equilibrado balanceado giros rotaciones altura ordenado bst rojo negro "
         "diccionario ordenado indice",
"idea": "Un árbol de búsqueda normal con datos ya ordenados degenera en una lista (altura n). El AVL guarda la altura "
        "de cada nodo y, al insertar, si un lado queda 2 más alto que el otro lo corrige con un giro simple o doble. "
        "Así la altura nunca pasa de ~1,44·log₂ n.",
"complejidad": "insertar, buscar y borrar O(log n) siempre (el árbol sin equilibrar llega a O(n))",
"codigo": r'''
class Nodo:
    __slots__ = ("clave", "izq", "der", "alto")

    def __init__(self, clave):
        self.clave, self.izq, self.der, self.alto = clave, None, None, 1


def alto(n):
    return n.alto if n else 0


def recalcular(n):
    n.alto = 1 + max(alto(n.izq), alto(n.der))


def girar_der(y):
    x = y.izq
    y.izq, x.der = x.der, y
    recalcular(y)
    recalcular(x)
    return x


def girar_izq(x):
    y = x.der
    x.der, y.izq = y.izq, x
    recalcular(x)
    recalcular(y)
    return y


def insertar(n, clave):
    """Inserta como en un árbol de búsqueda y, a la vuelta, re-equilibra si un lado es 2 más alto."""
    if n is None:
        return Nodo(clave)
    if clave < n.clave:
        n.izq = insertar(n.izq, clave)
    elif clave > n.clave:
        n.der = insertar(n.der, clave)
    else:
        return n
    recalcular(n)
    equilibrio = alto(n.izq) - alto(n.der)
    if equilibrio > 1:
        if clave > n.izq.clave:                      # izquierda-derecha: doble giro
            n.izq = girar_izq(n.izq)
        return girar_der(n)
    if equilibrio < -1:
        if clave < n.der.clave:                      # derecha-izquierda: doble giro
            n.der = girar_der(n.der)
        return girar_izq(n)
    return n


def altura_sin_equilibrar(claves):
    """Árbol de búsqueda normal, sin giros (iterativo para no agotar la recursión cuando degenera)."""
    hijos, raiz, altura = {}, None, 0
    for c in claves:
        if raiz is None:
            raiz, altura = c, 1
            continue
        n, prof = raiz, 1
        while c != n:
            lado = c > n
            sig = hijos.get((n, lado))
            prof += 1
            if sig is None:
                hijos[(n, lado)] = c
                altura = max(altura, prof)
                break
            n = sig
    return altura


def en_orden(n, salida):
    if n:
        en_orden(n.izq, salida)
        salida.append(n.clave)
        en_orden(n.der, salida)
    return salida


def dibujar(n, sangria, lineas):
    if n:
        dibujar(n.der, sangria + "    ", lineas)
        lineas.append(sangria + str(n.clave))
        dibujar(n.izq, sangria + "    ", lineas)
    return lineas


def registrar():
    def avl(texto):
        # «arbol avl 1 2 3 4 5 6 7» (números o palabras)
        datos = texto.replace(",", " ").split()
        if not datos or len(datos) > 500:
            raise ValueError("Uso: arbol avl 1 2 3 4 5 6 7 (hasta 500 datos)")
        try:
            datos = [float(x) if "." in x else int(x) for x in datos]
        except ValueError:
            pass                                     # son palabras: se ordenan alfabéticamente
        raiz = None
        for x in datos:
            raiz = insertar(raiz, x)
        lineas = [f"AVL: altura {raiz.alto} (raíz {raiz.clave}). Sin equilibrar: altura {altura_sin_equilibrar(datos)}.",
                  "En orden: " + " ".join(str(x) for x in en_orden(raiz, []))]
        if len(datos) <= 31:
            lineas.append("Árbol (gíralo 90°: la raíz queda a la izquierda):")
            lineas += dibujar(raiz, "", [])
        return "\n".join(lineas)
    return {"arbol avl": avl, "árbol avl": avl}
''',
"prueba": [("arbol avl", "1 2 3 4 5 6 7", "AVL: altura 3 (raíz 4)"),
           ("arbol avl", "1 2 3 4 5 6 7", "Sin equilibrar: altura 7")],
},
{
"id": "tecnicas_lineales",
"titulo": "Técnicas en O(n): ventana deslizante, Kadane y dos punteros",
"area": "Técnicas de algoritmos",
"temas": "ventana deslizante deque monotona maximos subarray kadane mejor tramo suma maxima dos punteros pareja "
         "suma lineal optimizar bucle",
"idea": "Tres trucos para pasar de O(n²) a O(n): (1) ventana deslizante con una cola que guarda índices de valores "
        "DECRECIENTES: lo que queda detrás y es menor nunca será máximo; (2) Kadane: el mejor tramo que acaba en i "
        "es max(x, mejor_anterior + x); (3) dos punteros sobre datos ordenados que se acercan desde los extremos.",
"complejidad": "las tres O(n) (dos punteros O(n log n) si hay que ordenar antes)",
"codigo": r'''
from collections import deque


def maximos_ventana(datos, k):
    q, res = deque(), []
    for i, x in enumerate(datos):
        while q and datos[q[-1]] <= x:               # los menores de detrás ya no pueden ser máximos
            q.pop()
        q.append(i)
        if q[0] <= i - k:                            # el máximo se salió de la ventana
            q.popleft()
        if i >= k - 1:
            res.append(datos[q[0]])
    return res


def kadane(datos):
    mejor, actual, ini, mejor_ini, mejor_fin = datos[0], datos[0], 0, 0, 0
    for i in range(1, len(datos)):
        if actual + datos[i] < datos[i]:             # empezar de nuevo sale mejor que arrastrar lo anterior
            actual, ini = datos[i], i
        else:
            actual += datos[i]
        if actual > mejor:
            mejor, mejor_ini, mejor_fin = actual, ini, i
    return mejor, mejor_ini, mejor_fin


def pareja_que_suma(datos, objetivo):
    d = sorted(datos)
    i, j = 0, len(d) - 1
    while i < j:
        s = d[i] + d[j]
        if s == objetivo:
            return d[i], d[j]
        if s < objetivo:
            i += 1
        else:
            j -= 1
    return None


def enteros(texto):
    try:
        return [int(x) for x in texto.replace(",", " ").split()]
    except ValueError:
        raise ValueError("Escribe números enteros separados por espacios.")


def registrar():
    def ventana(texto):
        # «maximos ventana 3 | 1 3 -1 -3 5 3 6 7»
        k, _, resto = texto.partition("|")
        datos = enteros(resto)
        if not k.strip().isdigit() or not 1 <= int(k) <= len(datos):
            raise ValueError("Uso: maximos ventana 3 | 1 3 -1 -3 5 3 6 7")
        return f"Máximo de cada ventana de {int(k)}: " + ", ".join(map(str, maximos_ventana(datos, int(k))))

    def mejor_tramo(texto):
        datos = enteros(texto)
        if not datos:
            raise ValueError("Uso: mejor tramo -2 1 -3 4 -1 2 1 -5 4")
        s, a, b = kadane(datos)
        return f"Mejor tramo (Kadane): posiciones {a + 1} a {b + 1} -> {', '.join(map(str, datos[a:b + 1]))}, suma {s}"

    def pareja(texto):
        objetivo, _, resto = texto.partition("|")
        r = pareja_que_suma(enteros(resto), int(objetivo))
        return f"{r[0]} + {r[1]} = {int(objetivo)} (dos punteros)" if r else "Ninguna pareja suma eso."
    return {"maximos ventana": ventana, "máximos ventana": ventana, "mejor tramo": mejor_tramo,
            "pareja que suma": pareja}
''',
"prueba": [("maximos ventana", "3 | 1 3 -1 -3 5 3 6 7", "3, 3, 5, 5, 6, 7"),
           ("mejor tramo", "-2 1 -3 4 -1 2 1 -5 4", "4, -1, 2, 1, suma 6"),
           ("pareja que suma", "9 | 2 7 11 15", "2 + 7 = 9")],
},
# =====================================================================================================================
#  GRAFOS
# =====================================================================================================================
{
"id": "dijkstra",
"titulo": "Dijkstra: el camino más corto con pesos (mapas, rutas, redes)",
"area": "Grafos",
"temas": "dijkstra camino corto ruta rutas mapa gps distancia pesos grafo red enrutamiento navegacion coste "
         "cola prioridad",
"idea": "Desde el origen se va cerrando siempre el nodo PENDIENTE más cercano (con una cola de prioridad). Al "
        "cerrarlo, su distancia ya es definitiva y se intenta mejorar la de sus vecinos (relajar). Funciona porque "
        "los pesos no son negativos; con negativos hace falta Bellman-Ford.",
"complejidad": "O((V + E) log V) con montículo; memoria O(V)",
"codigo": r'''
import heapq


def leer_grafo(texto):
    """«A-B:4» une A y B en los dos sentidos con peso 4; «A>B:4» solo de A a B; sin «:peso» vale 1."""
    g = {}
    for t in texto.replace(",", " ").split():
        sep = ">" if ">" in t else "-"
        ab, _, peso = t.partition(":")
        a, _, b = ab.partition(sep)
        if not a or not b:
            raise ValueError(f"No entiendo «{t}»: escribe A-B:4 (o A>B:4 si es de un solo sentido)")
        w = float(peso) if peso else 1.0
        if w < 0:
            raise ValueError("Dijkstra no admite pesos negativos (para eso está Bellman-Ford).")
        g.setdefault(a, []).append((b, w))
        g.setdefault(b, [])
        if sep == "-":
            g[b].append((a, w))
    return g


def dijkstra(g, origen):
    dist, previo = {origen: 0.0}, {origen: None}
    cola, cerrados = [(0.0, origen)], set()
    while cola:
        d, u = heapq.heappop(cola)
        if u in cerrados:
            continue                                 # entrada vieja: ya se cerró con una distancia menor
        cerrados.add(u)
        for v, w in g[u]:
            nueva = d + w
            if nueva < dist.get(v, float("inf")):   # relajar
                dist[v], previo[v] = nueva, u
                heapq.heappush(cola, (nueva, v))
    return dist, previo


def camino(previo, destino):
    res = []
    while destino is not None:
        res.append(destino)
        destino = previo[destino]
    return res[::-1]


def registrar():
    def ruta(texto):
        # «camino más corto A-B:4 A-C:2 C-B:1 B-D:5 C-D:8 | A D»
        grafo_txt, _, extremos = texto.partition("|")
        if len(extremos.split()) != 2:
            raise ValueError("Uso: camino más corto A-B:4 A-C:2 C-B:1 | A B")
        o, d = extremos.split()
        g = leer_grafo(grafo_txt)
        if o not in g or d not in g:
            raise ValueError(f"{o} o {d} no aparece en el grafo.")
        dist, previo = dijkstra(g, o)
        if d not in dist:
            return f"No hay ningún camino de {o} a {d}."
        resto = ", ".join(f"{n} {dist[n]:g}" for n in sorted(dist) if n != o)
        return (f"Ruta más corta de {o} a {d}: {' → '.join(camino(previo, d))} (coste {dist[d]:g})\n"
                f"Distancias desde {o}: {resto}")
    return {"camino más corto": ruta, "camino mas corto": ruta}
''',
"prueba": [("camino más corto", "A-B:4 A-C:2 C-B:1 B-D:5 C-D:8 | A D", "A → C → B → D (coste 8)")],
},
{
"id": "bellman_ford",
"titulo": "Bellman-Ford: pesos negativos y detección de ciclos negativos",
"area": "Grafos",
"temas": "bellman ford pesos negativos ciclo negativo arbitraje divisas camino corto relajar distancia grafo "
         "dirigido deuda",
"idea": "Relaja TODAS las aristas V-1 veces: un camino corto tiene como mucho V-1 aristas. Si en una vuelta más "
        "todavía mejora algo, hay un ciclo negativo (dar vueltas lo abarata sin fin); retrocediendo V pasos por los "
        "predecesores se cae dentro de él. Con logaritmos de cambios de divisa detecta arbitraje.",
"complejidad": "O(V·E); memoria O(V)",
"codigo": r'''
def leer_aristas(texto):
    aristas, nodos = [], []
    for t in texto.replace(",", " ").split():
        ab, _, peso = t.partition(":")
        a, _, b = ab.partition(">")
        if not a or not b:
            raise ValueError(f"No entiendo «{t}»: escribe A>B:-3 (de A a B con peso -3)")
        w = float(peso) if peso else 1.0
        aristas.append((a, b, w))
        for n in (a, b):
            if n not in nodos:
                nodos.append(n)
    return nodos, aristas


def bellman_ford(nodos, aristas, origen):
    inf = float("inf")
    dist = {n: inf for n in nodos}
    previo = {n: None for n in nodos}
    dist[origen] = 0.0
    for _ in range(len(nodos) - 1):
        cambio = False
        for a, b, w in aristas:
            if dist[a] + w < dist[b]:
                dist[b], previo[b] = dist[a] + w, a
                cambio = True
        if not cambio:
            break                                    # ya no mejora nada: se puede parar antes
    for a, b, w in aristas:                          # una vuelta más: si aún mejora, hay ciclo negativo
        if dist[a] + w < dist[b]:
            previo[b] = a
            x = b
            for _ in range(len(nodos)):              # retroceder V pasos asegura caer DENTRO del ciclo
                x = previo[x]
                if x is None:
                    return dist, previo, [b]
            ciclo, y = [x], previo[x]
            while y != x:
                ciclo.append(y)
                y = previo[y]
            return dist, previo, ciclo[::-1] + [ciclo[-1]]
    return dist, previo, None


def registrar():
    def bf(texto):
        # «bellman ford A>B:4 A>C:5 C>B:-3 B>D:2 | A»
        grafo_txt, _, origen = texto.partition("|")
        origen = origen.strip()
        nodos, aristas = leer_aristas(grafo_txt)
        if origen not in nodos:
            raise ValueError("Uso: bellman ford A>B:4 A>C:5 C>B:-3 | A   (A es el origen)")
        dist, previo, ciclo = bellman_ford(nodos, aristas, origen)
        if ciclo:
            return ("Hay un ciclo negativo: " + " → ".join(ciclo) + ". Dando vueltas el coste baja sin límite, así "
                    "que no existe «camino más corto» (en divisas sería una oportunidad de arbitraje).")
        lineas = [f"Distancias desde {origen} (admite pesos negativos):"]
        for n in nodos:
            if n == origen:
                continue
            if dist[n] == float("inf"):
                lineas.append(f"{n}: inalcanzable")
                continue
            c, x = [], n
            while x is not None:
                c.append(x)
                x = previo[x]
            lineas.append(f"{n}: {dist[n]:g} ({' → '.join(c[::-1])})")
        return "\n".join(lineas)
    return {"bellman ford": bf}
''',
"prueba": [("bellman ford", "A>B:4 A>C:5 C>B:-3 B>D:2 | A", "D: 4 (A → C → B → D)"),
           ("bellman ford", "A>B:1 B>C:-2 C>B:1 | A", "ciclo negativo")],
},
{
"id": "floyd_warshall",
"titulo": "Floyd-Warshall: las distancias entre TODOS los pares",
"area": "Grafos",
"temas": "floyd warshall todas distancias pares matriz camino corto programacion dinamica intermedio diametro "
         "grafo denso",
"idea": "Programación dinámica: d[i][j] es lo mejor usando como paradas intermedias solo los k primeros nodos. "
        "Al permitir el nodo k: d[i][j] = min(d[i][j], d[i][k] + d[k][j]). Con «siguiente[i][j]» se reconstruye "
        "el camino. Si algún d[i][i] queda negativo, hay ciclo negativo.",
"complejidad": "O(V³) tiempo y O(V²) memoria: ideal para grafos pequeños o densos",
"codigo": r'''
def leer(texto):
    nodos, aristas = [], []
    for t in texto.replace(",", " ").split():
        sep = ">" if ">" in t else "-"
        ab, _, peso = t.partition(":")
        a, _, b = ab.partition(sep)
        if not a or not b:
            raise ValueError(f"No entiendo «{t}»: escribe A-B:3 (o A>B:3 si es de un solo sentido)")
        aristas.append((a, b, float(peso) if peso else 1.0, sep == "-"))
        for n in (a, b):
            if n not in nodos:
                nodos.append(n)
    return nodos, aristas


def floyd_warshall(nodos, aristas):
    inf = float("inf")
    d = {i: {j: (0.0 if i == j else inf) for j in nodos} for i in nodos}
    sig = {i: {j: (j if i == j else None) for j in nodos} for i in nodos}
    for a, b, w, doble in aristas:
        if w < d[a][b]:
            d[a][b], sig[a][b] = w, b
        if doble and w < d[b][a]:
            d[b][a], sig[b][a] = w, a
    for k in nodos:
        dk = d[k]
        for i in nodos:
            dik = d[i][k]
            if dik == inf:
                continue
            di = d[i]
            for j in nodos:
                if dik + dk[j] < di[j]:
                    di[j] = dik + dk[j]
                    sig[i][j] = sig[i][k]
    return d, sig


def camino(sig, i, j):
    if sig[i][j] is None:
        return []
    res = [i]
    while i != j and len(res) <= len(sig):
        i = sig[i][j]
        res.append(i)
    return res


def registrar():
    def todas(texto):
        # «todas las distancias A-B:3 B-C:4 A-C:10»
        nodos, aristas = leer(texto)
        if not aristas or len(nodos) > 60:
            raise ValueError("Uso: todas las distancias A-B:3 B-C:4 A-C:10 (hasta 60 nodos)")
        d, sig = floyd_warshall(nodos, aristas)
        if any(d[n][n] < 0 for n in nodos):
            return "Hay un ciclo negativo: las distancias no están definidas."
        ancho = max(6, max(len(n) for n in nodos) + 1)
        lineas = [" " * ancho + "".join(f"{n:>{ancho}}" for n in nodos)]
        for i in nodos:
            lineas.append(f"{i:>{ancho}}" + "".join(f"{('∞' if d[i][j] == float('inf') else f'{d[i][j]:g}'):>{ancho}}"
                                                    for j in nodos))
        finitos = [(d[i][j], i, j) for i in nodos for j in nodos if i != j and d[i][j] != float("inf")]
        if finitos:
            w, i, j = max(finitos, key=lambda x: x[0])
            lineas.append(f"El par más alejado: {i} ↔ {j} = {w:g} (camino {' → '.join(camino(sig, i, j))})")
        return "\n".join(lineas)
    return {"todas las distancias": todas}
''',
"prueba": [("todas las distancias", "A-B:3 B-C:4 A-C:10", "A ↔ C = 7 (camino A → B → C)")],
},
{
"id": "kruskal",
"titulo": "Kruskal: árbol de expansión mínimo (conectar todo al menor coste)",
"area": "Grafos",
"temas": "kruskal prim arbol expansion minimo minima mst cable red conectar barato coste union find voraz "
         "aristas ordenar",
"idea": "Algoritmo voraz: se ordenan las conexiones de más barata a más cara y se coge cada una si une dos grupos "
        "distintos (si los dos extremos ya estaban conectados, cerraría un ciclo y sobra). Los grupos se llevan con "
        "Union-Find. Sirve para tender cable, tuberías o redes al mínimo coste.",
"complejidad": "O(E log E) por la ordenación; Union-Find casi O(1)",
"codigo": r'''
def leer(texto):
    nodos, aristas = set(), []
    for t in texto.replace(",", " ").split():
        ab, _, peso = t.partition(":")
        a, _, b = ab.partition("-")
        if not a or not b:
            raise ValueError(f"No entiendo «{t}»: escribe A-B:4")
        aristas.append((a, b, float(peso) if peso else 1.0))
        nodos.update((a, b))
    return nodos, aristas


def kruskal(nodos, aristas):
    padre = {n: n for n in nodos}

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]              # compresión a medias: cada nodo salta a su abuelo
            x = padre[x]
        return x
    arbol = []
    for w, a, b in sorted((w, a, b) for a, b, w in aristas):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:                                 # une dos grupos distintos: sirve
            padre[ra] = rb
            arbol.append((a, b, w))
    grupos = len({raiz(n) for n in nodos})
    return arbol, grupos


def registrar():
    def mst(texto):
        # «arbol minimo A-B:4 A-C:1 B-C:2 B-D:5 C-D:8»
        nodos, aristas = leer(texto)
        if not aristas:
            raise ValueError("Uso: arbol minimo A-B:4 A-C:1 B-C:2 B-D:5")
        arbol, grupos = kruskal(nodos, aristas)
        total = sum(w for _, _, w in arbol)
        texto_arbol = ", ".join(f"{a}-{b} ({w:g})" for a, b, w in arbol)
        aviso = "" if grupos == 1 else f"\nOjo: el grafo tiene {grupos} partes sin conexión (es un bosque)."
        return f"Árbol de expansión mínimo: {texto_arbol}; total {total:g} con {len(arbol)} conexiones.{aviso}"
    return {"arbol minimo": mst, "árbol mínimo": mst}
''',
"prueba": [("arbol minimo", "A-B:4 A-C:1 B-C:2 B-D:5 C-D:8", "A-C (1), B-C (2), B-D (5); total 8")],
},
{
"id": "orden_topologico",
"titulo": "Orden topológico (Kahn): dependencias, compilación por etapas y ciclos",
"area": "Grafos",
"temas": "topologico orden dependencias tareas compilar compilacion paquetes requisitos makefile etapas paralelo "
         "ciclo kahn grafo aciclico dag planificar",
"idea": "Se empieza por lo que no depende de nada; al terminar algo, sus dependientes pierden un requisito y, si "
        "se quedan sin ninguno, pasan a la cola. Si al final sobran tareas, hay un ciclo de dependencias. La etapa "
        "de cada tarea (1 + la etapa más tardía de lo que necesita) dice qué se puede hacer en paralelo.",
"complejidad": "O(V + E) (O(V log V + E) con el montículo para dar un orden estable)",
"codigo": r'''
import heapq


def leer(texto):
    """«app>red» significa «app necesita red» (red va antes)."""
    deps = {}
    for t in texto.replace(",", " ").split():
        a, _, b = t.partition(">")
        if not a or not b:
            raise ValueError(f"No entiendo «{t}»: escribe app>red (app necesita red)")
        deps.setdefault(a, set()).add(b)
        deps.setdefault(b, set())
    return deps


def kahn(deps):
    pendientes = {n: len(ds) for n, ds in deps.items()}
    dependientes = {n: [] for n in deps}
    for n, ds in deps.items():
        for d in ds:
            dependientes[d].append(n)
    listos = [n for n, p in pendientes.items() if p == 0]
    heapq.heapify(listos)
    etapa = {n: 1 for n in listos}
    orden = []
    while listos:
        n = heapq.heappop(listos)
        orden.append(n)
        for m in dependientes[n]:
            pendientes[m] -= 1
            etapa[m] = max(etapa.get(m, 1), etapa[n] + 1)
            if pendientes[m] == 0:
                heapq.heappush(listos, m)
    atascados = {n for n, p in pendientes.items() if p > 0}
    return orden, etapa, atascados


def un_ciclo(deps, atascados):
    x, camino = min(atascados), []
    while x not in camino:                           # todo atascado depende de algún otro atascado
        camino.append(x)
        x = min(d for d in deps[x] if d in atascados)
    return camino[camino.index(x):] + [x]


def registrar():
    def ordenar(texto):
        # «orden dependencias app>red app>ui ui>motor red>motor»
        deps = leer(texto)
        if not deps:
            raise ValueError("Uso: orden dependencias app>red app>ui ui>motor")
        orden, etapa, atascados = kahn(deps)
        if atascados:
            return ("Imposible: hay un ciclo de dependencias, nada de él puede empezar: "
                    + " → ".join(un_ciclo(deps, atascados)))
        por_etapa = {}
        for n in orden:
            por_etapa.setdefault(etapa[n], []).append(n)
        etapas = "  ".join(f"{k}) {', '.join(v)}" for k, v in sorted(por_etapa.items()))
        return f"Orden válido: {' → '.join(orden)}\nEn paralelo, por etapas: {etapas}"
    return {"orden dependencias": ordenar, "orden de dependencias": ordenar}
''',
"prueba": [("orden dependencias", "app>red app>ui ui>motor red>motor", "motor → red → ui → app"),
           ("orden dependencias", "app>red app>ui ui>motor red>motor", "2) red, ui"),
           ("orden dependencias", "a>b b>c c>a", "ciclo de dependencias")],
},
{
"id": "tarjan_scc",
"titulo": "Tarjan: componentes fuertemente conexas de un grafo dirigido",
"area": "Grafos",
"temas": "tarjan kosaraju componentes fuertemente conexas scc grafo dirigido ciclos condensar enlaces web "
         "dependencias circulares alcanzar",
"idea": "Un recorrido en profundidad da a cada nodo un número de llegada y calcula «bajo»: el número más pequeño "
        "alcanzable desde su subárbol sin salir de la pila. Si bajo == su número, ese nodo es la raíz de una "
        "componente: se sacan de la pila hasta él. Al juntar cada componente en un punto queda un grafo sin ciclos.",
"complejidad": "O(V + E), una sola pasada",
"codigo": r'''
def leer(texto):
    g = {}
    for t in texto.replace(",", " ").split():
        a, _, b = t.partition(">")
        if not a or not b:
            raise ValueError(f"No entiendo «{t}»: escribe a>b (flecha de a hacia b)")
        g.setdefault(a, []).append(b)
        g.setdefault(b, [])
    return g


def tarjan(g):
    numero, bajo, en_pila, pila, comps = {}, {}, set(), [], []
    contador = [0]

    def visitar(v):
        numero[v] = bajo[v] = contador[0]
        contador[0] += 1
        pila.append(v)
        en_pila.add(v)
        for w in g[v]:
            if w not in numero:
                visitar(w)
                bajo[v] = min(bajo[v], bajo[w])
            elif w in en_pila:
                bajo[v] = min(bajo[v], numero[w])
        if bajo[v] == numero[v]:                     # v es la raíz de una componente
            comp = []
            while True:
                w = pila.pop()
                en_pila.discard(w)
                comp.append(w)
                if w == v:
                    break
            comps.append(sorted(comp))
    for v in sorted(g):
        if v not in numero:
            visitar(v)
    return sorted(comps)


def registrar():
    def componentes(texto):
        # «componentes fuertes a>b b>c c>a c>d d>e e>d»
        g = leer(texto)
        if not g or len(g) > 400:
            raise ValueError("Uso: componentes fuertes a>b b>c c>a c>d (hasta 400 nodos)")
        comps = tarjan(g)
        nombre = {v: "{" + ", ".join(c) + "}" for c in comps for v in c}
        enlaces = sorted({(nombre[a], nombre[b]) for a in g for b in g[a] if nombre[a] != nombre[b]})
        lineas = [f"{len(comps)} componentes fuertemente conexas (dentro de cada una se llega de cualquiera a cualquiera):"]
        lineas += ["- " + nombre[c[0]] for c in comps]
        if enlaces:
            lineas.append("Grafo condensado (ya sin ciclos): " + "; ".join(f"{a} → {b}" for a, b in enlaces))
        return "\n".join(lineas)
    return {"componentes fuertes": componentes}
''',
"prueba": [("componentes fuertes", "a>b b>c c>a c>d d>e e>d", "2 componentes"),
           ("componentes fuertes", "a>b b>c c>a c>d d>e e>d", "{a, b, c} → {d, e}")],
},
{
"id": "flujo_maximo",
"titulo": "Flujo máximo (Edmonds-Karp) y corte mínimo: el cuello de botella de una red",
"area": "Grafos",
"temas": "flujo maximo edmonds karp ford fulkerson corte minimo capacidad red tuberias trafico cuello botella "
         "camino aumentante residual",
"idea": "Mientras exista un camino de la fuente al sumidero con capacidad sobrante (buscado con BFS en la red "
        "RESIDUAL), se manda por él tanto como permita su tramo más estrecho, y se anota capacidad en sentido "
        "contrario para poder deshacer. Al acabar, lo alcanzable desde la fuente marca el corte mínimo: las "
        "conexiones que limitan de verdad (teorema flujo máximo = corte mínimo).",
"complejidad": "O(V·E²) con BFS (Edmonds-Karp)",
"codigo": r'''
from collections import deque


def leer(texto):
    cap = {}
    for t in texto.replace(",", " ").split():
        sep = ">" if ">" in t else "-"
        ab, _, c = t.partition(":")
        a, _, b = ab.partition(sep)
        if not a or not b or not c:
            raise ValueError(f"No entiendo «{t}»: escribe s>a:10 (de s a a con capacidad 10)")
        cap[(a, b)] = cap.get((a, b), 0) + float(c)
        if sep == "-":
            cap[(b, a)] = cap.get((b, a), 0) + float(c)
    return cap


def edmonds_karp(cap, s, t):
    res = {}                                         # capacidad residual
    for (a, b), c in cap.items():
        res.setdefault(a, {})
        res.setdefault(b, {})
        res[a][b] = res[a].get(b, 0) + c
        res[b].setdefault(a, 0)
    flujo = 0
    while True:
        previo, cola = {s: None}, deque([s])
        while cola and t not in previo:              # BFS: el camino aumentante con menos tramos
            u = cola.popleft()
            for v, c in res[u].items():
                if c > 0 and v not in previo:
                    previo[v] = u
                    cola.append(v)
        if t not in previo:
            break
        cuello, v = float("inf"), t
        while previo[v] is not None:
            cuello = min(cuello, res[previo[v]][v])
            v = previo[v]
        v = t
        while previo[v] is not None:
            u = previo[v]
            res[u][v] -= cuello
            res[v][u] += cuello                      # se podrá «devolver» flujo si conviene
            v = u
        flujo += cuello
    alcanzables, cola = {s}, deque([s])
    while cola:
        u = cola.popleft()
        for v, c in res[u].items():
            if c > 0 and v not in alcanzables:
                alcanzables.add(v)
                cola.append(v)
    corte = sorted((a, b) for (a, b) in cap if a in alcanzables and b not in alcanzables)
    return flujo, corte


def registrar():
    def flujo(texto):
        # «flujo máximo s>a:10 s>b:5 a>b:15 a>t:10 b>t:10 | s t»
        red, _, ext = texto.partition("|")
        if len(ext.split()) != 2:
            raise ValueError("Uso: flujo máximo s>a:10 a>t:5 | s t")
        s, t = ext.split()
        cap = leer(red)
        nodos = {n for par in cap for n in par}
        if s not in nodos or t not in nodos:
            raise ValueError(f"{s} o {t} no está en la red.")
        f, corte = edmonds_karp(cap, s, t)
        texto_corte = ", ".join(f"{a}>{b} ({cap[(a, b)]:g})" for a, b in corte)
        return (f"Flujo máximo de {s} a {t}: {f:g}\n"
                f"Corte mínimo (lo que de verdad limita; si lo amplías, sube el flujo): {texto_corte}")
    return {"flujo máximo": flujo, "flujo maximo": flujo}
''',
"prueba": [("flujo máximo", "s>a:10 s>b:5 a>b:15 a>t:10 b>t:10 | s t", "Flujo máximo de s a t: 15"),
           ("flujo máximo", "s>a:10 s>b:5 a>b:15 a>t:4 b>t:20 | s t", "Flujo máximo de s a t: 15")],
},
{
"id": "emparejamiento",
"titulo": "Emparejamiento bipartito (Kuhn): asignar tareas a personas",
"area": "Grafos",
"temas": "emparejamiento bipartito asignar asignacion tareas personas turnos parejas kuhn hopcroft karp "
         "camino aumentante matching trabajos",
"idea": "Cada persona intenta quedarse con una de sus tareas; si está cogida, se le pide al que la tiene que "
        "pruebe con OTRA de las suyas (camino aumentante). Si esa cadena de cambios acaba en una tarea libre, todos "
        "se recolocan y hay una pareja más. Con pesos (costes) se usaría el algoritmo húngaro.",
"complejidad": "O(V·E) (Kuhn); Hopcroft-Karp lo baja a O(E·√V)",
"codigo": r'''
def leer(texto):
    prefs = {}
    for t in texto.split():
        p, _, ts = t.partition(":")
        if not p or not ts:
            raise ValueError(f"No entiendo «{t}»: escribe ana:web,app (ana puede hacer web o app)")
        prefs[p] = [x for x in ts.split(",") if x]
    return prefs


def emparejar(prefs):
    dueno = {}                                       # tarea -> persona

    def intentar(persona, vistas):
        for tarea in prefs[persona]:
            if tarea in vistas:
                continue
            vistas.add(tarea)
            if tarea not in dueno or intentar(dueno[tarea], vistas):   # libre, o su dueño puede cambiarse
                dueno[tarea] = persona
                return True
        return False
    for p in prefs:
        intentar(p, set())
    return {p: t for t, p in dueno.items()}


def registrar():
    def asigna(texto):
        # «asigna ana:web,app luis:web eva:app,datos»
        prefs = leer(texto)
        if not prefs or len(prefs) > 300:
            raise ValueError("Uso: asigna ana:web,app luis:web eva:app,datos")
        par = emparejar(prefs)
        lineas = [f"Asignadas {len(par)} de {len(prefs)} personas: " +
                  ", ".join(f"{p} → {par[p]}" for p in sorted(par))]
        sin = sorted(set(prefs) - set(par))
        if sin:
            lineas.append("Sin tarea posible (no hay forma de recolocar a los demás): " + ", ".join(sin))
        return "\n".join(lineas)
    return {"asigna": asigna}
''',
"prueba": [("asigna", "ana:web,app luis:web eva:app,datos", "Asignadas 3 de 3"),
           ("asigna", "ana:web luis:web", "Sin tarea posible")],
},
# =====================================================================================================================
#  CADENAS Y TEXTO
# =====================================================================================================================
{
"id": "kmp",
"titulo": "KMP: buscar un patrón en un texto sin volver atrás",
"area": "Cadenas y texto",
"temas": "kmp knuth morris pratt buscar patron texto subcadena coincidencias tabla fallos prefijo sufijo "
         "busqueda cadenas ocurrencias",
"idea": "La tabla de fallos dice, para cada prefijo del patrón, cuánto de él vuelve a servir si el siguiente "
        "carácter no encaja (el mayor prefijo que también es sufijo). Así nunca se retrocede en el texto: cada "
        "carácter se mira una vez. La búsqueda ingenua puede repetir trabajo y llegar a O(n·m).",
"complejidad": "O(n + m): n el texto y m el patrón",
"codigo": r'''
def tabla_fallos(p):
    """f[i] = largo del mayor prefijo de p que también es sufijo de p[:i+1] (sin ser todo él)."""
    f, k = [0] * len(p), 0
    for i in range(1, len(p)):
        while k and p[i] != p[k]:
            k = f[k - 1]
        if p[i] == p[k]:
            k += 1
        f[i] = k
    return f


def kmp(texto, p):
    f, k, res = tabla_fallos(p), 0, []
    for i, c in enumerate(texto):
        while k and c != p[k]:
            k = f[k - 1]                             # reaprovecha lo ya casado en vez de retroceder en el texto
        if c == p[k]:
            k += 1
        if k == len(p):
            res.append(i - k + 1)
            k = f[k - 1]                             # permite coincidencias que se solapan
    return res


def registrar():
    def busca(texto):
        # «busca patron abab | abababab»
        p, _, t = texto.partition("|")
        p, t = p.strip(), t.strip()
        if not p or not t:
            raise ValueError("Uso: busca patron abab | abababab")
        pos = kmp(t, p)
        tabla = ", ".join(map(str, tabla_fallos(p)))
        if not pos:
            return f"«{p}» no aparece. (Tabla de fallos de KMP: [{tabla}])"
        return (f"«{p}» aparece {len(pos)} veces, en las posiciones {', '.join(map(str, pos))} (desde 0). "
                f"Tabla de fallos: [{tabla}]")
    return {"busca patron": busca, "busca patrón": busca}
''',
"prueba": [("busca patron", "abab | abababab", "posiciones 0, 2, 4"), ("busca patron", "aab | aaaab", "posiciones 2")],
},
{
"id": "aho_corasick",
"titulo": "Aho-Corasick: buscar MUCHAS palabras a la vez en una pasada",
"area": "Cadenas y texto",
"temas": "aho corasick buscar varias muchas palabras diccionario filtro palabrotas spam automata trie enlaces "
         "fallo antivirus firmas coincidencias",
"idea": "Las palabras forman un trie y cada nodo recibe un enlace de FALLO: a dónde saltar si la siguiente letra no "
        "encaja (el sufijo más largo que también está en el trie), calculado por capas con una cola. El texto se "
        "recorre una sola vez, como una máquina de estados, y en cada estado se sabe qué palabras terminan ahí.",
"complejidad": "construir O(suma de largos); buscar O(n + número de coincidencias), da igual cuántas palabras",
"codigo": r'''
from collections import deque


def construir(palabras):
    hijos, fallo, salida = [{}], [0], [[]]
    for w in palabras:
        n = 0
        for c in w:
            if c not in hijos[n]:
                hijos[n][c] = len(hijos)
                hijos.append({})
                fallo.append(0)
                salida.append([])
            n = hijos[n][c]
        salida[n].append(w)
    cola = deque(hijos[0].values())                  # los hijos de la raíz fallan a la raíz
    while cola:
        n = cola.popleft()
        for c, h in hijos[n].items():
            f = fallo[n]
            while f and c not in hijos[f]:
                f = fallo[f]
            fallo[h] = hijos[f].get(c, 0) if hijos[f].get(c) != h else 0
            salida[h] = salida[h] + salida[fallo[h]]   # también terminan las palabras del estado de fallo
            cola.append(h)
    return hijos, fallo, salida


def buscar(texto, automata):
    hijos, fallo, salida = automata
    n, res = 0, []
    for i, c in enumerate(texto):
        while n and c not in hijos[n]:
            n = fallo[n]
        n = hijos[n].get(c, 0)
        for w in salida[n]:
            res.append((i - len(w) + 1, w))
    return sorted(res)


def registrar():
    def busca_palabras(texto):
        # «busca palabras he she his hers | ushers»
        ws, _, t = texto.lower().partition("|")
        palabras = sorted(set(ws.split()))
        if not palabras or not t.strip():
            raise ValueError("Uso: busca palabras he she his hers | ushers")
        hallado = buscar(t.strip(), construir(palabras))
        if not hallado:
            return "No aparece ninguna."
        return f"Encontradas {len(hallado)}: " + ", ".join(f"«{w}» en {i}" for i, w in hallado)
    return {"busca palabras": busca_palabras}
''',
"prueba": [("busca palabras", "he she his hers | ushers", "«she» en 1, «he» en 2, «hers» en 2")],
},
{
"id": "levenshtein",
"titulo": "Distancia de edición (Levenshtein) y corrector ortográfico",
"area": "Cadenas y texto",
"temas": "levenshtein distancia edicion corrector ortografico corregir parecidas faltas errata similitud palabras "
         "programacion dinamica fuzzy aproximada",
"idea": "d[i][j] = cambios mínimos para convertir los i primeros caracteres de a en los j primeros de b: el mínimo "
        "entre borrar (d[i-1][j]+1), insertar (d[i][j-1]+1) o cambiar/mantener (d[i-1][j-1] + 0 o 1). Recorriendo la "
        "tabla hacia atrás salen las operaciones. Un corrector propone las palabras conocidas a menor distancia.",
"complejidad": "O(n·m) tiempo; O(n·m) memoria si se quieren las operaciones (O(min(n, m)) si solo la distancia)",
"codigo": r'''
VOCABULARIO = ("programa algoritmo python kira memoria proceso variable funcion clase objeto lista diccionario "
               "compilador servidor cliente archivo carpeta pantalla teclado sistema red internet seguridad "
               "contraseña ordenador movil telefono musica video imagen texto palabra numero hola gracias").split()


def distancia(a, b):
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    ops, i, j = [], n, m
    while i or j:                                    # reconstruir: de la esquina hacia el origen
        if i and j and d[i][j] == d[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            if a[i - 1] != b[j - 1]:
                ops.append(f"cambia «{a[i - 1]}» por «{b[j - 1]}»")
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            ops.append(f"borra «{a[i - 1]}»")
            i -= 1
        else:
            ops.append(f"inserta «{b[j - 1]}»")
            j -= 1
    return d[n][m], ops[::-1]


def registrar():
    def dist(texto):
        # «distancia kitten | sitting»
        a, _, b = texto.partition("|")
        a, b = a.strip(), b.strip()
        if not a or not b or len(a) * len(b) > 400_000:
            raise ValueError("Uso: distancia gato | pato")
        d, ops = distancia(a, b)
        return f"Distancia de edición: {d}" + (f" ({', '.join(ops)})" if ops else " (son iguales)")

    def corrige(texto):
        w = texto.strip().lower()
        if not w:
            raise ValueError("Uso: corrige progama")
        mejores = sorted((distancia(w, v)[0], v) for v in VOCABULARIO)[:3]
        if mejores[0][0] == 0:
            return f"«{w}» está bien escrita."
        return f"¿Quisiste decir «{mejores[0][1]}»? Otras: " + ", ".join(f"{v} ({d})" for d, v in mejores[1:])
    return {"distancia": dist, "corrige": corrige}
''',
"prueba": [("distancia", "kitten | sitting", "Distancia de edición: 3"), ("corrige", "progama", "«programa»")],
},
{
"id": "diff_lcs",
"titulo": "Diferencias entre dos textos (diff) con la subsecuencia común más larga",
"area": "Cadenas y texto",
"temas": "diff diferencias comparar textos versiones git cambios lineas lcs subsecuencia comun mas larga parche "
         "control versiones",
"idea": "La subsecuencia común más larga (LCS) es lo que NO cambió. L[i][j] = LCS de a[i:] y b[j:]: si a[i] == b[j], "
        "1 + L[i+1][j+1]; si no, el mayor entre saltar uno u otro. Recorriendo la tabla se marca cada elemento como "
        "igual, borrado (-) o añadido (+), igual que hace git diff (que usa el algoritmo de Myers, más rápido).",
"complejidad": "O(n·m) tiempo y memoria (Myers: O((n + m)·D), D = número de cambios)",
"codigo": r'''
def diff(a, b):
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            L[i][j] = L[i + 1][j + 1] + 1 if a[i] == b[j] else max(L[i + 1][j], L[i][j + 1])
    i = j = 0
    res = []
    while i < n and j < m:
        if a[i] == b[j]:
            res.append("  " + a[i])
            i, j = i + 1, j + 1
        elif L[i + 1][j] >= L[i][j + 1]:
            res.append("- " + a[i])
            i += 1
        else:
            res.append("+ " + b[j])
            j += 1
    res += ["- " + x for x in a[i:]] + ["+ " + x for x in b[j:]]
    return L[0][0], res


def trozos(t):
    """Si hay «;» compara líneas; si no, palabras."""
    return [x.strip() for x in t.split(";") if x.strip()] if ";" in t else t.split()


def registrar():
    def diferencias(texto):
        # «diferencias uno dos tres cuatro | uno tres cuatro cinco»   (o líneas separadas por ;)
        a, _, b = texto.partition("|")
        a, b = trozos(a), trozos(b)
        if not a or not b or len(a) * len(b) > 250_000:
            raise ValueError("Uso: diferencias uno dos tres | uno tres cuatro")
        comun, lineas = diff(a, b)
        quitados = sum(1 for x in lineas if x.startswith("-"))
        puestos = sum(1 for x in lineas if x.startswith("+"))
        return "\n".join(lineas + [f"Iguales: {comun}; quitados: {quitados}; añadidos: {puestos}"])
    return {"diferencias": diferencias}
''',
"prueba": [("diferencias", "uno dos tres cuatro | uno tres cuatro cinco", "- dos"),
           ("diferencias", "uno dos tres cuatro | uno tres cuatro cinco", "+ cinco"),
           ("diferencias", "x = 1; y = 2; print(x) | x = 1; print(x)", "- y = 2")],
},
{
"id": "array_sufijos",
"titulo": "Array de sufijos y LCP: la repetición más larga y subcadenas distintas",
"area": "Cadenas y texto",
"temas": "array sufijos suffix lcp kasai repetido repeticion subcadena mas larga plagio adn genoma "
         "subcadenas distintas indice texto",
"idea": "Se ordenan todos los sufijos del texto (duplicando el prefijo comparado en cada ronda: 1, 2, 4… letras). "
        "El LCP dice cuánto comparten dos sufijos vecinos (algoritmo de Kasai). El mayor LCP es la subcadena que "
        "más se repite; n·(n+1)/2 − suma(LCP) cuenta las subcadenas distintas. Es la base de buscadores de ADN.",
"complejidad": "O(n log² n) construir con ordenación; LCP O(n)",
"codigo": r'''
def array_sufijos(s):
    n = len(s)
    rango = [ord(c) for c in s]
    sa, k = list(range(n)), 1
    while True:
        claves = [(rango[i], rango[i + k] if i + k < n else -1) for i in range(n)]
        sa.sort(key=lambda i: claves[i])
        nuevo = [0] * n
        for a, b in zip(sa, sa[1:]):
            nuevo[b] = nuevo[a] + (claves[a] != claves[b])
        rango = nuevo
        if rango[sa[-1]] == n - 1:                   # todos distintos: ya están ordenados
            return sa
        k *= 2


def lcp_kasai(s, sa):
    n = len(s)
    pos = [0] * n
    for i, p in enumerate(sa):
        pos[p] = i
    lcp, h = [0] * n, 0
    for i in range(n):                               # en orden de texto: h baja como mucho 1 cada vez
        if pos[i] > 0:
            j = sa[pos[i] - 1]
            while i + h < n and j + h < n and s[i + h] == s[j + h]:
                h += 1
            lcp[pos[i]] = h
            if h:
                h -= 1
        else:
            h = 0
    return lcp


def registrar():
    def repetido(texto):
        # «repetido banana»
        s = texto.strip()
        if not s or len(s) > 5000:
            raise ValueError("Uso: repetido banana (hasta 5000 letras)")
        sa = array_sufijos(s)
        lcp = lcp_kasai(s, sa)
        largo = max(lcp)
        distintas = len(s) * (len(s) + 1) // 2 - sum(lcp)
        if largo == 0:
            rep = "No se repite ningún trozo."
        else:
            i = lcp.index(largo)
            rep = f"Lo que más se repite: «{s[sa[i]:sa[i] + largo]}» ({largo} letras)."
        primeros = ", ".join(s[p:][:12] for p in sa[:6])
        return f"{rep} Hay {distintas} subcadenas distintas.\nSufijos ordenados: {primeros}…"
    return {"repetido": repetido}
''',
"prueba": [("repetido", "banana", "«ana»"), ("repetido", "banana", "15 subcadenas distintas")],
},
# =====================================================================================================================
#  PROGRAMACIÓN DINÁMICA
# =====================================================================================================================
{
"id": "mochila",
"titulo": "Problema de la mochila 0/1 (programación dinámica con reconstrucción)",
"area": "Programación dinámica",
"temas": "mochila knapsack programacion dinamica optimizar elegir objetos peso valor presupuesto capacidad "
         "seleccion inversion maletas",
"idea": "dp[i][c] = el mejor valor usando los i primeros objetos con capacidad c: o no se coge el objeto i "
        "(dp[i-1][c]) o se coge (dp[i-1][c-peso] + valor). Comparando filas de abajo arriba se sabe qué se cogió. "
        "Coger «lo que más vale por kilo» (voraz) puede fallar; la DP no.",
"complejidad": "O(n·C) pseudo-polinómico (C = capacidad); el problema general es NP-difícil",
"codigo": r'''
def mochila(capacidad, objetos):
    n = len(objetos)
    dp = [[0] * (capacidad + 1) for _ in range(n + 1)]
    for i, (_, peso, valor) in enumerate(objetos, 1):
        anterior, fila = dp[i - 1], dp[i]
        for c in range(capacidad + 1):
            fila[c] = anterior[c]
            if peso <= c and anterior[c - peso] + valor > fila[c]:
                fila[c] = anterior[c - peso] + valor
    elegidos, c = [], capacidad
    for i in range(n, 0, -1):                        # si la fila cambió, el objeto i se cogió
        if dp[i][c] != dp[i - 1][c]:
            nombre, peso, _ = objetos[i - 1]
            elegidos.append(nombre)
            c -= peso
    return dp[n][capacidad], elegidos[::-1]


def voraz(capacidad, objetos):
    total, usado = 0, 0
    for nombre, peso, valor in sorted(objetos, key=lambda o: -o[2] / o[1]):
        if usado + peso <= capacidad:
            usado += peso
            total += valor
    return total


def registrar():
    def mochila_orden(texto):
        # «mochila 10 | agua:3:10 comida:4:40 tienda:5:30 linterna:1:15»   (nombre:peso:valor)
        cap_txt, _, resto = texto.partition("|")
        objetos = []
        for t in resto.split():
            partes = t.split(":")
            if len(partes) != 3 or not partes[1].isdigit() or int(partes[1]) < 1:
                raise ValueError(f"No entiendo «{t}»: escribe nombre:peso:valor con el peso entero (agua:3:10)")
            objetos.append((partes[0], int(partes[1]), float(partes[2])))
        if not cap_txt.strip().isdigit() or not objetos:
            raise ValueError("Uso: mochila 10 | agua:3:10 comida:4:40 tienda:5:30")
        cap = int(cap_txt)
        if cap * len(objetos) > 2_000_000:
            raise ValueError("Demasiado grande para el móvil: baja la capacidad o el número de objetos.")
        valor, elegidos = mochila(cap, objetos)
        peso = sum(p for n, p, _ in objetos if n in elegidos)
        return (f"Lo mejor: {', '.join(elegidos) or 'nada'} -> valor {valor:g} (peso {peso} de {cap}).\n"
                f"Eligiendo «lo que más vale por kilo» (voraz) saldría {voraz(cap, objetos):g}.")
    return {"mochila": mochila_orden}
''',
"prueba": [("mochila", "10 | agua:3:10 comida:4:40 tienda:5:30 linterna:1:15", "valor 85"),
           ("mochila", "50 | a:10:60 b:20:100 c:30:120", "b, c -> valor 220"),
           ("mochila", "50 | a:10:60 b:20:100 c:30:120", "(voraz) saldría 160")],
},
{
"id": "subsecuencia_creciente",
"titulo": "Subsecuencia creciente más larga en O(n log n) (paciencia)",
"area": "Programación dinámica",
"temas": "subsecuencia creciente larga lis paciencia busqueda binaria bisect tendencia progreso racha ordenada "
         "programacion dinamica",
"idea": "colas[k] guarda el MENOR final posible de una subsecuencia creciente de largo k+1. Cada número sustituye "
        "al primer final que no sea menor que él (búsqueda binaria) o alarga la mejor. Guardando de qué número "
        "venía cada uno se reconstruye la subsecuencia.",
"complejidad": "O(n log n) (la DP directa es O(n²))",
"codigo": r'''
import bisect


def lis(datos):
    colas, indices, previo = [], [], [None] * len(datos)
    for i, x in enumerate(datos):
        k = bisect.bisect_left(colas, x)
        if k == len(colas):
            colas.append(x)
            indices.append(i)
        else:
            colas[k] = x                             # mismo largo, pero con un final más pequeño
            indices[k] = i
        previo[i] = indices[k - 1] if k else None
    res, i = [], indices[-1] if indices else None
    while i is not None:
        res.append(datos[i])
        i = previo[i]
    return res[::-1]


def registrar():
    def creciente(texto):
        # «subsecuencia creciente 10 9 2 5 3 7 101 18»
        try:
            datos = [float(x) if "." in x else int(x) for x in texto.replace(",", " ").split()]
        except ValueError:
            raise ValueError("Uso: subsecuencia creciente 10 9 2 5 3 7 101 18")
        if not datos:
            raise ValueError("Uso: subsecuencia creciente 10 9 2 5 3 7 101 18")
        r = lis(datos)
        return f"Longitud {len(r)}: " + ", ".join(f"{x:g}" if isinstance(x, float) else str(x) for x in r)
    return {"subsecuencia creciente": creciente}
''',
"prueba": [("subsecuencia creciente", "10 9 2 5 3 7 101 18", "Longitud 4: 2, 3, 7, 18")],
},
{
"id": "cambio_monedas",
"titulo": "Cambio de monedas: óptimo (programación dinámica) frente a voraz",
"area": "Programación dinámica",
"temas": "cambio monedas billetes pagar devolver programacion dinamica voraz greedy minimo formas combinaciones "
         "dinero contar",
"idea": "mejor[c] = 1 + min(mejor[c - m]) para cada moneda m ≤ c. Coger siempre la moneda más grande (voraz) "
        "funciona con el euro, pero NO con monedas de 1, 3 y 4 para pagar 6 (4+1+1 frente a 3+3). Contar de "
        "cuántas formas se puede pagar es otra DP: formas[c] += formas[c - m], moneda a moneda.",
"complejidad": "O(cantidad · número de monedas)",
"codigo": r'''
def minimo(cantidad, monedas):
    inf = float("inf")
    mejor, ultima = [0] + [inf] * cantidad, [0] * (cantidad + 1)
    for c in range(1, cantidad + 1):
        for m in monedas:
            if m <= c and mejor[c - m] + 1 < mejor[c]:
                mejor[c], ultima[c] = mejor[c - m] + 1, m
    if mejor[cantidad] == inf:
        return None
    res, c = [], cantidad
    while c:
        res.append(ultima[c])
        c -= ultima[c]
    return sorted(res, reverse=True)


def voraz(cantidad, monedas):
    res = []
    for m in sorted(monedas, reverse=True):
        while cantidad >= m:
            cantidad -= m
            res.append(m)
    return res if cantidad == 0 else None


def formas(cantidad, monedas):
    f = [1] + [0] * cantidad
    for m in monedas:                                # moneda a moneda: cuenta combinaciones, no órdenes
        for c in range(m, cantidad + 1):
            f[c] += f[c - m]
    return f[cantidad]


def registrar():
    def cambio(texto):
        # «cambio 6 con 1 3 4»
        cant, _, mon = texto.partition("con")
        try:
            cantidad, monedas = int(cant), sorted({int(x) for x in mon.replace(",", " ").split()})
        except ValueError:
            raise ValueError("Uso: cambio 6 con 1 3 4")
        if not monedas or monedas[0] < 1 or cantidad < 1 or cantidad > 200_000:
            raise ValueError("Uso: cambio 6 con 1 3 4")
        opt, vor = minimo(cantidad, monedas), voraz(cantidad, monedas)
        if opt is None:
            return f"No se puede pagar {cantidad} con {monedas}."
        lineas = [f"Óptimo (programación dinámica): {len(opt)} monedas: {' + '.join(map(str, opt))}"]
        if vor is None:
            lineas.append("Voraz (la más grande primero): ¡se atasca y no llega!")
        else:
            lineas.append(f"Voraz (la más grande primero): {len(vor)} monedas: {' + '.join(map(str, vor))}")
        lineas.append(f"Formas distintas de pagarlo: {formas(cantidad, monedas)}")
        return "\n".join(lineas)
    return {"cambio": cambio}
''',
"prueba": [("cambio", "6 con 1 3 4", "2 monedas: 3 + 3"), ("cambio", "6 con 1 3 4", "Voraz (la más grande primero): 3 monedas"),
           ("cambio", "6 con 1 3 4", "Formas distintas de pagarlo: 4")],
},
{
"id": "viajante_exacto",
"titulo": "Problema del viajante exacto (Held-Karp, programación dinámica con máscaras de bits)",
"area": "Programación dinámica",
"temas": "viajante tsp ruta reparto ciudades recorrido held karp mascara bits bitmask programacion dinamica "
         "exacto optimo vecino cercano logistica",
"idea": "coste[S][j] = el camino más corto que sale de la ciudad 0, visita exactamente el conjunto S y acaba en j. "
        "S es un número cuyos bits dicen qué ciudades están dentro. Se amplía S de una en una ciudad. Es exacto pero "
        "exponencial: hasta ~12 ciudades; para más, heurísticas (vecino más cercano, 2-opt, recocido simulado).",
"complejidad": "O(n²·2ⁿ) tiempo y O(n·2ⁿ) memoria (probarlo todo sería O(n!))",
"codigo": r'''
import math
import random


def leer_ciudades(texto):
    t = texto.strip()
    if t.isdigit():
        rnd = random.Random(int(t))                 # ciudades al azar, pero siempre las mismas para ese número
        pts = [(rnd.randint(0, 100), rnd.randint(0, 100)) for _ in range(int(t))]
    else:
        pts = []
        for par in t.split():
            x, _, y = par.partition(",")
            pts.append((float(x), float(y)))
    if not 3 <= len(pts) <= 11:
        raise ValueError("Entre 3 y 11 ciudades: «viajante exacto 8» o «viajante exacto 0,0 3,4 6,0»")
    return pts


def held_karp(d):
    n, inf = len(d), float("inf")
    coste = [[inf] * n for _ in range(1 << n)]
    previo = [[-1] * n for _ in range(1 << n)]
    coste[1][0] = 0.0
    for S in range(1, 1 << n, 2):                    # solo conjuntos que contienen la ciudad 0
        for j in range(n):
            c = coste[S][j]
            if c == inf:
                continue
            for k in range(1, n):
                if S >> k & 1:
                    continue
                T = S | 1 << k
                if c + d[j][k] < coste[T][k]:
                    coste[T][k], previo[T][k] = c + d[j][k], j
    todo = (1 << n) - 1
    mejor, j = min((coste[todo][j] + d[j][0], j) for j in range(1, n))
    ruta, S = [], todo
    while j != -1:
        ruta.append(j)
        j, S = previo[S][j], S & ~(1 << j)
    return mejor, ruta[::-1] + [0]


def vecino_mas_cercano(d):
    ruta, libres = [0], set(range(1, len(d)))
    while libres:
        sig = min(libres, key=lambda k: d[ruta[-1]][k])
        ruta.append(sig)
        libres.discard(sig)
    return sum(d[a][b] for a, b in zip(ruta, ruta[1:] + [0]))


def registrar():
    def viajante(texto):
        pts = leer_ciudades(texto)
        d = [[math.dist(a, b) for b in pts] for a in pts]
        largo, ruta = held_karp(d)
        vc = vecino_mas_cercano(d)
        return (f"Ruta óptima (Held-Karp): {' → '.join(map(str, ruta))}, longitud {largo:.4g}\n"
                f"Vecino más cercano: {vc:.4g} ({100 * (vc - largo) / largo:.1f} % más larga)")
    return {"viajante exacto": viajante}
''',
"prueba": [("viajante exacto", "0,0 0,1 1,1 1,0", "longitud 4"), ("viajante exacto", "9", "Ruta óptima (Held-Karp): 0 →")],
},
# =====================================================================================================================
#  MATEMÁTICAS, NÚMEROS Y CRIPTOGRAFÍA
# =====================================================================================================================
{
"id": "criba",
"titulo": "Criba de Eratóstenes: todos los primos hasta N",
"area": "Matemáticas y números",
"temas": "criba eratostenes primos numeros primos contar lista tachar multiplos teoria numeros matematicas",
"idea": "Se apunta que todos son primos y, para cada primo p hasta √N, se tachan sus múltiplos empezando en p² (los "
        "menores ya los tachó un primo más pequeño). Con un bytearray y asignación por tramos, Python tacha millones "
        "de casillas de golpe.",
"complejidad": "O(N log log N) tiempo; O(N) bytes de memoria",
"codigo": r'''
def criba(n):
    es = bytearray([1]) * (n + 1)
    es[0] = es[1] = 0
    p = 2
    while p * p <= n:
        if es[p]:
            es[p * p::p] = bytes(len(range(p * p, n + 1, p)))    # tacha todos los múltiplos de una vez
        p += 1
    return es


def registrar():
    def primos(texto):
        # «primos hasta 30»
        t = texto.strip().replace(".", "")
        if not t.isdigit() or not 2 <= int(t) <= 5_000_000:
            raise ValueError("Uso: primos hasta 30 (entre 2 y 5.000.000)")
        n = int(t)
        es = criba(n)
        lista = [i for i in range(n + 1) if es[i]]
        if len(lista) <= 30:
            muestra = ", ".join(map(str, lista))
        else:
            muestra = ", ".join(map(str, lista[:10])) + ", … , " + ", ".join(map(str, lista[-3:]))
        gemelos = sum(1 for a, b in zip(lista, lista[1:]) if b - a == 2)
        return f"Hay {len(lista)} primos hasta {n}: {muestra}\nParejas de primos gemelos (p, p+2): {gemelos}"
    return {"primos hasta": primos}
''',
"prueba": [("primos hasta", "30", "Hay 10 primos hasta 30"), ("primos hasta", "1000000", "78498 primos")],
},
{
"id": "primos_factores",
"titulo": "Miller-Rabin y rho de Pollard: ¿es primo? y factorizar números enormes",
"area": "Matemáticas y números",
"temas": "primo primalidad miller rabin pollard rho factorizar factores descomponer numero grande teoria numeros "
         "criptografia carmichael",
"idea": "Miller-Rabin escribe n-1 = d·2^s y comprueba con varias bases a si a^d da 1 o -1 en algún cuadrado; con las "
        "12 primeras bases primas es EXACTO para n < 3·10²⁴. La rho de Pollard busca un factor con la sucesión "
        "x → x²+c (mod n): por la paradoja del cumpleaños choca módulo un factor p en unos √p pasos y el mcd lo revela.",
"complejidad": "Miller-Rabin O(k·log³ n); Pollard rho ~O(n^¼) por factor",
"codigo": r'''
import math
import random

BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def es_primo(n):
    if n < 2:
        return False
    for p in BASES:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in BASES:                                  # con estas bases es exacto para n < 3,3·10^24
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False                             # a es un «testigo»: n es compuesto seguro
    return True


def rho(n, rnd, limite=400_000):
    if n % 2 == 0:
        return 2
    pasos = 0
    while True:
        c, x = rnd.randrange(1, n), rnd.randrange(2, n)
        y, d = x, 1
        while d == 1:
            x = (x * x + c) % n                      # la tortuga avanza 1
            y = (y * y + c) % n
            y = (y * y + c) % n                      # la liebre avanza 2
            d = math.gcd(abs(x - y), n)
            pasos += 1
            if pasos > limite:
                raise ValueError("Ese número tiene factores demasiado grandes para el móvil.")
        if d != n:
            return d


def factorizar(n, rnd):
    factores = []
    for p in range(2, 1000):                         # los factores pequeños, por división
        while n % p == 0:
            factores.append(p)
            n //= p
    pila = [n] if n > 1 else []
    while pila:
        m = pila.pop()
        if es_primo(m):
            factores.append(m)
        else:
            d = rho(m, rnd)
            pila += [d, m // d]
    return sorted(factores)


def leer(texto):
    t = texto.strip().replace(".", "").replace(" ", "")
    if not t.isdigit() or len(t) > 30:
        raise ValueError("Escribe un número entero positivo (hasta 30 cifras).")
    return int(t)


def registrar():
    def factoriza(texto):
        n = leer(texto)
        if n < 2:
            return f"{n} no tiene factores primos."
        f = factorizar(n, random.Random(n))
        return f"{n} = " + " × ".join(map(str, f))

    def primo(texto):
        n = leer(texto)
        if es_primo(n):
            return f"{n} es primo (Miller-Rabin determinista)."
        hay_testigo = any(math.gcd(a, n) == 1 and pow(a, n - 1, n) != 1 for a in BASES)
        nota = "" if n < 4 or hay_testigo else " (¡engaña a la prueba de Fermat! Es un número de Carmichael)"
        return f"{n} no es primo{nota}."
    return {"factoriza": factoriza, "es primo": primo}
''',
"prueba": [("factoriza", "600851475143", "600851475143 = 71 × 839 × 1471 × 6857"),
           ("factoriza", "1000000016000000063", "1000000007 × 1000000009"),
           ("es primo", "1000000007", "es primo"), ("es primo", "561", "Carmichael")],
},
{
"id": "rsa_didactico",
"titulo": "RSA didáctico: claves, cifrar, descifrar y firmar (para APRENDER, no para proteger)",
"area": "Matemáticas y números",
"temas": "rsa cifrado clave publica privada asimetrico firma digital euclides extendido inverso modular "
         "exponenciacion criptografia aprender",
"idea": "Se eligen dos primos p y q; n = p·q es público y φ = (p-1)(q-1) secreto. e = 65537 y d es su inverso módulo "
        "φ (algoritmo de Euclides extendido). Cifrar: c = m^e mod n; descifrar: m = c^d mod n. Firmar es al revés: "
        "con d se firma el resumen (hash) y con e cualquiera lo comprueba. OJO: aquí sin relleno y con claves "
        "diminutas; para datos reales se usan librerías probadas, claves de 2048+ bits y relleno OAEP/PSS.",
"complejidad": "cifrar y descifrar O(log e) multiplicaciones modulares (exponenciación rápida)",
"codigo": r'''
import hashlib
import math
import random


def es_primo(n):
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def euclides_ext(a, b):
    """(g, x, y) con a·x + b·y = g = mcd(a, b)."""
    x0, x1, y0, y1 = 1, 0, 0, 1
    while b:
        q = a // b
        a, b = b, a - q * b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    return a, x0, y0


def generar_claves(rnd, bits=32, e=65537):
    while True:
        p = q = 0
        while not es_primo(p):
            p = rnd.getrandbits(bits) | 1 << (bits - 1) | 1
        while not es_primo(q) or q == p:
            q = rnd.getrandbits(bits) | 1 << (bits - 1) | 1
        phi = (p - 1) * (q - 1)
        if math.gcd(e, phi) == 1:
            d = euclides_ext(e, phi)[1] % phi        # inverso de e módulo φ
            return p, q, p * q, e, d


def registrar():
    def rsa(texto):
        mensaje = texto.strip()
        if not mensaje or len(mensaje) > 200:
            raise ValueError("Uso: rsa hola kira (un mensaje corto)")
        p, q, n, e, d = generar_claves(random.Random(2026))
        tam = (n.bit_length() - 1) // 8                # bytes por bloque: cada bloque debe ser menor que n
        datos = mensaje.encode("utf-8")
        bloques = [int.from_bytes(datos[i:i + tam], "big") for i in range(0, len(datos), tam)]
        cifrado = [pow(m, e, n) for m in bloques]
        partes = [pow(c, d, n) for c in cifrado]
        ultimo = len(datos) - tam * (len(bloques) - 1)
        recuperado = b"".join(m.to_bytes(tam if i < len(partes) - 1 else ultimo, "big") for i, m in enumerate(partes))
        h = int.from_bytes(hashlib.sha256(datos).digest(), "big") % n
        firma = pow(h, d, n)
        valida = pow(firma, e, n) == h
        return (f"Clave pública (n, e) = ({n}, {e}); privada d = {d} (p = {p}, q = {q})\n"
                f"Cifrado: {cifrado}\nDescifrado: {recuperado.decode('utf-8')}\n"
                f"Firma del resumen SHA-256: {firma} -> {'firma válida' if valida else 'firma NO válida'}\n"
                "Solo para aprender: claves de 64 bits se rompen en segundos y sin relleno RSA no es seguro.")
    return {"rsa": rsa}
''',
"prueba": [("rsa", "hola kira", "Descifrado: hola kira"), ("rsa", "hola kira", "firma válida"),
           ("rsa", "ñandú y café ☕", "Descifrado: ñandú y café ☕")],
},
{
"id": "fft",
"titulo": "Transformada rápida de Fourier (FFT): multiplicar polinomios y números enormes",
"area": "Matemáticas y números",
"temas": "fft fourier transformada rapida cooley tukey convolucion polinomios multiplicar numeros grandes senal "
         "audio frecuencias espectro",
"idea": "Multiplicar polinomios es una convolución: O(n²) a mano. La FFT los pasa a «valores en las raíces de la "
        "unidad» en O(n log n) partiendo en pares e impares (Cooley-Tukey); ahí multiplicar es punto a punto, y la "
        "FFT inversa vuelve a coeficientes. Un número es un polinomio en base 10 (luego se arrastran las llevadas). "
        "La misma FFT analiza las frecuencias de un audio.",
"complejidad": "O(n log n) frente a O(n²) de la multiplicación escolar",
"codigo": r'''
import cmath


def fft(a, inversa=False):
    n = len(a)
    if n == 1:
        return list(a)
    pares, impares = fft(a[0::2], inversa), fft(a[1::2], inversa)
    signo = 1 if inversa else -1
    res = [0j] * n
    for k in range(n // 2):
        w = cmath.exp(signo * 2j * cmath.pi * k / n) * impares[k]
        res[k] = pares[k] + w
        res[k + n // 2] = pares[k] - w
    return res


def multiplicar_polinomios(p, q):
    largo = len(p) + len(q) - 1
    n = 1
    while n < largo:
        n *= 2
    fp = fft([complex(x) for x in p] + [0j] * (n - len(p)))
    fq = fft([complex(x) for x in q] + [0j] * (n - len(q)))
    r = fft([a * b for a, b in zip(fp, fq)], inversa=True)
    return [round((x / n).real) for x in r[:largo]]


def multiplicar_numeros(a, b):
    coef = multiplicar_polinomios([int(c) for c in reversed(a)], [int(c) for c in reversed(b)])
    digitos, llevada = [], 0
    for c in coef:
        llevada += c
        digitos.append(llevada % 10)
        llevada //= 10
    while llevada:
        digitos.append(llevada % 10)
        llevada //= 10
    return "".join(map(str, reversed(digitos))).lstrip("0") or "0"


def registrar():
    def numeros(texto):
        # «multiplica grande 12345678901234567890 98765432109876543210»
        partes = texto.replace(",", "").split()
        if len(partes) != 2 or not all(p.lstrip("-").isdigit() for p in partes) or max(map(len, partes)) > 2000:
            raise ValueError("Uso: multiplica grande 123456789 987654321 (hasta 2000 cifras cada uno)")
        signo = "-" if (partes[0][0] == "-") != (partes[1][0] == "-") else ""
        r = multiplicar_numeros(partes[0].lstrip("-"), partes[1].lstrip("-"))
        r = signo + r if r != "0" else r
        exacto = str(int(partes[0]) * int(partes[1])) == r
        return f"{r}\n(Con FFT. Comprobado con la multiplicación exacta de Python: {'correcto' if exacto else 'NO coincide'})"

    def polinomios(texto):
        # «multiplica polinomios 1 2 3 | 4 5»  = (1 + 2x + 3x²)(4 + 5x), coeficientes enteros de menor a mayor grado
        a, _, b = texto.partition("|")
        try:
            p, q = [int(x) for x in a.split()], [int(x) for x in b.split()]
        except ValueError:
            raise ValueError("Uso: multiplica polinomios 1 2 3 | 4 5 (coeficientes enteros)")
        if not p or not q:
            raise ValueError("Uso: multiplica polinomios 1 2 3 | 4 5")
        r = multiplicar_polinomios(p, q)
        termino = ["" if i == 0 else ("x" if i == 1 else f"x^{i}") for i in range(len(r))]
        return "Coeficientes: " + ", ".join(map(str, r)) + "\n= " + " + ".join(
            f"{c}{t}" for c, t in zip(r, termino) if c)
    return {"multiplica grande": numeros, "multiplica polinomios": polinomios}
''',
"prueba": [("multiplica grande", "12345678901234567890 98765432109876543210",
            "1219326311370217952237463801111263526900\n(Con FFT. Comprobado con la multiplicación exacta de Python: correcto"),
           ("multiplica polinomios", "1 2 3 | 4 5", "Coeficientes: 4, 13, 22, 15")],
},
{
"id": "potencia_rapida",
"titulo": "Exponenciación rápida y matrices: Fibonacci gigante en O(log n)",
"area": "Matemáticas y números",
"temas": "exponenciacion rapida potencia modular matriz matrices fibonacci recurrencia cuadrados logaritmico "
         "pow binario algebra lineal",
"idea": "a^n se calcula elevando al cuadrado y mirando los bits de n: a^13 = a^8·a^4·a¹, unas log₂ n "
        "multiplicaciones en vez de n. Funciona con matrices: [[1,1],[1,0]]^n contiene F(n), así que cualquier "
        "recurrencia lineal se salta millones de pasos. Con «mod m» los números no crecen.",
"complejidad": "O(log n) multiplicaciones (cada una O(k³) si es una matriz k×k)",
"codigo": r'''
def mult(A, B, mod=None):
    C = [[A[0][0] * B[0][0] + A[0][1] * B[1][0], A[0][0] * B[0][1] + A[0][1] * B[1][1]],
         [A[1][0] * B[0][0] + A[1][1] * B[1][0], A[1][0] * B[0][1] + A[1][1] * B[1][1]]]
    return [[x % mod for x in fila] for fila in C] if mod else C


def potencia(M, n, mod=None):
    R, veces = [[1, 0], [0, 1]], 0
    while n:
        if n & 1:                                    # este bit de n está encendido: se multiplica
            R = mult(R, M, mod)
            veces += 1
        M = mult(M, M, mod)                          # siguiente cuadrado: M, M², M⁴, M⁸…
        veces += 1
        n >>= 1
    return R, veces


def registrar():
    def fibonacci(texto):
        # «fibonacci 90»  o  «fibonacci 1000000 mod 1000000007»
        n_txt, _, mod_txt = texto.lower().partition("mod")
        if not n_txt.strip().isdigit() or (mod_txt and not mod_txt.strip().isdigit()):
            raise ValueError("Uso: fibonacci 90   o   fibonacci 1000000 mod 1000000007")
        n, mod = int(n_txt), int(mod_txt) if mod_txt else None
        if mod is None and n > 10_000:
            raise ValueError("Sin «mod», hasta F(10000) (más tendría miles de cifras). Prueba con «mod 1000000007».")
        if mod is not None and (mod < 2 or n > 10 ** 18):
            raise ValueError("El módulo debe ser al menos 2 y n hasta 10^18.")
        R, veces = potencia([[1, 1], [1, 0]], n, mod)
        texto_mod = f" mod {mod}" if mod else ""
        return (f"F({n}){texto_mod} = {R[0][1]}  ({veces} multiplicaciones de matrices; "
                f"sumando de uno en uno serían {n})")
    return {"fibonacci": fibonacci}
''',
"prueba": [("fibonacci", "90", "F(90) = 2880067194370816120"), ("fibonacci", "10 mod 7", "F(10) mod 7 = 6"),
           ("fibonacci", "1000000000000 mod 1000000007", "F(1000000000000) mod 1000000007 =")],
},
{
"id": "gauss",
"titulo": "Eliminación de Gauss con fracciones exactas: resolver sistemas de ecuaciones",
"area": "Matemáticas y números",
"temas": "gauss eliminacion sistema ecuaciones lineales resolver incognitas matriz fracciones exactas algebra "
         "lineal determinante pivote",
"idea": "Se escoge un pivote no nulo en cada columna, se intercambian filas si hace falta y se hacen ceros en el "
        "resto de la columna restando múltiplos de la fila del pivote (Gauss-Jordan). Con Fraction no hay errores "
        "de redondeo: 1/3 es exactamente 1/3. El producto de los pivotes (con su signo) es el determinante.",
"complejidad": "O(n³) operaciones",
"codigo": r'''
import re
from fractions import Fraction

TERMINO = re.compile(r"(-?)(\d+(?:\.\d+)?(?:/\d+)?)?\*?([a-z]\w*)?")


def lado(texto):
    coef, const = {}, Fraction(0)
    for t in texto.replace(" ", "").replace(",", ".").replace("-", "+-").split("+"):
        if not t:
            continue
        m = TERMINO.fullmatch(t)
        if not m or not (m.group(2) or m.group(3)):
            raise ValueError(f"No entiendo «{t}». Ejemplo: resuelve 2x + y = 5; x - y = 1")
        valor = (-1 if m.group(1) else 1) * Fraction(m.group(2) or 1)
        if m.group(3):
            coef[m.group(3)] = coef.get(m.group(3), 0) + valor
        else:
            const += valor
    return coef, const


def gauss_jordan(A):
    """A: matriz aumentada n×(n+1). Devuelve (soluciones, determinante) o (None, 0) si no hay solución única."""
    n, det = len(A), Fraction(1)
    A = [[Fraction(x) for x in fila] for fila in A]
    for col in range(n):
        piv = next((f for f in range(col, n) if A[f][col] != 0), None)
        if piv is None:
            return None, Fraction(0)
        if piv != col:
            A[col], A[piv] = A[piv], A[col]
            det = -det                               # cambiar dos filas cambia el signo del determinante
        det *= A[col][col]
        for f in range(n):
            if f != col and A[f][col] != 0:
                k = A[f][col] / A[col][col]
                A[f] = [a - k * b for a, b in zip(A[f], A[col])]
    return [A[i][n] / A[i][i] for i in range(n)], det


def registrar():
    def resuelve(texto):
        # «resuelve 2x + y = 5; x - y = 1»
        ecuaciones = [e for e in texto.lower().split(";") if e.strip()]
        filas, nombres = [], []
        for e in ecuaciones:
            izq, igual, der = e.partition("=")
            if not igual:
                raise ValueError("Cada ecuación necesita «=». Ejemplo: resuelve 2x + y = 5; x - y = 1")
            ci, ki = lado(izq)
            cd, kd = lado(der)
            for v in list(ci) + list(cd):
                if v not in nombres:
                    nombres.append(v)
            filas.append((ci, cd, kd - ki))
        if not filas or len(nombres) != len(filas):
            raise ValueError(f"Hay {len(filas)} ecuaciones y {len(nombres)} incógnitas: tienen que ser las mismas.")
        A = [[ci.get(v, 0) - cd.get(v, 0) for v in nombres] + [k] for ci, cd, k in filas]
        sol, det = gauss_jordan(A)
        if sol is None:
            return "El sistema no tiene solución única (determinante 0: o no tiene ninguna o tiene infinitas)."
        return ", ".join(f"{v} = {s}" for v, s in zip(nombres, sol)) + f"  (determinante {det})"
    return {"resuelve": resuelve}
''',
"prueba": [("resuelve", "2x + y = 5; x - y = 1", "x = 2, y = 1"), ("resuelve", "x + y = 1; x - y = 0", "x = 1/2, y = 1/2"),
           ("resuelve", "x + y = 1; 2x + 2y = 2", "no tiene solución única")],
},
# =====================================================================================================================
#  SISTEMAS OPERATIVOS Y CONCURRENCIA
# =====================================================================================================================
{
"id": "planificador_cpu",
"titulo": "Planificación de la CPU: FCFS, SJF, SRTF y Round Robin con diagrama de Gantt",
"area": "Sistemas operativos y concurrencia",
"temas": "planificador planificacion cpu procesos fcfs sjf srtf round robin quantum turnos gantt espera retorno "
         "sistema operativo scheduler hilos",
"idea": "El sistema operativo decide qué proceso usa la CPU. FCFS: por orden de llegada (sufre el «efecto convoy»). "
        "SJF: el más corto de los que esperan. SRTF: el que MENOS le queda, expulsando si llega uno más corto (da la "
        "menor espera media posible). Round Robin: turnos de un quantum fijo (justo y con buena respuesta, a cambio "
        "de más cambios de contexto).",
"complejidad": "simulación O(n²) aquí; un planificador real usa colas de prioridad: O(log n) por decisión",
"codigo": r'''
from collections import deque


def leer(texto):
    procs = []
    for t in texto.split():
        partes = t.split(":")
        if len(partes) != 3 or not partes[1].isdigit() or not partes[2].isdigit() or int(partes[2]) < 1:
            raise ValueError(f"No entiendo «{t}»: escribe nombre:llegada:ráfaga, por ejemplo P1:0:5")
        procs.append((partes[0], int(partes[1]), int(partes[2])))
    if not procs or len(procs) > 50:
        raise ValueError("Uso: planifica P1:0:5 P2:1:3 P3:2:8 | 2   (el último número es el quantum)")
    return procs


def fcfs(procs):
    t, gantt, fin = 0, [], {}
    for n, llegada, rafaga in sorted(procs, key=lambda p: (p[1], p[0])):
        t = max(t, llegada)
        gantt.append((n, t, t + rafaga))
        t += rafaga
        fin[n] = t
    return fin, gantt


def sjf(procs):
    pendientes, t, gantt, fin = sorted(procs, key=lambda p: (p[1], p[0])), 0, [], {}
    while pendientes:
        listos = [p for p in pendientes if p[1] <= t]
        if not listos:
            t = pendientes[0][1]
            continue
        p = min(listos, key=lambda p: (p[2], p[1], p[0]))
        pendientes = [q for q in pendientes if q is not p]
        gantt.append((p[0], t, t + p[2]))
        t += p[2]
        fin[p[0]] = t
    return fin, gantt


def srtf(procs):
    resto = {n: r for n, _, r in procs}
    llegada = {n: l for n, l, _ in procs}
    t, gantt, fin = 0, [], {}
    while len(fin) < len(procs):
        listos = [n for n in resto if llegada[n] <= t and n not in fin]
        if not listos:
            t = min(llegada[n] for n in resto if n not in fin)
            continue
        n = min(listos, key=lambda x: (resto[x], llegada[x], x))
        siguiente_llegada = min([llegada[m] for m in resto if llegada[m] > t] + [t + resto[n]])
        uso = min(resto[n], siguiente_llegada - t)   # corre hasta acabar o hasta que llegue alguien
        if gantt and gantt[-1][0] == n and gantt[-1][2] == t:
            gantt[-1] = (n, gantt[-1][1], t + uso)
        else:
            gantt.append((n, t, t + uso))
        t += uso
        resto[n] -= uso
        if resto[n] == 0:
            fin[n] = t
    return fin, gantt


def round_robin(procs, q):
    orden = sorted(procs, key=lambda p: (p[1], p[0]))
    resto = {n: r for n, _, r in procs}
    t, i, cola, gantt, fin = 0, 0, deque(), [], {}
    while len(fin) < len(procs):
        while i < len(orden) and orden[i][1] <= t:
            cola.append(orden[i][0])
            i += 1
        if not cola:
            t = orden[i][1]
            continue
        n = cola.popleft()
        uso = min(q, resto[n])
        if gantt and gantt[-1][0] == n and gantt[-1][2] == t:
            gantt[-1] = (n, gantt[-1][1], t + uso)  # sigue el mismo: no hay cambio de contexto
        else:
            gantt.append((n, t, t + uso))
        t += uso
        resto[n] -= uso
        while i < len(orden) and orden[i][1] <= t:   # los que llegan durante el turno van antes que el que vuelve
            cola.append(orden[i][0])
            i += 1
        if resto[n]:
            cola.append(n)
        else:
            fin[n] = t
    return fin, gantt


def registrar():
    def planifica(texto):
        # «planifica P1:0:5 P2:1:3 P3:2:8 | 2»
        lista, _, quantum = texto.partition("|")
        procs = leer(lista)
        q = int(quantum) if quantum.strip().isdigit() and int(quantum) > 0 else 2
        lineas, medias = [], []
        for nombre, (fin, gantt) in (("FCFS", fcfs(procs)), ("SJF", sjf(procs)), ("SRTF", srtf(procs)),
                                     (f"Round Robin (q={q})", round_robin(procs, q))):
            espera = sum(fin[n] - l - r for n, l, r in procs) / len(procs)
            retorno = sum(fin[n] - l for n, l, r in procs) / len(procs)
            medias.append((espera, nombre))
            diagrama = " ".join(f"{n}[{a}-{b}]" for n, a, b in gantt)
            lineas.append(f"{nombre}: espera media {espera:.2f}, retorno medio {retorno:.2f}, "
                          f"{len(gantt) - 1} cambios de contexto\n   {diagrama}")
        lineas.append(f"Menor espera media: {min(medias)[1]}")
        return "\n".join(lineas)
    return {"planifica": planifica}
''',
"prueba": [("planifica", "P1:0:5 P2:1:3 P3:2:8 | 2", "FCFS: espera media 3.33"),
           ("planifica", "P1:0:5 P2:1:3 P3:2:8 | 2", "Menor espera media: SRTF"),
           ("planifica", "P1:0:5 P2:1:3 P3:2:8 | 2", "Round Robin (q=2)")],
},
{
"id": "reemplazo_paginas",
"titulo": "Memoria virtual: reemplazo de páginas FIFO, LRU y Óptimo (y la anomalía de Belady)",
"area": "Sistemas operativos y concurrencia",
"temas": "paginas paginacion memoria virtual reemplazo fallos pagina fifo lru optimo belady marcos ram swap "
         "sistema operativo cache",
"idea": "Cuando la RAM (los marcos) está llena y hace falta otra página, hay que expulsar una. FIFO saca la que "
        "entró antes; LRU la usada hace más tiempo; el Óptimo (de Belady) la que más tardará en volver a usarse: es "
        "imposible en la realidad (habría que ver el futuro) pero sirve de vara de medir. Con FIFO, MÁS memoria puede "
        "dar MÁS fallos: la anomalía de Belady.",
"complejidad": "FIFO y LRU O(1) por acceso; Óptimo O(n) por fallo en esta simulación",
"codigo": r'''
from collections import OrderedDict, deque


def fifo(refs, marcos):
    memoria, cola, fallos = set(), deque(), 0
    for p in refs:
        if p not in memoria:
            fallos += 1
            if len(memoria) == marcos:
                memoria.discard(cola.popleft())     # sale la que entró primero
            memoria.add(p)
            cola.append(p)
    return fallos


def lru(refs, marcos):
    memoria, fallos = OrderedDict(), 0
    for p in refs:
        if p in memoria:
            memoria.move_to_end(p)                   # usada ahora: pasa a ser la más reciente
        else:
            fallos += 1
            if len(memoria) == marcos:
                memoria.popitem(last=False)          # sale la usada hace más tiempo
            memoria[p] = True
    return fallos


def optimo(refs, marcos):
    memoria, fallos = set(), 0
    for i, p in enumerate(refs):
        if p in memoria:
            continue
        fallos += 1
        if len(memoria) == marcos:
            futuro = refs[i + 1:]
            victima = max(sorted(memoria), key=lambda x: futuro.index(x) if x in futuro else len(futuro))
            memoria.discard(victima)                 # sale la que más tardará en volver (o nunca vuelve)
        memoria.add(p)
    return fallos


BELADY = "1 2 3 4 1 2 5 1 2 3 4 5"


def registrar():
    def paginas(texto):
        # «paginas 3 | 7 0 1 2 0 3 0 4 2 3 0 3 2»   (marcos | páginas pedidas)   o   «paginas belady»
        if texto.strip().lower() == "belady":
            r = BELADY.split()
            f3, f4 = fifo(r, 3), fifo(r, 4)
            return (f"Anomalía de Belady con FIFO y las páginas {BELADY}:\n3 marcos: {f3} fallos; 4 marcos: {f4} "
                    f"fallos. ¡Más memoria y MÁS fallos! LRU y Óptimo no la sufren (son algoritmos «de pila»).")
        marcos, _, resto = texto.partition("|")
        refs = resto.split()
        if not marcos.strip().isdigit() or int(marcos) < 1 or not refs:
            raise ValueError("Uso: paginas 3 | 7 0 1 2 0 3 0 4 2 3 0 3 2   (o «paginas belady»)")
        m = int(marcos)
        return (f"{len(refs)} accesos con {m} marcos:\nFIFO: {fifo(refs, m)} fallos\nLRU: {lru(refs, m)} fallos\n"
                f"Óptimo: {optimo(refs, m)} fallos (el mínimo posible)")
    return {"paginas": paginas, "páginas": paginas}
''',
"prueba": [("paginas", "3 | 1 2 3 4 1 2 5 1 2 3 4 5", "FIFO: 9 fallos"),
           ("paginas", "3 | 7 0 1 2 0 3 0 4 2 3 0 3 2", "Óptimo: 7 fallos"),
           ("paginas", "belady", "3 marcos: 9 fallos; 4 marcos: 10 fallos")],
},
{
"id": "banquero",
"titulo": "Algoritmo del banquero: evitar interbloqueos antes de dar recursos",
"area": "Sistemas operativos y concurrencia",
"temas": "banquero dijkstra interbloqueo deadlock recursos estado seguro evitar procesos asignar peticion "
         "sistema operativo bloqueo",
"idea": "Antes de conceder recursos, el sistema finge que los da y comprueba si el estado sigue siendo SEGURO: si "
        "existe un orden en el que cada proceso puede conseguir lo que le falta (con lo libre más lo que devuelven "
        "los que acaban). Si no existe ese orden, la petición espera. Es la forma de EVITAR interbloqueos (otras: "
        "prevenirlos rompiendo una condición de Coffman, o detectarlos y recuperarse).",
"complejidad": "O(n²·m) por comprobación (n procesos, m tipos de recurso)",
"codigo": r'''
EJEMPLO = {"asignado": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
           "maximo": [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]],
           "disponible": [3, 3, 2]}


def es_seguro(asignado, maximo, disponible):
    n = len(asignado)
    falta = [[m - a for m, a in zip(maximo[i], asignado[i])] for i in range(n)]
    libre, hecho, orden = list(disponible), [False] * n, []
    avanza = True
    while avanza:
        avanza = False
        for i in range(n):
            if not hecho[i] and all(f <= l for f, l in zip(falta[i], libre)):
                libre = [l + a for l, a in zip(libre, asignado[i])]   # acaba y devuelve lo que tenía
                hecho[i], avanza = True, True
                orden.append(f"P{i}")
    return all(hecho), orden


def leer(texto):
    estado = {k: [fila[:] for fila in v] if k != "disponible" else v[:] for k, v in EJEMPLO.items()}
    peticion = None
    for parte in texto.split("|"):
        p = parte.strip().lower()
        if not p:
            continue
        clave, _, resto = p.partition(" ")
        if clave in ("asignado", "maximo", "máximo"):
            estado["maximo" if clave != "asignado" else "asignado"] = [[int(x) for x in fila.split()] for fila in resto.split(",")]
        elif clave == "disponible":
            estado["disponible"] = [int(x) for x in resto.split()]
        elif clave == "pide":
            proc, _, cant = resto.partition(" ")
            peticion = (int(proc.lstrip("p")), [int(x) for x in cant.split()])
        else:
            raise ValueError("Uso: banquero   |   banquero pide P1 1 0 2   (o da tu estado: asignado 0 1 0, 2 0 0 | "
                             "maximo 7 5 3, 3 2 2 | disponible 3 3 2)")
    return estado, peticion


def registrar():
    def banquero(texto):
        estado, peticion = leer(texto)
        A, M, D = estado["asignado"], estado["maximo"], estado["disponible"]
        if len(A) != len(M) or any(len(f) != len(D) for f in A + M):
            raise ValueError("Las matrices no cuadran: cada proceso con un número por tipo de recurso.")
        if peticion is None:
            seguro, orden = es_seguro(A, M, D)
            return ("Estado seguro. Orden en que todos pueden acabar: " + " → ".join(orden) if seguro else
                    "Estado INSEGURO: podría haber interbloqueo (solo acabarían: " + (", ".join(orden) or "ninguno") + ").")
        i, pide = peticion
        if not 0 <= i < len(A) or len(pide) != len(D):
            raise ValueError("Ese proceso no existe o la petición no tiene un número por recurso.")
        falta = [m - a for m, a in zip(M[i], A[i])]
        if any(p > f for p, f in zip(pide, falta)):
            return f"Error: P{i} pide más de lo que declaró como máximo."
        if any(p > d for p, d in zip(pide, D)):
            return f"P{i} tiene que esperar: ahora no hay recursos libres suficientes."
        A2 = [fila[:] for fila in A]
        A2[i] = [a + p for a, p in zip(A[i], pide)]
        seguro, orden = es_seguro(A2, M, [d - p for d, p in zip(D, pide)])
        if seguro:
            return f"Se concede a P{i}: el estado sigue siendo seguro ({' → '.join(orden)})."
        return f"No se concede a P{i}: el estado pasaría a ser inseguro (riesgo de interbloqueo). Espera."
    return {"banquero": banquero}
''',
"prueba": [("banquero", "", "P1 → P3 → P4 → P0 → P2"), ("banquero", "pide P1 1 0 2", "Se concede a P1"),
           ("banquero", "pide P4 3 3 0", "No se concede a P4")],
},
{
"id": "productor_consumidor",
"titulo": "Productor-consumidor con hilos: búfer acotado, Condition y píldora venenosa",
"area": "Sistemas operativos y concurrencia",
"temas": "productor consumidor hilos threads concurrencia buffer cola acotada condition condicion lock mutex "
         "sincronizacion carrera esperar notificar",
"idea": "Varios hilos producen datos y otros los consumen a través de un búfer de tamaño fijo. Con una Condition "
        "(cerrojo + aviso): quien encuentra el búfer lleno (o vacío) ESPERA sin gastar CPU y se le avisa cuando "
        "cambia; la comprobación va en un while porque al despertar el estado puede haber cambiado otra vez. Para "
        "terminar, una «píldora venenosa» (None) por consumidor.",
"complejidad": "O(1) por operación; el reto no es el coste sino la corrección (sin carreras ni bloqueos)",
"codigo": r'''
import threading


class BuferAcotado:
    def __init__(self, capacidad):
        self.datos, self.capacidad, self.maximo = [], capacidad, 0
        self.cond = threading.Condition()

    def meter(self, x):
        with self.cond:
            while len(self.datos) >= self.capacidad:  # while, no if: al despertar hay que volver a mirar
                if not self.cond.wait(timeout=3):
                    raise RuntimeError("esperando demasiado: ¿interbloqueo?")
            self.datos.append(x)
            self.maximo = max(self.maximo, len(self.datos))
            self.cond.notify_all()

    def sacar(self):
        with self.cond:
            while not self.datos:
                if not self.cond.wait(timeout=3):
                    raise RuntimeError("esperando demasiado: ¿interbloqueo?")
            x = self.datos.pop(0)
            self.cond.notify_all()
            return x


def simular(productores, consumidores, cada, capacidad=5):
    buf = BuferAcotado(capacidad)
    suma, cuenta = [0] * consumidores, [0] * consumidores

    def producir():
        for i in range(1, cada + 1):
            buf.meter(i)

    def consumir(k):
        while True:
            x = buf.sacar()
            if x is None:                            # píldora venenosa: se acabó el trabajo
                return
            suma[k] += x
            cuenta[k] += 1
    hc = [threading.Thread(target=consumir, args=(k,), daemon=True) for k in range(consumidores)]
    hp = [threading.Thread(target=producir, daemon=True) for _ in range(productores)]
    for h in hc + hp:
        h.start()
    for h in hp:
        h.join(timeout=10)
    for _ in hc:
        buf.meter(None)
    for h in hc:
        h.join(timeout=10)
    return sum(suma), productores * cada * (cada + 1) // 2, cuenta, buf.maximo


def registrar():
    def prod_cons(texto):
        # «productor consumidor 3 2 100»: 3 productores, 2 consumidores, 100 datos por productor
        partes = texto.split()
        if len(partes) != 3 or not all(p.isdigit() for p in partes):
            raise ValueError("Uso: productor consumidor 3 2 100 (productores, consumidores, datos de cada uno)")
        p, c, n = map(int, partes)
        if not (1 <= p <= 8 and 1 <= c <= 8 and 1 <= n <= 2000):
            raise ValueError("Hasta 8 productores, 8 consumidores y 2000 datos por productor.")
        total, esperado, cuenta, maximo = simular(p, c, n)
        return (f"Producidos {p * n}, consumidos {sum(cuenta)} (por consumidor: {cuenta}); suma correcta: "
                f"{'sí' if total == esperado else 'NO'} ({total}); el búfer de 5 llegó a tener {maximo}.")
    return {"productor consumidor": prod_cons}
''',
"prueba": [("productor consumidor", "3 2 100", "suma correcta: sí (15150)")],
},
{
"id": "filosofos",
"titulo": "La cena de los filósofos: interbloqueo y cómo evitarlo ordenando los recursos",
"area": "Sistemas operativos y concurrencia",
"temas": "filosofos cena interbloqueo deadlock tenedores cerrojos locks orden recursos espera circular coffman "
         "hilos inanicion concurrencia",
"idea": "Cinco filósofos y cinco tenedores; cada uno necesita los dos de su lado. Si todos cogen primero el de su "
        "izquierda, pueden quedarse esperando para siempre: interbloqueo. Las 4 condiciones de Coffman (exclusión "
        "mutua, retener y esperar, sin expulsión, espera circular) deben darse a la vez; aquí se rompe la ESPERA "
        "CIRCULAR haciendo que todos cojan antes el tenedor de número menor.",
"complejidad": "O(1) por comida; lo importante es la propiedad: sin interbloqueo",
"codigo": r'''
import threading


def cenar(n, platos):
    tenedores = [threading.Lock() for _ in range(n)]
    comidas = [0] * n

    def filosofo(i):
        izq, der = i, (i + 1) % n
        primero, segundo = min(izq, der), max(izq, der)  # orden global: nunca hay espera circular
        for _ in range(platos):
            with tenedores[primero]:
                with tenedores[segundo]:
                    comidas[i] += 1
    hilos = [threading.Thread(target=filosofo, args=(i,), daemon=True) for i in range(n)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=5)
    return comidas, sum(1 for h in hilos if h.is_alive())


def registrar():
    def filosofos(texto):
        # «filosofos 5 100»: 5 filósofos y 100 platos cada uno
        partes = (texto.split() + ["5", "100"])[:2]
        if not all(p.isdigit() for p in partes) or not (2 <= int(partes[0]) <= 20 and 1 <= int(partes[1]) <= 5000):
            raise ValueError("Uso: filosofos 5 100 (entre 2 y 20 filósofos, hasta 5000 platos)")
        n, platos = int(partes[0]), int(partes[1])
        comidas, atascados = cenar(n, platos)
        if atascados:
            return f"¡Interbloqueo! {atascados} filósofos se quedaron esperando."
        return (f"{n} filósofos, {platos} platos cada uno: comieron {comidas}. Todos acabaron: sin interbloqueo, "
                "porque todos cogen primero el tenedor de número menor (no puede formarse un círculo de esperas).")
    return {"filosofos": filosofos, "filósofos": filosofos}
''',
"prueba": [("filosofos", "5 100", "sin interbloqueo")],
},
# =====================================================================================================================
#  SISTEMAS DISTRIBUIDOS Y BACKEND
# =====================================================================================================================
{
"id": "relojes_vectoriales",
"titulo": "Relojes de Lamport y vectoriales: qué pasó antes en un sistema distribuido",
"area": "Sistemas distribuidos",
"temas": "relojes vectoriales lamport sistemas distribuidos causalidad concurrentes ocurrio antes mensajes "
         "procesos orden eventos sincronizacion",
"idea": "En varias máquinas no hay un reloj común fiable. Lamport: cada evento suma 1 y al recibir se toma "
        "max(propio, recibido) + 1; si A pasó antes que B, L(A) < L(B), pero no al revés. El reloj VECTORIAL guarda "
        "un contador por proceso: A pasó antes que B si el vector de A es ≤ en todo y distinto; si ninguno es ≤ que "
        "el otro, fueron CONCURRENTES (ninguno pudo influir en el otro).",
"complejidad": "O(P) por evento con P procesos (Lamport, O(1))",
"codigo": r'''
def simular(eventos):
    procesos = sorted({p for e in eventos for p in e.split(">")})
    idx = {p: i for i, p in enumerate(procesos)}
    vector = {p: [0] * len(procesos) for p in procesos}
    lamport = {p: 0 for p in procesos}
    cuenta = {p: 0 for p in procesos}
    registro = []

    def anotar(p, que):
        cuenta[p] += 1
        registro.append((f"{p}{cuenta[p]}", p, tuple(vector[p]), lamport[p], que))
    for e in eventos:
        if ">" in e:
            a, b = e.split(">", 1)
            vector[a][idx[a]] += 1
            lamport[a] += 1
            anotar(a, f"envía a {b}")
            vector[b] = [max(x, y) for x, y in zip(vector[b], vector[a])]   # al recibir: máximo componente a componente
            vector[b][idx[b]] += 1
            lamport[b] = max(lamport[b], lamport[a]) + 1
            anotar(b, f"recibe de {a}")
        else:
            vector[e][idx[e]] += 1
            lamport[e] += 1
            anotar(e, "evento local")
    return procesos, registro


def antes(u, v):
    return u != v and all(x <= y for x, y in zip(u, v))


def registrar():
    def relojes(texto):
        # «relojes a a>b c b>c»: «a» es un evento local de a; «a>b» un mensaje de a a b
        eventos = texto.lower().split()
        for e in eventos:
            a, sep, b = e.partition(">")
            if not a or (sep and (not b or a == b)):
                raise ValueError(f"No entiendo «{e}». Uso: relojes a a>b c b>c")
        if not eventos:
            raise ValueError("Uso: relojes a a>b c b>c")
        procesos, reg = simular(eventos)
        lineas = [f"Procesos {', '.join(procesos)}. Evento: vector | Lamport"]
        lineas += [f"{n} ({que}): {list(v)} | {l}" for n, _, v, l, que in reg]
        conc = [f"{x[0]} ∥ {y[0]}" for i, x in enumerate(reg) for y in reg[i + 1:]
                if x[1] != y[1] and not antes(x[2], y[2]) and not antes(y[2], x[2])]
        lineas.append(("Concurrentes (ninguno pudo influir en el otro): " + ", ".join(sorted(conc)[:12]))
                      if conc else "No hay eventos concurrentes: todo está ordenado por mensajes.")
        return "\n".join(lineas)
    return {"relojes": relojes}
''',
"prueba": [("relojes", "a a>b c b>c", "a1 ∥ c1"), ("relojes", "a a>b c b>c", "c2 (recibe de b): [2, 2, 2] | 5")],
},
{
"id": "hash_consistente",
"titulo": "Hash consistente: repartir datos entre servidores sin moverlo todo al crecer",
"area": "Sistemas distribuidos",
"temas": "hash consistente anillo servidores repartir claves particionado sharding nodos virtuales escalar "
         "balanceo carga cache distribuida",
"idea": "Con «hash(clave) % n», añadir un servidor cambia n y mueve casi TODAS las claves. En el hash consistente "
        "servidores y claves se colocan en un anillo y cada clave va al primer servidor que encuentra girando: al "
        "añadir uno solo se mueve ~1/n de las claves. Cada servidor aparece en muchos puntos (nodos virtuales) para "
        "que el reparto salga equilibrado.",
"complejidad": "buscar el servidor O(log(n·v)) con búsqueda binaria; añadir uno mueve ~K/n claves",
"codigo": r'''
import bisect
import hashlib


def h(texto):
    return int.from_bytes(hashlib.sha256(texto.encode("utf-8")).digest()[:8], "big")


class Anillo:
    def __init__(self, servidores, virtuales=100):
        self.puntos, self.dueno = [], {}
        for s in servidores:
            for i in range(virtuales):
                p = h(f"{s}#{i}")
                self.dueno[p] = s
                self.puntos.append(p)
        self.puntos.sort()

    def servidor(self, clave):
        i = bisect.bisect(self.puntos, h(clave)) % len(self.puntos)   # el siguiente punto girando
        return self.dueno[self.puntos[i]]


def registrar():
    def reparte(texto):
        # «reparte claves 4»: 4 servidores, y se mide qué pasa al añadir uno más
        t = texto.strip() or "4"
        if not t.isdigit() or not 1 <= int(t) <= 50:
            raise ValueError("Uso: reparte claves 4 (entre 1 y 50 servidores)")
        n = int(t)
        claves = [f"usuario{i}" for i in range(10000)]
        antes = [f"s{i}" for i in range(n)]
        despues = antes + [f"s{n}"]
        modulo = sum(1 for c in claves if h(c) % n != h(c) % (n + 1))
        a1, a2 = Anillo(antes), Anillo(despues)
        movidas = sum(1 for c in claves if a1.servidor(c) != a2.servidor(c))
        carga = {}
        for c in claves:
            s = a1.servidor(c)
            carga[s] = carga.get(s, 0) + 1
        return (f"10000 claves en {n} servidores; al añadir uno más:\n"
                f"- Módulo (hash % n): se mueven {100 * modulo / len(claves):.1f} %\n"
                f"- Hash consistente: se mueven {100 * movidas / len(claves):.1f} % (lo ideal: {100 / (n + 1):.1f} %)\n"
                f"Reparto con hash consistente: mínimo {min(carga.values())}, máximo {max(carga.values())} claves "
                f"por servidor (media {len(claves) // n}).")
    return {"reparte claves": reparte}
''',
"prueba": [("reparte claves", "4", "Hash consistente: se mueven"), ("reparte claves", "4", "lo ideal: 20.0 %")],
},
{
"id": "limitador_peticiones",
"titulo": "Limitador de peticiones (token bucket)",
"area": "Sistemas distribuidos",
"temas": "limitador peticiones rate limit token bucket fichas rafaga api servidor proteger abuso "
         "trafico throttling backend",
"idea": "Un cubo se llena de fichas a ritmo constante (la tasa) hasta un máximo (la ráfaga). Cada petición gasta "
        "una ficha; si no queda ninguna, se rechaza (o espera). Así se permiten ráfagas cortas sin dejar que nadie "
        "sature el servicio. No hace falta un temporizador: las fichas se calculan con el tiempo transcurrido.",
"complejidad": "O(1) por petición y O(1) de memoria por cliente",
"codigo": r'''
class CuboFichas:
    def __init__(self, tasa, rafaga):
        self.tasa, self.rafaga = tasa, rafaga
        self.fichas, self.ultimo = float(rafaga), None

    def permitir(self, t):
        if self.ultimo is not None:
            self.fichas = min(self.rafaga, self.fichas + (t - self.ultimo) * self.tasa)
        self.ultimo = t
        if self.fichas >= 1:
            self.fichas -= 1
            return True
        return False


def registrar():
    def limita(texto):
        # «limita 2 3 | 0 0.1 0.2 0.3 1 1.1»: 2 fichas por segundo, ráfaga de 3, y los instantes de cada petición
        conf, _, tiempos = texto.partition("|")
        try:
            tasa, rafaga = (float(x) for x in conf.split())
            ts = [float(x) for x in tiempos.split()]
        except ValueError:
            raise ValueError("Uso: limita 2 3 | 0 0.1 0.2 0.3 1 1.1 (tasa por segundo, ráfaga | segundos)")
        if tasa <= 0 or rafaga < 1 or not ts or ts != sorted(ts):
            raise ValueError("La tasa debe ser positiva, la ráfaga al menos 1 y los tiempos en orden.")
        cubo = CuboFichas(tasa, rafaga)
        res = [f"{t:g}: {'aceptada' if cubo.permitir(t) else 'rechazada'}" for t in ts]
        return "\n".join(res + [f"Aceptadas {sum('aceptada' in r for r in res)} de {len(ts)}."])
    return {"limita": limita}
''',
"prueba": [("limita", "2 3 | 0 0.1 0.2 0.3 1 1.1", "0.3: rechazada"), ("limita", "2 3 | 0 0.1 0.2 0.3 1 1.1", "Aceptadas 5 de 6")],
},
# =====================================================================================================================
#  COMPILADORES Y LENGUAJES
# =====================================================================================================================
{
"id": "maquina_pila",
"titulo": "Mini compilador: patio de maniobras → bytecode optimizado → máquina virtual de pila",
"area": "Compiladores y lenguajes",
"temas": "compilador compilar bytecode maquina virtual pila stack vm shunting yard patio maniobras postfija "
         "notacion polaca inversa optimizar plegado constantes interprete expresiones",
"idea": "Las fases de un compilador en pequeño: (1) análisis léxico: el texto se parte en fichas; (2) el algoritmo "
        "del patio de maniobras de Dijkstra pasa la expresión a notación POSTFIJA respetando prioridades y "
        "paréntesis; (3) generación de código para una máquina de PILA, con plegado de constantes (2*3 se calcula "
        "al compilar); (4) la máquina virtual ejecuta el bytecode. Así funcionan, a lo grande, Python y Java.",
"complejidad": "O(n) en cada fase (n = número de fichas)",
"codigo": r'''
import re

PRIORIDAD = {"+": 1, "-": 1, "*": 2, "/": 2, "%": 2, "neg": 3, "^": 4}
A_LA_DERECHA = {"^", "neg"}                          # 2^3^2 = 2^(3^2)
INSTRUCCION = {"+": "SUMA", "-": "RESTA", "*": "MULT", "/": "DIV", "%": "MOD", "^": "POT"}
SIMBOLO = {v: k for k, v in INSTRUCCION.items()}
FICHA = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([a-z_]\w*)|(\S))")


def num(x):
    return f"{x:g}" if isinstance(x, float) else str(x)


def operar(op, a, b):
    if op in "/%" and b == 0:
        raise ValueError("División por cero.")
    if op == "^" and abs(b) > 1000:
        raise ValueError("Exponente demasiado grande.")
    if op == "/":
        return a // b if isinstance(a, int) and isinstance(b, int) and a % b == 0 else a / b
    return {"+": a + b, "-": a - b, "*": a * b, "%": a % b if op == "%" else 0,
            "^": a ** b if op == "^" else 0}[op]


def analizar(expr):
    """Análisis léxico: números, variables, operadores y paréntesis. Distingue el menos UNARIO (-2) del binario."""
    res = []
    for numero, nombre, s in FICHA.findall(expr.lower()):
        previa = res[-1] if res else None
        if numero:
            f = ("num", float(numero) if "." in numero else int(numero))
        elif nombre:
            f = ("var", nombre)
        elif s in "+-" and (previa is None or previa[0] in ("op", "(")):
            if s == "+":
                continue                             # +5 es 5
            f = ("op", "neg")
        elif s in "+-*/%^":
            f = ("op", s)
        elif s in "()":
            f = (s, s)
        else:
            raise ValueError(f"Símbolo no válido: «{s}»")
        res.append(f)
    return res


def a_postfija(fichas):
    """Patio de maniobras (Dijkstra): los operadores esperan en una pila hasta que llega uno de menor prioridad."""
    salida, pila = [], []
    for tipo, v in fichas:
        if tipo in ("num", "var"):
            salida.append((tipo, v))
        elif tipo == "(":
            pila.append(v)
        elif tipo == ")":
            while pila and pila[-1] != "(":
                salida.append(("op", pila.pop()))
            if not pila:
                raise ValueError("Sobra un «)».")
            pila.pop()
        elif v == "neg":
            pila.append(v)                           # operador prefijo: no tiene operando a su izquierda
        else:
            while pila and pila[-1] != "(" and (PRIORIDAD[pila[-1]] > PRIORIDAD[v] or
                                                (PRIORIDAD[pila[-1]] == PRIORIDAD[v] and v not in A_LA_DERECHA)):
                salida.append(("op", pila.pop()))
            pila.append(v)
    while pila:
        if pila[-1] == "(":
            raise ValueError("Falta un «)».")
        salida.append(("op", pila.pop()))
    return salida


def generar(postfija, optimizar=True):
    codigo = []
    for tipo, v in postfija:
        if tipo == "num":
            codigo.append(("PUSH", v))
        elif tipo == "var":
            codigo.append(("LOAD", v))
        elif v == "neg":
            if optimizar and codigo and codigo[-1][0] == "PUSH":
                codigo[-1] = ("PUSH", -codigo[-1][1])
            else:
                codigo.append(("NEG", None))
        elif optimizar and len(codigo) >= 2 and codigo[-1][0] == codigo[-2][0] == "PUSH":
            b, a = codigo.pop()[1], codigo.pop()[1]  # plegado de constantes: se calcula al compilar
            codigo.append(("PUSH", operar(v, a, b)))
        else:
            codigo.append((INSTRUCCION[v], None))
    return codigo


def maquina(codigo, variables):
    pila = []
    try:
        for op, arg in codigo:
            if op == "PUSH":
                pila.append(arg)
            elif op == "LOAD":
                if arg not in variables:
                    raise ValueError(f"La variable «{arg}» no tiene valor: añade «| {arg}=5».")
                pila.append(variables[arg])
            elif op == "NEG":
                pila.append(-pila.pop())
            else:
                b, a = pila.pop(), pila.pop()
                pila.append(operar(SIMBOLO[op], a, b))
    except IndexError:
        raise ValueError("Expresión incompleta: falta algún número.")
    if len(pila) != 1:
        raise ValueError("Expresión incompleta: sobran números.")
    return pila[0]


def listar(codigo):
    return "; ".join(op + ("" if arg is None else " " + num(arg)) for op, arg in codigo)


def registrar():
    def compila(texto):
        # «compila 2 + 3 * (4 - 1)»   o con variables: «compila 2*x + 1 | x=5»
        expr, _, asignaciones = texto.partition("|")
        variables = {}
        for a in asignaciones.replace(",", " ").split():
            nombre, _, valor = a.partition("=")
            variables[nombre.strip().lower()] = float(valor) if "." in valor else int(valor)
        fichas = analizar(expr)
        if not fichas:
            raise ValueError("Uso: compila 2 + 3 * (4 - 1)   o   compila 2*x + 1 | x=5")
        post = a_postfija(fichas)
        crudo, opt = generar(post, optimizar=False), generar(post)
        return (f"Postfija (Dijkstra): {' '.join(num(v) if t == 'num' else str(v) for t, v in post)}\n"
                f"Bytecode ({len(crudo)} instrucciones): {listar(crudo)}\n"
                f"Optimizado ({len(opt)}): {listar(opt)}\n"
                f"Máquina de pila: = {num(maquina(opt, variables))}")
    return {"compila": compila}
''',
"prueba": [("compila", "2 + 3 * (4 - 1)", "Postfija (Dijkstra): 2 3 4 1 - * +"), ("compila", "2 + 3 * (4 - 1)", "= 11"),
           ("compila", "2*x + 1 | x=5", "Optimizado (5): PUSH 2; LOAD x; MULT; PUSH 1; SUMA"),
           ("compila", "2*x + 1 | x=5", "= 11"), ("compila", "-2^2", "= -4"), ("compila", "2^3^2", "= 512")],
},
{
"id": "regex_thompson",
"titulo": "Expresiones regulares desde cero: construcción de Thompson y autómata finito",
"area": "Compiladores y lenguajes",
"temas": "expresion regular regex automata finito afn nfa thompson coincidir patron validar redos backtracking "
         "lenguajes formales teoria computacion compiladores",
"idea": "Cada pieza de la expresión (letra, concatenación, |, *, +, ?) se traduce en un trocito de autómata con "
        "transiciones vacías (ε) y se enchufan entre sí (construcción de Thompson). Para comprobar un texto se "
        "lleva el CONJUNTO de estados posibles a la vez, en vez de probar caminos y volver atrás: el tiempo es "
        "lineal y patrones como (a*)*b no se cuelgan (los motores con vuelta atrás sí: ataques ReDoS).",
"complejidad": "construir O(m); comprobar O(n·m) garantizado (n = texto, m = patrón)",
"codigo": r'''
POSTFIJOS = "*+?"


def con_concatenacion(r):
    """Hace explícita la concatenación con «·»: ab*c -> a·b*·c."""
    res = []
    for i, c in enumerate(r):
        res.append(c)
        if c in "(|" or i + 1 == len(r):
            continue
        if r[i + 1] not in "*+?)|":
            res.append("·")
    return "".join(res)


def a_postfija(r):
    prioridad = {"|": 1, "·": 2}
    salida, pila = [], []
    for c in r:
        if c == "(":
            pila.append(c)
        elif c == ")":
            while pila and pila[-1] != "(":
                salida.append(pila.pop())
            if not pila:
                raise ValueError("Sobra un «)».")
            pila.pop()
        elif c in prioridad:
            while pila and pila[-1] != "(" and prioridad[pila[-1]] >= prioridad[c]:
                salida.append(pila.pop())
            pila.append(c)
        else:
            salida.append(c)                         # letras y * + ? (ya van detrás de su operando)
    while pila:
        if pila[-1] == "(":
            raise ValueError("Falta un «)».")
        salida.append(pila.pop())
    return salida


def thompson(postfija):
    trans = []                                       # por estado: lista de (símbolo o None = ε, destino)

    def nuevo():
        trans.append([])
        return len(trans) - 1
    pila = []
    try:
        for c in postfija:
            if c == "·":
                b, a = pila.pop(), pila.pop()
                trans[a[1]].append((None, b[0]))
                pila.append((a[0], b[1]))
            elif c == "|":
                b, a = pila.pop(), pila.pop()
                i, f = nuevo(), nuevo()
                trans[i] += [(None, a[0]), (None, b[0])]
                trans[a[1]].append((None, f))
                trans[b[1]].append((None, f))
                pila.append((i, f))
            elif c in POSTFIJOS:
                a = pila.pop()
                i, f = nuevo(), nuevo()
                trans[i].append((None, a[0]))
                trans[a[1]].append((None, f))
                if c in "*?":
                    trans[i].append((None, f))       # cero veces
                if c in "*+":
                    trans[a[1]].append((None, a[0])) # otra vez
                pila.append((i, f))
            else:
                i, f = nuevo(), nuevo()
                trans[i].append((c, f))
                pila.append((i, f))
    except IndexError:
        raise ValueError("Expresión mal formada (falta algo alrededor de un |, * , + o ?).")
    if len(pila) != 1:
        raise ValueError("Expresión mal formada.")
    return trans, pila[0]


def cierre(trans, estados):
    pila, vistos = list(estados), set(estados)
    while pila:
        for sim, d in trans[pila.pop()]:
            if sim is None and d not in vistos:
                vistos.add(d)
                pila.append(d)
    return vistos


def coincide(trans, inicio_fin, texto):
    inicio, fin = inicio_fin
    actuales = cierre(trans, {inicio})
    for ch in texto:
        actuales = cierre(trans, {d for s in actuales for sim, d in trans[s] if sim == ch or sim == "."})
        if not actuales:
            return False
    return fin in actuales


def registrar():
    def regex(texto):
        # «coincide (a|b)*abb | aababb»   (admite letras, ., |, *, +, ? y paréntesis; debe encajar el texto entero)
        patron, sep, cadena = texto.partition(" | ")
        patron = patron.strip()
        if not sep or not patron or "·" in patron:
            raise ValueError("Uso: coincide (a|b)*abb | aababb   (deja espacios alrededor de la barra que separa)")
        trans, ext = thompson(a_postfija(con_concatenacion(patron)))
        cadena = cadena.strip()
        si = coincide(trans, ext, cadena)
        return (f"{'Sí' if si else 'No'}: «{cadena}» {'encaja' if si else 'no encaja'} con {patron} "
                f"(autómata de Thompson con {len(trans)} estados, sin vuelta atrás).")
    return {"coincide": regex}
''',
"prueba": [("coincide", "(a|b)*abb | aababb", "Sí"), ("coincide", "(a|b)*abb | abab", "No"),
           ("coincide", "k(i|a)+ra? | kiiir", "Sí"), ("coincide", "(a*)*b | " + "a" * 60 + "c", "No")],
},
{
"id": "kiralang",
"titulo": "KiraLang: un lenguaje de programación propio (léxico, parser, árbol y intérprete)",
"area": "Compiladores y lenguajes",
"temas": "lenguaje programacion interprete parser analizador sintactico descenso recursivo arbol sintaxis ast "
         "lexico tokens variables funciones recursion bucles crear lenguaje",
"idea": "Un lenguaje en español completo en cuatro piezas: el LÉXICO parte el texto en fichas; el PARSER de descenso "
        "recursivo (una función por nivel de prioridad) construye el árbol de sintaxis; el INTÉRPRETE recorre el "
        "árbol con un entorno de variables, y las funciones tienen su propio entorno local (por eso la recursión "
        "funciona). Un contador de pasos corta los bucles infinitos.",
"complejidad": "léxico y parser O(n); ejecutar depende del programa (limitado a 200.000 pasos)",
"codigo": r'''
import re

FICHAS = re.compile(r'\s*(?:(\d+(?:\.\d+)?)|("[^"]*")|([A-Za-z_áéíóúñ]\w*)|(==|!=|<=|>=|[-+*/%<>=(){},;]))')
CLAVES = {"si", "sino", "mientras", "escribe", "funcion", "devuelve", "y", "o", "no", "verdad", "falso"}
NIVELES = [("o",), ("y",), ("==", "!=", "<", ">", "<=", ">="), ("+", "-"), ("*", "/", "%")]


def lexico(codigo):
    res, pos, codigo = [], 0, codigo.replace("\n", ";")
    while pos < len(codigo):
        m = FICHAS.match(codigo, pos)
        if not m:
            if not codigo[pos:].strip():
                break
            raise ValueError(f"No entiendo «{codigo[pos:].strip()[:10]}»")
        pos = m.end()
        n, cadena, nombre, simbolo = m.groups()
        if n:
            res.append(("num", float(n) if "." in n else int(n)))
        elif cadena:
            res.append(("cad", cadena[1:-1]))
        elif nombre:
            res.append(("clave" if nombre in CLAVES else "nom", nombre))
        else:
            res.append(("sim", simbolo))
    return res + [("fin", None)]


class Parser:
    def __init__(self, fichas):
        self.f, self.i = fichas, 0

    def es(self, tipo, valor=None):
        t = self.f[self.i]
        return t[0] == tipo and (valor is None or t[1] == valor)

    def tomar(self, tipo=None, valor=None):
        t = self.f[self.i]
        if (tipo and t[0] != tipo) or (valor is not None and t[1] != valor):
            raise ValueError(f"Esperaba «{valor or tipo}» y encontré «{t[1] if t[1] is not None else 'el final'}».")
        self.i += 1
        return t

    def sentencias(self, hasta):
        res = []
        while True:
            while self.es("sim", ";"):
                self.tomar()
            if self.es(*hasta):
                return res
            if self.es("fin"):
                raise ValueError("Falta cerrar un «}».")
            res.append(self.sentencia())

    def bloque(self):
        self.tomar("sim", "{")
        s = self.sentencias(("sim", "}"))
        self.tomar("sim", "}")
        return s

    def lista(self, elemento):
        self.tomar("sim", "(")
        res = []
        while not self.es("sim", ")"):
            res.append(elemento())
            if not self.es("sim", ")"):
                self.tomar("sim", ",")
        self.tomar("sim", ")")
        return res

    def sentencia(self):
        if self.es("clave", "si"):
            self.tomar()
            cond, entonces, sino = self.expr(), self.bloque(), []
            while self.es("sim", ";") and self.f[self.i + 1] == ("clave", "sino"):
                self.tomar()
            if self.es("clave", "sino"):
                self.tomar()
                sino = [self.sentencia()] if self.es("clave", "si") else self.bloque()
            return ("si", cond, entonces, sino)
        if self.es("clave", "mientras"):
            self.tomar()
            return ("mientras", self.expr(), self.bloque())
        if self.es("clave", "escribe") or self.es("clave", "devuelve"):
            return (self.tomar()[1], self.expr())
        if self.es("clave", "funcion"):
            self.tomar()
            nombre = self.tomar("nom")[1]
            return ("funcion", nombre, self.lista(lambda: self.tomar("nom")[1]), self.bloque())
        if self.es("nom") and self.f[self.i + 1] == ("sim", "="):
            nombre = self.tomar()[1]
            self.tomar()
            return ("asigna", nombre, self.expr())
        return ("expr", self.expr())

    def expr(self, nivel=0):                         # descenso recursivo: un nivel por prioridad
        if nivel == len(NIVELES):
            return self.unario()
        izq = self.expr(nivel + 1)
        while self.f[self.i][0] in ("sim", "clave") and self.f[self.i][1] in NIVELES[nivel]:
            op = self.tomar()[1]
            izq = ("bin", op, izq, self.expr(nivel + 1))
        return izq

    def unario(self):
        if self.es("sim", "-") or self.es("clave", "no"):
            op = self.tomar()[1]
            return ("neg" if op == "-" else "no", self.unario())
        t = self.tomar()
        if t[0] in ("num", "cad"):
            return ("val", t[1])
        if t[0] == "clave" and t[1] in ("verdad", "falso"):
            return ("val", t[1] == "verdad")
        if t == ("sim", "("):
            e = self.expr()
            self.tomar("sim", ")")
            return e
        if t[0] == "nom":
            return ("llamada", t[1], self.lista(self.expr)) if self.es("sim", "(") else ("var", t[1])
        raise ValueError(f"No esperaba «{t[1] if t[1] is not None else 'el final'}».")


class Devolver(Exception):
    def __init__(self, valor):
        self.valor = valor


def dividir(a, b):
    if b == 0:
        raise ValueError("División por cero.")
    return a // b if isinstance(a, int) and isinstance(b, int) and a % b == 0 else a / b


OPS = {"+": lambda a, b: str(a) + str(b) if isinstance(a, str) or isinstance(b, str) else a + b,
       "-": lambda a, b: a - b, "*": lambda a, b: a * b, "/": dividir, "%": lambda a, b: a % b,
       "==": lambda a, b: a == b, "!=": lambda a, b: a != b, "<": lambda a, b: a < b, ">": lambda a, b: a > b,
       "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}


class Interprete:
    def __init__(self, limite=200_000):
        self.globales, self.funciones, self.salida = {}, {}, []
        self.pasos, self.limite, self.profundidad = 0, limite, 0

    def contar(self):
        self.pasos += 1
        if self.pasos > self.limite:
            raise ValueError("Demasiados pasos: ¿un bucle infinito?")

    def ejecutar(self, sentencias, entorno):
        for s in sentencias:
            self.contar()
            if s[0] == "asigna":
                entorno[s[1]] = self.valor(s[2], entorno)
            elif s[0] == "escribe":
                v = self.valor(s[1], entorno)
                self.salida.append({True: "verdad", False: "falso"}.get(v, v) if isinstance(v, bool) else
                                   (f"{v:g}" if isinstance(v, float) else str(v)))
            elif s[0] == "si":
                self.ejecutar(s[2] if self.valor(s[1], entorno) else s[3], entorno)
            elif s[0] == "mientras":
                while self.valor(s[1], entorno):
                    self.ejecutar(s[2], entorno)
            elif s[0] == "funcion":
                self.funciones[s[1]] = (s[2], s[3])
            elif s[0] == "devuelve":
                raise Devolver(self.valor(s[1], entorno))
            else:
                self.valor(s[1], entorno)

    def valor(self, e, entorno):
        self.contar()
        tipo = e[0]
        if tipo == "val":
            return e[1]
        if tipo == "var":
            for ambito in (entorno, self.globales):
                if e[1] in ambito:
                    return ambito[e[1]]
            raise ValueError(f"La variable «{e[1]}» no tiene valor.")
        if tipo == "neg":
            return -self.valor(e[1], entorno)
        if tipo == "no":
            return not self.valor(e[1], entorno)
        if tipo == "bin":
            if e[1] == "y":                          # cortocircuito: si la izquierda ya decide, no se evalúa la derecha
                return self.valor(e[2], entorno) and self.valor(e[3], entorno)
            if e[1] == "o":
                return self.valor(e[2], entorno) or self.valor(e[3], entorno)
            return OPS[e[1]](self.valor(e[2], entorno), self.valor(e[3], entorno))
        params, cuerpo = self.funciones.get(e[1], (None, None))
        if params is None or len(params) != len(e[2]):
            raise ValueError(f"La función «{e[1]}» no existe o recibe otro número de datos.")
        local = dict(zip(params, [self.valor(a, entorno) for a in e[2]]))
        self.profundidad += 1
        try:
            if self.profundidad > 60:
                raise ValueError("Recursión demasiado profunda (máximo 60 llamadas anidadas).")
            self.ejecutar(cuerpo, local)             # entorno propio: así funciona la recursión
        except Devolver as d:
            return d.valor
        finally:
            self.profundidad -= 1
        return None


def registrar():
    def kiralang(texto):
        # «kiralang x = 0; s = 0; mientras x < 5 { s = s + x; x = x + 1 }; escribe s»
        if not texto.strip():
            raise ValueError('Uso: kiralang x = 3; si x > 2 { escribe "grande" } sino { escribe "pequeño" }')
        try:
            arbol = Parser(lexico(texto)).sentencias(("fin",))
        except (ValueError, IndexError) as e:
            return f"Error de sintaxis: {e}"
        vm = Interprete()
        try:
            vm.ejecutar(arbol, vm.globales)
        except Devolver:
            vm.salida.append("Error: «devuelve» solo vale dentro de una función.")
        except (ValueError, RecursionError) as e:
            vm.salida.append(f"Error al ejecutar: {e}")  # lo escrito hasta el error se conserva
        except TypeError:
            vm.salida.append("Error al ejecutar: esos datos no se pueden operar juntos (¿texto con número?).")
        return "\n".join(vm.salida or ["(el programa no escribió nada)"]) + f"\n({vm.pasos} pasos)"
    return {"kiralang": kiralang}
''',
"prueba": [("kiralang", "x = 0; s = 0; mientras x < 5 { s = s + x; x = x + 1 }; escribe s", "10\n"),
           ("kiralang", "funcion fib(n) { si n < 2 { devuelve n }; devuelve fib(n - 1) + fib(n - 2) }; escribe fib(15)", "610"),
           ("kiralang", 'nombre = "Kira"; si 2 > 1 y no falso { escribe "hola " + nombre } sino { escribe "adiós" }', "hola Kira"),
           ("kiralang", "mientras verdad { x = 1 }", "Demasiados pasos")],
},
# =====================================================================================================================
#  COMPRESIÓN Y CODIFICACIÓN
# =====================================================================================================================
{
"id": "lzw",
"titulo": "Compresión LZW (la de GIF y compress): diccionario que se aprende solo",
"area": "Compresión y codificación",
"temas": "lzw lempel ziv welch comprimir compresion descomprimir texto diccionario gif zip codigos sin perdida "
         "repeticiones archivos ahorrar espacio",
"idea": "Empieza con un diccionario de los 256 bytes. Va leyendo mientras lo leído siga estando en el diccionario; "
        "cuando no, emite el código de lo anterior y añade lo nuevo como palabra. El descompresor reconstruye EL "
        "MISMO diccionario sin que se lo envíen (el único caso raro, «cScSc», se resuelve con w + w[0]).",
"complejidad": "O(n) comprimir y descomprimir",
"codigo": r'''
def comprimir(datos):
    dic = {bytes([i]): i for i in range(256)}
    w, res = b"", []
    for b in datos:
        wc = w + bytes([b])
        if wc in dic:
            w = wc                                   # sigue creciendo mientras lo conozca
        else:
            res.append(dic[w])
            dic[wc] = len(dic)                       # aprende la palabra nueva
            w = bytes([b])
    if w:
        res.append(dic[w])
    return res


def descomprimir(codigos):
    if not codigos:
        return b""
    dic = {i: bytes([i]) for i in range(256)}
    w = dic[codigos[0]]
    res = [w]
    for k in codigos[1:]:
        if k in dic:
            entrada = dic[k]
        elif k == len(dic):
            entrada = w + w[:1]                      # el caso «cScSc»: el código que se está creando ahora mismo
        else:
            raise ValueError("Código no válido.")
        res.append(entrada)
        dic[len(dic)] = w + entrada[:1]
        w = entrada
    return b"".join(res)


def registrar():
    def comprime(texto):
        datos = texto.encode("utf-8")
        if not datos or len(datos) > 100_000:
            raise ValueError("Uso: comprime TOBEORNOTTOBEORTOBEORNOT")
        codigos = comprimir(datos)
        bits = max(9, max(codigos).bit_length())
        total = len(codigos) * bits
        ok = descomprimir(codigos) == datos
        muestra = " ".join(map(str, codigos[:20])) + (" …" if len(codigos) > 20 else "")
        return (f"{len(datos)} bytes ({len(datos) * 8} bits) -> {len(codigos)} códigos de {bits} bits = {total} bits "
                f"({100 * total / (len(datos) * 8):.0f} % del original)\nCódigos: {muestra}\n"
                f"Recuperado: {'sí' if ok else 'NO'}")
    return {"comprime": comprime}
''',
"prueba": [("comprime", "TOBEORNOTTOBEORTOBEORNOT", "16 códigos de 9 bits"), ("comprime", "TOBEORNOTTOBEORTOBEORNOT", "Recuperado: sí"),
           ("comprime", "abababababababab", "Recuperado: sí")],
},
{
"id": "bwt",
"titulo": "Transformada de Burrows-Wheeler y mover al frente (el corazón de bzip2)",
"area": "Compresión y codificación",
"temas": "burrows wheeler bwt transformada bzip2 compresion mover frente mtf rachas rotaciones ordenar "
         "reversible adn indice fm",
"idea": "Se ordenan todas las rotaciones del texto (con una marca de fin) y se toma la ÚLTIMA columna: las letras "
        "que preceden a contextos parecidos quedan juntas, en rachas que comprimen muy bien. Lo mágico es que se "
        "puede deshacer: la primera columna es la última ordenada, y emparejando ambas (mapeo LF) se recorre el "
        "texto. Mover al frente convierte esas rachas en muchos ceros.",
"complejidad": "O(n² log n) con rotaciones como aquí; O(n) con array de sufijos",
"codigo": r'''
FIN = "\x00"                                         # menor que cualquier letra; se muestra como $


def bwt(s):
    t = s + FIN
    filas = sorted(range(len(t)), key=lambda i: t[i:] + t[:i])
    return "".join(t[i - 1] for i in filas)


def inversa(r):
    siguiente = sorted(range(len(r)), key=lambda i: (r[i], i))  # mapeo LF al revés: fila -> fila del carácter siguiente
    k, res = siguiente[0], []
    for _ in range(len(r) - 1):
        res.append(r[siguiente[k]])
        k = siguiente[k]
    return "".join(res)


def mover_al_frente(texto):
    alfabeto, res = sorted(set(texto)), []
    for c in texto:
        i = alfabeto.index(c)
        res.append(i)
        alfabeto.insert(0, alfabeto.pop(i))          # lo recién usado pasa delante: las rachas dan ceros
    return res


def rachas(t):
    return sum(1 for i, c in enumerate(t) if i == 0 or c != t[i - 1])


def registrar():
    def transforma(texto):
        s = texto.strip()
        if not s or len(s) > 2000 or FIN in s:
            raise ValueError("Uso: bwt banana (hasta 2000 letras)")
        r = bwt(s)
        mtf = mover_al_frente(r)
        ok = inversa(r) == s
        return (f"BWT: {r.replace(FIN, '$')}\nRachas: {rachas(s)} en el original -> {rachas(r)} tras la BWT\n"
                f"Mover al frente: {mtf[:30]}{' …' if len(mtf) > 30 else ''} ({mtf.count(0)} ceros de {len(mtf)})\n"
                f"Inversa: {inversa(r)[:60]} (recuperado: {'sí' if ok else 'NO'})")
    return {"bwt": transforma}
''',
"prueba": [("bwt", "banana", "BWT: annb$aa"), ("bwt", "banana", "recuperado: sí"),
           ("bwt", "kira kira kira programa programa", "recuperado: sí")],
},
{
"id": "deteccion_errores",
"titulo": "Detectar y corregir errores: código de Hamming (7,4) y CRC-32",
"area": "Compresión y codificación",
"temas": "hamming crc crc32 errores bits corregir detectar paridad sindrome codigo corrector checksum "
         "transmision ruido redes discos qr",
"idea": "Hamming(7,4) añade 3 bits de paridad en las posiciones 1, 2 y 4; cada uno vigila las posiciones cuyo "
        "número tiene ese bit. Al recibir, el XOR de las posiciones que valen 1 (el SÍNDROME) es 0 si todo va bien "
        "o justo la posición del bit cambiado: se corrige solo. El CRC-32 divide el mensaje (como polinomio) entre "
        "un polinomio fijo y envía el resto: detecta casi cualquier error (Ethernet, ZIP, PNG).",
"complejidad": "Hamming O(1) por bloque de 4 bits; CRC O(n) (con tabla, 1 paso por byte)",
"codigo": r'''
import zlib


def hamming_codificar(d1, d2, d3, d4):
    p1 = d1 ^ d2 ^ d4                                # vigila las posiciones 1, 3, 5, 7
    p2 = d1 ^ d3 ^ d4                                # vigila 2, 3, 6, 7
    p3 = d2 ^ d3 ^ d4                                # vigila 4, 5, 6, 7
    return [p1, p2, d1, p3, d2, d3, d4]


def hamming_corregir(c):
    sindrome = 0
    for pos in range(1, 8):
        if c[pos - 1]:
            sindrome ^= pos                          # 0 si está bien; si no, la posición del error
    c = c[:]
    if sindrome:
        c[sindrome - 1] ^= 1
    return [c[2], c[4], c[5], c[6]], sindrome


def crc32(datos):
    crc = 0xFFFFFFFF
    for byte in datos:
        crc ^= byte
        for _ in range(8):                           # división polinómica bit a bit (polinomio reflejado)
            crc = (crc >> 1) ^ 0xEDB88320 if crc & 1 else crc >> 1
    return crc ^ 0xFFFFFFFF


def bits(lista):
    return "".join(map(str, lista))


def registrar():
    def hamming(texto):
        # «hamming 1011 error 3»: codifica 4 bits, cambia el bit 3 y lo corrige
        datos, _, pos = texto.lower().partition("error")
        datos = datos.strip()
        if len(datos) != 4 or set(datos) - {"0", "1"}:
            raise ValueError("Uso: hamming 1011 error 3 (4 bits y la posición, 1-7, que se estropea)")
        p = int(pos) if pos.strip().isdigit() else 5
        if not 1 <= p <= 7:
            raise ValueError("La posición del error va de 1 a 7.")
        codigo = hamming_codificar(*[int(b) for b in datos])
        roto = codigo[:]
        roto[p - 1] ^= 1
        recuperado, s = hamming_corregir(roto)
        return (f"Datos {datos} -> código {bits(codigo)}\nCon el bit {p} cambiado: {bits(roto)}\n"
                f"Síndrome {s} -> bit {s} corregido -> datos recuperados {bits(recuperado)}")

    def crc(texto):
        datos = texto.encode("utf-8")
        if not datos:
            raise ValueError("Uso: crc hola")
        propio, oficial = crc32(datos), zlib.crc32(datos)
        cambiado = bytes([datos[0] ^ 1]) + datos[1:]
        return (f"CRC-32 de «{texto}»: {propio:08x} ({'coincide' if propio == oficial else 'NO coincide'} con zlib)\n"
                f"Cambiando un solo bit de la primera letra: {crc32(cambiado):08x} -> el error se detecta.")
    return {"hamming": hamming, "crc": crc}
''',
"prueba": [("hamming", "1011 error 3", "código 0110011"), ("hamming", "1011 error 3", "Síndrome 3"),
           ("hamming", "1011 error 3", "datos recuperados 1011"), ("crc", "hola", "6fa0f988 (coincide con zlib)")],
},
{
"id": "arbol_b",
"titulo": "Árbol B: el índice de las bases de datos y los sistemas de archivos",
"area": "Estructuras de datos",
"temas": "arbol b btree b+ indice indices base datos sqlite disco bloques sistema archivos nodos claves partir "
         "orden busqueda",
"idea": "Cada nodo guarda MUCHAS claves ordenadas (entre t-1 y 2t-1) y tiene un hijo más que claves: así el árbol "
        "es muy bajo y buscar lee muy pocos bloques de disco. Al insertar en un nodo lleno, se parte en dos y la "
        "clave del medio sube al padre; si la raíz se llena, el árbol crece por ARRIBA, así que todas las hojas "
        "están siempre a la misma profundidad. SQLite, PostgreSQL y los sistemas de archivos usan árboles B+.",
"complejidad": "buscar, insertar y borrar O(log_t n) lecturas de nodo; con t = 100, mil millones de claves en 5 niveles",
"codigo": r'''
import bisect


class NodoB:
    def __init__(self, hoja=True):
        self.claves, self.hijos, self.hoja = [], [], hoja


class ArbolB:
    def __init__(self, t=2):
        self.t, self.raiz = t, NodoB()

    def buscar(self, k):
        nodo, lecturas = self.raiz, 1
        while True:
            i = bisect.bisect_left(nodo.claves, k)
            if i < len(nodo.claves) and nodo.claves[i] == k:
                return True, lecturas
            if nodo.hoja:
                return False, lecturas
            nodo, lecturas = nodo.hijos[i], lecturas + 1

    def insertar(self, k):
        if self.buscar(k)[0]:
            return
        r = self.raiz
        if len(r.claves) == 2 * self.t - 1:          # raíz llena: se parte y el árbol crece por arriba
            nueva = NodoB(hoja=False)
            nueva.hijos.append(r)
            self._partir(nueva, 0)
            self.raiz = nueva
        nodo = self.raiz
        while not nodo.hoja:                         # al bajar, se parte todo hijo lleno: nunca hay que retroceder
            i = bisect.bisect_right(nodo.claves, k)
            if len(nodo.hijos[i].claves) == 2 * self.t - 1:
                self._partir(nodo, i)
                if k > nodo.claves[i]:
                    i += 1
            nodo = nodo.hijos[i]
        bisect.insort(nodo.claves, k)

    def _partir(self, padre, i):
        t, y = self.t, padre.hijos[i]
        z = NodoB(hoja=y.hoja)
        medio = y.claves[t - 1]
        z.claves, y.claves = y.claves[t:], y.claves[:t - 1]
        if not y.hoja:
            z.hijos, y.hijos = y.hijos[t:], y.hijos[:t]
        padre.claves.insert(i, medio)                # la clave del medio sube al padre
        padre.hijos.insert(i + 1, z)

    def niveles(self):
        res, nivel = [], [self.raiz]
        while nivel:
            res.append("  ".join("[" + " ".join(map(str, n.claves)) + "]" for n in nivel))
            nivel = [h for n in nivel for h in n.hijos]
        return res


def registrar():
    def arbol_b(texto):
        # «arbol b 2 | 10 20 5 6 12 30 7 17 | busca 6»   (grado mínimo t | claves | opcional: busca X)
        partes = [p.strip() for p in texto.split("|")]
        if len(partes) < 2 or not partes[0].isdigit() or not 2 <= int(partes[0]) <= 50:
            raise ValueError("Uso: arbol b 2 | 10 20 5 6 12 30 7 17 | busca 6   (t entre 2 y 50)")
        claves = [int(x) for x in partes[1].split()]
        if not claves or len(claves) > 5000:
            raise ValueError("Escribe entre 1 y 5000 claves (números enteros).")
        a = ArbolB(int(partes[0]))
        for k in claves:
            a.insertar(k)
        lineas = a.niveles()
        res = [f"Árbol B con t={a.t} (de {a.t - 1} a {2 * a.t - 1} claves por nodo), altura {len(lineas)}:"]
        res += [f"nivel {i + 1}: {l}" for i, l in enumerate(lineas[:4])]
        if len(lineas) > 4:
            res.append("…")
        for p in partes[2:]:
            if p.lower().startswith("busca"):
                x = int(p.split()[1])
                esta, lecturas = a.buscar(x)
                res.append(f"Buscar {x}: {'encontrado' if esta else 'no está'} leyendo {lecturas} nodo(s).")
        return "\n".join(res)
    return {"arbol b": arbol_b, "árbol b": arbol_b}
''',
"prueba": [("arbol b", "2 | 10 20 5 6 12 30 7 17 | busca 6", "altura 2"),
           ("arbol b", "2 | 10 20 5 6 12 30 7 17 | busca 6", "Buscar 6: encontrado leyendo 2 nodo(s)"),
           ("arbol b", "3 | " + " ".join(str(i) for i in range(1, 101)), "altura 4")],
},
# =====================================================================================================================
#  INTELIGENCIA ARTIFICIAL Y OPTIMIZACIÓN
# =====================================================================================================================
{
"id": "minimax_alfabeta",
"titulo": "Minimax con poda alfa-beta: una IA que nunca pierde al tres en raya",
"area": "Inteligencia artificial y optimización",
"temas": "minimax poda alfa beta negamax tres raya ia rival adversario arbol busqueda ajedrez damas decision "
         "estrategia jugada optima",
"idea": "Cada jugador escoge lo mejor para él suponiendo que el otro también juega perfecto: el valor de una "
        "posición es el máximo de lo que deja al rival cambiado de signo (negamax). La poda alfa-beta deja de mirar "
        "una jugada en cuanto se ve que el rival nunca permitiría llegar a ella; mirar primero las mejores casillas "
        "(centro y esquinas) poda mucho más. Igual funcionan las IA de ajedrez, con profundidad limitada.",
"complejidad": "minimax O(b^d); con alfa-beta y buen orden ~O(b^(d/2)) (b = jugadas por turno, d = profundidad)",
"codigo": r'''
LINEAS = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
ORDEN = (4, 0, 2, 6, 8, 1, 3, 5, 7)                  # centro y esquinas primero: se poda antes


def ganador(t):
    for a, b, c in LINEAS:
        if t[a] != "." and t[a] == t[b] == t[c]:
            return t[a]
    return None


def negamax(t, jugador, alfa, beta, nodos):
    """Valor para quien mueve ahora: >0 gana (antes = mejor), 0 empate, <0 pierde."""
    nodos[0] += 1
    rival = "o" if jugador == "x" else "x"
    if ganador(t) == rival:
        return -(1 + t.count("."))                   # perder pronto es peor que perder tarde
    if "." not in t:
        return 0
    mejor = -100
    for i in ORDEN:
        if t[i] == ".":
            v = -negamax(t[:i] + jugador + t[i + 1:], rival, -beta, -alfa, nodos)
            mejor = max(mejor, v)
            alfa = max(alfa, v)
            if alfa >= beta:
                break                                # poda: el rival nunca dejaría llegar aquí
    return mejor


def dibujar(t):
    return "\n".join(" " + " | ".join(t[f * 3 + c] if t[f * 3 + c] != "." else str(f * 3 + c + 1) for c in range(3))
                     for f in range(3))


def registrar():
    def tres_en_raya(texto):
        # «tres en raya xx.oo....» (9 casillas por filas: x, o y . para las vacías)
        t = "".join(c for c in texto.lower().replace("_", ".").replace("-", ".") if c in "xo.")
        if len(t) != 9 or not 0 <= t.count("x") - t.count("o") <= 1:
            raise ValueError("Uso: tres en raya xx.oo....  (9 casillas; empieza x)")
        if ganador(t) or "." not in t:
            return dibujar(t) + "\n" + (f"Ya ha ganado {ganador(t)}." if ganador(t) else "Empate: no quedan casillas.")
        jugador = "x" if t.count("x") == t.count("o") else "o"
        rival = "o" if jugador == "x" else "x"
        nodos, mejor, casilla, alfa = [0], -100, None, -100
        for i in ORDEN:
            if t[i] == ".":
                v = -negamax(t[:i] + jugador + t[i + 1:], rival, -100, -alfa, nodos)
                if v > mejor:
                    mejor, casilla = v, i
                alfa = max(alfa, v)
        veredicto = (f"{jugador} gana" if mejor > 0 else ("empate con juego perfecto" if mejor == 0 else
                     f"{jugador} pierde si {rival} no falla"))
        return (dibujar(t) + f"\nMejor jugada para {jugador}: casilla {casilla + 1} ({veredicto}). "
                f"Posiciones analizadas con poda alfa-beta: {nodos[0]}.")
    return {"tres en raya": tres_en_raya}
''',
"prueba": [("tres en raya", "xx.oo....", "casilla 3 (x gana)"), ("tres en raya", ".........", "empate con juego perfecto"),
           ("tres en raya", "x...o...x", "Mejor jugada para o")],
},
{
"id": "recocido_simulado",
"titulo": "Recocido simulado: optimizar rutas largas aceptando a veces empeorar",
"area": "Inteligencia artificial y optimización",
"temas": "recocido simulado annealing optimizacion heuristica metaheuristica viajante ruta reparto 2opt "
         "temperatura enfriar minimo local busqueda local",
"idea": "Una búsqueda local se queda atascada en el primer «valle». El recocido acepta a veces cambios A PEOR con "
        "probabilidad e^(-Δ/T); la temperatura T baja poco a poco: al principio explora y al final solo mejora. "
        "Aquí cada cambio invierte un tramo de la ruta (movimiento 2-opt) y su coste se calcula en O(1) mirando "
        "solo las dos aristas que cambian.",
"complejidad": "O(pasos) con Δ en O(1); no garantiza el óptimo, pero sirve para miles de ciudades",
"codigo": r'''
import math
import random


def longitud(ruta, d):
    return sum(d[a][b] for a, b in zip(ruta, ruta[1:] + ruta[:1]))


def vecino_mas_cercano(d):
    ruta, libres = [0], set(range(1, len(d)))
    while libres:
        sig = min(libres, key=lambda k: d[ruta[-1]][k])
        ruta.append(sig)
        libres.discard(sig)
    return ruta


def recocido(d, rnd, pasos=30000):
    n = len(d)
    ruta = list(range(n))
    rnd.shuffle(ruta)
    actual = longitud(ruta, d)
    mejor, mejor_largo = ruta[:], actual
    temp = actual / n                                # temperatura inicial: del orden de una arista
    enfriar = 0.0005 ** (1 / pasos)                  # al final queda en 0,05 % de la inicial
    for _ in range(pasos):
        i, j = sorted(rnd.sample(range(n), 2))
        if j - i < 1 or j - i >= n - 1:
            continue
        a, b, c, e = ruta[i - 1], ruta[i], ruta[j], ruta[(j + 1) % n]
        delta = d[a][c] + d[b][e] - d[a][b] - d[c][e]   # solo cambian dos aristas
        if delta < 0 or rnd.random() < math.exp(-delta / temp):
            ruta[i:j + 1] = ruta[i:j + 1][::-1]
            actual += delta
            if actual < mejor_largo - 1e-9:
                mejor, mejor_largo = ruta[:], actual
        temp *= enfriar
    return mejor, longitud(mejor, d)


def registrar():
    def optimiza(texto):
        # «recocido 30»: 30 ciudades al azar (siempre las mismas para ese número)
        t = texto.strip()
        if not t.isdigit() or not 5 <= int(t) <= 300:
            raise ValueError("Uso: recocido 30 (entre 5 y 300 ciudades)")
        rnd = random.Random(int(t))
        pts = [(rnd.uniform(0, 100), rnd.uniform(0, 100)) for _ in range(int(t))]
        d = [[math.dist(p, q) for q in pts] for p in pts]
        inicio = list(range(len(pts)))
        rnd.shuffle(inicio)
        azar = longitud(inicio, d)
        vc = longitud(vecino_mas_cercano(d), d)
        ruta, largo = recocido(d, random.Random(7))
        return (f"{t} ciudades. Ruta al azar: {azar:.1f}; vecino más cercano: {vc:.1f}\n"
                f"Recocido simulado: {largo:.1f} ({100 * (vc - largo) / vc:+.1f} % frente al vecino más cercano)")
    return {"recocido": optimiza}
''',
"prueba": [("recocido", "30", "Recocido simulado:")],
},
{
"id": "algoritmo_genetico",
"titulo": "Algoritmo genético: evolucionar soluciones con selección, cruce y mutación",
"area": "Inteligencia artificial y optimización",
"temas": "algoritmo genetico evolutivo evolucion seleccion natural cruce mutacion poblacion aptitud torneo "
         "elitismo optimizacion generaciones",
"idea": "Una población de candidatos al azar; cada generación se puntúa (aptitud), se eligen padres por TORNEO (el "
        "mejor de 3 al azar), se CRUZAN (un trozo de cada uno) y se MUTAN un poco; los 2 mejores pasan intactos "
        "(elitismo). Sin saber «cómo» resolver el problema, solo midiendo lo bueno que es cada intento, la población "
        "converge. Aquí evoluciona hasta escribir una frase.",
"complejidad": "O(generaciones · población · coste de la aptitud)",
"codigo": r'''
import random

ALFABETO = "abcdefghijklmnñopqrstuvwxyzáéíóú 0123456789.,¡!¿?"


def evolucionar(objetivo, rnd, poblacion=150, max_gen=1500):
    n = len(objetivo)
    mutacion = 1 / n

    def aptitud(ind):
        return sum(a == b for a, b in zip(ind, objetivo))
    pob = ["".join(rnd.choice(ALFABETO) for _ in range(n)) for _ in range(poblacion)]
    historia = []
    for gen in range(max_gen + 1):
        puntuados = sorted(((aptitud(i), i) for i in pob), reverse=True)
        if gen % 10 == 0 or puntuados[0][1] == objetivo:
            historia.append(f"generación {gen:4}: {puntuados[0][1]}  ({puntuados[0][0]}/{n})")
        if puntuados[0][1] == objetivo:
            return gen, historia
        hijos = [ind for _, ind in puntuados[:2]]    # elitismo
        while len(hijos) < poblacion:
            p1 = max(rnd.sample(puntuados, 3))[1]    # selección por torneo
            p2 = max(rnd.sample(puntuados, 3))[1]
            corte = rnd.randrange(n + 1)
            hijo = p1[:corte] + p2[corte:]           # cruce en un punto
            hijos.append("".join(rnd.choice(ALFABETO) if rnd.random() < mutacion else c for c in hijo))
        pob = hijos
    return None, historia


def registrar():
    def evoluciona(texto):
        # «evoluciona hola kira»
        objetivo = texto.strip().lower()
        if not objetivo or len(objetivo) > 40 or any(c not in ALFABETO for c in objetivo):
            raise ValueError("Uso: evoluciona hola kira (hasta 40 letras, números, espacios y . , ¡ ! ¿ ?)")
        gen, historia = evolucionar(objetivo, random.Random(len(objetivo)))
        if len(historia) > 12:
            historia = historia[:6] + ["…"] + historia[-5:]
        fin = f"¡encontrado en la generación {gen}!" if gen is not None else "no llegó (prueba otra frase)"
        return "\n".join(historia) + f"\n{objetivo} ({fin})"
    return {"evoluciona": evoluciona}
''',
"prueba": [("evoluciona", "hola kira", "hola kira (¡encontrado")],
},
{
"id": "kmeans",
"titulo": "k-means++: agrupar datos sin etiquetas (aprendizaje no supervisado)",
"area": "Inteligencia artificial y optimización",
"temas": "kmeans k medias clustering agrupar grupos centroides aprendizaje automatico no supervisado datos "
         "segmentar clientes colores inercia",
"idea": "Repite dos pasos hasta que nada cambia: (1) cada punto va con su centro más cercano; (2) cada centro se "
        "mueve a la media de sus puntos. Converge siempre, pero a un mínimo local: k-means++ elige los centros "
        "iniciales lejos unos de otros (con probabilidad proporcional a la distancia²) y así sale mucho mejor. La "
        "inercia (suma de distancias² a su centro) mide lo compactos que quedan.",
"complejidad": "O(iteraciones · n · k)",
"codigo": r'''
import random


def d2(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2


def kmeans(puntos, k, rnd, iteraciones=100):
    centros = [rnd.choice(puntos)]
    while len(centros) < k:                          # k-means++: los siguientes centros, lejos de los que hay
        pesos = [min(d2(p, c) for c in centros) for p in puntos]
        r, acum = rnd.uniform(0, sum(pesos)), 0.0
        for p, w in zip(puntos, pesos):
            acum += w
            if acum >= r and w > 0:
                centros.append(p)
                break
        else:
            centros.append(rnd.choice(puntos))
    for vuelta in range(1, iteraciones + 1):
        grupos = [[] for _ in range(k)]
        for p in puntos:
            grupos[min(range(k), key=lambda j: d2(p, centros[j]))].append(p)
        nuevos = [(sum(x for x, _ in g) / len(g), sum(y for _, y in g) / len(g)) if g else centros[j]
                  for j, g in enumerate(grupos)]
        if nuevos == centros:
            break
        centros = nuevos
    inercia = sum(d2(p, centros[j]) for j, g in enumerate(grupos) for p in g)
    return centros, grupos, vuelta, inercia


def registrar():
    def agrupa(texto):
        # «agrupa 1,1 1.5,2 3,4 5,7 3.5,5 4.5,5 3.5,4.5 | 2»   o   «agrupa aleatorio | 3»
        datos, _, k_txt = texto.partition("|")
        k = int(k_txt) if k_txt.strip().isdigit() else 2
        rnd = random.Random(42)
        if datos.strip().lower().startswith("aleatorio"):
            centros_reales = [(2, 2), (8, 3), (5, 8)]
            puntos = [(rnd.gauss(cx, 0.8), rnd.gauss(cy, 0.8)) for cx, cy in centros_reales for _ in range(30)]
        else:
            try:
                puntos = [tuple(float(v) for v in par.split(",")) for par in datos.split()]
            except ValueError:
                raise ValueError("Uso: agrupa 1,1 1.5,2 3,4 5,7 | 2   (puntos x,y | número de grupos)")
        if not 1 <= k <= len(puntos) or any(len(p) != 2 for p in puntos):
            raise ValueError("Necesito al menos tantos puntos x,y como grupos.")
        centros, grupos, vueltas, inercia = kmeans(puntos, k, rnd)
        lineas = [f"{k} grupos (k-means++, {vueltas} vueltas, inercia {inercia:.2f}):"]
        for c, g in sorted(zip(centros, grupos)):
            lineas.append(f"- centro ({c[0]:.2f}, {c[1]:.2f}): {len(g)} puntos")
        return "\n".join(lineas)
    return {"agrupa": agrupa}
''',
"prueba": [("agrupa", "1,1 1.5,2 3,4 5,7 3.5,5 4.5,5 3.5,4.5 | 2", "- centro (1.25, 1.50): 2 puntos"),
           ("agrupa", "aleatorio | 3", "30 puntos")],
},
{
"id": "red_neuronal",
"titulo": "Red neuronal con retropropagación desde cero: aprende XOR",
"area": "Inteligencia artificial y optimización",
"temas": "red neuronal neuronas capas oculta retropropagacion backpropagation gradiente xor aprendizaje "
         "profundo deep learning pesos activacion sigmoide tanh entrenar",
"idea": "Una neurona sola solo separa con una línea recta: no puede aprender XOR. Con una capa oculta sí. Hacia "
        "delante se calcula la salida; hacia atrás, la regla de la cadena reparte el error a cada peso "
        "(retropropagación) y se mueve cada peso un poquito en contra de su gradiente. Es lo mismo que hacen las "
        "redes enormes, con muchas más capas y datos.",
"complejidad": "O(épocas · datos · pesos)",
"codigo": r'''
import math
import random

TABLAS = {"xor": lambda a, b: a ^ b, "and": lambda a, b: a & b, "or": lambda a, b: a | b,
          "nand": lambda a, b: 1 - (a & b)}


def sigmoide(z):
    return 1 / (1 + math.exp(-max(-60.0, min(60.0, z))))


def entrenar(datos, ocultas=4, epocas=3000, ritmo=0.5, semilla=3):
    rnd = random.Random(semilla)
    W1 = [[rnd.uniform(-1, 1) for _ in range(2)] for _ in range(ocultas)]
    b1, W2, b2 = [0.0] * ocultas, [rnd.uniform(-1, 1) for _ in range(ocultas)], 0.0

    def adelante(x):
        h = [math.tanh(W1[j][0] * x[0] + W1[j][1] * x[1] + b1[j]) for j in range(ocultas)]
        return h, sigmoide(sum(w * hj for w, hj in zip(W2, h)) + b2)
    for _ in range(epocas):
        for x, y in datos:
            h, o = adelante(x)
            d_o = o - y                                # error de salida (entropía cruzada + sigmoide)
            d_h = [d_o * W2[j] * (1 - h[j] ** 2) for j in range(ocultas)]   # regla de la cadena hacia atrás
            for j in range(ocultas):
                W2[j] -= ritmo * d_o * h[j]
                W1[j][0] -= ritmo * d_h[j] * x[0]
                W1[j][1] -= ritmo * d_h[j] * x[1]
                b1[j] -= ritmo * d_h[j]
            b2 -= ritmo * d_o
    return lambda x: adelante(x)[1]


def registrar():
    def red(texto):
        # «red neuronal xor»  (también and, or, nand)
        op = texto.strip().lower() or "xor"
        if op not in TABLAS:
            raise ValueError("Uso: red neuronal xor   (o and, or, nand)")
        datos = [((a, b), TABLAS[op](a, b)) for a in (0, 1) for b in (0, 1)]
        predecir = entrenar(datos)
        lineas, bien = [], 0
        for (a, b), y in datos:
            p = predecir((a, b))
            bien += round(p) == y
            lineas.append(f"{a} {op} {b} -> {p:.3f} (debe ser {y}) {'✔' if round(p) == y else '✘'}")
        nota = ("\nUna sola neurona NO podría: xor no se separa con una línea recta." if op == "xor" else "")
        return "\n".join(lineas) + f"\nAprendido: {bien} de 4 con 2 entradas, 4 neuronas ocultas y 1 salida.{nota}"
    return {"red neuronal": red}
''',
"prueba": [("red neuronal", "xor", "Aprendido: 4 de 4"), ("red neuronal", "nand", "Aprendido: 4 de 4")],
},
{
"id": "regresion_lineal",
"titulo": "Regresión lineal: mínimos cuadrados y descenso de gradiente (y R²)",
"area": "Inteligencia artificial y optimización",
"temas": "regresion lineal minimos cuadrados descenso gradiente recta ajuste prediccion tendencia r2 "
         "estadistica aprendizaje automatico datos predecir",
"idea": "Buscar la recta y = a·x + b que menos se equivoca (suma de errores al cuadrado). Tiene fórmula cerrada: "
        "a = cov(x, y) / var(x), b = media(y) − a·media(x). El descenso de gradiente llega a lo mismo dando pasos "
        "pequeños cuesta abajo del error: es el método que se usa cuando no hay fórmula (redes neuronales). R² dice "
        "qué parte de la variación explica la recta (1 = perfecta).",
"complejidad": "fórmula O(n); gradiente O(pasos · n)",
"codigo": r'''
def minimos_cuadrados(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise ValueError("Todas las x son iguales: no hay recta posible.")
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return a, my - a * mx


def gradiente(xs, ys, ritmo=0.1, pasos=2000):
    n = len(xs)
    mx = sum(xs) / n
    sx = (sum((x - mx) ** 2 for x in xs) / n) ** 0.5
    zs = [(x - mx) / sx for x in xs]                 # escalar x hace que el descenso converja rápido
    a = b = 0.0
    for _ in range(pasos):
        errores = [a * z + b - y for z, y in zip(zs, ys)]
        a -= ritmo * 2 * sum(e * z for e, z in zip(errores, zs)) / n   # derivada del error cuadrático medio
        b -= ritmo * 2 * sum(errores) / n
    return a / sx, b - a * mx / sx                   # deshacer el escalado


def r2(xs, ys, a, b):
    my = sum(ys) / len(ys)
    total = sum((y - my) ** 2 for y in ys)
    resid = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    return 1 - resid / total if total else 1.0


def registrar():
    def regresion(texto):
        # «regresion 1,2 2,4.1 3,6.2 4,7.9 | 5»  (puntos x,y y, si quieres, una x para predecir)
        datos, _, predecir = texto.partition("|")
        try:
            pares = [tuple(float(v) for v in p.split(",")) for p in datos.split()]
        except ValueError:
            raise ValueError("Uso: regresion 1,2 2,4.1 3,6.2 4,7.9 | 5")
        if len(pares) < 2 or any(len(p) != 2 for p in pares):
            raise ValueError("Necesito al menos 2 puntos x,y.")
        xs, ys = [p[0] for p in pares], [p[1] for p in pares]
        a, b = minimos_cuadrados(xs, ys)
        ga, gb = gradiente(xs, ys)
        res = [f"Mínimos cuadrados: y = {a:.4g}·x + {b:.4g}  (R² = {r2(xs, ys, a, b):.4f})",
               f"Descenso de gradiente (2000 pasos): y = {ga:.4g}·x + {gb:.4g}"]
        if predecir.strip():
            x = float(predecir)
            res.append(f"Para x = {x:g}: y ≈ {a * x + b:.4g}")
        return "\n".join(res)
    return {"regresion": regresion, "regresión": regresion}
''',
"prueba": [("regresion", "1,2 2,4.1 3,6.2 4,7.9", "y = 1.98·x + 0.1"),
           ("regresion", "1,2 2,4.1 3,6.2 4,7.9", "Descenso de gradiente (2000 pasos): y = 1.98·x + 0.1"),
           ("regresion", "1,2 2,4.1 3,6.2 4,7.9 | 5", "Para x = 5: y ≈ 10")],
},
# =====================================================================================================================
#  BÚSQUEDA, LÓGICA Y ORDENACIÓN
# =====================================================================================================================
{
"id": "n_reinas",
"titulo": "N reinas: vuelta atrás con máscaras de bits y simetrías",
"area": "Búsqueda, lógica y ordenación",
"temas": "reinas ocho reinas vuelta atras backtracking mascaras bits bitmask combinatoria restricciones poda "
         "simetrias tablero ajedrez",
"idea": "Se coloca una reina por fila. Tres números de bits dicen qué columnas y qué diagonales están atacadas; las "
        "casillas libres son ~(columnas | diag1 | diag2) y cada una se prueba sacando su bit más bajo (x & -x). Al "
        "bajar de fila, las diagonales se desplazan un bit. Probar y deshacer al atascarse es la VUELTA ATRÁS. Las "
        "soluciones que solo se diferencian por giros o reflejos se cuentan aparte.",
"complejidad": "exponencial (~O(n!)), pero la poda y los bits la hacen muy rápida hasta n ≈ 12",
"codigo": r'''
def reinas(n):
    todas = (1 << n) - 1
    soluciones = []

    def colocar(cols, d1, d2, pos):
        if len(pos) == n:
            soluciones.append(tuple(pos))
            return
        libres = todas & ~(cols | d1 | d2)
        while libres:
            bit = libres & -libres                   # la primera casilla libre
            libres ^= bit
            pos.append(bit.bit_length() - 1)
            colocar(cols | bit, (d1 | bit) << 1 & todas, (d2 | bit) >> 1, pos)
            pos.pop()                                # deshacer: vuelta atrás
    colocar(0, 0, 0, [])
    return soluciones


def canonica(sol, n):
    variantes, s = [], sol
    for _ in range(4):
        s = tuple(n - 1 - s.index(c) for c in range(n))   # girar 90°
        variantes += [s, tuple(n - 1 - c for c in s)]     # y su reflejo
    return min(variantes)


def registrar():
    def n_reinas(texto):
        t = texto.strip() or "8"
        if not t.isdigit() or not 1 <= int(t) <= 10:
            raise ValueError("Uso: reinas 8 (de 1 a 10)")
        n = int(t)
        sols = reinas(n)
        if not sols:
            return f"Con {n} reinas no hay ninguna solución."
        distintas = len({canonica(s, n) for s in sols})
        tablero = "\n".join(" ".join("♛" if c == s else "·" for c in range(n)) for s in sols[0])
        return f"{n} reinas: {len(sols)} soluciones ({distintas} distintas sin contar giros y reflejos). La primera:\n{tablero}"
    return {"reinas": n_reinas}
''',
"prueba": [("reinas", "8", "8 reinas: 92 soluciones (12 distintas"), ("reinas", "3", "no hay ninguna solución")],
},
{
"id": "sat_dpll",
"titulo": "Resolver lógica: satisfacibilidad (SAT) con DPLL",
"area": "Búsqueda, lógica y ordenación",
"temas": "sat satisfacibilidad logica booleana dpll clausulas cnf propagacion unitaria np completo resolver "
         "restricciones verdad falso formula",
"idea": "¿Hay valores verdadero/falso que cumplan a la vez todas las cláusulas (cada una es un «o» de literales)? "
        "DPLL hace vuelta atrás con dos atajos: la PROPAGACIÓN UNITARIA (si una cláusula solo tiene un literal, ese "
        "valor es obligatorio) y los LITERALES PUROS (si una variable solo aparece en un sentido, se fija así). SAT "
        "fue el primer problema NP-completo (Cook, 1971) y los resolvedores modernos verifican chips y software.",
"complejidad": "exponencial en el peor caso (es NP-completo); en la práctica, muy rápido con buenas heurísticas",
"codigo": r'''
def leer(texto):
    nombres, clausulas = [], []
    for parte in texto.replace("∧", "&").split("&"):
        c = set()
        for lit in parte.replace("(", " ").replace(")", " ").replace("∨", "|").split("|"):
            lit = lit.strip()
            negado = lit[:1] in ("!", "¬", "~", "-")
            nombre = lit.lstrip("!¬~-").strip()
            if not nombre.isidentifier():
                raise ValueError(f"No entiendo «{lit}». Ejemplo: satisfacible (a | b) & (!a | c)")
            if nombre not in nombres:
                nombres.append(nombre)
            c.add(-(nombres.index(nombre) + 1) if negado else nombres.index(nombre) + 1)
        clausulas.append(frozenset(c))
    return nombres, clausulas


def fijar(clausulas, lit):
    res = []
    for c in clausulas:
        if lit in c:
            continue                                 # cláusula ya cumplida
        if -lit in c:
            c = c - {-lit}
            if not c:
                return None                          # cláusula vacía: contradicción
        res.append(c)
    return res


def dpll(clausulas, valores, llamadas):
    llamadas[0] += 1
    while True:                                      # propagación unitaria
        unitaria = next((c for c in clausulas if len(c) == 1), None)
        if unitaria is None:
            break
        lit = next(iter(unitaria))
        valores[abs(lit)] = lit > 0
        clausulas = fijar(clausulas, lit)
        if clausulas is None:
            return None
    literales = {l for c in clausulas for l in c}
    for l in literales:                              # literales puros
        if -l not in literales:
            valores[abs(l)] = l > 0
            clausulas = fijar(clausulas, l)
    if not clausulas:
        return valores
    cuenta = {}
    for c in clausulas:
        for l in c:
            cuenta[abs(l)] = cuenta.get(abs(l), 0) + 1
    v = max(cuenta, key=cuenta.get)                  # la variable que más aparece
    for lit in (v, -v):
        resto = fijar(clausulas, lit)
        if resto is not None:
            r = dpll(resto, {**valores, v: lit > 0}, llamadas)
            if r is not None:
                return r
    return None


def registrar():
    def sat(texto):
        # «satisfacible (a | b) & (!a | c) & (!c | !b)»
        nombres, clausulas = leer(texto)
        if not clausulas or len(nombres) > 60:
            raise ValueError("Uso: satisfacible (a | b) & (!a | c)  (hasta 60 variables)")
        llamadas = [0]
        r = dpll(clausulas, {}, llamadas)
        if r is None:
            return f"No: es insatisfacible, ninguna combinación cumple todo ({llamadas[0]} llamada(s) a DPLL)."
        valores = {i + 1: r.get(i + 1, False) for i in range(len(nombres))}
        cumple = all(any(valores[abs(l)] == (l > 0) for l in c) for c in clausulas)
        texto_val = ", ".join(f"{n} = {'verdad' if valores[i + 1] else 'falso'}" for i, n in enumerate(nombres))
        return f"Sí, se puede cumplir: {texto_val} ({'comprobado' if cumple else 'ERROR'}; {llamadas[0]} llamada(s) a DPLL)."
    return {"satisfacible": sat}
''',
"prueba": [("satisfacible", "(a | b) & (!a | c) & (!c | !b)", "Sí, se puede cumplir"),
           ("satisfacible", "(a | b) & (!a | c) & (!c | !b)", "comprobado"),
           ("satisfacible", "(a) & (!a | b) & (!b)", "No: es insatisfacible")],
},
{
"id": "busqueda_binaria_respuesta",
"titulo": "Búsqueda binaria sobre la respuesta, bisección y método de Newton",
"area": "Técnicas de algoritmos",
"temas": "busqueda binaria respuesta biseccion newton raiz cuadrada minimo maximo capacidad monotono "
         "optimizar aproximar ecuaciones convergencia",
"idea": "Si «¿vale con X?» es monótono (si vale X, vale todo lo mayor), se busca el X mínimo partiendo el intervalo "
        "por la mitad: O(log rango) comprobaciones. Lo mismo para raíces de ecuaciones (bisección, 1 bit de "
        "precisión por paso). Newton usa la derivada: x ← x − f(x)/f'(x) y DUPLICA las cifras correctas en cada paso "
        "(convergencia cuadrática).",
"complejidad": "búsqueda binaria O(log R · coste de comprobar); bisección ~50 pasos; Newton ~5",
"codigo": r'''
def capacidad_minima(pesos, dias):
    def cabe(cap):                                   # ¿se puede enviar todo en 'dias' viajes de capacidad cap?
        viajes, carga = 1, 0
        for p in pesos:
            if carga + p > cap:
                viajes, carga = viajes + 1, 0
            carga += p
        return viajes <= dias
    izq, der, pruebas = max(pesos), sum(pesos), 0
    while izq < der:
        pruebas += 1
        medio = (izq + der) // 2
        if cabe(medio):
            der = medio                              # vale: probamos con menos
        else:
            izq = medio + 1
    return izq, pruebas


def biseccion(n):
    izq, der, pasos = 0.0, max(1.0, n), 0
    while der - izq > 1e-12 * max(1.0, n):
        medio = (izq + der) / 2
        if medio * medio < n:
            izq = medio
        else:
            der = medio
        pasos += 1
    return (izq + der) / 2, pasos


def newton(n):
    x, pasos = max(1.0, n), 0
    while True:
        nuevo = (x + n / x) / 2                      # x - f(x)/f'(x) con f(x) = x² - n
        pasos += 1
        if abs(nuevo - x) <= 1e-15 * nuevo:
            return nuevo, pasos
        x = nuevo


def registrar():
    def capacidad(texto):
        # «capacidad minima 1 2 3 4 5 6 7 8 9 10 | 5»: pesos en orden y número de días
        datos, _, dias = texto.partition("|")
        try:
            pesos, d = [int(x) for x in datos.split()], int(dias)
        except ValueError:
            raise ValueError("Uso: capacidad minima 1 2 3 4 5 6 7 8 9 10 | 5")
        if not pesos or d < 1 or min(pesos) < 1:
            raise ValueError("Uso: capacidad minima 1 2 3 4 5 6 7 8 9 10 | 5")
        cap, pruebas = capacidad_minima(pesos, d)
        return (f"Capacidad mínima: {cap} (búsqueda binaria entre {max(pesos)} y {sum(pesos)}: {pruebas} pruebas, "
                f"en vez de probar los {sum(pesos) - max(pesos) + 1} valores uno a uno)")

    def raiz(texto):
        try:
            n = float(texto.replace(",", "."))
        except ValueError:
            raise ValueError("Uso: raiz 2")
        if n < 0:
            raise ValueError("Sin números negativos (su raíz no es real).")
        if n == 0:
            return "La raíz de 0 es 0."
        b, pb = biseccion(n)
        nw, pn = newton(n)
        return f"Bisección: {b:.12g} en {pb} pasos\nNewton: {nw:.12g} en {pn} pasos"
    return {"capacidad minima": capacidad, "capacidad mínima": capacidad, "raiz": raiz, "raíz": raiz}
''',
"prueba": [("capacidad minima", "1 2 3 4 5 6 7 8 9 10 | 5", "Capacidad mínima: 15"), ("raiz", "2", "Newton: 1.41421356237")],
},
{
"id": "ordenaciones",
"titulo": "Algoritmos de ordenación comparados: inserción, mezcla, rápida, montículo y radix",
"area": "Búsqueda, lógica y ordenación",
"temas": "ordenar ordenacion sort algoritmos merge sort mezcla quicksort rapida heapsort monticulo radix "
         "insercion comparaciones estable timsort complejidad lista numeros datos",
"idea": "Inserción es O(n²) pero buenísima en listas cortas o casi ordenadas. Mezcla (merge sort) divide y vence: "
        "O(n log n) siempre y estable. Rápida (quicksort) parte por un pivote al azar: O(n log n) de media y muy "
        "rápida en la práctica. Montículo: O(n log n) sin memoria extra. Radix no compara: reparte por dígitos, "
        "O(n·d). Ninguna ordenación por comparaciones baja de ~n·log₂ n comparaciones. Python usa Timsort (mezcla + "
        "inserción, aprovecha los tramos ya ordenados).",
"complejidad": "inserción O(n²); mezcla, montículo O(n log n); rápida O(n log n) de media; radix O(n·d)",
"codigo": r'''
import math
import random


def insercion(a, c):
    a = a[:]
    for i in range(1, len(a)):
        x, j = a[i], i - 1
        while j >= 0:
            c[0] += 1
            if a[j] <= x:
                break
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = x
    return a


def mezcla(a, c):
    if len(a) <= 1:
        return a
    m = len(a) // 2
    izq, der = mezcla(a[:m], c), mezcla(a[m:], c)
    res, i, j = [], 0, 0
    while i < len(izq) and j < len(der):
        c[0] += 1
        if izq[i] <= der[j]:                         # <= la hace estable
            res.append(izq[i])
            i += 1
        else:
            res.append(der[j])
            j += 1
    return res + izq[i:] + der[j:]


def rapida(a, c, rnd):
    if len(a) <= 1:
        return a
    pivote = rnd.choice(a)                           # pivote al azar: evita el peor caso con datos ordenados
    menores, iguales, mayores = [], [], []
    for x in a:
        c[0] += 1
        (menores if x < pivote else mayores if x > pivote else iguales).append(x)
    return rapida(menores, c, rnd) + iguales + rapida(mayores, c, rnd)


def monticulo(a, c):
    a, n = a[:], len(a)

    def hundir(i, fin):
        while 2 * i + 1 < fin:
            h = 2 * i + 1
            if h + 1 < fin:
                c[0] += 1
                if a[h + 1] > a[h]:
                    h += 1
            c[0] += 1
            if a[i] >= a[h]:
                return
            a[i], a[h] = a[h], a[i]
            i = h
    for i in range(n // 2 - 1, -1, -1):              # montículo de máximos en O(n)
        hundir(i, n)
    for fin in range(n - 1, 0, -1):
        a[0], a[fin] = a[fin], a[0]
        hundir(0, fin)
    return a


def radix(a):
    a, exp = a[:], 1
    while a and max(a) // exp > 0:
        cubos = [[] for _ in range(10)]
        for x in a:
            cubos[x // exp % 10].append(x)           # reparte por el dígito actual, sin comparar
        a = [x for cubo in cubos for x in cubo]
        exp *= 10
    return a


def registrar():
    def ordena(texto):
        # «ordena 5 3 8 1 9 2»   o   «ordena aleatorio 1000»
        t = texto.lower().split()
        rnd = random.Random(1)
        if t[:1] == ["aleatorio"]:
            n = int(t[1]) if len(t) > 1 and t[1].isdigit() else 1000
            datos = [rnd.randrange(100000) for _ in range(min(n, 5000))]
        else:
            try:
                datos = [int(x) for x in t]
            except ValueError:
                raise ValueError("Uso: ordena 5 3 8 1 9 2   o   ordena aleatorio 1000 (enteros)")
        if not datos or len(datos) > 5000:
            raise ValueError("Entre 1 y 5000 números.")
        bien, n = sorted(datos), len(datos)
        lineas, resultados = [], []
        pruebas = [("Mezcla", lambda c: mezcla(datos, c)), ("Rápida", lambda c: rapida(datos, c, rnd)),
                   ("Montículo", lambda c: monticulo(datos, c))]
        if n <= 2000:
            pruebas.insert(0, ("Inserción", lambda c: insercion(datos, c)))
        for nombre, f in pruebas:
            c = [0]
            r = f(c)
            resultados.append(r)
            lineas.append(f"{nombre}: {c[0]} comparaciones")
        if min(datos) >= 0:
            resultados.append(radix(datos))
            lineas.append("Radix: 0 comparaciones (reparte por dígitos)")
        cota = math.ceil(math.log2(math.factorial(n))) if n <= 1000 else round(n * math.log2(n) - 1.44 * n)
        muestra = " ".join(map(str, bien[:20])) + (" …" if n > 20 else "")
        ok = all(r == bien for r in resultados)
        return (f"Resultado: {muestra}\n" + "\n".join(lineas) +
                f"\nMínimo teórico al comparar: ~{cota} comparaciones (log₂ n!)\n"
                f"{'Todos coinciden con sorted()' if ok else 'ERROR: alguno no coincide'}")
    return {"ordena": ordena}
''',
"prueba": [("ordena", "5 3 8 1 9 2", "Resultado: 1 2 3 5 8 9"), ("ordena", "aleatorio 500", "Todos coinciden con sorted()")],
},
]


# =====================================================================================================================
#  CONCEPTOS: teoría de ingeniería informática (texto que Kira guarda en su baúl con «estudia ingeniería»)
# =====================================================================================================================
CONCEPTOS = [
# ---------- algoritmia y teoría ----------
{"id": "notacion_o", "area": "Algoritmia", "titulo": "Notación O grande y clases de complejidad",
 "temas": "complejidad notacion o grande big o eficiencia crecimiento tiempo memoria",
 "texto": "La notación O describe cómo CRECE el coste de un algoritmo cuando crecen los datos, ignorando constantes. "
          "De mejor a peor: O(1) constante (leer una posición de una lista, un diccionario), O(log n) logarítmica "
          "(búsqueda binaria: 20 pasos para un millón), O(n) lineal (recorrer una vez), O(n log n) (buenas "
          "ordenaciones), O(n²) cuadrática (dos bucles anidados: con 100.000 datos ya son 10.000 millones de pasos), "
          "O(2ⁿ) y O(n!) exponenciales (probar todas las combinaciones: inviables a partir de 30-40 o de 12-15 "
          "elementos). Ω es la cota inferior y Θ la exacta. También se mide la memoria. Ojo: con pocos datos, las "
          "constantes importan más que la O; hay que medir."},
{"id": "amortizado", "area": "Algoritmia", "titulo": "Análisis amortizado",
 "temas": "amortizado coste medio lista dinamica append redimensionar tabla hash crecer",
 "texto": "El coste amortizado es la media por operación en el PEOR caso de una secuencia larga. Ejemplo: una lista "
          "de Python (array dinámico) a veces tiene que copiarse entera a un espacio mayor al hacer append, pero "
          "como crece multiplicando su tamaño, esas copias se reparten y cada append cuesta O(1) amortizado. Igual "
          "con las tablas hash que se agrandan al llenarse. No es lo mismo que el caso medio (que depende de los "
          "datos de entrada): el amortizado es una garantía sobre cualquier secuencia."},
{"id": "divide_y_venceras", "area": "Algoritmia", "titulo": "Divide y vencerás y el teorema maestro",
 "temas": "divide venceras recursion recurrencia teorema maestro merge sort subproblemas",
 "texto": "Divide y vencerás parte el problema en trozos más pequeños del mismo tipo, los resuelve (recursivamente) "
          "y combina las respuestas: ordenación por mezcla, quicksort, búsqueda binaria, FFT, multiplicación de "
          "Karatsuba. Su coste se escribe como T(n) = a·T(n/b) + f(n) y el teorema maestro lo resuelve comparando "
          "f(n) con n^(log_b a): por ejemplo, mezcla es T(n) = 2T(n/2) + O(n), que da O(n log n); la búsqueda "
          "binaria, T(n) = T(n/2) + O(1), da O(log n)."},
{"id": "p_np", "area": "Algoritmia", "titulo": "P, NP y problemas NP-completos",
 "temas": "p np np completo np dificil reduccion cook sat viajante intratable aproximacion heuristica",
 "texto": "P son los problemas que se RESUELVEN en tiempo polinómico; NP, los que tienen soluciones que se "
          "COMPRUEBAN en tiempo polinómico. Un problema es NP-completo si está en NP y cualquier otro de NP se "
          "reduce a él: SAT (el primero, Cook 1971), el viajante (versión de decisión), la mochila, colorear grafos, "
          "el sudoku generalizado. Nadie sabe si P = NP (es uno de los problemas del milenio). En la práctica, ante "
          "un problema NP-difícil: casos pequeños exactos (vuelta atrás, programación dinámica), aproximaciones con "
          "garantía, heurísticas (voraz, recocido simulado, genéticos) o resolvedores SAT/ILP."},
{"id": "elegir_tecnica", "area": "Algoritmia", "titulo": "Cómo elegir técnica: voraz, programación dinámica, vuelta atrás",
 "temas": "elegir tecnica voraz greedy programacion dinamica vuelta atras backtracking subestructura optima",
 "texto": "VORAZ: decidir lo mejor ahora y no volver atrás; solo es correcto si se puede demostrar (Dijkstra, Kruskal, "
          "Huffman, planificar por fin más temprano). PROGRAMACIÓN DINÁMICA: cuando hay subestructura óptima y "
          "subproblemas que se repiten; se guarda cada respuesta (memoización de arriba abajo o tabla de abajo "
          "arriba): mochila, distancia de edición, caminos. VUELTA ATRÁS: explorar opciones y deshacer al "
          "atascarse, con poda (sudoku, N reinas, SAT). DIVIDE Y VENCERÁS: subproblemas independientes. Pista: si "
          "el voraz falla con un contraejemplo pequeño, prueba DP; si el estado es enorme, busca poda o heurística."},
{"id": "tablas_hash", "area": "Algoritmia", "titulo": "Tablas hash: cómo funcionan los diccionarios",
 "temas": "tabla hash diccionario dict set funcion hash colision factor carga direccionamiento abierto",
 "texto": "Una función hash convierte la clave en un número que indica la casilla de una tabla: buscar, insertar y "
          "borrar cuestan O(1) de media. Dos claves pueden caer en la misma casilla (colisión): se resuelve con "
          "listas en cada casilla (encadenamiento) o buscando otra casilla libre (direccionamiento abierto, lo que "
          "usa el dict de Python). Cuando el factor de carga (ocupadas/total) sube, la tabla se agranda y se "
          "redistribuye (O(1) amortizado). Las claves deben ser inmutables y, si son iguales, tener el mismo hash. "
          "Python aleatoriza el hash de los textos en cada arranque para evitar ataques que provocan colisiones."},
{"id": "grafos_cual", "area": "Algoritmia", "titulo": "Qué algoritmo de grafos usar",
 "temas": "grafos grafo algoritmo elegir bfs dfs dijkstra bellman ford a estrella floyd kruskal prim topologico flujo",
 "texto": "Camino más corto sin pesos: BFS, O(V+E). Con pesos no negativos: Dijkstra; si hay una buena estimación "
          "de la distancia restante (mapas), A*. Con pesos negativos: Bellman-Ford (detecta ciclos negativos). "
          "Todos los pares en grafos pequeños: Floyd-Warshall O(V³). Conectar todo al menor coste: Kruskal o Prim. "
          "Orden de tareas con dependencias: orden topológico (Kahn o DFS). Grupos conectados: Union-Find o "
          "BFS/DFS; en dirigidos, componentes fuertes con Tarjan o Kosaraju. Capacidades y cuellos de botella: "
          "flujo máximo (Edmonds-Karp, Dinic). Representación: listas de adyacencia para grafos dispersos y "
          "matriz para densos."},
{"id": "probabilisticas", "area": "Algoritmia", "titulo": "Estructuras de datos probabilísticas",
 "temas": "probabilistico bloom hyperloglog count min sketch skip list aproximado memoria grandes datos",
 "texto": "Cuando los datos son enormes se cambia exactitud por memoria. Filtro de Bloom: ¿lo he visto? sin falsos "
          "negativos. HyperLogLog: cuenta elementos DISTINTOS de miles de millones con unos pocos KB y ~1 % de error "
          "(mira el máximo número de ceros iniciales de los hashes). Count-Min Sketch: cuenta frecuencias "
          "aproximadas (los temas más repetidos) con una matriz de contadores. Skip list: lista enlazada con "
          "«atajos» aleatorios que da búsquedas O(log n) esperadas (la usa Redis). MinHash: estima cuánto se "
          "parecen dos conjuntos (detectar duplicados)."},
{"id": "computabilidad", "area": "Algoritmia", "titulo": "Computabilidad: máquinas de Turing y el problema de la parada",
 "temas": "computabilidad turing maquina problema parada decidible indecidible church lenguajes formales automatas",
 "texto": "Una máquina de Turing (una cinta infinita, un cabezal y una tabla de reglas) puede calcular todo lo que "
          "calcula cualquier ordenador (tesis de Church-Turing). Pero hay problemas que NINGÚN programa resuelve: "
          "Turing demostró en 1936 que no existe un programa que diga, para cualquier programa y entrada, si "
          "terminará (problema de la parada). Por eso ningún antivirus ni analizador puede ser perfecto y Kira corta "
          "los programas por tiempo. Jerarquía de Chomsky: lenguajes regulares (autómatas finitos, expresiones "
          "regulares), libres de contexto (autómatas de pila, la sintaxis de los lenguajes de programación) y "
          "recursivamente enumerables (máquinas de Turing)."},
# ---------- arquitectura de computadores ----------
{"id": "jerarquia_memoria", "area": "Arquitectura de computadores", "titulo": "Jerarquía de memoria y localidad",
 "temas": "cache memoria jerarquia l1 l2 l3 ram disco latencia localidad espacial temporal rendimiento",
 "texto": "Cuanto más cerca de la CPU, más rápida y pequeña es la memoria: registros; caché L1 (~1 ns, decenas de "
          "KB); L2 (~4 ns); L3 (~10-40 ns, varios MB); RAM (~100 ns, GB); SSD (decenas de µs); disco duro (~10 ms); "
          "red (de ms en adelante). La caché trae bloques de 64 bytes (líneas), así que acceder a datos CONTIGUOS es "
          "mucho más rápido (localidad espacial) y repetir accesos recientes también (localidad temporal). Por eso "
          "recorrer una matriz por filas en C es más rápido que por columnas, y un array compacto gana a una lista "
          "enlazada aunque ambos sean O(n)."},
{"id": "cpu", "area": "Arquitectura de computadores", "titulo": "Cómo ejecuta la CPU: segmentación, saltos, SIMD",
 "temas": "cpu procesador pipeline segmentacion prediccion saltos fuera orden simd neon arm x86 nucleos dotprod",
 "texto": "La CPU trabaja en cadena (pipeline): mientras una instrucción se ejecuta, la siguiente se decodifica y "
          "otra se lee. Un salto condicional rompería la cadena, así que el procesador PREDICE hacia dónde irá; si "
          "falla, tira trabajo (por eso los datos ordenados a veces se procesan más rápido). Ejecuta fuera de orden "
          "lo que no depende entre sí. SIMD hace la misma operación sobre varios datos a la vez (NEON en ARM, AVX en "
          "x86): es lo que acelera la IA en el móvil (la extensión dotprod de ARMv8.2 multiplica y suma bytes en "
          "bloque; por eso Kira trae un cerebro rápido y otro genérico). ARM (móviles) prima la eficiencia; x86 "
          "(PC), la compatibilidad."},
{"id": "numeros_binarios", "area": "Arquitectura de computadores", "titulo": "Números en el ordenador: complemento a dos y coma flotante",
 "temas": "binario complemento dos desbordamiento coma flotante ieee 754 decimal precision redondeo float",
 "texto": "Los enteros con signo se guardan en complemento a dos: con 8 bits van de -128 a 127, y sumar 1 a 127 da "
          "-128 (desbordamiento); Python evita esto con enteros de tamaño ilimitado. Los decimales usan coma "
          "flotante IEEE 754 (signo, exponente y mantisa; un double tiene 53 bits de mantisa, ~15-17 cifras). 0,1 no "
          "tiene representación exacta en binario, por eso 0.1 + 0.2 da 0.30000000000000004: nunca compares floats "
          "con ==, usa math.isclose. Para dinero usa decimal.Decimal o céntimos enteros; para fracciones exactas, "
          "fractions.Fraction. También existen inf, -inf y nan (nan no es igual ni a sí mismo)."},
{"id": "unicode", "area": "Arquitectura de computadores", "titulo": "Texto: Unicode y UTF-8",
 "temas": "unicode utf8 utf-8 codificacion caracteres bytes acentos emoji normalizacion nfc nfd ascii",
 "texto": "Unicode da un número (punto de código) a cada carácter de todos los idiomas: «ñ» es U+00F1. UTF-8 lo "
          "guarda en 1 a 4 bytes: lo ASCII ocupa 1 (compatible), los acentos 2, los emojis 4. En Python, str son "
          "puntos de código y bytes son bytes: hay que decodificar al leer y codificar al escribir, siempre "
          "indicando encoding='utf-8'. Un mismo texto visible puede escribirse de dos formas («é» de una pieza o «e» "
          "+ tilde combinada): unicodedata.normalize('NFC', t) las iguala (Kira usa NFD para quitar acentos al "
          "buscar). Cortar bytes UTF-8 por la mitad rompe caracteres."},
# ---------- sistemas operativos ----------
{"id": "procesos_hilos", "area": "Sistemas operativos", "titulo": "Procesos, hilos, el GIL y asincronía",
 "temas": "proceso hilo thread gil python concurrencia paralelismo multiprocessing asyncio cambio contexto",
 "texto": "Un PROCESO tiene su propia memoria; sus HILOS la comparten (más ligeros, pero hay que sincronizarlos). "
          "Concurrencia es avanzar en varias tareas intercalándolas; paralelismo, ejecutarlas a la vez en varios "
          "núcleos. En CPython el GIL deja que solo un hilo ejecute código Python a la vez: los hilos sirven para "
          "esperar (red, disco, interfaz), no para calcular más rápido; para cálculo en paralelo, multiprocessing o "
          "librerías en C que sueltan el GIL (Python 3.13 trae una versión experimental sin GIL). asyncio reparte un "
          "solo hilo entre miles de tareas que esperan, con async/await. Cambiar de contexto entre hilos cuesta "
          "microsegundos: no crees un hilo por cada cosita, usa una piscina (ThreadPoolExecutor)."},
{"id": "sincronizacion", "area": "Sistemas operativos", "titulo": "Sincronización: carreras, cerrojos e interbloqueos",
 "temas": "condicion carrera race mutex lock cerrojo semaforo condicion atomico interbloqueo deadlock inanicion",
 "texto": "Una condición de CARRERA ocurre cuando el resultado depende de cómo se intercalan los hilos (dos hilos "
          "haciendo x += 1 pueden perder sumas). Se protege la sección crítica con un cerrojo (Lock, mutex); un "
          "semáforo deja pasar a N a la vez; una variable de condición permite esperar a que algo cambie sin gastar "
          "CPU (siempre comprobando en un while). Interbloqueo: hilos esperándose en círculo; requiere las 4 "
          "condiciones de Coffman (exclusión mutua, retener y esperar, sin expulsión, espera circular) y se evita "
          "cogiendo los cerrojos siempre en el mismo orden o con tiempos de espera. Inanición: alguien nunca consigue "
          "turno. Lo más seguro: compartir lo mínimo y pasar mensajes por colas (queue.Queue)."},
{"id": "memoria_virtual", "area": "Sistemas operativos", "titulo": "Memoria virtual y paginación",
 "temas": "memoria virtual paginacion pagina marco tlb fallo pagina swap mmap proteccion direcciones",
 "texto": "Cada proceso ve su propio espacio de direcciones VIRTUAL; el sistema lo traduce a memoria física por "
          "páginas (normalmente de 4 KB) usando tablas de páginas, y la TLB guarda las traducciones recientes. Si "
          "una página no está en RAM, salta un fallo de página y el sistema la trae (de disco o de swap), lo que es "
          "miles de veces más lento. Ventajas: aislamiento (un proceso no puede tocar la memoria de otro), "
          "protección (páginas de solo lectura o no ejecutables), compartir librerías y mapear archivos (mmap). "
          "Android, con poca memoria, mata las apps en segundo plano en vez de usar mucho swap."},
{"id": "gestion_memoria", "area": "Sistemas operativos", "titulo": "Pila, montículo y recolección de basura",
 "temas": "pila stack heap monticulo memoria recoleccion basura garbage collector conteo referencias fuga",
 "texto": "La PILA guarda las variables locales y las llamadas (rápida, se libera sola al volver de la función; una "
          "recursión demasiado honda la desborda). El MONTÍCULO (heap) guarda lo que vive más tiempo; en C se "
          "libera a mano (errores: fugas y usar memoria ya liberada), en Rust lo decide el compilador con la "
          "propiedad, y en Python, Java o Go lo hace un recolector de basura. CPython cuenta referencias (libera en "
          "cuanto un objeto deja de usarse) y añade un recolector generacional para ciclos. Fugas típicas en "
          "Python: cachés y listas globales que solo crecen; se investigan con tracemalloc."},
{"id": "archivos", "area": "Sistemas operativos", "titulo": "Sistemas de archivos y escrituras seguras",
 "temas": "sistema archivos inodo journaling fsync escritura atomica renombrar replace corrupcion disco",
 "texto": "Un sistema de archivos organiza bloques del disco: los inodos guardan los datos de cada archivo y los "
          "directorios asocian nombres a inodos. El journaling apunta las operaciones antes de hacerlas para "
          "recuperarse de un apagón. Si un programa se corta a mitad de escribir, el archivo queda roto: la técnica "
          "segura es escribir en un temporal y luego RENOMBRAR (os.replace), que es atómico; así lo hace Kira con sus "
          "datos. write() no garantiza que esté en el disco: f.flush() + os.fsync() fuerzan a guardarlo. Rutas: "
          "nunca construyas rutas con texto del usuario sin validarlo (ataques de «../»)."},
{"id": "asincronia", "area": "Sistemas operativos", "titulo": "Bucle de eventos, corrutinas y async/await",
 "temas": "asincrono async await event loop bucle eventos corrutina callback promesa futuro no bloqueante",
 "texto": "Un bucle de eventos va atendiendo tareas que están listas; cuando una tiene que esperar (red, "
          "temporizador), cede el turno con await y el bucle sigue con otra. Así un solo hilo maneja miles de "
          "conexiones (Node.js, asyncio, Kivy con su Clock). Regla de oro: nunca bloquees el bucle con trabajo "
          "largo o esperas síncronas (time.sleep, peticiones sin await): todo se congela (en una app, la pantalla). "
          "El trabajo pesado va a un hilo o proceso y su resultado vuelve al bucle (en Kivy, con Clock.schedule_once "
          "desde el hilo principal)."},
# ---------- redes ----------
{"id": "capas_red", "area": "Redes", "titulo": "El modelo de capas de Internet (TCP/IP)",
 "temas": "red capas tcp ip osi enlace internet transporte aplicacion encapsular paquete router",
 "texto": "Cada capa usa la de abajo sin saber cómo funciona: ENLACE (WiFi, Ethernet: entre aparatos vecinos, "
          "direcciones MAC); RED (IP: direcciones y routers que reenvían paquetes por el mejor camino, sin "
          "garantías); TRANSPORTE (TCP fiable u UDP rápido, con puertos para distinguir programas); APLICACIÓN (HTTP, "
          "DNS, TLS…). Al enviar, cada capa ENCAPSULA lo de arriba con su cabecera. El modelo OSI tiene 7 capas pero "
          "Internet usa estas 4-5. NAT permite que muchos aparatos de casa compartan una IP pública; IPv6 sobra en "
          "direcciones."},
{"id": "tcp_udp", "area": "Redes", "titulo": "TCP y UDP: fiabilidad frente a rapidez",
 "temas": "tcp udp handshake fiable congestion control flujo quic http3 puertos retransmision latencia",
 "texto": "TCP da un flujo de bytes FIABLE y ordenado: conexión con saludo en tres pasos (SYN, SYN-ACK, ACK), "
          "números de secuencia, confirmaciones y reenvío de lo perdido, control de flujo (no saturar al receptor) y "
          "de congestión (baja el ritmo si la red se satura). UDP solo envía datagramas, sin garantías ni orden, "
          "pero sin esperas: va mejor para voz, vídeo en directo, juegos y DNS. QUIC (base de HTTP/3) monta encima de "
          "UDP algo fiable, cifrado y que no se bloquea entero si se pierde un paquete. Latencia (tiempo de ida) y "
          "ancho de banda (cantidad por segundo) son cosas distintas."},
{"id": "http", "area": "Redes", "titulo": "HTTP, APIs REST e idempotencia",
 "temas": "http https api rest get post put delete codigos estado 200 404 500 idempotente cabeceras json",
 "texto": "HTTP es pedir y responder: un método (GET leer, POST crear o actuar, PUT reemplazar, PATCH modificar, "
          "DELETE borrar), una ruta, cabeceras y un cuerpo (a menudo JSON). Códigos: 2xx bien, 3xx redirección, 4xx "
          "error del cliente (400 petición mala, 401 sin identificar, 403 prohibido, 404 no existe, 429 demasiadas "
          "peticiones), 5xx error del servidor. GET, PUT y DELETE deben ser IDEMPOTENTES (repetirlos no cambia más "
          "el resultado), así se pueden reintentar con seguridad; para POST se usan claves de idempotencia. REST "
          "organiza la API en recursos con URLs; la API de Claude que usa Kira es HTTP + JSON con eventos SSE para la "
          "respuesta por trozos."},
{"id": "tls", "area": "Redes", "titulo": "HTTPS y TLS: cifrado y certificados",
 "temas": "tls ssl https certificado autoridad cadena confianza cifrado handshake ecdhe secreto perfecto",
 "texto": "TLS protege la conexión en tres sentidos: confidencialidad (cifrado), integridad (nadie lo altera) y "
          "autenticidad (hablas con quien dices). En el saludo, cliente y servidor acuerdan una clave con "
          "Diffie-Hellman de curva elíptica (ECDHE, que da secreto perfecto hacia delante: robar la clave del "
          "servidor mañana no descifra lo de hoy) y el servidor demuestra su identidad con un CERTIFICADO firmado por "
          "una autoridad en la que el sistema confía; después todo va con cifrado simétrico (AES-GCM o ChaCha20). "
          "Nunca desactives la verificación de certificados: Kira usa los de certifi en Android para comprobarlos "
          "siempre."},
{"id": "dns", "area": "Redes", "titulo": "DNS: de nombres a direcciones",
 "temas": "dns nombres dominio resolver ip ttl cache registro servidor raiz",
 "texto": "DNS traduce nombres (es.wikipedia.org) a direcciones IP. El resolvedor pregunta, de arriba abajo, a los "
          "servidores raíz, a los del dominio de primer nivel (.org) y al autoritativo del dominio, y guarda la "
          "respuesta en caché el tiempo que diga su TTL. Registros: A (IPv4), AAAA (IPv6), CNAME (alias), MX "
          "(correo), TXT (verificaciones). Si una web «no carga» pero la IP responde, a menudo es DNS. DNS sobre "
          "HTTPS (DoH) cifra las consultas."},
# ---------- bases de datos ----------
{"id": "acid", "area": "Bases de datos", "titulo": "Transacciones ACID y niveles de aislamiento",
 "temas": "acid transaccion atomicidad consistencia aislamiento durabilidad commit rollback sqlite aislamiento",
 "texto": "Una transacción agrupa operaciones con cuatro garantías: Atomicidad (todo o nada, con rollback si "
          "falla), Consistencia (se respetan las reglas: claves, restricciones), aIslamiento (las transacciones "
          "simultáneas no se pisan) y Durabilidad (lo confirmado sobrevive a un apagón; de ahí el registro de "
          "escritura anticipada, WAL). El aislamiento tiene niveles: lectura no confirmada, lectura confirmada, "
          "lectura repetible y serializable; los bajos son más rápidos pero permiten anomalías (lecturas sucias, no "
          "repetibles, fantasmas). SQLite, la base de datos de los móviles, es ACID y serializable."},
{"id": "indices", "area": "Bases de datos", "titulo": "Índices: por qué una consulta es lenta",
 "temas": "indice indices base datos consulta lenta b+ explain sql where order by escaneo completo",
 "texto": "Sin índice, buscar en una tabla es recorrerla entera (O(n)). Un índice (normalmente un árbol B+) sobre "
          "una columna permite encontrar filas en O(log n) y recorrerlas ya ordenadas. Ayuda en WHERE, JOIN y ORDER "
          "BY sobre esa columna; no sirve si se aplica una función a la columna o se busca con LIKE '%texto'. Los "
          "índices compuestos funcionan de izquierda a derecha. Tienen coste: ocupan espacio y hacen más lentas "
          "las escrituras. Para saber qué hace la base de datos: EXPLAIN QUERY PLAN (SQLite) o EXPLAIN. Y siempre "
          "consultas con parámetros (?), nunca pegando texto: evita la inyección SQL."},
{"id": "normalizacion", "area": "Bases de datos", "titulo": "Diseño relacional: normalización",
 "temas": "normalizacion formas normales relacional tablas claves primaria foranea redundancia diseno",
 "texto": "Normalizar es repartir los datos en tablas para que cada dato esté en UN solo sitio y no haya "
          "contradicciones: 1FN (valores atómicos, sin listas en una celda), 2FN (cada columna depende de toda la "
          "clave), 3FN (no depende de otras columnas que no son clave). Las relaciones se hacen con claves foráneas "
          "y se juntan con JOIN. A veces se desnormaliza a propósito (copiar un dato) para leer más rápido, "
          "aceptando mantener las copias al día. Cada tabla, con su clave primaria."},
{"id": "cap_nosql", "area": "Bases de datos", "titulo": "NoSQL, teorema CAP y consistencia eventual",
 "temas": "nosql cap teorema consistencia disponibilidad particion eventual documentos clave valor grafos pacelc",
 "texto": "Las bases NoSQL cambian el modelo de tablas por documentos (MongoDB), clave-valor (Redis), columnas anchas "
          "(Cassandra) o grafos (Neo4j), para escalar o encajar mejor con los datos. El teorema CAP dice que un "
          "sistema distribuido, cuando la red se PARTE, debe elegir entre Consistencia (todos ven lo mismo) y "
          "Disponibilidad (todos responden). PACELC añade que, aun sin fallos, se elige entre latencia y "
          "consistencia. Consistencia eventual: las réplicas acaban coincidiendo si dejan de llegar cambios; los "
          "CRDT son estructuras que se fusionan sin conflictos (edición colaborativa)."},
# ---------- sistemas distribuidos ----------
{"id": "consenso", "area": "Sistemas distribuidos", "titulo": "Consenso: Raft y Paxos",
 "temas": "consenso raft paxos lider eleccion replica log mayoria quorum tolerancia fallos distribuido",
 "texto": "Consenso es lograr que varias máquinas se pongan de acuerdo en una secuencia de decisiones aunque algunas "
          "fallen. Raft (2014) lo hace entendible: se elige un LÍDER por votación (con términos numerados y tiempos "
          "de espera al azar); el líder añade cada operación a su registro y la da por confirmada cuando la tiene "
          "una MAYORÍA. Con 2f+1 máquinas se toleran f caídas. Paxos es el clásico equivalente. Lo usan etcd, "
          "Consul, CockroachDB y Kubernetes. Si los nodos pueden mentir (fallos bizantinos) hacen falta 3f+1 y otros "
          "algoritmos (PBFT, cadenas de bloques)."},
{"id": "escalabilidad", "area": "Sistemas distribuidos", "titulo": "Escalar un servicio: caché, réplicas, particiones y colas",
 "temas": "escalabilidad escalar horizontal vertical balanceo carga cache replicas sharding colas mensajes reintentos",
 "texto": "Escalar en vertical es una máquina más grande; en horizontal, más máquinas tras un balanceador de carga "
          "(requiere servidores sin estado). Para leer más: caché (Redis, CDN) y réplicas de lectura. Para escribir "
          "más: particionar los datos (sharding, con hash consistente). Para picos y tareas lentas: colas de mensajes "
          "(el trabajo se hace en segundo plano). Todo falla a veces: tiempos de espera en cada llamada, reintentos "
          "con espera exponencial y algo de azar (jitter), operaciones idempotentes, limitadores de peticiones y "
          "cortacircuitos (circuit breaker) para no hundir a un servicio que ya va mal."},
{"id": "falacias", "area": "Sistemas distribuidos", "titulo": "Las falacias de la computación distribuida",
 "temas": "falacias distribuido red fiable latencia cero tiempo espera timeout fallos parciales",
 "texto": "Ocho suposiciones falsas que causan errores (Deutsch y otros, Sun): la red es fiable; la latencia es "
          "cero; el ancho de banda es infinito; la red es segura; la topología no cambia; hay un solo "
          "administrador; el transporte no cuesta; la red es homogénea. Consecuencias prácticas: toda llamada por "
          "red puede tardar o fallar A MEDIAS (¿se hizo o no?), así que hay que poner tiempos de espera, diseñar "
          "para reintentar sin duplicar, cifrar, y no fiarse de los relojes de distintas máquinas (relojes lógicos)."},
# ---------- compiladores y lenguajes ----------
{"id": "fases_compilador", "area": "Compiladores y lenguajes", "titulo": "Fases de un compilador e intérprete",
 "temas": "compilador fases lexico sintactico semantico ast representacion intermedia optimizacion jit bytecode dis",
 "texto": "1) Análisis LÉXICO: texto a fichas (tokens). 2) SINTÁCTICO: fichas a árbol de sintaxis según la "
          "gramática (descenso recursivo, LR). 3) SEMÁNTICO: tipos, nombres declarados, ámbitos. 4) Representación "
          "INTERMEDIA (a menudo SSA). 5) OPTIMIZACIÓN: plegado de constantes, eliminar código muerto, sacar cálculos "
          "de los bucles, poner funciones en línea. 6) GENERACIÓN de código máquina o bytecode. Un intérprete "
          "ejecuta el árbol o el bytecode directamente; un JIT compila en marcha lo que más se usa (Java, "
          "JavaScript, PyPy). CPython compila a bytecode (míralo con import dis; dis.dis(funcion)) y lo ejecuta en "
          "una máquina de pila."},
{"id": "tipos", "area": "Compiladores y lenguajes", "titulo": "Sistemas de tipos",
 "temas": "tipos tipado estatico dinamico fuerte debil inferencia genericos anotaciones mypy type hints",
 "texto": "Tipado ESTÁTICO: los tipos se comprueban antes de ejecutar (C, Java, Rust, TypeScript); DINÁMICO: al "
          "ejecutar (Python, JavaScript). FUERTE: no mezcla tipos a escondidas (Python: '1' + 1 da error); DÉBIL: "
          "convierte solo (JavaScript: '1' + 1 = '11'). La inferencia deduce tipos sin escribirlos. Los genéricos "
          "permiten código para cualquier tipo (list[int]). En Python, las anotaciones (def f(x: int) -> str) no "
          "cambian la ejecución pero herramientas como mypy encuentran errores antes de ejecutar, y documentan."},
{"id": "paradigmas", "area": "Compiladores y lenguajes", "titulo": "Paradigmas: imperativo, orientado a objetos y funcional",
 "temas": "paradigma funcional orientado objetos imperativo inmutable funcion pura orden superior cierre closure",
 "texto": "Imperativo: órdenes que cambian el estado paso a paso. Orientado a objetos: datos y comportamiento "
          "juntos en objetos, con encapsulación, herencia y polimorfismo (mejor composición que herencias "
          "profundas). Funcional: funciones PURAS (mismo resultado para la misma entrada, sin efectos secundarios), "
          "datos inmutables y funciones de orden superior (map, filter, reduce, funciones que devuelven funciones; "
          "los cierres recuerdan las variables de donde nacieron). Lo puro es fácil de probar y de paralelizar. "
          "Lógico/declarativo: describes qué quieres (SQL, Prolog, expresiones regulares). Python mezcla los tres "
          "primeros."},
# ---------- ingeniería de software ----------
{"id": "solid", "area": "Ingeniería de software", "titulo": "Principios SOLID",
 "temas": "solid principios diseno responsabilidad unica abierto cerrado liskov interfaces dependencias",
 "texto": "S, responsabilidad única: un módulo, un motivo para cambiar. O, abierto/cerrado: ampliar sin modificar "
          "lo que ya funciona (como los módulos de mejora de Kira, que se añaden sin tocar el núcleo). L, "
          "sustitución de Liskov: una subclase debe poder usarse donde se usa su padre sin sorpresas. I, segregación "
          "de interfaces: muchas interfaces pequeñas mejor que una gorda. D, inversión de dependencias: depender de "
          "abstracciones, no de detalles concretos (pasar el objeto que se usa en vez de crearlo dentro: facilita "
          "probar con dobles). Son guías, no leyes: aplicarlas sin necesidad complica el código."},
{"id": "patrones", "area": "Ingeniería de software", "titulo": "Patrones de diseño",
 "temas": "patrones diseno gof observador estrategia fabrica singleton adaptador decorador comando fachada",
 "texto": "Soluciones con nombre a problemas repetidos (libro de la «Banda de los Cuatro», 1994). Creacionales: "
          "fábrica (decide qué clase crear), constructor (builder), singleton (una sola instancia; úsalo poco, es un "
          "global disfrazado). Estructurales: adaptador (encaja interfaces), decorador (añade comportamiento "
          "envolviendo), fachada (una puerta sencilla a algo complejo). De comportamiento: observador (avisar a "
          "suscriptores; los eventos de Kivy), estrategia (cambiar el algoritmo pasando otra función: lo que hace "
          "Kira al elegir cerebro local o Claude), comando (una acción como objeto: deshacer, colas), máquina de "
          "estados. En Python muchos se simplifican con funciones de primera clase."},
{"id": "arquitectura", "area": "Ingeniería de software", "titulo": "Arquitectura: capas, hexagonal, monolito y microservicios",
 "temas": "arquitectura capas hexagonal puertos adaptadores limpia monolito microservicios inyeccion dependencias",
 "texto": "Separar la LÓGICA de los detalles (pantalla, base de datos, red) hace el código probable y cambiable: en "
          "la arquitectura hexagonal (puertos y adaptadores) el núcleo define interfaces y los adaptadores las "
          "implementan. Kira lo sigue: la lógica pura (escucha_kira, recuerdos_kira…) se prueba sin Kivy y las "
          "pantallas son una capa aparte. Monolito: una sola aplicación, más fácil de desarrollar y desplegar al "
          "principio. Microservicios: servicios pequeños independientes, escalan y se despliegan por separado, pero "
          "añaden red, fallos parciales y complejidad operativa; casi siempre conviene empezar con un monolito bien "
          "modular."},
{"id": "pruebas", "area": "Ingeniería de software", "titulo": "Pruebas de software",
 "temas": "pruebas tests unitarias integracion extremo tdd mocks dobles cobertura propiedades mutacion regresion",
 "texto": "Pirámide: muchas pruebas UNITARIAS (rápidas, de una pieza), menos de INTEGRACIÓN (piezas juntas) y pocas de "
          "EXTREMO A EXTREMO (como el usuario). TDD: escribir la prueba antes que el código. Los dobles (falsos, "
          "mocks) sustituyen lo lento o externo: Kira prueba la interfaz con un Kivy falso y la red con servidores "
          "simulados. Una prueba de regresión fija un error ya arreglado para que no vuelva. La cobertura mide qué "
          "líneas se ejecutan, no si se comprueba lo correcto; las pruebas de propiedades (Hypothesis) generan "
          "entradas al azar y las de mutación cambian el código para ver si alguna prueba lo detecta."},
{"id": "git", "area": "Ingeniería de software", "titulo": "Git por dentro",
 "temas": "git control versiones commit rama merge rebase objetos blob tree hash reflog conflicto",
 "texto": "Git guarda instantáneas, no diferencias: cada archivo es un objeto blob, cada carpeta un tree y cada "
          "commit apunta a un tree y a su(s) padre(s), todo identificado por el hash de su contenido. Los commits "
          "forman un grafo dirigido sin ciclos; una RAMA es solo un puntero móvil a un commit y HEAD indica dónde "
          "estás. merge une dos historias con un commit de fusión; rebase reescribe tus commits encima de otros "
          "(historia lineal; no reescribas lo ya compartido). Si algo «se pierde», git reflog guarda a dónde apuntó "
          "HEAD. Commits pequeños y con mensajes que expliquen el porqué."},
{"id": "ci_cd", "area": "Ingeniería de software", "titulo": "Integración y entrega continuas (CI/CD) y versiones",
 "temas": "integracion continua entrega despliegue ci cd pipeline github actions compilacion versionado semantico",
 "texto": "Integración continua: cada cambio que se sube se compila y se prueba automáticamente, para enterarse de "
          "los fallos en minutos. Entrega continua: además produce un paquete listo para instalar; despliegue "
          "continuo: lo publica solo. Kira funciona así: cada subida a main lanza GitHub Actions, que compila el APK "
          "y comprueba lo que lleva dentro. Versionado semántico MAYOR.MENOR.PARCHE: mayor si rompe compatibilidad, "
          "menor si añade funciones, parche si solo arregla. Las compilaciones deben ser reproducibles (versiones "
          "fijadas de herramientas y dependencias)."},
{"id": "codigo_limpio", "area": "Ingeniería de software", "titulo": "Código limpio, refactorizar y deuda técnica",
 "temas": "codigo limpio refactorizar refactorizacion deuda tecnica nombres funciones legibilidad duplicacion",
 "texto": "El código se lee muchas más veces de las que se escribe. Nombres que digan qué es, funciones cortas que "
          "hagan una cosa, sin números mágicos, sin duplicar lógica (pero mejor algo de duplicación que una "
          "abstracción equivocada), errores con mensajes claros y comentarios que expliquen el PORQUÉ, no el qué. "
          "Refactorizar es cambiar la estructura sin cambiar el comportamiento, a pasos pequeños y con pruebas que lo "
          "vigilen. La deuda técnica son los atajos que habrá que pagar después: a veces conviene, siempre que se "
          "apunte y se pague."},
{"id": "rendimiento", "area": "Ingeniería de software", "titulo": "Optimizar: medir primero y ley de Amdahl",
 "temas": "rendimiento optimizar perfilar profiler cprofile timeit cuello botella amdahl lento rapido",
 "texto": "Primero que funcione, después medir, y solo entonces optimizar lo que de verdad pesa: suele ser un 10 % "
          "del código. En Python: timeit para trozos y cProfile para programas enteros. Mejoras por orden de impacto: "
          "mejor algoritmo o estructura (un set en vez de buscar en una lista), evitar trabajo repetido (cachés, "
          "lru_cache), hacer menos entrada/salida y en bloque, y al final micro-optimizaciones. Ley de Amdahl: si "
          "solo una parte p del programa se puede acelerar, la mejora máxima es 1 / ((1 − p) + p / n); con un 90 % "
          "paralelizable, ni con infinitos núcleos pasas de 10 veces más rápido."},
# ---------- seguridad (defensiva) ----------
{"id": "criptografia", "area": "Seguridad (defensiva)", "titulo": "Criptografía: hash, cifrado y firma",
 "temas": "criptografia hash cifrado simetrico asimetrico firma aes rsa curva eliptica aleatorio secrets",
 "texto": "HASH (SHA-256): huella de tamaño fijo, imposible de invertir; detecta cambios. HMAC: hash con clave, "
          "demuestra que lo escribió quien tiene la clave (así firma Kira sus recuerdos). Cifrado SIMÉTRICO (AES-GCM, "
          "ChaCha20-Poly1305): la misma clave cifra y descifra; rápido. ASIMÉTRICO (RSA, curvas elípticas): clave "
          "pública para cifrar o verificar y privada para descifrar o firmar; se usa para acordar claves y firmar. "
          "Reglas: nunca inventes tu propia criptografía, usa librerías probadas; usa modos autenticados; números "
          "aleatorios con secrets, nunca con random; y guarda las claves fuera del código."},
{"id": "contrasenas", "area": "Seguridad (defensiva)", "titulo": "Guardar contraseñas y autenticación",
 "temas": "contrasenas contraseña hash sal argon2 bcrypt scrypt pbkdf2 autenticacion doble factor 2fa",
 "texto": "Las contraseñas no se guardan nunca en claro ni cifradas, sino con un hash LENTO y con SAL aleatoria por "
          "usuario: Argon2id (la recomendación actual), scrypt, bcrypt o PBKDF2 con muchas iteraciones. La sal "
          "impide usar tablas precalculadas y que dos contraseñas iguales se delaten; la lentitud frena los ataques "
          "de fuerza bruta. Al comparar secretos, hmac.compare_digest (tiempo constante). El doble factor (una app "
          "de códigos o una llave física) protege aunque roben la contraseña; los SMS son el más débil. Los tokens y "
          "claves de API caducan y se pueden revocar."},
{"id": "seguridad_web", "area": "Seguridad (defensiva)", "titulo": "Programar seguro: inyección, XSS y mínimo privilegio",
 "temas": "seguridad web owasp inyeccion sql xss csrf validar entrada minimo privilegio defensa profundidad secretos",
 "texto": "Nunca mezcles datos del usuario con código: consultas SQL con parámetros (?), escapar el HTML que se "
          "muestra (evita XSS), no pasar texto a la consola del sistema ni a eval. Valida la entrada con listas de lo "
          "PERMITIDO (como el ffmpeg restringido de Kira) mejor que con listas de lo prohibido. Mínimo privilegio: "
          "cada pieza con los permisos justos. Defensa en profundidad: varias capas, por si una falla (Kira: revisión "
          "previa, laboratorio y tu aprobación). Secretos fuera del código y del historial de git. Mantén las "
          "dependencias al día. La lista OWASP Top 10 resume los fallos más comunes, con el control de acceso roto "
          "a la cabeza."},
# ---------- inteligencia artificial ----------
{"id": "aprendizaje_automatico", "area": "Inteligencia artificial", "titulo": "Aprendizaje automático: lo esencial",
 "temas": "aprendizaje automatico machine learning supervisado no supervisado refuerzo sobreajuste validacion metricas",
 "texto": "SUPERVISADO: aprender de ejemplos con su respuesta (clasificar, predecir números). NO SUPERVISADO: "
          "encontrar estructura sin respuestas (agrupar con k-means, reducir dimensiones). POR REFUERZO: aprender "
          "por premios y castigos al actuar. El gran enemigo es el SOBREAJUSTE: memorizar los ejemplos en vez de "
          "generalizar; se detecta separando datos de entrenamiento, validación y prueba (o con validación cruzada) "
          "y se combate con más datos, modelos más simples y regularización. Métricas: exactitud engaña con clases "
          "desequilibradas; mejor precisión, exhaustividad (recall) y F1. Los datos importan más que el algoritmo."},
{"id": "llm", "area": "Inteligencia artificial", "titulo": "Modelos de lenguaje (LLM) y transformers",
 "temas": "llm modelo lenguaje transformer atencion tokens contexto embeddings temperatura alucinacion qwen claude",
 "texto": "Un modelo de lenguaje predice la siguiente ficha (token, un trozo de palabra) según todas las anteriores. "
          "El transformer (2017) usa ATENCIÓN: cada token mira a todos los demás y decide cuánto le importa cada "
          "uno; apilando muchas capas aparecen gramática, hechos y razonamiento. La ventana de contexto limita "
          "cuántos tokens ve a la vez. La temperatura controla el azar al elegir. Pueden «alucinar» (inventar con "
          "seguridad) porque generan lo plausible, no lo comprobado: por eso Kira prefiere su baúl y las fuentes, y "
          "prueba el código en el laboratorio. Tras el preentrenamiento, se ajustan con instrucciones y preferencias "
          "humanas."},
{"id": "cuantizacion", "area": "Inteligencia artificial", "titulo": "Modelos en el móvil: cuantización y memoria",
 "temas": "cuantizacion q4 q8 gguf llama cpp memoria ram parametros bits modelo local movil velocidad",
 "texto": "Un modelo guarda miles de millones de pesos. En 16 bits, cada parámetro ocupa 2 bytes: 4.000 millones "
          "serían 8 GB. CUANTIZAR guarda los pesos con menos bits (Q8 ≈ 1 byte, Q4 ≈ 0,5-0,6 bytes por parámetro, "
          "en bloques con su propia escala), perdiendo muy poca calidad: así un modelo de 4B cabe en ~3 GB y uno de "
          "2B en ~1,5 GB (los de Kira). llama.cpp usa el formato GGUF. La velocidad al generar depende sobre todo de "
          "cuántos bytes hay que leer de la memoria por token, por eso los modelos pequeños y cuantizados van más "
          "rápidos, y el contexto largo gasta además memoria en la caché de atención (KV cache)."},
{"id": "teoria_informacion", "area": "Inteligencia artificial", "titulo": "Teoría de la información: entropía y compresión",
 "temas": "entropia shannon informacion bits compresion limite huffman sin perdida aleatorio sorpresa",
 "texto": "Shannon (1948) midió la información como sorpresa: un suceso de probabilidad p aporta −log₂ p bits, y la "
          "ENTROPÍA es la media. Es el límite de la compresión sin pérdida: ningún compresor baja de ella en media. "
          "Huffman y la codificación aritmética se acercan dando códigos cortos a lo frecuente; LZ77/LZW y la BWT "
          "explotan las repeticiones; ZIP combina LZ77 + Huffman. Los datos aleatorios o ya comprimidos (o "
          "cifrados) no se pueden comprimir más. Con pérdida (MP3, JPEG, H.264) se descarta lo que el oído o la "
          "vista apenas notan."},
]


# =====================================================================================================================
#  AYUDAS
# =====================================================================================================================
def areas():
    """Áreas en el orden en que aparecen: [(area, [recetas])]."""
    orden = {}
    for r in RECETAS:
        orden.setdefault(r["area"], []).append(r)
    return list(orden.items())


def demo(r):
    """La receta como PROGRAMA para el editor seguro: el módulo y, debajo, sus pruebas impresas."""
    lineas = [r["codigo"].strip(), "", "", "# ---- Pruébalo: es lo mismo que pedírselo a Kira cuando el módulo está instalado ----",
              "ordenes = registrar()"]
    vistos = set()
    for orden, arg, _espera in r.get("prueba", []):
        if (orden, arg) in vistos:
            continue
        vistos.add((orden, arg))
        lineas.append(f"print('>', {orden!r}, {arg!r})")
        lineas.append(f"print(ordenes[{orden!r}]({arg!r}))")
        lineas.append("print()")
    return "\n".join(lineas) + "\n"


def leccion(r):
    """Ficha de lección (mismo formato que curso_avanzado_kira) para la terminal y los ejemplos del editor."""
    return {"id": "ing_" + r["id"], "titulo": r["titulo"], "nivel": "ingeniería",
            "texto": f"{r['idea']} Coste: {r['complejidad']}.", "codigo": demo(r)}


def fichas():
    """(tema, texto) de todo el saber de ingeniería, para guardarlo en el baúl de recuerdos."""
    res = [(r["titulo"], f"{r['titulo']} ({r['area']}): {r['idea']} Coste: {r['complejidad']}. "
                         f"Kira tiene una receta probada: «receta {r['id'].replace('_', ' ')}».") for r in RECETAS]
    res += [(c["titulo"], f"{c['titulo']}: {c['texto']}") for c in CONCEPTOS]
    return res
