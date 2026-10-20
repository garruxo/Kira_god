# -*- coding: utf-8 -*-
"""
curso_avanzado_kira.py - PROGRAMACIÓN AVANZADA sin internet (lógica PURA, sin Kivy).

  CURSO_AVANZADO   : lecciones de nivel alto (clases, decoradores, generadores, concurrencia, algoritmos, patrones…).
  CODIGOS          : programas completos y avanzados para estudiar, ejecutar en el editor y modificar.
  CURSO_DISENO     : programación avanzada y diseño (saber_avanzado_kira), con sus pruebas.
  CURSO_INGENIERIA : ingeniería informática (estructuras de datos, grafos, sistemas, compiladores, IA…), sacado de
                     recetas_ingenieria_kira: cada lección es un módulo probado que se ejecuta con sus pruebas.

Todo el código de aquí se comprueba EJECUTÁNDOLO en las pruebas (tests/test_curso_avanzado.py), así que funciona.
Ninguno usa archivos, red ni el sistema: se pueden ejecutar en el editor seguro de Kira.
"""

CURSO_AVANZADO = [
    {"id": "clases", "titulo": "Clases y objetos", "nivel": "avanzado",
     "texto": "Una clase es un molde: define datos (atributos) y comportamiento (métodos). __init__ prepara cada objeto y "
              "self es el propio objeto. __repr__ dice cómo se muestra. Agrupa en una clase lo que va junto.",
     "codigo": "class Cuenta:\n    def __init__(self, titular, saldo=0):\n        self.titular = titular\n        self.saldo = saldo\n\n"
               "    def ingresar(self, cantidad):\n        if cantidad <= 0:\n            raise ValueError('cantidad no válida')\n"
               "        self.saldo += cantidad\n        return self.saldo\n\n    def __repr__(self):\n"
               "        return f'Cuenta({self.titular!r}, {self.saldo})'\n\nc = Cuenta('Ana')\nc.ingresar(50)\nprint(c)"},
    {"id": "herencia", "titulo": "Herencia y polimorfismo", "nivel": "avanzado",
     "texto": "Una clase hija hereda de otra y puede cambiar (sobrescribir) sus métodos. super() llama al método del padre. "
              "Polimorfismo: distintos objetos responden al mismo método cada uno a su manera.",
     "codigo": "class Forma:\n    def area(self):\n        raise NotImplementedError\n\nclass Rect(Forma):\n"
               "    def __init__(self, a, b):\n        self.a, self.b = a, b\n    def area(self):\n        return self.a * self.b\n\n"
               "class Circulo(Forma):\n    def __init__(self, r):\n        self.r = r\n    def area(self):\n"
               "        return round(3.14159 * self.r ** 2, 2)\n\nfor f in (Rect(2, 3), Circulo(1)):\n"
               "    print(type(f).__name__, f.area())"},
    {"id": "dataclasses", "titulo": "Dataclasses y tipos", "nivel": "avanzado",
     "texto": "@dataclass escribe por ti __init__, __repr__ y la comparación. Las anotaciones de tipo (nombre: str) documentan "
              "qué espera cada campo; field(default_factory=list) evita compartir la misma lista entre objetos.",
     "codigo": "from dataclasses import dataclass, field\n\n@dataclass\nclass Tarea:\n    titulo: str\n    prioridad: int = 1\n"
               "    etiquetas: list = field(default_factory=list)\n\nt = Tarea('Compilar APK', 3)\nt.etiquetas.append('kira')\n"
               "print(t)\nprint(t == Tarea('Compilar APK', 3, ['kira']))"},
    {"id": "decoradores", "titulo": "Decoradores", "nivel": "avanzado",
     "texto": "Un decorador es una función que envuelve a otra para añadirle algo (medir, registrar, reintentar) sin tocar su "
              "código. Se aplica con @nombre. functools.wraps conserva el nombre de la función original.",
     "codigo": "import functools\n\ndef contar_llamadas(f):\n    @functools.wraps(f)\n    def envoltura(*args, **kw):\n"
               "        envoltura.llamadas += 1\n        return f(*args, **kw)\n    envoltura.llamadas = 0\n    return envoltura\n\n"
               "@contar_llamadas\ndef doble(x):\n    return x * 2\n\nprint(doble(3), doble(5))\nprint(doble.__name__, 'llamada', doble.llamadas, 'veces')"},
    {"id": "generadores", "titulo": "Generadores e iteradores", "nivel": "avanzado",
     "texto": "Un generador produce valores de uno en uno con yield, sin guardarlos todos en memoria: ideal para secuencias "
              "largas o infinitas. itertools trae piezas listas para combinarlos.",
     "codigo": "import itertools\n\ndef fibonacci():\n    a, b = 0, 1\n    while True:\n        yield a\n        a, b = b, a + b\n\n"
               "print(list(itertools.islice(fibonacci(), 10)))\npares = (n for n in range(20) if n % 2 == 0)\nprint(sum(pares))"},
    {"id": "contexto", "titulo": "Gestores de contexto (with)", "nivel": "avanzado",
     "texto": "with garantiza que algo se cierra o se limpia aunque haya un error. Puedes crear los tuyos con __enter__ y "
              "__exit__, o más fácil con @contextmanager.",
     "codigo": "from contextlib import contextmanager\nimport time\n\n@contextmanager\ndef cronometro(nombre):\n"
               "    inicio = time.perf_counter()\n    try:\n        yield\n    finally:\n"
               "        print(nombre, 'tardó', round(time.perf_counter() - inicio, 3) >= 0)\n\n"
               "with cronometro('suma'):\n    total = sum(range(100000))\nprint(total)"},
    {"id": "excepciones", "titulo": "Excepciones propias", "nivel": "avanzado",
     "texto": "Crea tus propios tipos de error heredando de Exception: así quien use tu código puede capturar solo los "
              "tuyos. raise ... from e conserva la causa original. finally se ejecuta siempre.",
     "codigo": "class ErrorDeKira(Exception):\n    pass\n\nclass SinCerebro(ErrorDeKira):\n    pass\n\ndef pensar(clave):\n"
               "    if not clave:\n        raise SinCerebro('falta la clave')\n    return 'pensando'\n\ntry:\n    pensar('')\n"
               "except ErrorDeKira as e:\n    print(type(e).__name__, '->', e)\nfinally:\n    print('fin')"},
    {"id": "hilos", "titulo": "Concurrencia con hilos", "nivel": "avanzado",
     "texto": "Los hilos hacen varias cosas a la vez (esperar la red mientras la pantalla sigue viva). Si comparten datos, "
              "protégelos con un Lock. queue.Queue pasa datos entre hilos de forma segura.",
     "codigo": "import threading, queue\n\ncola = queue.Queue()\ntotal = {'n': 0}\ncandado = threading.Lock()\n\ndef trabajador():\n"
               "    while True:\n        x = cola.get()\n        if x is None:\n            break\n        with candado:\n"
               "            total['n'] += x\n\nhilos = [threading.Thread(target=trabajador) for _ in range(3)]\nfor h in hilos:\n"
               "    h.start()\nfor i in range(1, 101):\n    cola.put(i)\nfor _ in hilos:\n    cola.put(None)\nfor h in hilos:\n"
               "    h.join()\nprint('suma', total['n'])"},
    {"id": "asincrono", "titulo": "Programación asíncrona (asyncio)", "nivel": "avanzado",
     "texto": "async/await reparte el tiempo entre muchas tareas que esperan (red, temporizadores) en un solo hilo. "
              "asyncio.gather lanza varias a la vez y espera a todas.",
     "codigo": "import asyncio\n\nasync def tarea(nombre, espera):\n    await asyncio.sleep(espera)\n    return f'{nombre} lista'\n\n"
               "async def principal():\n    resultados = await asyncio.gather(tarea('A', 0.02), tarea('B', 0.01))\n    print(resultados)\n\n"
               "asyncio.run(principal())"},
    {"id": "regex", "titulo": "Expresiones regulares", "nivel": "avanzado",
     "texto": "Una expresión regular describe un patrón de texto: \\d dígito, \\w letra o número, + uno o más, (…) grupo. "
              "re.findall saca todas las coincidencias; los grupos con nombre (?P<n>…) se leen por nombre.",
     "codigo": "import re\n\ntexto = 'Kira v2.7 compilada el 19/10/2026; antes v2.6 el 18/10/2026'\n"
               "print(re.findall(r'v(\\d+\\.\\d+)', texto))\nm = re.search(r'(?P<d>\\d{2})/(?P<m>\\d{2})/(?P<a>\\d{4})', texto)\n"
               "print(m.group('a'), m.group('m'), m.group('d'))"},
    {"id": "sqlite", "titulo": "Bases de datos con SQLite", "nivel": "avanzado",
     "texto": "SQLite es una base de datos completa dentro de un archivo (o en memoria). Usa ? para pasar valores: nunca "
              "pegues texto del usuario dentro del SQL, así evitas la inyección SQL.",
     "codigo": "import sqlite3\n\ndb = sqlite3.connect(':memory:')\ndb.execute('CREATE TABLE notas (id INTEGER PRIMARY KEY, texto TEXT)')\n"
               "for t in ('comprar pilas', 'compilar kira'):\n    db.execute('INSERT INTO notas (texto) VALUES (?)', (t,))\n"
               "busca = '%kira%'\nfor fila in db.execute('SELECT id, texto FROM notas WHERE texto LIKE ?', (busca,)):\n    print(fila)"},
    {"id": "complejidad", "titulo": "Complejidad y búsqueda binaria", "nivel": "avanzado",
     "texto": "La notación O mide cómo crece el trabajo: buscar en una lista es O(n); en una lista ORDENADA, la búsqueda "
              "binaria es O(log n): parte por la mitad cada vez. Con un millón de datos son unas 20 comparaciones.",
     "codigo": "def buscar(lista, x):\n    izq, der, pasos = 0, len(lista) - 1, 0\n    while izq <= der:\n        pasos += 1\n"
               "        mitad = (izq + der) // 2\n        if lista[mitad] == x:\n            return mitad, pasos\n"
               "        if lista[mitad] < x:\n            izq = mitad + 1\n        else:\n            der = mitad - 1\n"
               "    return -1, pasos\n\nnumeros = list(range(0, 2000000, 2))\nprint(buscar(numeros, 1234568))"},
    {"id": "grafos", "titulo": "Grafos: BFS y caminos", "nivel": "avanzado",
     "texto": "Un grafo son nodos unidos por aristas (mapas, redes, amistades). La búsqueda en anchura (BFS) explora por "
              "capas y encuentra el camino más corto en número de pasos. Se usa una cola (deque).",
     "codigo": "from collections import deque\n\nmapa = {'casa': ['parque', 'tienda'], 'parque': ['playa'], 'tienda': ['playa', 'cine'],\n"
               "        'playa': ['cine'], 'cine': []}\n\ndef camino(origen, destino):\n    cola, previo = deque([origen]), {origen: None}\n"
               "    while cola:\n        n = cola.popleft()\n        if n == destino:\n            ruta = []\n            while n:\n"
               "                ruta.append(n)\n                n = previo[n]\n            return ruta[::-1]\n"
               "        for v in mapa[n]:\n            if v not in previo:\n                previo[v] = n\n                cola.append(v)\n\n"
               "print(camino('casa', 'cine'))"},
    {"id": "dinamica", "titulo": "Programación dinámica", "nivel": "avanzado",
     "texto": "Si un problema se repite en subproblemas, guarda las respuestas para no recalcularlas (memoización). "
              "functools.lru_cache lo hace por ti. Convierte cálculos exponenciales en casi instantáneos.",
     "codigo": "from functools import lru_cache\n\n@lru_cache(maxsize=None)\ndef caminos(filas, cols):\n"
               "    # ¿de cuántas formas se cruza una cuadrícula moviéndose solo a la derecha o abajo?\n"
               "    if filas == 1 or cols == 1:\n        return 1\n    return caminos(filas - 1, cols) + caminos(filas, cols - 1)\n\n"
               "print(caminos(18, 18))"},
    {"id": "patrones", "titulo": "Patrones de diseño", "nivel": "avanzado",
     "texto": "Soluciones probadas a problemas típicos. Observador: avisa a quien esté suscrito cuando algo cambia (así "
              "funcionan los eventos de Kivy). Estrategia: cambia el comportamiento pasando otra función u objeto.",
     "codigo": "class Evento:\n    def __init__(self):\n        self._suscritos = []\n    def suscribir(self, f):\n"
               "        self._suscritos.append(f)\n    def emitir(self, *datos):\n        for f in self._suscritos:\n            f(*datos)\n\n"
               "al_hablar = Evento()\nal_hablar.suscribir(lambda t: print('pantalla:', t))\n"
               "al_hablar.suscribir(lambda t: print('memoria guarda', len(t), 'letras'))\nal_hablar.emitir('Hola, soy Kira')"},
    {"id": "pruebas", "titulo": "Pruebas automáticas", "nivel": "avanzado",
     "texto": "Un test comprueba que tu código hace lo que debe, cada vez que lo cambias. assert falla si algo no se cumple. "
              "unittest organiza muchas pruebas. Así se prueba Kira: más de 1.500 comprobaciones.",
     "codigo": "import unittest\n\ndef invertir(t):\n    return t[::-1]\n\nclass PruebaInvertir(unittest.TestCase):\n"
               "    def test_palabra(self):\n        self.assertEqual(invertir('kira'), 'arik')\n    def test_vacio(self):\n"
               "        self.assertEqual(invertir(''), '')\n\nr = unittest.TextTestRunner(verbosity=0).run(\n"
               "    unittest.defaultTestLoader.loadTestsFromTestCase(PruebaInvertir))\nprint('fallos:', len(r.failures))"},
]

