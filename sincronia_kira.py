# -*- coding: utf-8 -*-
"""
sincronia_kira.py - El «sistema nervioso» entre la Kira del MÓVIL y KiraOS (v2.87). VA EN EL APK; puro, sin red.

Lo pidió el dueño: «KiraOS será el cerebro central; la Kira del móvil es parte de sus redes neuronales: piensa,
estudia y le envía lo aprendido». Eligió:
  - el móvil envía SOLO LO NUEVO, solo, en cuanto llega a casa, y SIN BORRAR nada de KiraOS (se suma, no se pisa);
  - al revés también: el móvil recibe lo que aprende KiraOS, sus mejoras de sistema y hasta su aspecto (tema);
  - fuera de casa el móvil piensa y estudia con su cerebro pequeño y lo guarda para enviarlo al volver.

Qué viaja del MÓVIL a KiraOS (`paquete_movil`): los recuerdos nuevos del baúl (lo estudiado, las charlas, las fichas),
los pensamientos nuevos del cuaderno, las soluciones, tus encargos («pregúntate…») y el foco.
Qué viaja de KiraOS al MÓVIL (`paquete_para_movil`): sus recuerdos nuevos (menos los que vinieron del móvil), sus
soluciones, el tema (colores) que KiraOS le ponga y las MEJORAS de sistema que KiraOS preparó para él.

Reglas que no cambian:
  - una mejora que llega de KiraOS NO se instala sola: el móvil la vuelve a probar en SU laboratorio y espera tus dos
    toques (o la auto-mejora, si tú la encendiste). Aquí solo se guarda como «recibida»;
  - el tema es solo DATOS (colores con forma #rrggbb y nombres conocidos): se valida antes de guardarlo;
  - las claves (Claude, GitHub), la conexión y los modelos nunca viajan.

Todo es idempotente: si un paquete llega dos veces, el baúl no duplica (Recuerdos.guardar reconoce lo idéntico).
"""
import hashlib
import json
import os
import re
import time

VERSION = 1
MAX_REC = 300                       # recuerdos por viaje (si hay más, se hacen varios viajes)
MAX_NOTAS = 200
MAX_IMPORTADOS = 20000
ESTADO_MOVIL = "sincronia.json"
ESTADO_KIRAOS = "sincronia_kiraos.json"
TEMA_KIRAOS = "tema_kiraos.json"     # en el móvil: el aspecto que le puso KiraOS
TEMA_MOVIL = "tema_movil.json"       # en KiraOS: el aspecto que quiere para el móvil
MEJORAS_RECIBIDAS = "mejoras_kiraos"  # en el móvil: carpeta con las mejoras que llegan (pendientes de tus dos toques)
PARA_MOVIL = "para_movil"            # en KiraOS: carpeta con las mejoras preparadas para el móvil


# =====================================================================================
#  ESTADO (en disco, escritura atómica)
# =====================================================================================
def _leer(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(defecto)) else defecto
    except (OSError, ValueError):
        return defecto


def _escribir(ruta, datos):
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, ruta)


def estado_movil(dir_):
    d = _leer(os.path.join(dir_, ESTADO_MOVIL), {})
    d.setdefault("rec_enviados", 0)       # hasta qué recuerdo (número) ya se envió
    d.setdefault("notas_desde", 0)        # pensamientos con «cuando» mayor que esto aún no enviados
    d.setdefault("sol_desde", 0)
    d.setdefault("cursor", {})            # lo que ya tiene de KiraOS (lo da KiraOS)
    d.setdefault("importados", [])        # recuerdos que llegaron de KiraOS (no se devuelven)
    d.setdefault("ultima", 0)
    d.setdefault("resumen", "")
    d.setdefault("enviados_total", 0)
    d.setdefault("recibidos_total", 0)
    return d


def guardar_estado_movil(dir_, d):
    d["importados"] = d.get("importados", [])[-MAX_IMPORTADOS:]
    _escribir(os.path.join(dir_, ESTADO_MOVIL), d)


def estado_kiraos(dir_):
    d = _leer(os.path.join(dir_, ESTADO_KIRAOS), {})
    d.setdefault("importados", [])        # recuerdos de KiraOS que vinieron del móvil (no se le devuelven)
    d.setdefault("ultima", 0)
    d.setdefault("recibidos_total", 0)
    return d


def guardar_estado_kiraos(dir_, d):
    d["importados"] = d.get("importados", [])[-MAX_IMPORTADOS:]
    _escribir(os.path.join(dir_, ESTADO_KIRAOS), d)


