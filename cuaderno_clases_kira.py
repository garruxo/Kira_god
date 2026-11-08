# -*- coding: utf-8 -*-
"""
cuaderno_clases_kira.py - El CUADERNO de Kira ORDENADO en pestañas (v3.08, lo pidió el dueño):

  · PENSAMIENTO   : lo que se pregunta y aún está pensando (dudas, ideas, experimentos a medias).
  · CONOCIMIENTO  : lo que ya sabe con seguridad (soluciones guardadas y respuestas comprobadas).
  · MEJORAS       : lo que se PUEDE o se DEBE mejorar en su sistema, separado en KiraOS (portátil) y Kira app (móvil),
                    más las mejoras de verdad que esperan tus dos toques.
  · TAREAS        : activas, en espera y terminadas.

Lógica pura (sin red ni ventanas): recibe los datos y devuelve textos. Las pruebas están en tests/test_cuaderno_clases.py.
"""
import re
import time
import unicodedata


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# preguntas de serie que miran a SU propio sistema (pensador_kira._TIPOS_PREGUNTA)
_DE_SISTEMA = re.compile(r"(?:incorporar .* a mi propio sistema|mejorar en mi propio codigo|en mi propio codigo|"
                         r"mi propio sistema|mejorar (?:mi|el) (?:sistema|codigo)|como mejorar kira)")
_MOVIL = re.compile(r"\b(?:movil|android|telefono|kira app|la app|apk|bateria|kivy)\b")
_PORTATIL = re.compile(r"\b(?:portatil|kiraos|kira os|linux|xubuntu|escritorio|maquina virtual|ordenador|pc)\b")
_DEBE = re.compile(r"\b(?:deberia|debe|hay que|falta|faltan|error|falla|fallo|lento|lenta|ineficiente|peligro|"
                   r"inseguro|vulnerab|se cuelga|no funciona|roto|rota)\b")


def es_de_sistema(nota):
    """¿La nota habla de mejorar SU propio sistema (Kira)?"""
    return bool(_DE_SISTEMA.search(_plano(nota.get("pregunta", ""))))


def donde(nota):
    """'movil', 'portatil' o 'los dos' según de qué hable."""
    t = _plano(str(nota.get("pregunta", "")) + " " + str(nota.get("respuesta", "")))
    m, p = bool(_MOVIL.search(t)), bool(_PORTATIL.search(t))
    if m and not p:
        return "movil"
    if p and not m:
        return "portatil"
    return "los dos"


def urgencia(nota):
    """'debe' (algo falla, es lento, inseguro o falta) o 'puede' (una idea para ir a mejor)."""
    exp = nota.get("experimento") or {}
    if exp and not exp.get("ok"):
        return "debe"
    hist = nota.get("historial") or []
    if hist and not hist[-1].get("ok"):
        return "debe"
    return "debe" if _DEBE.search(_plano(nota.get("respuesta", ""))) else "puede"


def resuelta(nota):
    if nota.get("seguridad") != "alta" or nota.get("duda"):
        return False
    if nota.get("fuente") in ("sin cerebro", "error", "permiso"):
        return False
    exp = nota.get("experimento")
    if exp and not exp.get("ok"):
        return False
    hist = nota.get("historial") or []
    return not hist or bool(hist[-1].get("ok") or any(h.get("ok") for h in hist))


def clase(nota):
    """'mejora', 'conocimiento' o 'pensamiento'."""
    if es_de_sistema(nota):
        return "mejora"
    return "conocimiento" if resuelta(nota) else "pensamiento"


def _corta(t, n):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def _linea_nota(nt, n=220):
    marca = {"alta": "✔", "media": "~", "baja": "?"}.get(nt.get("seguridad"), "~")
    etq = {"ciclo": " [ciclo de mejora]", "experimento": " [experimento]", "reflexión": " [reflexión]"}.get(
        nt.get("tipo"), " [duda]" if nt.get("duda") else "")
    out = [f"{marca}{etq} {nt.get('pregunta', '')}", "   → " + _corta(nt.get("respuesta", ""), n)]
    exp = nt.get("experimento")
    if exp:
        out.append(f"   · prueba: {'OK' if exp.get('ok') else 'falló'} — {_corta(exp.get('resultado', ''), 120)}")
    for h in (nt.get("historial") or [])[-3:]:
        out.append(f"   · ronda {h.get('ronda')}: {'OK' if h.get('ok') else 'falló'}")
    comp = nt.get("comparacion")
    if comp:
        out.append(f"   · comparé con {comp.get('fuente', 'otra fuente')}: {_corta(comp.get('resumen', ''), 120)}")
    return "\n".join(out)


