# -*- coding: utf-8 -*-
"""
tablero_kira.py - Lo que enseña el PANEL de la app del móvil (v2.87). VA EN EL APK; puro (sin Kivy ni red).

Lo pidió el dueño: la app del móvil se queda en DOS pantallas: hablar con Kira y este panel, con el cerebro, las
conversaciones, lo que están haciendo Kira app y KiraOS, las órdenes que les has dado, la información del portátil y
del móvil, y si está estudiando, programando, experimentando o pensando.

`secciones(datos)` devuelve la lista de tarjetas: [{"id", "titulo", "texto", "botones": [(etiqueta, accion)]}].
La pantalla (interfaz_kira) solo las pinta y hace la acción del botón. `datos` lo junta la interfaz:
  movil (core.actividad()), tarea (lo que hace ahora), cerebro (texto), kiraos (/hola de KiraOS o None),
  sinc (sincronia_kira.estado_movil), pendiente (cosas sin enviar), ordenes (lista de ordenes_kira), mejoras
  (recibidas de KiraOS), charla ([(rol, texto)]), equipo_movil, ultimo (último trabajo de KiraOS), ahora (time).
"""
import os
import shutil
import time


# ---------- información del móvil (lo que se puede leer sin permisos) ----------
def _meminfo():
    d = {}
    try:
        with open("/proc/meminfo") as f:
            for linea in f:
                k, _, v = linea.partition(":")
                d[k.strip()] = int(v.split()[0]) // 1024        # MB
    except (OSError, ValueError, IndexError):
        pass
    return d


def _leer(ruta):
    try:
        with open(ruta) as f:
            return f.read().strip()
    except OSError:
        return ""


def equipo_movil(dir_=".", modelo=""):
    m = _meminfo()
    d = {"modelo": str(modelo or ""), "ram_mb": m.get("MemTotal", 0), "ram_libre_mb": m.get("MemAvailable", 0),
         "nucleos": os.cpu_count() or 0, "disco_libre_gb": None, "bateria": None, "cargando": None}
    try:
        d["disco_libre_gb"] = round(shutil.disk_usage(dir_).free / 1e9, 1)
    except OSError:
        pass
    for base in ("/sys/class/power_supply/battery", "/sys/class/power_supply/Battery"):
        cap = _leer(os.path.join(base, "capacity"))
        if cap.isdigit():
            d["bateria"] = int(cap)
            est = _leer(os.path.join(base, "status")).lower()
            d["cargando"] = est in ("charging", "full") if est else None
            break
    return d


def hace(segundos):
    s = max(0, int(segundos))
    if s < 60:
        return "hace un momento"
    if s < 3600:
        return f"hace {s // 60} min"
    if s < 86400:
        return f"hace {s // 3600} h"
    return f"hace {s // 86400} día(s)"


def _si(v):
    return "sí" if v else "no"


def _corta(texto, n):
    t = str(texto or "").replace("\n", " ").strip()
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def _num(x, dec=1):
    """Números a la española: 91,8 · 1,35."""
    try:
        return (f"{float(x):.{dec}f}".rstrip("0").rstrip(".") if dec else str(int(x))).replace(".", ",")
    except (TypeError, ValueError):
        return str(x)


# ---------- cada tarjeta ----------
def _haciendo(act, tarea):
    partes = []
    if tarea:
        partes.append(tarea)
    if act.get("estudiando"):
        partes.append("estudiando")
    if act.get("foco"):
        partes.append(f"centrada en «{act['foco']}»")
    if act.get("pensando"):
        partes.append("pensando (en pausa mientras me hablas)" if act.get("pausada") else "pensando")
    if act.get("maquina"):
        partes.append("con su máquina virtual encendida")
    return ", ".join(partes) or "libre"


def tarjeta_movil(d):
    act, eq = d.get("movil") or {}, d.get("equipo_movil") or {}
    lineas = [f"Ahora: {_haciendo(act, d.get('tarea', ''))}.",
              f"Cuaderno: {act.get('pensamientos', 0)} pensamientos · {act.get('soluciones', 0)} soluciones."]
    eqs = []
    if eq.get("modelo"):
        eqs.append(eq["modelo"])
    if eq.get("ram_mb"):
        eqs.append(f"RAM libre {_num(eq.get('ram_libre_mb', 0) / 1024)} de {_num(eq['ram_mb'] / 1024)} GB")
    if eq.get("disco_libre_gb") is not None:
        eqs.append(f"{_num(eq['disco_libre_gb'])} GB de disco libres")
    if eq.get("bateria") is not None:
        eqs.append(f"batería {eq['bateria']} %" + (" (cargando)" if eq.get("cargando") else ""))
    if eqs:
        lineas.append("Móvil: " + " · ".join(eqs) + ".")
    lineas.append("Estudio y pienso: " + ("SOLO lo que tú me mandas." if act.get("solo_mio") else
                                          "lo tuyo primero y, si no hay nada, lo que yo quiera."))
    botones = [("Deja de pensar" if act.get("pensando") else "Ponte a pensar", "pensar"),
               ("Pensar también libre" if act.get("solo_mio") else "Solo lo que yo mande", "solo_mio")]
    return {"id": "movil", "titulo": "KIRA APP (este móvil)", "texto": "\n".join(lineas), "botones": botones}


