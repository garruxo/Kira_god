"""catalogo_programas_kira.py — v3.84: el CATÁLOGO de programas de Kira (ventana «Mis programas» de Programando).

Pedido del dueño: «en la ventana Programando, un botón que abra una ventana con una lista de los programas,
aplicaciones o herramientas que ha aprendido por la web, con un botón para instalar en cada uno; otra con lo aprendido
por su cuenta, igual; y otra con los instalados y funcionando, con Desinstalar y Mejorar (que saca una barra para
darle la orden de mejorar ese programa en concreto)».

  - APRENDIDOS EN LA WEB: al estudiar, cada página que es un programa de verdad (un repositorio de GitHub o una página
    con descargas para Linux) se apunta aquí, en `<dir>/programas_vistos.json`. NO se instala: el botón «Instalar»
    le da a Kira la orden «instala <fuente>» (el camino de siempre: versiones, análisis, icono).
  - APRENDIDOS POR SU CUENTA: las soluciones con código que funcionó que sacó pensando/investigando sola.
    «Instalar» = acceso directo con icono (app web, como los demás programas de Kira).
  - INSTALADOS: los accesos directos del escritorio (programas de Kira y apps externas).
Puro (sin red ni Kivy); lo que escribe va con permisos 0600.
"""
import hashlib
import json
import os
import re
import time
import urllib.parse

RUTA = "programas_vistos.json"
TOPE = 200
_GITHUB = re.compile(r"^https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/(?:tree|releases|blob)\b.*)?/?$",
                     re.I)
_NO_REPO = {"topics", "features", "marketplace", "about", "pricing", "orgs", "sponsors", "collections", "trending",
            "login", "join", "settings", "search", "explore", "enterprise", "security", "customer-stories"}
_LINUX = (".appimage", ".deb", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".zip", ".run", ".sh",
          ".flatpakref", ".snap")


def _ruta(dir_):
    return os.path.join(dir_, RUTA)


