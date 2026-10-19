# -*- coding: utf-8 -*-
"""
programacion_kira.py - El "aprendizaje de programación" de la Sala Hacker (lógica PURA, sin Kivy)

  - CURSO: mini-curso de Python escrito aquí (funciona sin internet y sin API).
  - Biblioteca: tus libros (lecciones guardadas, apuntes, código) en el dispositivo.
  - comprobar_sintaxis(): revisa un código con ast SIN ejecutarlo.
  - guardar_leccion(): al guardar una lección en la biblioteca, un resumen pasa también a la memoria de Kira
    (cerebro_local.Conocimiento), así que luego puede responder con ella.

Honesto: aquí NO se ejecuta código. Las mejoras reales de Kira pasan por el laboratorio (pasarela) y tu confirmación.
"""
import ast
import json
import os
import re
import threading
import time

MAX_LIBROS = 200
MAX_TEXTO = 4000
TIPOS = ("leccion", "apunte")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

CURSO = [
    {"id": "variables", "titulo": "Variables y tipos",
     "texto": "Una variable es un nombre que guarda un valor. En Python no declaras el tipo: lo decide el valor. "
              "Los tipos básicos son int (enteros), float (decimales), str (texto) y bool (verdadero/falso). "
              "Con type() ves de qué tipo es algo.",
     "codigo": "nombre = 'Kira'\nedad = 3\naltura = 1.62\nactiva = True\nprint(nombre, edad, altura, activa)\nprint(type(edad))"},
    {"id": "condicionales", "titulo": "Condicionales (if)",
     "texto": "if ejecuta un bloque solo si la condición es verdadera. elif añade otra condición y else es lo que pasa "
              "si ninguna se cumple. Los bloques se marcan con sangría (4 espacios), no con llaves.",
     "codigo": "hora = 15\nif hora < 12:\n    print('Buenos días')\nelif hora < 20:\n    print('Buenas tardes')\nelse:\n    print('Buenas noches')"},
    {"id": "bucles", "titulo": "Bucles (for y while)",
     "texto": "for recorre una secuencia; while repite mientras la condición sea cierta. Cuidado con los bucles infinitos: "
              "el while necesita algo que cambie para terminar. range(n) da los números de 0 a n-1.",
     "codigo": "for i in range(3):\n    print('vuelta', i)\n\ncuenta = 3\nwhile cuenta > 0:\n    print(cuenta)\n    cuenta -= 1"},
    {"id": "listas", "titulo": "Listas y diccionarios",
     "texto": "Una lista guarda valores en orden: [1, 2, 3]. Un diccionario guarda pares clave:valor: {'a': 1}. "
              "Se accede por posición (lista[0]) o por clave (dic['a']). append añade a una lista.",
     "codigo": "colores = ['rojo', 'verde']\ncolores.append('azul')\nprint(colores[0], len(colores))\n\nficha = {'nombre': 'Kira', 'modulos': 4}\nficha['modulos'] += 1\nprint(ficha)"},
    {"id": "funciones", "titulo": "Funciones",
     "texto": "Una función agrupa código reutilizable. Se define con def, recibe parámetros y devuelve un resultado con return. "
              "Dale nombres claros y que cada función haga una sola cosa.",
     "codigo": "def saludar(nombre, formal=False):\n    if formal:\n        return 'Buenos días, ' + nombre\n    return 'Hola ' + nombre\n\nprint(saludar('Ana'))\nprint(saludar('Ana', formal=True))"},
    {"id": "errores", "titulo": "Errores y try/except",
     "texto": "Los errores (excepciones) paran el programa si no los controlas. try ejecuta algo que puede fallar y except dice "
              "qué hacer si falla. Captura errores concretos (ValueError, KeyError...) mejor que todos a la vez.",
     "codigo": "def a_entero(texto):\n    try:\n        return int(texto)\n    except ValueError:\n        return None\n\nprint(a_entero('42'))\nprint(a_entero('hola'))"},
    {"id": "archivos", "titulo": "Archivos y JSON",
     "texto": "Con open() lees y escribes archivos; with lo cierra solo. JSON es un formato de texto para guardar listas y "
              "diccionarios: json.dump guarda y json.load lee. Así guarda Kira sus notas y su memoria.",
     "codigo": "import json\n\ndatos = {'notas': ['comprar pilas']}\nwith open('prueba.json', 'w', encoding='utf-8') as f:\n    json.dump(datos, f, ensure_ascii=False)\nwith open('prueba.json', encoding='utf-8') as f:\n    print(json.load(f))"},
    {"id": "modulos_kira", "titulo": "Un módulo para Kira",
     "texto": "Las mejoras de Kira son módulos: archivos .py con una función registrar() que devuelve un diccionario "
              "{palabra_de_comando: función}. La función recibe el texto que escribes y devuelve la respuesta. "
              "Solo biblioteca estándar, sin subprocess, socket, eval ni exec. El laboratorio lo prueba y tú decides si se aplica.",
     "codigo": "import datetime\n\ndef hora(texto):\n    return 'Son las ' + datetime.datetime.now().strftime('%H:%M')\n\ndef registrar():\n    return {'hora': hora}"},
]