# =====================================================================================
#  PIEZAS: recuerdos, pensamientos, encargos, foco
# =====================================================================================
def _recuerdos_desde(rec, desde, excluir, maximo):
    """[(n, dict)] de los recuerdos con número > desde (sin los de `excluir`), como mucho `maximo`."""
    sal, total, n = [], rec.total(), int(desde)
    excl = set(excluir or ())
    while n < total and len(sal) < maximo:
        n += 1
        if n in excl:
            continue
        r = rec.leer(n)
        if r and r.get("texto"):
            sal.append((n, {"texto": r["texto"], "tema": r.get("tema", ""), "fuente": r.get("fuente", ""),
                            "pregunta": r.get("pregunta", ""), "t": r.get("t", 0)}))
    return sal, n


def _meter_recuerdos(rec, lista):
    """Guarda los recuerdos que llegan. Devuelve (nuevos, [números locales])."""
    nuevos, nums = 0, []
    for r in lista or []:
        if not isinstance(r, dict) or not r.get("texto"):
            continue
        antes = rec.total()
        n = rec.guardar(str(r["texto"]), tema=str(r.get("tema", "")), fuente=str(r.get("fuente", "") or "kira"),
                        pregunta=str(r.get("pregunta", "")))
        if n:
            nums.append(n)
            if rec.total() > antes:
                nuevos += 1
    return nuevos, nums


def _pensamientos(dir_):
    import pensador_kira as pn
    ruta = os.path.join(dir_, "pensamientos.json")
    return pn, ruta, pn.cargar(ruta)


def _clave_nota(nt):
    return (int(nt.get("cuando", 0) or 0), str(nt.get("pregunta", ""))[:200])


def _fusionar_pensamientos(dir_, notas, soluciones):
    """Suma notas (sin repetir) y soluciones (se queda con la mejor). Devuelve (notas_nuevas, soluciones_nuevas)."""
    if not notas and not soluciones:
        return 0, 0
    pn, ruta, est = _pensamientos(dir_)
    vistas = {_clave_nota(n) for n in est.get("notas", [])}
    nn = 0
    for nt in notas or []:
        if isinstance(nt, dict) and nt.get("pregunta") and _clave_nota(nt) not in vistas:
            est.setdefault("notas", []).append(nt)
            vistas.add(_clave_nota(nt))
            nn += 1
            q = pn._norm(nt.get("pregunta", ""))
            if q and q not in est.setdefault("vistas", []):
                est["vistas"].append(q)
    est["notas"] = sorted(est.get("notas", []), key=lambda x: x.get("cuando", 0))[-pn.MAX_NOTAS:]
    ns = 0
    sols = est.setdefault("soluciones", {})
    for tema, s in (soluciones or {}).items():
        if not isinstance(s, dict):
            continue
        prev = sols.get(tema)
        if prev is None or pn._punt_sol(s) > pn._punt_sol(prev) or \
                (pn._punt_sol(s) == pn._punt_sol(prev) and s.get("cuando", 0) > prev.get("cuando", 0)):
            mejor = dict(s)
            mejor["veces"] = max(int(s.get("veces", 1) or 1), int((prev or {}).get("veces", 0) or 0))
            sols[tema] = mejor
            ns += 1
    pn.guardar(est, ruta)
    return nn, ns


def _foco(dir_):
    return _leer(os.path.join(dir_, "foco.json"), {})


# =====================================================================================
#  EL MÓVIL ARMA SU PAQUETE (solo lo nuevo)
# =====================================================================================
def paquete_movil(dir_, rec, maximo=MAX_REC):
    """Lo nuevo del móvil para KiraOS. Devuelve (paquete, marcas): `marcas` se guardan SOLO si KiraOS lo recibió bien
    (ver `confirmar_envio`)."""
    est = estado_movil(dir_)
    lista, hasta = _recuerdos_desde(rec, est["rec_enviados"], est["importados"], maximo)
    _pn, _ruta, pen = _pensamientos(dir_)
    notas = [n for n in pen.get("notas", []) if (n.get("cuando", 0) or 0) > est["notas_desde"]][-MAX_NOTAS:]
    sols = {t: s for t, s in pen.get("soluciones", {}).items() if (s.get("cuando", 0) or 0) > est["sol_desde"]}
    import investigar_kira as iv
    preguntas = [{"texto": p.get("texto", ""), "recurrente": bool(p.get("recurrente"))}
                 for p in iv.listar(dir_) if not p.get("hecha")]
    foco = _foco(dir_)
    paquete = {"v": VERSION, "origen": "móvil", "recuerdos": [r for _n, r in lista], "notas": notas,
               "soluciones": sols, "preguntas": preguntas, "foco": foco if foco.get("activo") else None,
               "hay_mas": hasta < rec.total(), "cursor": est["cursor"]}
    marcas = {"rec_enviados": hasta,
              "notas_desde": max([est["notas_desde"]] + [n.get("cuando", 0) or 0 for n in notas]),
              "sol_desde": max([est["sol_desde"]] + [s.get("cuando", 0) or 0 for s in sols.values()]),
              "enviados": len(lista) + len(notas) + len(sols)}
    return paquete, marcas