def tarjeta_kiraos(d):
    h = d.get("kiraos")
    if not h:
        return {"id": "kiraos", "titulo": "KIRAOS (el portátil)",
                "texto": ("No la veo ni en la WiFi de casa ni por Tailscale. Fuera de casa yo pienso y estudio con mi "
                          "cerebro pequeño, lo guardo, y te apunto el trabajo (programas, juegos, apps…) para dárselo "
                          "al volver."),
                "botones": [("Buscarla", "buscar_kiraos")]}
    act = h.get("actividad") or {}
    haciendo = h.get("haciendo") if h.get("ocupada") else ""
    ahora = "EN PAUSA (no empieza nada nuevo)" if h.get("pausada") else _haciendo(act, haciendo)
    if h.get("ocupada"):
        ahora = "OCUPADA: " + ahora
    n = int(h.get("en_cola") or 0)
    lineas = [f"Despierta (versión {h.get('version', '?')}) · {h.get('recuerdos', 0)} recuerdos"
              + (f" · me llama «{h['llamar']}»" if h.get("llamar") else "") + ".",
              f"Ahora: {ahora}." + (f" {n} tarea(s) en espera." if n else ""),
              f"Su cuaderno: {act.get('pensamientos', 0)} pensamientos · {act.get('soluciones', 0)} soluciones."]
    w = act.get("wifi") or {}
    if w.get("ssid"):
        lineas.append(f"WiFi: «{w['ssid']}»" + (f" ({w['senal']} %)" if w.get("senal") is not None else "")
                      + ("" if w.get("internet") in (None, "full", "unknown") else " · sin salida a internet") + ".")
    elif w and not w.get("error"):
        lineas.append("WiFi: " + ("apagada." if w.get("radio") is False else "sin conectar."))
    eq = h.get("equipo") or {}
    eqs = [x for x in (eq.get("procesador"),
                       f"{_num(eq['ram_mb'] / 1024)} GB de RAM" if eq.get("ram_mb") else "",
                       f"{_num(eq['disco_libre_gb'])} GB de disco libres" if eq.get("disco_libre_gb") is not None else "",
                       f"carga {_num(eq['carga'], 2)}" if eq.get("carga") else "",
                       f"encendido {_num(eq['encendido_h'])} h" if eq.get("encendido_h") is not None else "") if x]
    if eqs:
        lineas.append("Portátil: " + " · ".join(eqs) + ".")
    if h.get("via") == "fuera":                       # v3.00
        lineas.append("Conectada por Tailscale (fuera de casa): me sincronizo, veo lo que hace y le paso lo "
                      "tranquilo (estudiar, investigar, pensar, programar); lo que toca el portátil o tu casa, al volver.")
    if act.get("solo_mio"):
        lineas.append("Estudia y piensa SOLO lo que tú le mandas.")
    botones = [("Parar lo que hace", "parar_kiraos")] if h.get("ocupada") else []
    botones.append(("Seguir", "seguir_kiraos") if h.get("pausada") else ("Pausar", "pausar_kiraos"))
    return {"id": "kiraos", "titulo": "KIRAOS (el portátil)", "texto": "\n".join(lineas), "botones": botones}


def tarjeta_cerebro(d):
    return {"id": "cerebro", "titulo": "CEREBRO", "texto": d.get("cerebro") or "Mirando qué cerebro uso…",
            "botones": [("Cerebro y oído", "ir_cerebro")]}


def tarjeta_sincronia(d):
    s, ahora = d.get("sinc") or {}, d.get("ahora") or time.time()
    if s.get("ultima"):
        t = f"Última vez: {hace(ahora - s['ultima'])}. {s.get('resumen', '')}".strip()
    else:
        t = "Todavía no me he sincronizado con KiraOS."
    t += f"\nPor enviar: {d.get('pendiente', 0)} cosa(s) nuevas · enviadas en total: {s.get('enviados_total', 0)}" \
         f" · recibidas: {s.get('recibidos_total', 0)}."
    t += "\nSe hace sola al llegar a casa y se suma: no se borra nada en ningún lado."
    return {"id": "sinc", "titulo": "SINCRONÍA CON KIRAOS", "texto": t,
            "botones": [("Sincronizar ahora", "sincronizar")] if d.get("kiraos") else []}