def _hace(seg):
    seg = max(0, int(seg))
    if seg < 90:
        return "hace un momento"
    if seg < 5400:
        return f"hace {seg // 60} min"
    if seg < 172800:
        return f"hace {seg // 3600} h"
    return f"hace {seg // 86400} días"


# ---------- las cuatro pestañas ----------
def pestana_pensamiento(estado, n=25):
    notas = [x for x in estado.get("notas", []) if clase(x) == "pensamiento"][-n:]
    if not notas:
        return "Ahora mismo no tengo nada a medio pensar. Dime «piensa» y me pongo a cuestionarme cosas."
    return (f"LO QUE ESTOY PENSANDO ({len(notas)}) — dudas, ideas y experimentos que aún no tengo claros:\n\n"
            + "\n\n".join(_linea_nota(x) for x in reversed(notas)))


def pestana_conocimiento(estado, n=25):
    sols = sorted((estado.get("soluciones") or {}).items(), key=lambda kv: -float(kv[1].get("cuando", 0) or 0))
    notas = [x for x in estado.get("notas", []) if clase(x) == "conocimiento"][-n:]
    if not sols and not notas:
        return "Todavía no tengo nada comprobado del todo. Cuando resuelva algo con seguridad, lo verás aquí."
    out = []
    if sols:
        out.append(f"SOLUCIONES GUARDADAS ({len(sols)}) — lo que ya resolví:")
        for tema, s in sols[:n]:
            veces = s.get("veces", 1)
            extra = " · con código que funciona" if (s.get("codigo") or "").strip() else ""
            out.append(f"✔ {tema}{extra}" + (f" · mejorada {veces} veces" if veces and veces > 1 else "")
                       + "\n   → " + _corta(s.get("respuesta") or s.get("resumen") or "", 220))
    if notas:
        out.append(f"\nLO QUE SÉ CON SEGURIDAD ({len(notas)}):")
        out.extend(_linea_nota(x) for x in reversed(notas))
    return "\n\n".join(out)


def pestana_mejoras(estado, sistema=None):
    """sistema: {'kiraos_pendiente': {...}|None, 'kiraos_instaladas': [...], 'para_movil': [...],
    'permisos': {nombre: {...}}} (lo que de verdad espera tu permiso)."""
    sistema = sistema or {}
    notas = [x for x in estado.get("notas", []) if clase(x) == "mejora"]
    grupos = {"portatil": [], "movil": [], "los dos": []}
    for x in notas:
        grupos[donde(x)].append(x)
    out = []
    pend = sistema.get("kiraos_pendiente")
    para_movil = sistema.get("para_movil") or []
    permisos = sistema.get("permisos") or {}
    real = []
    if pend:
        real.append(f"• KiraOS: «{pend.get('nombre')}» probada en mi laboratorio, ESPERA tus dos toques (icono "
                    "«Mejoras»).")
    for m in para_movil[:10]:
        real.append(f"• Kira app: «{m.get('nombre', '?')}» lista; se la doy al móvil al sincronizar y allí la "
                    "instalas tú con dos toques.")
    for nom, d in list(permisos.items())[:10]:
        real.append(f"• Necesito instalar «{nom}» para seguir" + (f" ({_corta(d.get('motivo'), 80)})"
                                                                  if d.get("motivo") else "") + ": te lo pregunto.")
    if real:
        out.append("ESPERAN TU PERMISO:\n" + "\n".join(real))
    titulos = {"portatil": "KIRAOS (el portátil)", "movil": "KIRA APP (el móvil)", "los dos": "LOS DOS"}
    for g in ("portatil", "movil", "los dos"):
        lista = grupos[g]
        if not lista:
            continue
        debe = [x for x in lista if urgencia(x) == "debe"]
        puede = [x for x in lista if urgencia(x) == "puede"]
        partes = [titulos[g] + ":"]
        if debe:
            partes.append("  SE DEBE mejorar (algo falla, falta o va lento):\n"
                          + "\n".join("  ! " + _corta(x.get("pregunta"), 110) + "\n      → "
                                      + _corta(x.get("respuesta"), 180) for x in debe[-8:]))
        if puede:
            partes.append("  SE PUEDE mejorar (ideas para ir a mejor):\n"
                          + "\n".join("  + " + _corta(x.get("pregunta"), 110) + "\n      → "
                                      + _corta(x.get("respuesta"), 180) for x in puede[-8:]))
        out.append("\n".join(partes))
    inst = sistema.get("kiraos_instaladas") or []
    if inst:
        out.append("YA INSTALADAS EN KIRAOS: " + ", ".join(m.get("nombre", "?") for m in inst))
    if not out:
        return ("Aún no he pensado nada sobre mejorar mi sistema. Cuando me pregunte «¿qué puedo mejorar en mi "
                "propio código?» o «¿podría incorporarlo a mí?», lo verás aquí, separado en portátil y móvil. "
                "Ojo: son IDEAS; nada se aplica solo (laboratorio + tus dos toques).")
    out.append("Son ideas y avisos míos: nada se aplica solo. Para hacer una: «mejórate: …» (KiraOS) o "
               "«mejora para el móvil: …».")
    return "\n\n".join(out)