def pendiente_movil(dir_, rec):
    """Cuántas cosas nuevas tiene el móvil sin enviar (aprox.)."""
    est = estado_movil(dir_)
    n = max(0, rec.total() - int(est["rec_enviados"]))
    try:
        _pn, _ruta, pen = _pensamientos(dir_)
        n += sum(1 for x in pen.get("notas", []) if (x.get("cuando", 0) or 0) > est["notas_desde"])
    except Exception:
        pass
    return n


# =====================================================================================
#  KiraOS RECIBE (suma, nunca borra) Y CONTESTA CON LO SUYO
# =====================================================================================
def aplicar_en_kiraos(dir_, rec, paquete, maximo=MAX_REC):
    """KiraOS mete lo que manda el móvil y devuelve (resumen, respuesta). La respuesta lleva lo nuevo de KiraOS para
    el móvil desde su cursor (recuerdos, soluciones, tema, mejoras)."""
    if not isinstance(paquete, dict) or paquete.get("v") != VERSION:
        raise ValueError("Paquete de sincronía con otra versión: actualiza las dos Kiras.")
    est = estado_kiraos(dir_)
    nuevos, nums = _meter_recuerdos(rec, paquete.get("recuerdos"))
    est["importados"] = est["importados"] + [n for n in nums if n not in set(est["importados"])]
    nn, ns = _fusionar_pensamientos(dir_, paquete.get("notas"), paquete.get("soluciones"))
    import investigar_kira as iv
    np_ = sum(1 for p in paquete.get("preguntas") or [] if isinstance(p, dict)
              and iv.anadir(dir_, p.get("texto", ""), recurrente=bool(p.get("recurrente"))))
    foco_m, foco_k, nf = paquete.get("foco"), _foco(dir_), 0
    if isinstance(foco_m, dict) and foco_m.get("tema") and not foco_k.get("activo"):
        _escribir(os.path.join(dir_, "foco.json"), foco_m)
        nf = 1
    est["ultima"] = int(time.time())
    est["recibidos_total"] = est.get("recibidos_total", 0) + nuevos + nn + ns
    guardar_estado_kiraos(dir_, est)
    resumen = {"recuerdos": nuevos, "notas": nn, "soluciones": ns, "preguntas": np_, "foco": nf}
    return resumen, paquete_para_movil(dir_, rec, paquete.get("cursor") or {}, est, maximo)


def paquete_para_movil(dir_, rec, cursor, est=None, maximo=MAX_REC):
    est = est or estado_kiraos(dir_)
    cursor = dict(cursor or {})
    lista, hasta = _recuerdos_desde(rec, cursor.get("rec", 0), est["importados"], maximo)
    _pn, _ruta, pen = _pensamientos(dir_)
    sol_ts = cursor.get("sol_ts", 0)
    sols = {t: s for t, s in pen.get("soluciones", {}).items() if (s.get("cuando", 0) or 0) > sol_ts}
    tema = tema_valido(_leer(os.path.join(dir_, TEMA_MOVIL), {}))
    tema = tema if tema and tema.get("v", 0) > cursor.get("tema_v", 0) else None
    entregadas = set(cursor.get("mejoras", []))
    mejoras = [m for m in mejoras_para_movil(dir_) if m["hash"] not in entregadas]
    nuevo = {"rec": hasta, "sol_ts": max([sol_ts] + [s.get("cuando", 0) or 0 for s in sols.values()]),
             "tema_v": (tema or {}).get("v", cursor.get("tema_v", 0)),
             "mejoras": sorted(entregadas | {m["hash"] for m in mejoras})[-500:]}
    return {"v": VERSION, "origen": "KiraOS", "recuerdos": [r for _n, r in lista], "soluciones": sols, "tema": tema,
            "mejoras": mejoras, "hay_mas": hasta < rec.total(), "cursor": nuevo}