def _leer(dir_):
    try:
        with open(_ruta(dir_), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _guardar(dir_, lista):
    os.makedirs(dir_, exist_ok=True)
    tmp = _ruta(dir_) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(lista[-TOPE:], f, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, _ruta(dir_))


def _id(fuente):
    return hashlib.sha1(str(fuente).encode("utf-8")).hexdigest()[:10]


def repo_de(url):
    """«https://github.com/dueño/proyecto[/…]» → (dueño, proyecto) o None (no las páginas generales de GitHub). PURO."""
    m = _GITHUB.match(str(url or "").strip())
    if not m or m.group(1).lower() in _NO_REPO:
        return None
    return m.group(1), m.group(2)


def es_programa(pag):
    """¿Esta página es un PROGRAMA que se podría instalar? → {nombre, fuente, archivos} o None. PURO.
    Un repositorio de GitHub, o una página con descargas para Linux (no basta con un .exe/.dmg/.apk)."""
    url = str((pag or {}).get("url") or "")
    r = repo_de(url)
    if r:
        return {"nombre": r[1], "fuente": f"https://github.com/{r[0]}/{r[1]}", "archivos": []}
    linux = [d for d in (pag or {}).get("descargas") or []
             if str(d.get("archivo") or d.get("url") or "").lower().endswith(_LINUX)]
    if not linux:
        return None
    titulo = " ".join(str((pag or {}).get("titulo") or "").split())
    nombre = re.split(r"\s+[-|–—:·]\s+", titulo)[0][:60] if titulo else ""
    if not nombre:
        nombre = urllib.parse.urlsplit(url).netloc or "programa"
    return {"nombre": nombre, "fuente": url, "archivos": [str(d.get("archivo") or "")[:80] for d in linux[:3]]}


def anotar_web(dir_, pag, tema=""):
    """Si la página es un programa, lo apunta (sin repetir). Devuelve el apunte nuevo o None."""
    p = es_programa(pag)
    if not p:
        return None
    lista = _leer(dir_)
    iid = _id(p["fuente"])
    if any(e.get("id") == iid for e in lista):
        return None
    texto = " ".join(str((pag or {}).get("texto") or "").split())
    e = {"id": iid, "nombre": p["nombre"], "fuente": p["fuente"], "pagina": str((pag or {}).get("url") or "")[:500],
         "desc": texto[:200], "tema": str(tema or "")[:80], "archivos": p["archivos"], "cuando": int(time.time())}
    lista.append(e)
    _guardar(dir_, lista)
    return e


def web(dir_):
    return list(reversed(_leer(dir_)))


def quitar_web(dir_, iid):
    lista = _leer(dir_)
    nueva = [e for e in lista if e.get("id") != iid]
    if len(nueva) == len(lista):
        return False
    _guardar(dir_, nueva)
    return True


def propios(estado):
    """Lo que sacó POR SU CUENTA (pensando, investigando, en su foco): soluciones con código que funcionó. PURO."""
    sal = []
    for tema, s in ((estado or {}).get("soluciones") or {}).items():
        if not isinstance(s, dict):
            continue
        exp = s.get("experimento") if isinstance(s.get("experimento"), dict) else {}
        codigo = s.get("codigo") or exp.get("codigo") or ""
        ok = s.get("ok", exp.get("ok", True))
        if codigo and ok is not False:
            sal.append({"id": _id("sol:" + str(tema)), "clave": str(tema),
                        "tema": str(s.get("semilla") or tema), "codigo": str(codigo),
                        "respuesta": str(s.get("respuesta") or "")[:200], "veces": int(s.get("veces") or 1),
                        "cuando": int(s.get("cuando") or 0)})
    sal.sort(key=lambda x: -x["cuando"])
    return sal


def _plano(t):
    return re.sub(r"[\W_]+", "", str(t or "").lower())


def instalado(accesos, nombre="", fuente=""):
    """¿Ya está instalado (por su título o su fuente)? PURO."""
    n = _plano(nombre)
    for a in accesos or []:
        if fuente and fuente in (a.get("fuente"), a.get("pagina")):
            return True
        if n and _plano(a.get("titulo")) == n:
            return True
    return False


def filas(vistos, mios, accesos):
    """Las tres pestañas de la ventana «Mis programas». PURO: {'web': [...], 'propios': [...], 'instalados': [...]},
    cada fila {seccion, texto, detalle, etiqueta, botones}."""
    f_web = []
    for e in vistos:
        if instalado(accesos, e.get("nombre"), e.get("fuente")):
            continue
        det = urllib.parse.urlsplit(e.get("fuente") or "").netloc
        if e.get("archivos"):
            det += " · " + ", ".join(x for x in e["archivos"] if x)
        if e.get("desc"):
            det += " · " + e["desc"][:120]
        f_web.append({"seccion": "web", "texto": e.get("nombre") or "programa", "detalle": det,
                      "etiqueta": "GitHub" if "github.com" in (e.get("fuente") or "") else "Web",
                      "botones": [{"texto": "Instalar", "accion": "decir:instala " + e["fuente"]},
                                  {"texto": "Quitar de la lista", "accion": "hacer:prog:olvidar:" + e["id"]}]})
    f_mios = []
    for s in mios:
        if instalado(accesos, s["tema"]):
            continue
        lineas = len([x for x in s["codigo"].splitlines() if x.strip()])
        det = f"{lineas} líneas de Python, probado y funcionando"
        if s["veces"] > 1:
            det += f" · mejorado {s['veces']} veces"
        if s["respuesta"]:
            det += " · " + s["respuesta"][:120]
        f_mios.append({"seccion": "propios", "texto": s["tema"][:70], "detalle": det, "etiqueta": "Con código",
                       "botones": [{"texto": "Instalar", "accion": "hacer:prog:instalar:" + s["id"]}]})
    f_inst = []
    for a in accesos:
        ext = a.get("tipo") == "externa"
        det = ("app instalada" + (f" · de {urllib.parse.urlsplit(a.get('fuente') or '').netloc}"
                                  if a.get("fuente") else "")) if ext else "programa de Kira (app web)"
        f_inst.append({"seccion": "instalados", "texto": a.get("titulo") or "programa", "detalle": det,
                       "etiqueta": "App" if ext else "Comprobado",
                       "botones": [{"texto": "Abrir", "accion": "app:acceso:" + a.get("id", "")},
                                   {"texto": "Mejorar", "pedir": f"¿Qué quieres que mejore de «{a.get('titulo')}»?",
                                    "accion": "decir:mejora el programa «" + str(a.get("titulo") or "") + "»: {texto}"},
                                   {"texto": "Desinstalar", "accion": "hacer:prog:quitar:" + a.get("id", ""),
                                    "dos": True}]})
    return {"web": f_web, "propios": f_mios, "instalados": f_inst}


def pestanas(vistos, mios, accesos):
    """Para la pantalla (pestañas con filas). PURO."""
    f = filas(vistos, mios, accesos)
    return [
        {"id": "web", "titulo": f"Aprendidos en la web ({len(f['web'])})", "filas": f["web"],
         "secciones": [["web", "Programas y herramientas que he visto estudiando"]],
         "texto": "Aún no he visto ningún programa estudiando. Cuando estudie una página que sea un programa "
                  "(un GitHub o una web con descargas para Linux) lo apunto aquí."},
        {"id": "propios", "titulo": f"Aprendidos por mi cuenta ({len(f['propios'])})", "filas": f["propios"],
         "secciones": [["propios", "Lo que he programado yo sola pensando e investigando"]],
         "texto": "Aún no he sacado ningún programa por mi cuenta."},
        {"id": "instalados", "titulo": f"Instalados ({len(f['instalados'])})", "filas": f["instalados"],
         "secciones": [["instalados", "Instalados y funcionando"]],
         "texto": "Aún no hay nada instalado."},
    ]


_MEJORA = re.compile(r"^\s*(?:kira[\s,]+)?mejora\s+(?:el\s+programa|la\s+app|la\s+aplicaci[oó]n|la\s+herramienta)\s+"
                     r"[«\"']?(.+?)[»\"']?\s*:\s*(.+?)\s*$", re.I | re.S)


def orden_mejorar(texto):
    """«mejora el programa «X»: <qué>» → (X, qué) o None. PURO."""
    m = _MEJORA.match(str(texto or ""))
    if not m or len(m.group(2).strip()) < 3:
        return None
    return m.group(1).strip(), m.group(2).strip()


def pedido_mejora(titulo, codigo, que):
    """Lo que se le pide al cerebro para mejorar un programa suyo (con su código de ahora). PURO."""
    return (f"Mejora el programa «{titulo}»: {que}\nDevuélveme el programa ENTERO ya mejorado, en Python, en un bloque "
            f"```python```. Mantén lo que ya funciona.\nCódigo actual:\n```python\n{codigo}\n```")