def pestana_tareas(trabajo=None, encargos=None, foco=None, ahora=None):
    """trabajo: el estado del núcleo ({'cola': [...], 'hechas': [...], 'actividad': {...}, 'pausada'});
    encargos: lista de investigar_kira; foco: foco.json."""
    trabajo = trabajo or {}
    ahora = ahora or time.time()
    act = trabajo.get("actividad") or {}
    activas, espera, hechas = [], [], []
    for t in trabajo.get("cola") or []:
        (activas if t.get("estado") == "en curso" else espera).append("• " + _corta(t.get("orden"), 120))
    if act.get("estudiando"):
        activas.append("• Estudiando (por mi cuenta o porque me lo mandaste)")
    if act.get("pensando"):
        activas.append("• Pensando en segundo plano (cuando llevas 5 min sin pedirme nada)")
    foco = foco or {}
    if foco.get("tema"):
        if foco.get("activo") and not foco.get("resuelto"):
            activas.append(f"• Centrada en «{foco['tema']}» hasta resolverlo")
        elif foco.get("resuelto"):
            hechas.append(f"✔ Resuelto el tema en que me centré: «{foco['tema']}»")
        else:
            espera.append(f"• Aparcado para otro día: «{foco['tema']}»")
    for e in encargos or []:
        if e.get("hecha"):
            hechas.append("✔ Encargo investigado: " + _corta(e.get("texto"), 110)
                          + (f" ({_hace(ahora - e['ultima'])})" if e.get("ultima") else ""))
        else:
            espera.append("• Encargo por investigar: " + _corta(e.get("texto"), 110)
                          + (" (lo repaso de vez en cuando)" if e.get("recurrente") else ""))
    for t in trabajo.get("hechas") or []:
        icono = {"hecho": "✔", "error": "✗", "cancelado": "■"}.get(t.get("estado"), "·")
        hechas.append(f"{icono} {_corta(t.get('orden'), 110)}"
                      + (f" ({_hace(ahora - t['fin'])})" if t.get("fin") else "")
                      + ({"error": " — falló", "cancelado": " — la paraste"}.get(t.get("estado"), "")))
    if trabajo.get("pausada"):
        activas.insert(0, "(EN PAUSA: no empiezo nada nuevo hasta que pulses «Seguir»)")
    def bloque(t, l, vacio):
        return t + f" ({len([x for x in l if not x.startswith('(')])}):\n" + ("\n".join(l) if l else "  " + vacio)
    return "\n\n".join([bloque("ACTIVAS", activas, "nada ahora mismo"),
                        bloque("EN ESPERA", espera, "nada esperando"),
                        bloque("TERMINADAS", hechas[:25], "aún nada terminado")])