# =====================================================================================
#  EL MÓVIL RECIBE DE KiraOS
# =====================================================================================
def aplicar_en_movil(dir_, rec, respuesta, marcas=None):
    """Mete en el móvil lo que manda KiraOS y deja anotado lo enviado. Devuelve el resumen."""
    if not isinstance(respuesta, dict) or respuesta.get("v") != VERSION:
        raise ValueError("Respuesta de sincronía con otra versión: actualiza las dos Kiras.")
    est = estado_movil(dir_)
    nuevos, nums = _meter_recuerdos(rec, respuesta.get("recuerdos"))
    est["importados"] = est["importados"] + [n for n in nums if n not in set(est["importados"])]
    _nn, ns = _fusionar_pensamientos(dir_, [], respuesta.get("soluciones"))
    tema = tema_valido(respuesta.get("tema"))
    if tema:
        _escribir(os.path.join(dir_, TEMA_KIRAOS), tema)
    nm = guardar_mejoras_recibidas(dir_, respuesta.get("mejoras"))
    if marcas:
        for k in ("rec_enviados", "notas_desde", "sol_desde"):
            est[k] = max(est.get(k, 0), marcas.get(k, 0))
        est["enviados_total"] = est.get("enviados_total", 0) + marcas.get("enviados", 0)
    if isinstance(respuesta.get("cursor"), dict):
        est["cursor"] = respuesta["cursor"]
    est["ultima"] = int(time.time())
    est["recibidos_total"] = est.get("recibidos_total", 0) + nuevos + ns
    resumen = {"recuerdos": nuevos, "soluciones": ns, "tema": bool(tema), "mejoras": nm}
    est["resumen"] = texto_resumen(marcas or {}, resumen)
    guardar_estado_movil(dir_, est)
    return resumen


def texto_resumen(marcas, recibido):
    env = (marcas or {}).get("enviados", 0)
    rec = (recibido or {}).get("recuerdos", 0) + (recibido or {}).get("soluciones", 0)
    t = f"Envié {env} cosa(s) nueva(s) a KiraOS y recibí {rec}."
    if (recibido or {}).get("mejoras"):
        t += f" KiraOS me preparó {recibido['mejoras']} mejora(s): esperan tus dos toques en el panel."
    if (recibido or {}).get("tema"):
        t += " Y me ha cambiado el aspecto (se verá al volver a abrir la app)."
    return t


# =====================================================================================
#  EL TEMA (aspecto) QUE KiraOS LE PONE AL MÓVIL — solo datos
# =====================================================================================
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
CLAVES_TEMA = ("fondo", "neon", "acento", "texto")
TEMAS = {
    "noche": {"fondo": "#05070f", "neon": "#22d3ee", "acento": "#f472d0", "texto": "#e7ecf5"},
    "bosque": {"fondo": "#06110b", "neon": "#4ade80", "acento": "#facc15", "texto": "#e6f4ea"},
    "oceano": {"fondo": "#04101c", "neon": "#38bdf8", "acento": "#818cf8", "texto": "#e3f1fb"},
    "fuego": {"fondo": "#140806", "neon": "#fb923c", "acento": "#f43f5e", "texto": "#fbeee6"},
    "violeta": {"fondo": "#0d0716", "neon": "#a78bfa", "acento": "#f472d0", "texto": "#efe9fb"},
    "claro": {"fondo": "#f4f6fb", "neon": "#0e7490", "acento": "#be185d", "texto": "#111827"},
}


def tema_valido(d):
    """Devuelve el tema limpio ({v, nombre, colores}) o None si no vale. Solo colores #rrggbb conocidos."""
    if not isinstance(d, dict):
        return None
    col = d.get("colores")
    if not isinstance(col, dict) or not all(isinstance(col.get(k), str) and _HEX.match(col[k]) for k in CLAVES_TEMA):
        return None
    try:
        v = int(d.get("v", 0))
    except (TypeError, ValueError):
        return None
    if v < 1:
        return None
    nombre = re.sub(r"[^\wáéíóúñ -]", "", str(d.get("nombre", "")), flags=re.I)[:30] or "de KiraOS"
    return {"v": v, "nombre": nombre, "colores": {k: col[k].lower() for k in CLAVES_TEMA}}


