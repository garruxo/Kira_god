# -*- coding: utf-8 -*-
"""
laboratorio_movil_kira.py - El LABORATORIO DE BOLSILLO: Kira prueba sus mejoras DENTRO del móvil, sin ordenador.

Hace lo mismo que el laboratorio del PC (kira_laboratorio/servidor_lab.py) y devuelve el mismo veredicto
({"ok", "sha256", "etapas", "avisos"}), así que el resto de Kira (Promotor, panel, «Aplicar» con dos toques) no cambia:
  1. sintaxis
  2. revisión de patrones (avisos para ti) y SEGURIDAD: solo módulos de una lista segura; sin archivos, red, sistema,
     eval/exec, trucos con atributos internos ni sleep (bloquearía a Kira)
  3. carga aislada: el módulo se carga con funciones recortadas y con tiempo máximo (un bucle infinito se corta)
  4. contrato: registrar() -> {"orden": función(texto) o función(texto, kira)} (como tests_fijos/test_contrato.py)
  5. juegos: si trae juegos, se juegan 20 s simulados con toques (como tests_fijos/test_juegos.py)
  6. prueba de uso: cada orden se llama con frases de ejemplo y un «kira de prueba» (sin archivos reales): si se
     cuelga, falla; si lanza un error raro, queda como aviso para que lo veas (y para que Claude lo revise)

LaboratorioDoble: prueba SIEMPRE en el móvil y, si el laboratorio del ordenador está conectado y responde, también
allí (las dos tienen que dar OK). Si el ordenador no está, basta con el móvil.

Honesto: en el móvil todo corre dentro de la propia app (Android no deja abrir otro Python aparte). La revisión de
seguridad protege contra errores y accidentes, no es una caja fuerte contra código hecho para saltársela. Por eso
sigues decidiendo tú: nada se instala sin tus dos toques en «Aplicar».
"""
import ast
import builtins
import hashlib
import inspect
import json
import sys
import threading
import time
import urllib.request

import mejoras_ia_kira as mi

# módulos que puede importar una mejora (librería estándar sin archivos, red ni sistema)
PERMITIDOS = {
    "math", "cmath", "random", "statistics", "datetime", "time", "calendar", "collections", "itertools", "functools",
    "operator", "string", "textwrap", "re", "json", "dataclasses", "enum", "typing", "abc", "copy", "heapq", "bisect",
    "array", "decimal", "fractions", "numbers", "unicodedata", "difflib", "pprint", "threading", "queue",
    "contextlib", "uuid", "secrets", "hashlib", "hmac", "base64", "binascii", "struct", "zlib", "colorsys",
    "graphlib", "keyword", "html", "csv", "motor_juegos_kira",
}
BUILTINS_FUERA = {"open", "eval", "exec", "compile", "__import__", "breakpoint", "globals", "vars", "memoryview",
                  "help", "exit", "quit", "input"}
ATRIBUTOS_PROHIBIDOS = {"__subclasses__", "__globals__", "__builtins__", "__code__", "__closure__", "__bases__",
                        "__mro__", "__getattribute__", "__import__", "__loader__", "__spec__", "__reduce__",
                        "__reduce_ex__", "gi_frame", "gi_code", "f_globals", "f_locals", "f_back", "f_builtins",
                        "tb_frame", "cr_frame", "ag_frame", "co_code", "settrace", "setprofile", "system", "popen",
                        "unlink", "rmtree", "sleep"}
TEXTOS_PROHIBIDOS = {a for a in ATRIBUTOS_PROHIBIDOS if a.startswith("__")} | {"f_globals", "gi_frame", "tb_frame"}
IMPORTS_SENSIBLES = {"subprocess", "socket", "shutil", "ctypes", "urllib", "requests", "pickle", "importlib"}
LLAMADAS_SENSIBLES = {"eval", "exec", "compile", "__import__", "open"}
EJEMPLOS_USO = ("", "hola", "3", "1 2 3", "mañana a las 10", "cosa rara ###")
TOPE_CARGA, TOPE_LLAMADA, TOPE_JUEGO = 5.0, 2.0, 12.0
NOMBRE_ARCHIVO = "<mejora en prueba>"


class TiempoAgotado(Exception):
    pass