def pestanas(estado, sistema=None, trabajo=None, encargos=None, foco=None):
    """Las cuatro pestañas del cuaderno, listas para la ventana: [{'id','titulo','texto'}]."""
    notas = estado.get("notas", [])
    n_p = sum(1 for x in notas if clase(x) == "pensamiento")
    n_c = sum(1 for x in notas if clase(x) == "conocimiento") + len(estado.get("soluciones") or {})
    n_m = sum(1 for x in notas if clase(x) == "mejora")
    return [{"id": "pensamiento", "titulo": f"Pensamiento ({n_p})", "texto": pestana_pensamiento(estado)},
            {"id": "conocimiento", "titulo": f"Conocimiento ({n_c})", "texto": pestana_conocimiento(estado)},
            {"id": "mejoras", "titulo": f"Mejoras ({n_m})", "texto": pestana_mejoras(estado, sistema)},
            {"id": "tareas", "titulo": "Tareas", "texto": pestana_tareas(trabajo, encargos, foco)}]


# ---------- v3.10: cómo acabó cada tarea (para «Terminadas») ----------
_FALLO = re.compile(r"^(?:\[x\]|no he podido|no pude|no me (?:ha )?salid|no la instalo|no lo instalo|no reconozco|"
                    r"no encuentro|no tengo|no se pudo|no puedo|algo fallo|error)|(?:no pasa (?:mi|el) laboratorio|"
                    r"no he cambiado nada)")
_IMPLEMENTADO = re.compile(r"\b(?:me he puesto|instalad[ao]|aplicad[ao]|implementad[ao]|ya esta instalada|"
                           r"actualizad[ao]|lista la app|app .{0,40}lista|guardad[ao] en (?:tu|mi) baul)")
_MEJORADO = re.compile(r"\b(?:mejorad[ao]|version nueva|mejor version|optimizad[ao]|mas rapid[ao])\b")
_ESPERA_PERMISO = re.compile(r"(?:no la he instalado|espera tu permiso|esperando tu permiso|dos (?:toques|veces))")
_NADA = re.compile(r"^(?:ya tengo todas|ya estoy al dia|no hay (?:nada|mejoras))")


def _primera_linea(t):
    for ln in str(t or "").splitlines():
        ln = re.sub(r"^\s*(?:\[(?:ok|x|i)\]\s*)", "", ln.strip(), flags=re.I).strip(" ·-")
        if ln:
            return _corta(ln, 170)
    return ""


def resultado_tarea(estado, respuesta=""):
    """(etiqueta, por qué) de una tarea acabada: Implementado / Mejorado / Hecho / Preparado (espera tu permiso) /
    Nada que hacer / Falló (no hizo nada) / Parada / Quitada."""
    motivo = _primera_linea(respuesta)
    p = _plano(respuesta).strip()
    if estado == "quitado":
        return "Quitada", "La quitaste tú antes de empezar: no se hizo nada."
    if estado == "cancelado":
        return "Parada", "La paraste tú a medias: lo que iba haciendo no se ha aplicado."
    if estado == "error":
        return "Falló", "No hizo nada: " + (motivo or "se cayó a medias.")
    if _FALLO.search(p):
        return "Falló", "No hizo nada: " + (motivo or "no le salió.")
    if _ESPERA_PERMISO.search(p):
        return "Preparado (espera tu permiso)", motivo
    if _NADA.search(p):
        return "Nada que hacer", motivo
    if _IMPLEMENTADO.search(p):
        return "Implementado", motivo
    if _MEJORADO.search(p):
        return "Mejorado", motivo
    return "Hecho", motivo or "Terminada."