CODIGOS = [
    {"id": "vida", "titulo": "Juego de la vida", "nivel": "código",
     "texto": "El autómata de Conway: cada célula vive o muere según sus 8 vecinas. Reglas simples, dibujos complejos.",
     "codigo": "def paso(vivas):\n    from collections import Counter\n    vecinas = Counter((x + dx, y + dy) for x, y in vivas\n"
               "                      for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)\n"
               "    return {c for c, n in vecinas.items() if n == 3 or (n == 2 and c in vivas)}\n\n"
               "def dibujar(vivas, ancho=8, alto=6):\n    for y in range(alto):\n"
               "        print(''.join('#' if (x, y) in vivas else '.' for x in range(ancho)))\n\n"
               "planeador = {(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)}\nfor _ in range(4):\n    planeador = paso(planeador)\n"
               "dibujar(planeador)"},
    {"id": "astar", "titulo": "Búsqueda de caminos A*", "nivel": "código",
     "texto": "El algoritmo que usan los videojuegos para que los personajes esquiven muros: explora primero lo más prometedor.",
     "codigo": "import heapq\n\nmapa = ['S..#....', '.#.#.##.', '.#...#..', '.####.#.', '......#G']\n\ndef a_estrella():\n"
               "    pos = {c: (x, y) for y, f in enumerate(mapa) for x, c in enumerate(f)}\n    ini, fin = pos['S'], pos['G']\n"
               "    h = lambda p: abs(p[0] - fin[0]) + abs(p[1] - fin[1])\n    abiertos, previo, coste = [(h(ini), ini)], {ini: None}, {ini: 0}\n"
               "    while abiertos:\n        _, p = heapq.heappop(abiertos)\n        if p == fin:\n            break\n"
               "        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n            q = (p[0] + dx, p[1] + dy)\n"
               "            if 0 <= q[1] < len(mapa) and 0 <= q[0] < len(mapa[0]) and mapa[q[1]][q[0]] != '#':\n"
               "                c = coste[p] + 1\n                if c < coste.get(q, 1e9):\n                    coste[q], previo[q] = c, p\n"
               "                    heapq.heappush(abiertos, (c + h(q), q))\n    ruta, p = set(), fin\n    while p:\n"
               "        ruta.add(p)\n        p = previo[p]\n    for y, f in enumerate(mapa):\n"
               "        print(''.join('*' if (x, y) in ruta and c == '.' else c for x, c in enumerate(f)))\n    print('pasos:', coste[fin])\n\n"
               "a_estrella()"},
    {"id": "huffman", "titulo": "Compresor Huffman", "nivel": "código",
     "texto": "Comprime texto dando códigos cortos a las letras frecuentes y largos a las raras (así funcionan ZIP y MP3, en parte).",
     "codigo": "import heapq\nfrom collections import Counter\n\ndef codigos(texto):\n"
               "    monton = [[n, [c, '']] for c, n in Counter(texto).items()]\n    heapq.heapify(monton)\n    while len(monton) > 1:\n"
               "        a, b = heapq.heappop(monton), heapq.heappop(monton)\n        for par in a[1:]:\n            par[1] = '0' + par[1]\n"
               "        for par in b[1:]:\n            par[1] = '1' + par[1]\n        heapq.heappush(monton, [a[0] + b[0]] + a[1:] + b[1:])\n"
               "    return dict(monton[0][1:])\n\ntexto = 'kira kira kira aprende y programa'\ntabla = codigos(texto)\n"
               "bits = ''.join(tabla[c] for c in texto)\nprint('original:', len(texto) * 8, 'bits; comprimido:', len(bits), 'bits')\n"
               "inversa = {v: k for k, v in tabla.items()}\nactual, salida = '', ''\nfor b in bits:\n    actual += b\n"
               "    if actual in inversa:\n        salida += inversa[actual]\n        actual = ''\nprint(salida == texto)"},
    {"id": "calculadora", "titulo": "Intérprete de expresiones", "nivel": "código",
     "texto": "Un analizador sintáctico de verdad (descenso recursivo): entiende + - * / ^ y paréntesis respetando prioridades.",
     "codigo": "import re\n\ndef calcular(expr):\n    fichas = re.findall(r'\\d+\\.?\\d*|[-+*/^()]', expr)\n    pos = [0]\n"
               "    def ver():\n        return fichas[pos[0]] if pos[0] < len(fichas) else None\n    def tomar():\n"
               "        pos[0] += 1\n        return fichas[pos[0] - 1]\n    def atomo():\n        if ver() == '(':\n            tomar()\n"
               "            v = suma()\n            tomar()\n            return v\n        if ver() == '-':\n            tomar()\n            return -atomo()\n"
               "        return float(tomar())\n    def potencia():\n        v = atomo()\n        if ver() == '^':\n            tomar()\n"
               "            return v ** potencia()\n        return v\n    def producto():\n        v = potencia()\n"
               "        while ver() in ('*', '/'):\n            v = v * potencia() if tomar() == '*' else v / potencia()\n        return v\n"
               "    def suma():\n        v = producto()\n        while ver() in ('+', '-'):\n"
               "            v = v + producto() if tomar() == '+' else v - producto()\n        return v\n    return suma()\n\n"
               "for e in ('2 + 3 * 4', '(2 + 3) * 4', '2 ^ 3 ^ 2', '-(4 - 10) / 3'):\n    print(e, '=', calcular(e))"},
    {"id": "vigenere", "titulo": "Cifrado Vigenère", "nivel": "código",
     "texto": "Un cifrado clásico con clave. Sirve para aprender criptografía; para proteger datos reales usa cifrados modernos.",
     "codigo": "ABC = 'abcdefghijklmnñopqrstuvwxyz'\n\ndef vigenere(texto, clave, signo=1):\n    salida, k = [], 0\n    for c in texto.lower():\n"
               "        if c in ABC:\n            d = ABC.index(clave[k % len(clave)])\n"
               "            salida.append(ABC[(ABC.index(c) + signo * d) % len(ABC)])\n            k += 1\n        else:\n"
               "            salida.append(c)\n    return ''.join(salida)\n\nsecreto = vigenere('nos vemos en la sala hacker', 'kira')\n"
               "print(secreto)\nprint(vigenere(secreto, 'kira', -1))"},
    {"id": "perceptron", "titulo": "Neurona artificial que aprende", "nivel": "código",
     "texto": "Un perceptrón aprende solo, a base de corregir errores, a separar dos grupos: la semilla de las redes neuronales.",
     "codigo": "import random\nrandom.seed(7)\n# aprende la regla 'aprobado si nota_teoria + nota_practica > 10'\n"
               "datos = [((t, p), 1 if t + p > 10 else 0) for t, p in ((random.uniform(0, 10), random.uniform(0, 10)) for _ in range(200))]\n"
               "datos = [((t / 10, p / 10), y) for (t, p), y in datos]   # normalizar ayuda a aprender\n"
               "w, b = [0.0, 0.0], 0.0\nfor epoca in range(200):\n    for (x1, x2), y in datos:\n"
               "        pred = 1 if w[0] * x1 + w[1] * x2 + b > 0 else 0\n        err = y - pred\n"
               "        w[0] += 0.1 * err * x1\n        w[1] += 0.1 * err * x2\n        b += 0.1 * err\n"
               "aciertos = sum((1 if w[0] * x1 + w[1] * x2 + b > 0 else 0) == y for (x1, x2), y in datos)\n"
               "print('acierta', aciertos, 'de', len(datos))"},
    {"id": "sudoku", "titulo": "Resolver sudokus", "nivel": "código",
     "texto": "Vuelta atrás (backtracking): prueba un número, sigue, y si se atasca deshace y prueba otro.",
     "codigo": "s = [list(map(int, f)) for f in ('530070000', '600195000', '098000060', '800060003', '400803001',\n"
               "                                   '700020006', '060000280', '000419005', '000080079')]\n\ndef vale(f, c, n):\n"
               "    if n in s[f] or any(s[i][c] == n for i in range(9)):\n        return False\n    f0, c0 = f // 3 * 3, c // 3 * 3\n"
               "    return all(s[f0 + i][c0 + j] != n for i in range(3) for j in range(3))\n\ndef resolver():\n    for f in range(9):\n"
               "        for c in range(9):\n            if s[f][c] == 0:\n                for n in range(1, 10):\n"
               "                    if vale(f, c, n):\n                        s[f][c] = n\n                        if resolver():\n"
               "                            return True\n                        s[f][c] = 0\n                return False\n    return True\n\n"
               "resolver()\nfor fila in s[:3]:\n    print(fila)"},
    {"id": "maquina", "titulo": "Máquina de estados", "nivel": "código",
     "texto": "Cómo se programan semáforos, personajes de videojuego o la propia Kira (reposo, escuchando, pensando, hablando).",
     "codigo": "TRANSICIONES = {('reposo', 'oye_kira'): 'atenta', ('atenta', 'orden'): 'pensando',\n"
               "                ('pensando', 'respuesta'): 'hablando', ('hablando', 'fin'): 'reposo', ('atenta', 'silencio'): 'reposo'}\n\n"
               "class Maquina:\n    def __init__(self):\n        self.estado = 'reposo'\n    def evento(self, e):\n"
               "        nuevo = TRANSICIONES.get((self.estado, e))\n        print(f'{self.estado:9} --{e}--> {nuevo or \"(ignorado)\"}')\n"
               "        self.estado = nuevo or self.estado\n\nm = Maquina()\nfor e in ('orden', 'oye_kira', 'orden', 'respuesta', 'fin'):\n    m.evento(e)"},
    {"id": "inventario", "titulo": "Inventario con clases y JSON", "nivel": "código",
     "texto": "Un programa completo: clases, validación, búsqueda, informe y guardado en texto JSON (en memoria).",
     "codigo": "import json\nfrom dataclasses import dataclass, asdict\n\n@dataclass\nclass Producto:\n    nombre: str\n    precio: float\n"
               "    unidades: int = 0\n    def valor(self):\n        return round(self.precio * self.unidades, 2)\n\nclass Inventario:\n"
               "    def __init__(self):\n        self.items = {}\n    def anadir(self, p):\n        if p.precio < 0:\n"
               "            raise ValueError('precio negativo')\n        self.items[p.nombre.lower()] = p\n    def buscar(self, texto):\n"
               "        return [p for k, p in self.items.items() if texto.lower() in k]\n    def a_json(self):\n"
               "        return json.dumps([asdict(p) for p in self.items.values()], ensure_ascii=False)\n\ninv = Inventario()\n"
               "for p in (Producto('Pilas AA', 0.8, 40), Producto('Cable USB', 4.5, 6), Producto('Pila botón', 1.2, 10)):\n"
               "    inv.anadir(p)\nprint([p.nombre for p in inv.buscar('pila')])\nprint('valor total:', sum(p.valor() for p in inv.items.values()))\n"
               "print(len(json.loads(inv.a_json())), 'productos en JSON')"},
    {"id": "markov", "titulo": "Generador de texto (cadenas de Markov)", "nivel": "código",
     "texto": "Aprende qué palabra suele seguir a cada otra y escribe frases nuevas: un antepasado muy simple de los modelos de lenguaje.",
     "codigo": "import random\nfrom collections import defaultdict\nrandom.seed(3)\n"
               "texto = ('kira aprende cada día . kira programa juegos . kira estudia programación avanzada . '\n"
               "         'el usuario programa juegos con kira . cada día kira estudia algo nuevo .').split()\n"
               "siguiente = defaultdict(list)\nfor a, b in zip(texto, texto[1:]):\n    siguiente[a].append(b)\n"
               "palabra, frase = 'kira', ['kira']\nwhile palabra != '.' and len(frase) < 12:\n    palabra = random.choice(siguiente[palabra])\n"
               "    frase.append(palabra)\nprint(' '.join(frase))"},
]


def _ingenieria():
    """Lecciones de INGENIERÍA: cada receta de recetas_ingenieria_kira como programa que se ejecuta en el editor
    seguro (el módulo y, debajo, sus pruebas). tests/test_ingenieria.py las ejecuta todas."""
    try:
        import recetas_ingenieria_kira as ri
    except ImportError:
        return []
    return [ri.leccion(r) for r in ri.RECETAS]


CURSO_INGENIERIA = _ingenieria()


def _diseno():
    """Lecciones de PROGRAMACIÓN AVANZADA y DISEÑO (saber_avanzado_kira), igual que las de ingeniería."""
    try:
        import saber_avanzado_kira as sa
    except ImportError:
        return []
    return [sa.leccion(r) for r in sa.RECETAS]


CURSO_DISENO = _diseno()


def todas():
    return CURSO_AVANZADO + CODIGOS + CURSO_INGENIERIA + CURSO_DISENO


def buscar(id_):
    return next((l for l in todas() if l["id"] == id_), None)