class ErrorDePrueba(RuntimeError):
    """Lo lanza el «kira de prueba» cuando una orden pide algo que en la prueba no existe (audio, vídeo…)."""


class FuncionInexistente(AttributeError):
    """La orden usa kira.<algo> que no existe: fallaría SIEMPRE en el móvil."""


def sha256(codigo):
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()


# =====================================================================================
#  REVISIÓN (sin ejecutar nada)
# =====================================================================================
def avisos_de(arbol):
    """Los mismos avisos que da el laboratorio del PC (para que tú los leas antes de aplicar)."""
    avisos = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] in IMPORTS_SENSIBLES:
                    avisos.add(f"importa '{a.name}' (línea {n.lineno})")
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.split(".")[0] in IMPORTS_SENSIBLES:
                avisos.add(f"importa de '{n.module}' (línea {n.lineno})")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in LLAMADAS_SENSIBLES:
            avisos.add(f"llama a '{n.func.id}()' (línea {n.lineno})")
    return sorted(avisos)


def revisar_seguridad(arbol):
    """None si el módulo se puede probar en el móvil; si no, el motivo (se le devuelve a la IA para que lo corrija)."""
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] not in PERMITIDOS:
                    return (f"Línea {n.lineno}: en una mejora no se puede importar «{a.name}». Módulos permitidos: "
                            "math, random, datetime, time, json, re, collections, itertools, statistics, string… "
                            "Para archivos, audio y avisos usa las funciones de 'kira'.")
        elif isinstance(n, ast.ImportFrom):
            if n.level or not n.module or n.module.split(".")[0] not in PERMITIDOS:
                return f"Línea {n.lineno}: en una mejora no se puede importar de «{n.module or '.'}»."
            for a in n.names:
                if a.name in ATRIBUTOS_PROHIBIDOS:
                    return f"Línea {n.lineno}: en una mejora no se puede importar «{a.name}»."
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in BUILTINS_FUERA:
            return f"Línea {n.lineno}: en una mejora no se puede usar {n.func.id}()."
        elif isinstance(n, ast.Name) and n.id in ("__builtins__", "__import__", "__loader__", "__spec__"):
            return f"Línea {n.lineno}: en una mejora no se puede usar {n.id}."
        elif isinstance(n, ast.Attribute) and n.attr in ATRIBUTOS_PROHIBIDOS:
            if n.attr == "sleep":
                return (f"Línea {n.lineno}: no uses sleep(): deja a Kira bloqueada. Para esperar o avisar más tarde "
                        "usa kira.avisar_en(segundos, texto).")
            return f"Línea {n.lineno}: en una mejora no se puede usar «.{n.attr}»."
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            for t in TEXTOS_PROHIBIDOS:
                if t in n.value:
                    return f"Línea {n.lineno}: el texto «{t}» no se permite en una mejora."
    return None


# =====================================================================================
#  EJECUTAR CON TOPE DE TIEMPO (solo se vigila el código de la mejora: el resto va a velocidad normal)
# =====================================================================================
def con_tope(funcion, limite, *args, **kw):
    """Llama a funcion cortándola si pasa de 'limite' segundos. Solo vigila el hilo de la prueba y los hilos que
    abra la propia mejora: los demás hilos de Kira que arranquen mientras tanto (la voz, el oído, la charla) no se
    tocan y se sueltan solos al acabar la prueba (antes podían cortarse más tarde por error)."""
    fin = time.monotonic() + float(limite)
    hilo = threading.get_ident()
    activo = {"si": True}

    def local(frame, evento, arg):
        if time.monotonic() > fin:
            raise TiempoAgotado()
        return local

    def general(frame, evento, arg):
        propio = frame.f_code.co_filename == NOMBRE_ARCHIVO
        if propio:                                       # código de la mejora (aunque sea en un hilo suyo): se corta
            if time.monotonic() > fin:
                raise TiempoAgotado()
            return local
        if not activo["si"] or threading.get_ident() != hilo:
            if not activo["si"]:
                sys.settrace(None)                       # hilo ajeno que arrancó durante la prueba: se suelta
            return None
        if time.monotonic() > fin:
            raise TiempoAgotado()
        return None

    viejo = sys.gettrace()
    viejo_hilos = threading.gettrace() if hasattr(threading, "gettrace") else None
    sys.settrace(general)
    threading.settrace(general)
    try:
        return funcion(*args, **kw)
    finally:
        activo["si"] = False
        sys.settrace(viejo)
        threading.settrace(viejo_hilos)


