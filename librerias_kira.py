# -*- coding: utf-8 -*-
"""
librerias_kira.py - Kira se descarga LIBRERÍAS de Python (de PyPI, el almacén oficial) para usarlas al programar.

  «Kira, instala la librería kivymd»  -> busca en PyPI, mira si tiene versión «de Python puro» (las únicas que se pueden
                                         instalar en el móvil sin compilar), sus dependencias, tamaño y licencia, y te lo
                                         ENSEÑA. Se instala solo cuando tú tocas «Instalar» DOS veces (como las mejoras).
  «mis librerías» · «quita la librería kivymd» · «busca librerías de …»
Se guardan en KIRA_DATA_DIR/librerias (que va en sys.path). Desde ese momento el editor, los programas, los
experimentos y las mejoras pueden importarlas (su nombre se añade a la lista de lo permitido).
Cada archivo se comprueba con la huella sha256 que publica PyPI.

Límites (honestos): las librerías con partes compiladas en C (numpy, pandas, torch, scikit-learn…) no tienen versión
para Android en PyPI: no se pueden bajar así. numpy va DENTRO del APK (compilado aparte). Una librería instalada
corre dentro de Kira con sus permisos: por eso la decides tú, una a una.
Lógica pura (sin Kivy): se prueba en el PC.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
import urllib.parse
import urllib.request
import zipfile

PYPI = "https://pypi.org/pypi/{}/json"
MAX_BYTES = 40 * 1024 * 1024          # por rueda
MAX_PAQUETES = 15                     # una librería con más dependencias que esto, mejor no en el móvil
PY = (3, 11)                          # la versión de Python del APK

# lo que ya trae Kira (no se baja): la librería estándar y lo que va dentro del APK
YA_INCLUIDAS = {"kivy", "pyjnius", "jnius", "plyer", "pypdf", "certifi", "numpy", "setuptools", "pip", "wheel",
                "typing-extensions", "typing_extensions", "dataclasses", "enum34", "importlib-metadata", "zipp",
                "importlib-resources", "pathlib", "futures", "six"}


class LibreriaError(RuntimeError):
    pass


def carpeta_base():
    return os.path.join(os.environ.get("KIRA_DATA_DIR") or os.path.expanduser("~"), "librerias")


def normalizar(nombre):
    """El nombre canónico de PyPI («KivyMD», «kivy_md» -> «kivymd» / «kivy-md»)."""
    return re.sub(r"[-_.]+", "-", str(nombre or "").strip().lower())


# =====================================================================================
#  DEPENDENCIAS: «requires_dist» con sus condiciones
# =====================================================================================
def _version(t):
    return tuple(int(x) for x in re.findall(r"\d+", t)[:3]) or (0,)


def _cumple_marcador(marcador):
    """¿Hace falta esta dependencia en el móvil? (Python 3.11, Android/Linux, sin extras)."""
    m = marcador.strip()
    if not m:
        return True
    if "extra" in m:
        return False                                        # «extra == "dev"»: solo si las pides
    entorno = {"python_version": "3.11", "python_full_version": "3.11.0", "sys_platform": "linux",
               "platform_system": "Linux", "os_name": "posix", "implementation_name": "cpython",
               "platform_python_implementation": "CPython", "platform_machine": "aarch64"}

    def uno(expr):
        mm = re.match(r"""\s*(\w+)\s*(==|!=|>=|<=|>|<|~=|in|not in)\s*['"]([^'"]*)['"]\s*$""", expr)
        if not mm:
            mm2 = re.match(r"""\s*['"]([^'"]*)['"]\s*(==|!=|in|not in)\s*(\w+)\s*$""", expr)
            if not mm2:
                return True
            valor, op, var = mm2.group(1), mm2.group(2), mm2.group(3)
            actual = entorno.get(var, "")
            return {"==": actual == valor, "!=": actual != valor, "in": actual in valor,
                    "not in": actual not in valor}[op]
        var, op, valor = mm.groups()
        actual = entorno.get(var, "")
        if var.startswith("python"):
            a, b = _version(actual), _version(valor)
            return {"==": a[:len(b)] == b, "!=": a[:len(b)] != b, ">=": a >= b, "<=": a <= b, ">": a > b, "<": a < b,
                    "~=": a >= b}.get(op, True)
        return {"==": actual == valor, "!=": actual != valor, "in": actual in valor, "not in": actual not in valor}.get(op, True)

    for o in re.split(r"\s+or\s+", m):
        if all(uno(y) for y in re.split(r"\s+and\s+", o.strip("() "))):
            return True
    return False


def cumple_python(especificacion, py=PY):
    """«>=3.8, <4» -> ¿vale para el Python del móvil?"""
    for parte in str(especificacion or "").split(","):
        m = re.match(r"\s*(==|!=|>=|<=|>|<|~=)\s*([\d.*]+)", parte)
        if not m:
            continue
        op, v = m.groups()
        comodin = v.endswith(".*")
        b = _version(v)
        a = py[:len(b)] if comodin or op in ("==", "!=") else py
        ok = {"==": a == b, "!=": a != b, ">=": a >= b, "<=": a <= b, ">": a > b, "<": a < b, "~=": py >= b}[op]
        if not ok:
            return False
    return True


def dependencias(requires_dist):
    """[nombre] de las dependencias que hacen falta en el móvil."""
    sal = []
    for r in requires_dist or []:
        req, _, marcador = str(r).partition(";")
        nombre = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", req)
        if nombre and _cumple_marcador(marcador):
            n = normalizar(nombre.group(1))
            if n not in sal:
                sal.append(n)
    return sal


def rueda_pura(urls):
    """La rueda (.whl) de Python puro de una versión (la que vale en cualquier móvil), o None."""
    candidatas = [u for u in urls or [] if u.get("packagetype") == "bdist_wheel"
                  and re.search(r"-(?:py3|py2\.py3|py3\d*)-none-any\.whl$", u.get("filename", ""))]
    return candidatas[0] if candidatas else None


# =====================================================================================
#  LAS LIBRERÍAS
# =====================================================================================
class Librerias:
    def __init__(self, carpeta=None, abrir=None):
        self.carpeta = carpeta or carpeta_base()
        os.makedirs(self.carpeta, exist_ok=True)
        self.ruta_indice = os.path.join(self.carpeta, "_indice_kira.json")
        self._abrir = abrir
        self.pypi = PYPI                            # (en las pruebas, un PyPI falso)
        self._lock = threading.Lock()
        try:
            with open(self.ruta_indice, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            d = {}
        self.indice = d if isinstance(d, dict) else {}
        self.pendiente = None                       # el plan que espera tus dos toques

    # ---------- en marcha ----------
    def activar(self):
        """Pone la carpeta en sys.path (al arrancar Kira) para que se puedan importar."""
        if self.carpeta not in sys.path:
            sys.path.insert(0, self.carpeta)

    def importables(self):
        """Nombres que se pueden importar gracias a las librerías instaladas (para el editor y el laboratorio)."""
        s = set()
        for v in self.indice.values():
            s.update(v.get("importa", []))
        return s

    def _guardar(self):
        tmp = self.ruta_indice + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.indice, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta_indice)

    # ---------- PyPI ----------
    def _json(self, url):
        import descargas_kira as dk
        req = urllib.request.Request(url, headers={"User-Agent": "KiraApp/1.0", "Accept": "application/json"})
        try:
            with (self._abrir or dk.abrir_https)(req, timeout=30) as r:
                return json.loads(r.read(8_000_000).decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise LibreriaError("No existe ninguna librería con ese nombre en PyPI.")
            raise LibreriaError(f"PyPI respondió {e.code}.")
        except LibreriaError:
            raise
        except Exception as e:
            raise LibreriaError(f"No pude conectar con PyPI ({e}). ¿Hay internet?")

    def ficha(self, nombre):
        """{'nombre', 'version', 'resumen', 'licencia', 'rueda', 'deps', 'web'} de la última versión."""
        d = self._json(self.pypi.format(urllib.parse.quote(normalizar(nombre))))
        info = d.get("info") or {}
        version = info.get("version") or ""
        rueda = rueda_pura(d.get("urls") or (d.get("releases") or {}).get(version))
        req_py = info.get("requires_python") or ""
        if not cumple_python(req_py):
            raise LibreriaError(f"«{info.get('name')}» {version} necesita Python {req_py} y el móvil tiene 3.11.")
        return {"nombre": normalizar(info.get("name") or nombre), "nombre_bonito": info.get("name") or nombre,
                "version": version, "resumen": (info.get("summary") or "")[:200],
                "licencia": (info.get("license_expression") or info.get("license") or "")[:60].split("\n")[0],
                "rueda": rueda, "deps": dependencias(info.get("requires_dist")),
                "web": info.get("home_page") or (info.get("project_urls") or {}).get("Homepage", "")}

    def preparar(self, nombre):
        """El PLAN para instalar una librería y lo que necesita (sin instalar nada). Queda como pendiente de tus dos
        toques. Lanza LibreriaError si no se puede (compilada, no existe, demasiadas dependencias…)."""
        plan, vistos, cola = [], set(), [normalizar(nombre)]
        while cola:
            n = cola.pop(0)
            if n in vistos or n in YA_INCLUIDAS or n.replace("-", "_") in YA_INCLUIDAS:
                continue
            vistos.add(n)
            instalada = self.indice.get(n)
            f = self.ficha(n)
            if instalada and instalada.get("version") == f["version"]:
                continue
            if f["rueda"] is None:
                raise LibreriaError(
                    f"«{f['nombre_bonito']}» lleva partes compiladas (C/C++) y PyPI no tiene versión para el móvil: no la "
                    "puedo instalar aquí." + (" Para cálculo numérico ya tengo numpy dentro." if n in ("scipy", "pandas")
                                               else "") + (" Es una dependencia de lo que pediste." if plan else ""))
            plan.append(f)
            if len(plan) > MAX_PAQUETES:
                raise LibreriaError(f"Necesita más de {MAX_PAQUETES} librerías: es demasiado grande para el móvil.")
            cola.extend(f["deps"])
        if not plan:
            raise LibreriaError(f"«{nombre}» ya está instalada (o ya viene dentro de Kira).")
        total = sum(int(p["rueda"].get("size") or 0) for p in plan)
        self.pendiente = {"pedida": normalizar(nombre), "plan": plan, "bytes": total}
        return self.pendiente

    def texto_plan(self, p=None):
        p = p or self.pendiente
        if not p:
            return ""
        principal = p["plan"][0]
        otras = [f"{x['nombre_bonito']} {x['version']}" for x in p["plan"][1:]]
        return (f"«{principal['nombre_bonito']}» {principal['version']}: {principal['resumen'] or 'sin descripción'}\n"
                f"Licencia: {principal['licencia'] or 'no la dice'} · {p['bytes'] / 1e6:.1f} MB"
                + (f"\nTambién necesita: {', '.join(otras)}" if otras else "")
                + "\nSe baja de PyPI y se comprueba con su huella. Correrá dentro de Kira con sus permisos.")

    # ---------- instalar (SOLO con tu confirmación) ----------
    def instalar_pendiente(self, confirmado=False, progreso=None, cancelado=None):
        """Instala el plan pendiente. Sin confirmado=True (tus dos toques en la pantalla) no hace nada."""
        if confirmado is not True:
            raise LibreriaError("Falta tu confirmación: no he instalado nada.")
        p, self.pendiente = self.pendiente, None
        if not p:
            raise LibreriaError("No hay ninguna librería esperando para instalar.")
        import descargas_kira as dk
        hechas = []
        for i, f in enumerate(reversed(p["plan"])):             # primero las dependencias
            r = f["rueda"]
            if int(r.get("size") or 0) > MAX_BYTES:
                raise LibreriaError(f"«{f['nombre_bonito']}» pesa demasiado ({int(r['size']) / 1e6:.0f} MB).")
            tmp = os.path.join(self.carpeta, "_bajando_" + r["filename"])

            def prog(fr, b, t, i_=i):
                if progreso:
                    progreso((i_ + fr) / len(p["plan"]), f"Bajando {f['nombre_bonito']} ({i_ + 1} de {len(p['plan'])})")
            try:
                dk.bajar(r["url"], tmp, int(r.get("size") or 0) or None, f["nombre_bonito"],
                         abrir=self._abrir or dk.abrir_https, progreso=prog, cancelado=cancelado)
            except dk.DescargaError as e:
                raise LibreriaError(str(e))
            sha = (r.get("digests") or {}).get("sha256")
            h = hashlib.sha256()
            with open(tmp, "rb") as fh:
                for b in iter(lambda: fh.read(1 << 20), b""):
                    h.update(b)
            if sha and h.hexdigest() != sha:
                os.remove(tmp)
                raise LibreriaError(f"La huella de «{f['nombre_bonito']}» no coincide con la de PyPI: no la instalo.")
            try:
                archivos, importa = self._extraer(tmp)
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            with self._lock:
                viejo = self.indice.get(f["nombre"])
                if viejo:
                    self._borrar_archivos(viejo, conservar=set(archivos))
                self.indice[f["nombre"]] = {"version": f["version"], "nombre": f["nombre_bonito"], "resumen": f["resumen"],
                                            "licencia": f["licencia"], "archivos": archivos, "importa": sorted(importa),
                                            "bytes": int(r.get("size") or 0), "fecha": time.strftime("%Y-%m-%d"),
                                            "por": p["pedida"]}
                self._guardar()
            hechas.append(f"{f['nombre_bonito']} {f['version']}")
        self.activar()
        try:
            import importlib
            importlib.invalidate_caches()
        except Exception:
            pass
        return hechas

    def _extraer(self, rueda):
        archivos, importa = [], set()
        base = os.path.realpath(self.carpeta)
        with zipfile.ZipFile(rueda) as z:
            for n in z.namelist():
                if n.endswith("/"):
                    continue
                destino = os.path.realpath(os.path.join(self.carpeta, n))
                if not destino.startswith(base + os.sep) or ".." in n.split("/") or n.startswith("/"):
                    raise LibreriaError(f"La rueda trae una ruta peligrosa ({n}): no la instalo.")
                partes = n.split("/")
                if partes[0].endswith(".dist-info") and partes[-1] == "top_level.txt":
                    importa.update(l.strip() for l in z.read(n).decode("utf-8", "replace").splitlines() if l.strip())
                elif not partes[0].endswith((".dist-info", ".data")):
                    raiz = partes[0][:-3] if partes[0].endswith(".py") and len(partes) == 1 else partes[0]
                    if re.match(r"^[A-Za-z_]\w*$", raiz):
                        importa.add(raiz)
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with z.open(n) as fuente, open(destino, "wb") as sal:
                    shutil.copyfileobj(fuente, sal)
                archivos.append(n)
        return archivos, importa

    # ---------- gestionar ----------
    def _borrar_archivos(self, e, conservar=()):
        carpetas = set()
        for n in e.get("archivos", []):
            if n in conservar:
                continue
            r = os.path.join(self.carpeta, n)
            try:
                os.remove(r)
            except OSError:
                pass
            carpetas.add(os.path.dirname(r))
        for c in sorted(carpetas, key=len, reverse=True):
            while c.startswith(self.carpeta + os.sep):
                try:
                    os.rmdir(c)
                except OSError:
                    break
                c = os.path.dirname(c)

    def quitar(self, nombre):
        n = normalizar(nombre)
        with self._lock:
            e = self.indice.pop(n, None)
            if e is None:
                raise LibreriaError(f"No tengo instalada «{nombre}».")
            self._borrar_archivos(e)
            self._guardar()
        for m in list(sys.modules):                         # lo ya cargado se olvida (se libera al reiniciar)
            if m.split(".")[0] in e.get("importa", []):
                sys.modules.pop(m, None)
        return e

    def texto_lista(self):
        if not self.indice:
            return ("No tengo librerías instaladas. Dime «instala la librería …» (por ejemplo kivymd, rich, sympy, "
                    "networkx, beautifulsoup4) y te enseño qué es antes de instalarla.")
        lineas = [f"Mis librerías ({len(self.indice)}):"]
        for n, e in sorted(self.indice.items()):
            lineas.append(f"- {e.get('nombre', n)} {e.get('version', '')}: {e.get('resumen', '')[:70]} "
                          f"(se importa como: {', '.join(e.get('importa', [])) or '?'})")
        return "\n".join(lineas)


_CACHE = {"mtime": None, "nombres": frozenset()}


def importables_instaladas():
    """Lo que se puede importar gracias a las librerías que TÚ instalaste (lo usan el editor y el laboratorio)."""
    ruta = os.path.join(carpeta_base(), "_indice_kira.json")
    try:
        mt = os.path.getmtime(ruta)
    except OSError:
        return frozenset()
    if _CACHE["mtime"] != mt:
        try:
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
            _CACHE["nombres"] = frozenset(x for v in d.values() for x in v.get("importa", []))
        except (OSError, ValueError, AttributeError):
            _CACHE["nombres"] = frozenset()
        _CACHE["mtime"] = mt
    return _CACHE["nombres"]


def con_numpy():
    try:
        import importlib.util
        return importlib.util.find_spec("numpy") is not None
    except Exception:
        return False


def extra_permitidos():
    """Módulos de fuera de la librería estándar que el modo seguro y el laboratorio aceptan: numpy (si va en el APK)
    y las librerías instaladas por ti."""
    return importables_instaladas() | ({"numpy"} if con_numpy() else frozenset())


# =====================================================================================
#  QUÉ SE PIDE
# =====================================================================================
_INSTALA = re.compile(r"^(?:kira[\s,]+)?(?:inst[aá]la(?:te|me)?|desc[aá]rga(?:te|me)?|b[aá]ja(?:te|me)?|a[nñ]ade|pon(?:me)?)"
                      r"\s+(?:la\s+)?(?:librer[ií]a|biblioteca|paquete|m[oó]dulo\s+de\s+python|libreria)\s+(?:de\s+python\s+)?"
                      r"[«\"']?(?P<n>[A-Za-z0-9][A-Za-z0-9._-]*)[»\"']?\s*$", re.I)
_QUITA = re.compile(r"^(?:kira[\s,]+)?(?:quita|borra|desinstala|elimina)\s+(?:la\s+)?(?:librer[ií]a|biblioteca|paquete)\s+"
                    r"[«\"']?(?P<n>[A-Za-z0-9][A-Za-z0-9._-]*)[»\"']?\s*$", re.I)
_LISTA = re.compile(r"^(?:kira[\s,]+)?(?:mis|qu[eé]|las|tus)\s+(?:librer[ií]as|bibliotecas|paquetes)(?:\s+tienes)?\s*\??$", re.I)


def interpretar(texto):
    t = " ".join(str(texto or "").split()).strip(" ¿?¡!.")
    m = _INSTALA.match(t)
    if m:
        return {"accion": "preparar", "nombre": m.group("n")}
    m = _QUITA.match(t)
    if m:
        return {"accion": "quitar", "nombre": m.group("n")}
    if _LISTA.match(t):
        return {"accion": "lista"}
    return None