def limpiar(texto, maximo=MAX_TEXTO):
    return _CONTROL.sub(" ", str(texto)).strip()[:maximo]


def comprobar_sintaxis(codigo):
    """(ok, mensaje). Solo analiza; NO ejecuta nada."""
    try:
        ast.parse(str(codigo)[:20000])
        return True, "Sintaxis correcta (no se ha ejecutado nada)."
    except SyntaxError as e:
        return False, f"Error de sintaxis en la línea {e.lineno}: {e.msg}"
    except (ValueError, MemoryError, RecursionError) as e:
        return False, f"No se pudo analizar: {e}"


def leccion_del_curso(id_):
    return next((l for l in CURSO if l["id"] == id_), None)


def texto_leccion(l):
    return f"{l['titulo']}\n\n{l['texto']}\n\nEjemplo:\n{l['codigo']}"


# =====================================================================================
#  BIBLIOTECA
# =====================================================================================
class Biblioteca:
    def __init__(self, ruta):
        self.ruta, self._lock = ruta, threading.Lock()
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            self.items = [d for d in datos if isinstance(d, dict) and {"id", "tipo", "titulo", "texto"} <= set(d)
                          and d["tipo"] in TIPOS][-MAX_LIBROS:]
        except (OSError, ValueError, TypeError):
            self.items = []

    def _guardar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)

    def listar(self, tipo=None):
        with self._lock:
            return [dict(i) for i in reversed(self.items) if tipo in (None, i["tipo"])]

    def obtener(self, id_):
        with self._lock:
            return next((dict(i) for i in self.items if i["id"] == id_), None)

    def anadir(self, tipo, titulo, texto):
        """(ok, mensaje, id). Un título repetido de la misma clase actualiza el libro en vez de duplicarlo."""
        titulo, texto = limpiar(titulo, 80), limpiar(texto)
        if tipo not in TIPOS:
            return False, "Tipo de libro no válido.", None
        if not titulo or not texto:
            return False, "Pon un título y un texto.", None
        with self._lock:
            for i in self.items:
                if i["tipo"] == tipo and i["titulo"].lower() == titulo.lower():
                    i.update(texto=texto, t=time.time())
                    self._guardar()
                    return True, "Libro actualizado.", i["id"]
            if len(self.items) >= MAX_LIBROS:
                return False, f"La biblioteca tiene {MAX_LIBROS} libros: borra alguno.", None
            nuevo = max((i["id"] for i in self.items), default=0) + 1
            self.items.append({"id": nuevo, "tipo": tipo, "titulo": titulo, "texto": texto, "t": time.time()})
            self._guardar()
            return True, "Libro guardado en la biblioteca.", nuevo

    def borrar(self, id_):
        with self._lock:
            antes = len(self.items)
            self.items = [i for i in self.items if i["id"] != id_]
            if len(self.items) != antes:
                self._guardar()
                return True
        return False

    def textos(self):
        return [f"{i['titulo']}: {i['texto']}" for i in self.listar()]


def guardar_leccion(biblioteca, conocimiento, titulo, texto):
    """Guarda la lección como libro y deja un resumen en la memoria de Kira. Devuelve (ok, mensaje)."""
    ok, msg, _ = biblioteca.anadir("leccion", titulo, texto)
    if ok and conocimiento is not None:
        try:
            resumen = re.split(r"\n\s*Ejemplo:", limpiar(texto), maxsplit=1)[0]
            conocimiento.guardar(f"programación {limpiar(titulo, 60)}", resumen, fuente="biblioteca")
            msg += " Kira también lo recordará."
        except Exception:
            pass
    return ok, msg


def formatear_leccion_api(titulo, explicacion, codigo):
    return f"{titulo}\n\n{explicacion}\n\nEjemplo:\n{codigo}"