def _importador(nombre, globales=None, locales=None, desde=(), nivel=0):
    if nivel or nombre.split(".")[0] not in PERMITIDOS:
        raise ImportError(f"en el laboratorio del móvil no se puede importar «{nombre}»")
    return builtins.__import__(nombre, globales, locales, desde, nivel)


def entorno(nombre):
    """Variables globales con las que se carga la mejora en la prueba: funciones peligrosas fuera, print callado."""
    seguros = {k: v for k, v in vars(builtins).items() if k not in BUILTINS_FUERA}
    seguros["__import__"] = _importador
    seguros["print"] = lambda *a, **k: None
    return {"__builtins__": seguros, "__name__": "kira_prueba_" + str(nombre)}


class KiraDePrueba:
    """El objeto 'kira' que reciben las órdenes (texto, kira) durante la prueba: todo en memoria, nada real."""

    def __init__(self):
        self._archivos, self._datos, self._dicho, self._avisos = {}, {}, [], []

    def __getattr__(self, nombre):
        raise FuncionInexistente(f"kira.{nombre} no existe (mira la lista de funciones de 'kira')")

    def medios(self, tipo=None):
        return []

    def importar(self, titulo):
        raise ErrorDePrueba("en la prueba no hay vídeos ni audios")

    def ffmpeg(self, entradas, salida, args=None):
        raise ErrorDePrueba("en la prueba no se procesa audio ni vídeo")

    def exportar(self, nombre):
        return False, "en la prueba no se exporta nada"

    def escribir(self, nombre, texto):
        self._archivos[str(nombre)] = str(texto)
        return str(nombre)

    def leer(self, nombre):
        if str(nombre) not in self._archivos:
            raise ErrorDePrueba(f"no existe {nombre}")
        return self._archivos[str(nombre)]

    def listar(self, *a, **k):
        return sorted(self._archivos)

    def existe(self, nombre):
        return str(nombre) in self._archivos

    def borrar(self, nombre):
        return self._archivos.pop(str(nombre), None) is not None

    def guardar_dato(self, clave, valor):
        json.dumps(valor)                                   # como el de verdad: solo datos que caben en JSON
        self._datos[str(clave)] = valor
        return True

    def leer_dato(self, clave, defecto=None):
        return self._datos.get(str(clave), defecto)

    def borrar_dato(self, clave):
        return self._datos.pop(str(clave), None) is not None

    def datos(self):
        return dict(self._datos)

    def recordar(self, texto):
        return 1

    def buscar_recuerdos(self, consulta, n=3):
        return []

    def avisar_en(self, segundos, texto):
        self._avisos.append((float(segundos), str(texto)))
        return len(self._avisos)

    def decir(self, texto):
        self._dicho.append(str(texto))

    def ahora(self):
        return time.strftime("%Y-%m-%d %H:%M")