def filas_tareas(trabajo=None, encargos=None, foco=None, ahora=None):
    """La pestaña «Tareas» con BOTONES por fila: [{'seccion','texto','detalle','botones':[…]}].
    Cada fila de las tres listas lleva Parar / Borrar / Empezar (desactivado lo que no tiene sentido)."""
    trabajo = trabajo or {}
    ahora = ahora or time.time()
    act = trabajo.get("actividad") or {}
    filas = []

    def b(texto, accion, activo=True, dos=False):
        d = {"texto": texto, "accion": accion}
        if not activo:
            d["off"] = True
        if dos:
            d["dos"] = True
        return d

    def fila(sec, texto, detalle="", botones=None, etiqueta=""):
        filas.append({"seccion": sec, "texto": texto, "detalle": detalle, "botones": botones or [],
                      "etiqueta": etiqueta})

    # ACTIVAS
    if trabajo.get("pausada"):
        fila("activas", "En pausa: no empiezo nada nuevo", "pulsa «Empezar» para que siga con la cola",
             [b("Parar", "", False), b("Borrar", "", False), b("Empezar", "hacer:kira:seguir")])
    for t in trabajo.get("cola") or []:
        if t.get("estado") == "en curso":
            tid = t.get("id", "")
            fila("activas", t.get("orden", ""), "Haciéndola ahora",
                 [b("Parar", f"hacer:tarea:parar:{tid}"), b("Borrar", f"hacer:tarea:borrar:{tid}", dos=True),
                  b("Empezar", "", False)])
    if act.get("estudiando"):
        fila("activas", "Estudiando", "por su cuenta o porque se lo mandaste",
             [b("Parar", "hacer:kira:parar"), b("Borrar", "", False), b("Empezar", "", False)])
    if act.get("pensando"):
        fila("activas", "Pensando en segundo plano", "cuando llevas 5 min sin pedirle nada",
             [b("Parar", "decir:deja de pensar"), b("Borrar", "", False), b("Empezar", "", False)])
    foco = foco or {}
    if foco.get("tema") and foco.get("activo") and not foco.get("resuelto"):
        fila("activas", f"Centrada en «{foco['tema']}» hasta resolverlo", "",
             [b("Parar", "decir:déjalo para otro día"), b("Borrar", "decir:deja el tema", dos=True),
              b("Empezar", "", False)])
    # EN ESPERA
    for t in trabajo.get("cola") or []:
        if t.get("estado") == "en curso":
            continue
        tid = t.get("id", "")
        ret = bool(t.get("retenida"))
        fila("espera", t.get("orden", ""), "Parada: no empezará hasta que pulses «Empezar»" if ret else "En cola",
             [b("Parar", f"hacer:tarea:parar:{tid}", not ret), b("Borrar", f"hacer:tarea:borrar:{tid}", dos=True),
              b("Empezar", f"hacer:tarea:empezar:{tid}")])
    if foco.get("tema") and not foco.get("activo") and not foco.get("resuelto"):
        fila("espera", f"Aparcado para otro día: «{foco['tema']}»", "",
             [b("Parar", "", False), b("Borrar", "decir:deja el tema", dos=True), b("Empezar", "decir:retoma el tema")])
    for i, e in enumerate(encargos or []):
        if e.get("hecha"):
            continue
        fila("espera", "Encargo: " + _corta(e.get("texto"), 110),
             "lo repasa de vez en cuando" if e.get("recurrente") else "lo investigará cuando piense",
             [b("Parar", "", False), b("Borrar", f"hacer:encargo:borrar:{i}", dos=True),
              b("Empezar", f"hacer:encargo:empezar:{i}")])
    # TERMINADAS
    for t in trabajo.get("hechas") or []:
        tid = t.get("id", "")
        etq = t.get("resultado") or resultado_tarea(t.get("estado"), t.get("respuesta", ""))[0]
        por = t.get("por_que") or resultado_tarea(t.get("estado"), t.get("respuesta", ""))[1]
        cuando = f" · {_hace(ahora - t['fin'])}" if t.get("fin") else ""
        fila("terminadas", t.get("orden", ""), f"{etq}{cuando} — {por}",
             [b("Parar", "", False), b("Borrar", f"hacer:tarea:borrar:{tid}"),
              b("Empezar", f"hacer:tarea:empezar:{tid}")], etiqueta=etq)
    for i, e in enumerate(encargos or []):
        if e.get("hecha"):
            fila("terminadas", "Encargo investigado: " + _corta(e.get("texto"), 110),
                 ("Investigado" + (f" · {_hace(ahora - e['ultima'])}" if e.get("ultima") else "")
                  + " — lo tienes en su baúl / Conocimiento"),
                 [b("Parar", "", False), b("Borrar", f"hacer:encargo:borrar:{i}"),
                  b("Empezar", f"hacer:encargo:empezar:{i}")])
    if foco.get("tema") and foco.get("resuelto"):
        fila("terminadas", f"Tema resuelto: «{foco['tema']}»", "Resuelto — la solución está en Conocimiento",
             [b("Parar", "", False), b("Borrar", "", False), b("Empezar", "decir:retoma el tema")])
    return filas