_ICONO = {"pendiente": "EN ESPERA", "enviada": "ENVIADA", "en curso": "EN CURSO", "hecha": "HECHA", "error": "ERROR",
          "cancelada": "PARADA"}      # palabras, no símbolos: la letra del móvil no tiene todos los iconos


def tarjeta_ordenes(d):
    lista = d.get("ordenes") or []
    if not lista:
        return {"id": "ordenes", "titulo": "ÓRDENES", "texto": "Todavía no me has dado órdenes.", "botones": []}
    filas, pend = [], 0
    for o in lista[:10]:
        donde = "KiraOS" if o.get("destino") == "kiraos" else "móvil"
        h = time.strftime("%d/%m %H:%M", time.localtime(o.get("cuando", 0)))
        f = f"[{_ICONO.get(o.get('estado'), '?')}] {donde} · {h} — {_corta(o.get('texto', ''), 70)}"
        if o.get("estado") == "pendiente":
            pend += 1
            f += " (al llegar a casa)"
        elif o.get("respuesta"):
            f += "\n      " + _corta(o["respuesta"], 140)
        filas.append(f)
    if pend:
        filas.append(f"\n{pend} orden(es) esperando a KiraOS: se las doy yo sola en cuanto la vea.")
    return {"id": "ordenes", "titulo": "ÓRDENES (a Kira app y a KiraOS)", "texto": "\n".join(filas), "botones": []}


def tarjeta_mejoras(d):
    ms = d.get("mejoras") or []
    if not ms:
        return None
    filas = ["Me las ha preparado KiraOS y las ha probado en su laboratorio. Aquí las vuelvo a probar en el mío y "
             "solo se instalan con tus DOS toques."]
    botones = []
    for m in ms[:4]:
        filas.append(f"· «{m['nombre']}»: {_corta(m.get('descripcion', ''), 90)}"
                     + (" — probada aquí: lista para instalar" if m.get("estado") == "probada" else ""))
        if m.get("estado") == "probada":
            botones.append((f"Instalar «{m['nombre']}» (2 toques)", "aplicar:" + m["nombre"]))
        else:
            botones.append((f"Probar «{m['nombre']}»", "probar:" + m["nombre"]))
        botones.append((f"Descartar «{m['nombre']}»", "descartar:" + m["nombre"]))
    return {"id": "mejoras", "titulo": "MEJORAS QUE ME MANDA KIRAOS", "texto": "\n".join(filas), "botones": botones}


def tarjeta_ultimo(d):
    u = d.get("ultimo")
    if not u:
        return None
    t = f"«{str(u.get('orden', ''))[:80]}»\n{str(u.get('respuesta', ''))[:400]}"
    if u.get("codigo"):
        lineas = str(u["codigo"]).splitlines()
        t += "\n\nEl código (lo tiene KiraOS; aquí solo lo enseño):\n" + "\n".join(lineas[:40]) + \
             (f"\n… ({len(lineas) - 40} líneas más)" if len(lineas) > 40 else "")
    return {"id": "ultimo", "titulo": "ÚLTIMO TRABAJO DE KIRAOS", "texto": t, "botones": []}


def tarjeta_charla(d):
    turnos = d.get("charla") or []
    if not turnos:
        return {"id": "charla", "titulo": "CONVERSACIONES", "texto": "Aún no hemos hablado.", "botones": []}
    filas = [("Tú: " if rol == "tu" else "Kira: ") + _corta(texto, 160) for rol, texto in turnos[-8:]]
    return {"id": "charla", "titulo": "CONVERSACIONES (lo último)", "texto": "\n".join(filas),
            "botones": [("Hablar con Kira", "ir_inicio")]}


def secciones(datos):
    d = dict(datos or {})
    d.setdefault("ahora", time.time())
    sal = [tarjeta_movil(d), tarjeta_kiraos(d), tarjeta_mejoras(d), tarjeta_ultimo(d), tarjeta_ordenes(d),
           tarjeta_sincronia(d), tarjeta_cerebro(d), tarjeta_charla(d)]
    sal = [x for x in sal if x]
    sal.append({"id": "ajustes", "titulo": "AJUSTES",
                "texto": "Conexión con el portátil, voz, notas y memoria; y el lector de capturas (OCR).",
                "botones": [("Conexión y ajustes", "ir_ajustes"), ("Lector de capturas (OCR)", "ir_lector")]})
    return sal