def _parametros(fn):
    try:
        return [p for p in inspect.signature(fn).parameters.values()
                if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    except (TypeError, ValueError):
        return None


def _ultima_linea(e):
    return f"{type(e).__name__}: {str(e)[:160]}"


# =====================================================================================
#  EL LABORATORIO
# =====================================================================================
class LaboratorioMovil:
    donde = "móvil"

    def probar(self, nombre, codigo):
        res = {"ok": False, "sha256": sha256(codigo), "etapas": [], "avisos": [], "donde": self.donde}
        etapa = lambda n, ok, d="": res["etapas"].append({"nombre": n, "ok": ok, "detalle": str(d)[:300]})  # noqa: E731
        try:
            arbol = ast.parse(codigo)
        except SyntaxError as e:
            etapa("sintaxis", False, f"línea {e.lineno}: {e.msg}")
            return res
        etapa("sintaxis", True)
        res["avisos"] = avisos_de(arbol)
        etapa("revision_patrones", True, f"{len(res['avisos'])} aviso(s)")
        motivo = mi.precomprobar(codigo) or revisar_seguridad(arbol)
        if motivo:
            etapa("seguridad_movil", False, motivo)
            return res
        etapa("seguridad_movil", True, "solo módulos seguros, sin archivos, red ni sistema")

        g = entorno(nombre)
        try:
            con_tope(exec, TOPE_CARGA, compile(codigo, NOMBRE_ARCHIVO, "exec"), g)
            tabla = con_tope(g["registrar"], TOPE_CARGA)
        except TiempoAgotado:
            etapa("carga_aislada", False, f"Tiempo excedido ({TOPE_CARGA:g} s) al cargar: posible bucle infinito.")
            return res
        except BaseException as e:
            etapa("carga_aislada", False, _ultima_linea(e))
            return res
        etapa("carga_aislada", True, "CARGA_OK")

        motivo = self._contrato(g, tabla)
        etapa("contrato", motivo is None, motivo or "CONTRATO_OK")
        if motivo:
            return res
        juegos = {k: v for k, v in tabla.items() if k.startswith("juego ")}
        if juegos:
            motivo = self._jugar(juegos)
            etapa("juegos", motivo is None, motivo or "JUEGOS_OK " + ", ".join(juegos))
            if motivo:
                return res
        ordenes = {k: v for k, v in tabla.items() if not k.startswith("juego ")}
        fallo, raros = self._usar(ordenes)
        if fallo:
            etapa("prueba_de_uso", False, fallo)
            return res
        res["avisos"].extend(raros)
        etapa("prueba_de_uso", True, f"{len(ordenes)} orden(es) probadas con frases de ejemplo"
              + (f"; {len(raros)} aviso(s)" if raros else ""))
        res["ok"] = True
        return res

    @staticmethod
    def _contrato(g, tabla):
        if "KiraGodCore" in g:
            return "Un módulo no puede redefinir KiraGodCore."
        if not isinstance(tabla, dict) or not tabla:
            return "registrar() debe devolver un diccionario no vacío {\"orden\": función}."
        for prefijo, fn in tabla.items():
            if not (isinstance(prefijo, str) and prefijo and prefijo.strip() == prefijo and prefijo == prefijo.lower()):
                return f"prefijo no válido: {prefijo!r} (en minúsculas y sin espacios al principio o al final)"
            if not callable(fn):
                return f"'{prefijo}' no es una función"
            if prefijo.startswith("juego "):
                continue
            ps = _parametros(fn)
            if ps is not None and len(ps) not in (1, 2):
                return f"'{prefijo}' debe recibir (texto) o (texto, kira)"
        return None

    @staticmethod
    def _jugar(juegos):
        import motor_juegos_kira as motor
        for nombre, crear in juegos.items():
            ps = _parametros(crear)
            if ps is None or len(ps) != 1:
                return f"'{nombre}' debe ser una función crear(motor) que devuelve la clase del juego"

            def partida():
                clase = crear(motor)
                if not (isinstance(clase, type) and issubclass(clase, motor.Juego)):
                    return f"'{nombre}' no devuelve una clase de Juego"
                j = clase(semilla=1)
                for i in range(60 * 20):                          # 20 segundos de juego simulado
                    if i % 25 == 0:
                        j.tocar(40 + (i * 7) % 280, 60 + (i * 11) % 500)
                    if i % 40 == 0:
                        j.mover_dedo(180, 300, 30 if i % 80 else 0, 0 if i % 80 else 30)
                    t0 = time.monotonic()
                    j.paso(1 / 60)
                    if time.monotonic() - t0 > 0.5:
                        return f"'{nombre}': un fotograma tardó demasiado"
                    if j.estado in ("fin", "ganado"):
                        j.tocar(10, 10)
                    if len(j.piezas) > motor.MAX_PIEZAS:
                        return f"'{nombre}': demasiadas piezas"
                for d in j.dibujo():
                    if d[0] not in motor.FORMAS or len(d[5]) != 4:
                        return f"'{nombre}': dibuja algo que el motor no entiende"
                return None
            try:
                motivo = con_tope(partida, TOPE_JUEGO)
            except TiempoAgotado:
                return f"'{nombre}' va demasiado lento o se queda colgado"
            except BaseException as e:
                return f"'{nombre}' falla al jugar: {_ultima_linea(e)}"
            if motivo:
                return motivo
        return None

    @staticmethod
    def _usar(ordenes):
        """(motivo_si_falla, [avisos]) llamando a cada orden con frases de ejemplo. Falla si se cuelga o si usa una
        función de 'kira' que no existe; un error raro con una frase de ejemplo queda como aviso."""
        raros = []
        for prefijo, fn in ordenes.items():
            ps = _parametros(fn)
            con_kira = ps is not None and len(ps) == 2
            for ejemplo in EJEMPLOS_USO:
                kira = KiraDePrueba()
                try:
                    r = con_tope(fn, TOPE_LLAMADA, *((ejemplo, kira) if con_kira else (ejemplo,)))
                except TiempoAgotado:
                    return f"«{(prefijo + ' ' + ejemplo).strip()}» se queda colgada (más de {TOPE_LLAMADA:g} s)", raros
                except FuncionInexistente as e:
                    return f"«{prefijo}» usa {e}", raros
                except (ValueError, ErrorDePrueba):
                    continue                                      # orden que no se entiende: lo esperado
                except BaseException as e:
                    raros.append(f"«{(prefijo + ' ' + ejemplo).strip()}» da {_ultima_linea(e)}")
                    break
                if r is not None and not isinstance(r, str):
                    raros.append(f"«{prefijo}» devuelve {type(r).__name__} en vez de un texto")
                    break
        return None, raros[:6]


class LaboratorioDoble:
    """Prueba SIEMPRE en el móvil; si el laboratorio del ordenador está conectado y responde, también allí.
    Tiene .url/.token/.nombre de la pasarela del ordenador para lo que los consulta."""

    def __init__(self, pasarela=None, movil=None, salud=None):
        self.pasarela = pasarela
        self.movil = movil or LaboratorioMovil()
        self._salud = salud or self._salud_http

    def __getattr__(self, nombre):                           # url, token, nombre… de la pasarela del ordenador
        p = self.__dict__.get("pasarela")
        if p is None:
            if nombre in ("url", "token", "nombre"):
                return ""
            raise AttributeError(nombre)
        return getattr(p, nombre)

    def _salud_http(self):
        url = getattr(self.pasarela, "url", "") if self.pasarela is not None else ""
        if not url:
            return False
        try:
            with urllib.request.urlopen(url + "/salud", timeout=3) as r:
                return json.loads(r.read(200).decode("utf-8")).get("ok") is True
        except Exception:
            return False

    def probar(self, nombre, codigo):
        res = self.movil.probar(nombre, codigo)
        if not res.get("ok"):
            return res
        p = self.pasarela
        if p is None or not getattr(p, "url", "") or not getattr(p, "token", ""):
            return res
        if not self._salud():
            res["etapas"].append({"nombre": "ordenador", "ok": True,
                                  "detalle": "no responde ahora: basta con la prueba del móvil"})
            return res
        pc = p.probar(nombre, codigo)
        res["donde"] = "móvil y ordenador"
        for e in pc.get("etapas", []):
            if isinstance(e, dict):
                res["etapas"].append(dict(e, nombre="ordenador: " + str(e.get("nombre"))))
        res["avisos"] = sorted(set(res["avisos"]) | {str(a) for a in pc.get("avisos", [])})
        if pc.get("error") and not pc.get("etapas"):        # se cayó a mitad: vale la prueba del móvil
            res["etapas"].append({"nombre": "ordenador", "ok": True, "detalle": f"no se pudo usar: {pc['error']}"[:300]})
            return res
        if not (pc.get("ok") and pc.get("sha256") == res["sha256"]):
            res["ok"] = False
            res["rechazo"] = "ordenador"
            res["etapas"].append({"nombre": "ordenador", "ok": False, "detalle": (
                "el laboratorio del ORDENADOR no la aprueba (el del móvil sí). Si cambiaste sus pruebas, vuelve a "
                "sellarlo (python kira_master.py → sellar SELLAR NUCLEO); si no lo quieres usar, dile a Kira "
                "«desconéctate del ordenador» y bastará con el del móvil.")})
        return res