def poner_tema_movil(dir_, nombre_o_colores):
    """En KiraOS: elige el aspecto del móvil (un tema de TEMAS por nombre, o un dict de colores). Devuelve el tema."""
    actual = _leer(os.path.join(dir_, TEMA_MOVIL), {})
    if isinstance(nombre_o_colores, dict):
        colores, nombre = nombre_o_colores, "a medida"
    else:
        clave = _sin_tildes(str(nombre_o_colores or "")).lower().strip()
        clave = {"verde": "bosque", "azul": "oceano", "naranja": "fuego", "rojo": "fuego", "morado": "violeta",
                 "lila": "violeta", "blanco": "claro", "oscuro": "noche", "negro": "noche"}.get(clave, clave)
        if clave not in TEMAS:
            raise ValueError("No conozco ese aspecto. Hay: " + ", ".join(TEMAS) + ".")
        colores, nombre = TEMAS[clave], clave
    tema = tema_valido({"v": int(actual.get("v", 0) or 0) + 1, "nombre": nombre, "colores": colores})
    if not tema:
        raise ValueError("Esos colores no valen (tienen que ser #rrggbb).")
    _escribir(os.path.join(dir_, TEMA_MOVIL), tema)
    return tema


def tema_del_movil(dir_):
    """En el móvil: el tema que le puso KiraOS (o None)."""
    return tema_valido(_leer(os.path.join(dir_, TEMA_KIRAOS), {}))


def _sin_tildes(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


# =====================================================================================
#  MEJORAS DE SISTEMA QUE KiraOS PREPARA PARA EL MÓVIL (nunca se instalan solas)
# =====================================================================================
_NOMBRE = re.compile(r"^[a-z][a-z0-9_]{0,30}$")


def _hash(codigo):
    return hashlib.sha256(str(codigo).encode("utf-8")).hexdigest()[:20]


def guardar_para_movil(dir_, nombre, codigo, descripcion="", prueba=None):
    """En KiraOS: deja una mejora (ya probada en su laboratorio) lista para entregarla al móvil."""
    if not _NOMBRE.match(str(nombre or "")) or "def registrar" not in str(codigo or ""):
        raise ValueError("Una mejora para el móvil tiene que ser un módulo de Kira (con registrar()) y un nombre simple.")
    m = {"nombre": nombre, "codigo": str(codigo), "descripcion": str(descripcion or "")[:300], "hash": _hash(codigo),
         "cuando": int(time.time()), "prueba_kiraos": bool((prueba or {}).get("ok"))}
    _escribir(os.path.join(dir_, PARA_MOVIL, nombre + ".json"), m)
    return m


def mejoras_para_movil(dir_):
    carpeta = os.path.join(dir_, PARA_MOVIL)
    sal = []
    try:
        nombres = sorted(os.listdir(carpeta))
    except OSError:
        return []
    for f in nombres:
        if f.endswith(".json"):
            m = _leer(os.path.join(carpeta, f), {})
            if m.get("nombre") and m.get("codigo") and m.get("hash") == _hash(m["codigo"]):
                sal.append({k: m[k] for k in ("nombre", "codigo", "descripcion", "hash", "cuando") if k in m})
    return sal


def guardar_mejoras_recibidas(dir_, mejoras):
    """En el móvil: guarda las mejoras que llegan como «recibidas» (pendientes de laboratorio + tus dos toques)."""
    n = 0
    for m in mejoras or []:
        if not isinstance(m, dict) or not _NOMBRE.match(str(m.get("nombre", ""))):
            continue
        if "def registrar" not in str(m.get("codigo", "")) or m.get("hash") != _hash(m.get("codigo", "")):
            continue
        ruta = os.path.join(dir_, MEJORAS_RECIBIDAS, m["nombre"] + ".json")
        prev = _leer(ruta, {})
        if prev.get("hash") == m["hash"]:
            continue
        _escribir(ruta, {"nombre": m["nombre"], "codigo": m["codigo"], "descripcion": m.get("descripcion", ""),
                         "hash": m["hash"], "estado": "recibida", "llego": int(time.time())})
        n += 1
    return n


def mejoras_recibidas(dir_, solo_pendientes=True):
    carpeta = os.path.join(dir_, MEJORAS_RECIBIDAS)
    sal = []
    try:
        nombres = sorted(os.listdir(carpeta))
    except OSError:
        return []
    for f in nombres:
        if f.endswith(".json"):
            m = _leer(os.path.join(carpeta, f), {})
            if m.get("nombre") and (not solo_pendientes or m.get("estado") == "recibida"):
                sal.append(m)
    return sal


def marcar_mejora(dir_, nombre, estado):
    """estado: 'probada' | 'instalada' | 'rechazada'."""
    ruta = os.path.join(dir_, MEJORAS_RECIBIDAS, str(nombre) + ".json")
    m = _leer(ruta, {})
    if not m:
        return False
    m["estado"] = estado
    _escribir(ruta, m)
    return True
