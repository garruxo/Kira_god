# -*- coding: utf-8 -*-
"""
pensador_kira.py - El NÚCLEO de la curiosidad de Kira (compartido: móvil y portátil). Lógica pura, sin red ni Kivy.

La idea del dueño: que Kira no solo GUARDE lo que sabe, sino que lo CUESTIONE sola y constantemente: «¿por qué esto
funciona así?, ¿cómo se hace?, ¿para qué sirve?, ¿y si fuera de otra forma?». Y, como es programadora, que cuando la
pregunta sea de código no se quede en pensar: que EXPERIMENTE (escriba un programa y lo pruebe) para entenderlo.

Aquí va solo la parte PURA (se prueba sin nada):
  - generar_preguntas(semilla)      las preguntas que se hace;
  - clasificar_respuesta(texto)     seguridad (alta/media/baja) y si es una duda;
  - es_programable(texto)           si conviene PROBARLO con código;
  - Cuaderno (cargar/guardar/anotar/ya_pensada/proxima_semilla/texto/resumen);
  - pensar_una(estado, preguntar, estudiar, experimentar, ...)  un pensamiento entero, con todo inyectado.

Cada sitio (móvil / portátil) pone sus propias funciones `preguntar` (su cerebro), `estudiar` (su internet) y
`experimentar` (su editor seguro o su espacio aislado). HONESTO: lo que piensa son NOTAS; nunca se aplica solo
(para eso: su laboratorio + los dos toques del dueño). El cerebro se equivoca: por eso cada nota lleva su seguridad.
"""
import json
import os
import time
import unicodedata

MAX_NOTAS = 2000

SEMILLAS = [
    "una función", "un bucle", "la recursividad", "una lista", "un diccionario", "una pila", "una cola",
    "un árbol binario", "un grafo", "la complejidad de un algoritmo", "la ordenación rápida (quicksort)",
    "la búsqueda binaria", "una tabla hash", "la memoria caché", "un hilo (thread)", "un proceso",
    "el cifrado", "una función hash", "una petición HTTP", "una base de datos", "una expresión regular",
    "la programación orientada a objetos", "una excepción", "un puntero", "la pila de llamadas",
    "un cortafuegos", "el phishing", "la detección de anomalías", "una contraseña segura", "una clave pública",
]

_TIPOS_PREGUNTA = [
    "¿por qué {s} funciona así por dentro?",
    "¿cómo se hace o se construye {s}, paso a paso?",
    "¿para qué sirve {s} en la práctica, con un ejemplo?",
    "¿qué pasaría si {s} fallara o no existiera?",
    "¿en qué se parece y en qué se diferencia {s} de algo que ya conozco?",
]

_PROGRAMABLE = ("funcion", "bucle", "recursi", "lista", "diccionario", "pila", "cola", "arbol", "grafo",
                "algoritmo", "quicksort", "ordenac", "busqueda binaria", "tabla hash", "hash", "cache",
                "hilo", "thread", "proceso", "cifrado", "regex", "expresion regular", "objeto", "clase",
                "excepcion", "puntero", "anomalia", "contrasena")


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def es_programable(texto):
    n = _norm(texto)
    return any(p in n for p in _PROGRAMABLE)


def generar_preguntas(semilla):
    return [p.format(s=semilla) for p in _TIPOS_PREGUNTA]


def clasificar_respuesta(texto):
    """(seguridad 'alta'|'media'|'baja', es_duda)."""
    t = _norm(texto)
    if len(t) < 25 or any(f in t for f in ("no lo se", "no se ", "no estoy seguro", "no tengo ni idea",
                                           "no puedo responder", "desconozco")):
        return "baja", True
    if any(f in t for f in ("creo que", "quiza", "quizas", "puede que", "tal vez", "no estoy del todo",
                            "probablemente", "me parece que")):
        return "media", False
    return "alta", False


def _vacio():
    return {"notas": [], "vistas": [], "soluciones": {}, "desde": int(time.time()), "i": 0}


def cargar(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in _vacio().items():
            d.setdefault(k, v)
        return d
    except (OSError, ValueError):
        return _vacio()


def guardar(estado, ruta):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)
    os.replace(tmp, ruta)
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass


def ya_pensada(estado, pregunta):
    return _norm(pregunta) in set(estado.get("vistas", []))


def anotar(estado, nota):
    clave = _norm(nota.get("pregunta", ""))
    if not clave or clave in set(estado.get("vistas", [])):
        return False
    estado.setdefault("notas", []).append(nota)
    estado.setdefault("vistas", []).append(clave)
    if len(estado["notas"]) > MAX_NOTAS:
        estado["notas"] = estado["notas"][-MAX_NOTAS:]
        estado["vistas"] = estado["vistas"][-MAX_NOTAS:]
    return True


def proxima_semilla(estado, semillas=None):
    semillas = semillas or SEMILLAS
    notas = estado.get("notas", [])
    sols = estado.get("soluciones", {})
    i = estado.get("i", 0)
    estado["i"] = i + 1
    # de vez en cuando VUELVE a una solución ya guardada para MEJORARLA (lo pidió el dueño: ir mejorando más adelante)
    if sols and i % 5 == 4:
        viejo = min(sols.values(), key=lambda s: s.get("cuando", 0))
        if viejo.get("semilla"):
            return viejo["semilla"] + " (mejorar)"
    if notas and i % 3 == 2:
        base = notas[-1].get("semilla") or ""
        if base:
            return base + " (más a fondo)"
    return semillas[i % len(semillas)]


def es_resuelta(nota):
    """¿Esta nota es ya una SOLUCIÓN fiable? Alta seguridad, sin duda y, si probó código, funcionó."""
    if not nota or nota.get("duda"):
        return False
    if nota.get("seguridad") != "alta":
        return False
    exp = nota.get("experimento")
    if exp is not None and not exp.get("ok"):
        return False
    return True


def _punt_sol(s):
    return (1 if (s.get("codigo") or "").strip() else 0, len(s.get("respuesta", "")))


def consolidar(estado, nota):
    """Lo pidió el dueño: cuando un tema queda RESUELTO, Kira se queda con la SOLUCIÓN y BORRA del cuaderno las notas
    flojas (dudas, fallos, sin cerebro) de ESE mismo tema, para dejarlo limpio y poder MEJORARLO más adelante.
    La solución va aparte (estado['soluciones'][tema]): se queda con la mejor y cuenta las veces que la ha mejorado.
    No toca 'vistas' (para no volver a hacerse la misma pregunta). Devuelve True si consolidó."""
    if not es_resuelta(nota):
        return False
    tema = _norm(nota.get("semilla", ""))
    if not tema:
        return False
    exp = nota.get("experimento") or {}
    sols = estado.setdefault("soluciones", {})
    prev = sols.get(tema)
    nueva = {"semilla": nota.get("semilla", ""), "pregunta": nota.get("pregunta", ""),
             "respuesta": (nota.get("respuesta", "") or "")[:800], "codigo": (exp.get("codigo") or "")[:1500],
             "cuando": int(nota.get("cuando", time.time())),
             "veces": (prev.get("veces", 1) if prev else 0) + 1}
    # se queda con la MEJOR (código que funciona > respuesta más completa), pero cuenta siempre la mejora
    mejor = nueva if (prev is None or _punt_sol(nueva) >= _punt_sol(prev)) else dict(prev)
    mejor["veces"] = nueva["veces"]
    mejor["cuando"] = nueva["cuando"]
    sols[tema] = mejor
    # limpiar las notas flojas del MISMO tema (ya está resuelto): fuera dudas, fallos, sin cerebro/permiso/error
    nuevas = []
    for nt in estado.get("notas", []):
        if nt is nota:
            nuevas.append(nt)
            continue
        mismo = _norm(nt.get("semilla", "")) == tema
        e = nt.get("experimento")
        floja = (nt.get("duda") or nt.get("seguridad") == "baja"
                 or nt.get("fuente") in ("sin cerebro", "error", "permiso")
                 or (e is not None and not e.get("ok")))
        if mismo and floja:
            continue
        nuevas.append(nt)
    estado["notas"] = nuevas
    return True


def texto_soluciones(estado):
    sols = estado.get("soluciones", {})
    if not sols:
        return ("Aún no tengo soluciones guardadas. Cuando resuelva un tema del todo, me quedo con la solución aquí "
                "y borro los intentos fallidos de ese tema, para ir mejorándola más adelante.")
    out = [f"Soluciones que Kira ya tiene ({len(sols)}):"]
    for s in sorted(sols.values(), key=lambda x: x.get("cuando", 0), reverse=True)[:20]:
        veces = s.get("veces", 1)
        mejora = f" (mejorada {veces} veces)" if veces > 1 else ""
        cod = " [con código]" if (s.get("codigo") or "").strip() else ""
        resp = (s.get("respuesta", "") or "").replace("\n", " ")[:160]
        out.append(f"\n• {s.get('semilla', '')}{mejora}{cod}\n   -> {resp}")
    return "\n".join(out)


def pensar_una(estado, preguntar, estudiar=None, experimentar=None, comparar=None, insistir=1, semillas=None,
               ahora=None):
    """Un pensamiento: elige semilla + pregunta NUEVA, se responde, estudia si duda y, si es de código, EXPERIMENTA
    y (si puede) COMPARA su código con uno de fuera para mejorar. Todo inyectado. Devuelve la nota (o None)."""
    ahora = int(ahora if ahora is not None else time.time())
    semilla = proxima_semilla(estado, semillas)
    pregunta = next((q for q in generar_preguntas(semilla) if not ya_pensada(estado, q)), None)
    if pregunta is None:
        pregunta = f"¿qué más debería entender sobre {semilla}?"
        if ya_pensada(estado, pregunta):
            return None

    base = ("Piensa como programadora curiosa. Responde BREVE y claro. Si no lo sabes, di «NO LO SÉ».\n"
            "Pregunta: " + pregunta)
    try:
        respuesta = str(preguntar(base) or "")
    except Exception as e:                               # el cerebro no está listo, sin red, etc.: QUE SE VEA
        nota = {"cuando": ahora, "semilla": semilla, "pregunta": pregunta,
                "respuesta": f"(no pude pensar ahora: {e})", "seguridad": "baja", "duda": True,
                "fuente": "sin cerebro", "tipo": "idea"}
        anotar(estado, nota)
        return nota
    seguridad, duda = clasificar_respuesta(respuesta)
    fuente = "lo que sé"

    # INSISTE: mientras siga siendo una DUDA, busca y vuelve a pensar, hasta `insistir` veces (no infinito: el
    # cerebro pequeño es lento y «la perfección» no se garantiza, pero así no se rinde al primer «no lo sé»).
    intentos = 0
    while duda and estudiar is not None and intentos < max(1, insistir):
        intentos += 1
        try:
            material = str(estudiar(pregunta) or "")
        except Exception:
            material = ""
        if not material:
            break
        respuesta = str(preguntar(base + "\n\nMe he informado y dice:\n" + material[:1500] +
                                  "\n\nAhora respóndete con esto, claro y seguro.") or "") or respuesta
        seguridad, duda = clasificar_respuesta(respuesta)
        fuente = "estudiado"

    nota = {"cuando": ahora, "semilla": semilla, "pregunta": pregunta, "respuesta": respuesta.strip(),
            "seguridad": seguridad, "duda": duda, "fuente": fuente, "tipo": "idea"}

    if experimentar is not None and es_programable(semilla):
        try:
            exp = experimentar(pregunta, semilla)
        except Exception as e:
            exp = {"ok": False, "resultado": f"no pude experimentar: {e}"}
        if exp:
            nota["tipo"] = "experimento"
            nota["experimento"] = exp
            if exp.get("ok"):
                nota["seguridad"] = "alta" if seguridad != "baja" else "media"

    # Comparar su código con uno de fuera (para mejorar su técnica). Es una NOTA; nada se mete solo en su cerebro.
    if comparar is not None and es_programable(semilla):
        codigo_mio = (nota.get("experimento") or {}).get("codigo", "")
        try:
            comp = comparar(pregunta, semilla, codigo_mio)
        except Exception:
            comp = None
        if comp:
            nota["comparacion"] = comp

    anotar(estado, nota)
    consolidar(estado, nota)      # si quedó resuelto, me quedo con la solución y limpio los intentos flojos del tema
    return nota


def ciclo(estado, semilla, preguntar, estudiar=None, experimentar=None, comparar=None, rondas=3, ahora=None):
    """El CICLO DE MEJORA que no para: pensar → buscar info → comparar → experimentar → juzgar si funciona → si no,
    buscar más y volver a intentarlo, mejorando cada vuelta. Se queda con la mejor versión y guarda el recorrido.
    Todo inyectado (preguntar/estudiar/experimentar/comparar) para probarlo sin red ni cerebro. Acotado a `rondas`
    (el cerebro pequeño es lento; nada infinito). Devuelve la nota del ciclo."""
    ahora = int(ahora if ahora is not None else time.time())
    pregunta = f"¿cómo dominar {semilla} y mejorarlo?"

    info = ""
    if estudiar is not None:
        try:
            info = str(estudiar(f"cómo se hace {semilla}") or "")[:1200]
        except Exception:
            info = ""
    try:
        idea = str(preguntar(f"Quiero dominar «{semilla}». "
                             + (f"Esto he averiguado: {info}\n" if info else "")
                             + "Explica BREVE cómo hacerlo y cómo probar que funciona.") or "")
    except Exception as e:
        nota = {"cuando": ahora, "semilla": semilla, "pregunta": pregunta,
                "respuesta": f"(no pude pensar ahora: {e})", "seguridad": "baja", "duda": True,
                "fuente": "sin cerebro", "tipo": "idea"}
        anotar(estado, nota)
        return nota

    historial, mejor, prev_codigo = [], None, ""
    for r in range(1, max(1, rondas) + 1):
        pedido = (f"{semilla}. Mejora este código y hazlo mejor:\n{prev_codigo}" if prev_codigo
                  else f"{semilla}. Escribe y prueba la idea.")
        exp = {}
        if experimentar is not None:
            try:
                exp = experimentar(pedido, semilla) or {}
            except Exception as e:
                exp = {"ok": False, "resultado": str(e)[:160]}
        comp = None
        if comparar is not None and (exp.get("codigo") or "").strip():
            try:
                comp = comparar(pedido, semilla, exp.get("codigo", ""))
            except Exception:
                comp = None
        funciona = bool(exp.get("ok"))
        historial.append({"ronda": r, "ok": funciona, "resultado": (exp.get("resultado") or "")[:160],
                          "comparacion": (comp or {}).get("resumen", "") if comp else ""})
        if funciona and mejor is None:
            mejor = exp
        if exp.get("codigo"):
            prev_codigo = exp["codigo"]
        # pensar cómo mejorar para la próxima vuelta
        try:
            idea = str(preguntar(f"Mi intento de «{semilla}» {'funcionó' if funciona else 'falló'}: "
                                 f"{(exp.get('resultado') or '')[:200]}. ¿Cómo lo mejoro en la próxima vuelta? "
                                 "Una idea concreta y breve.") or "") or idea
        except Exception:
            pass
        if funciona and r >= 2:                 # ya funciona y ha dado al menos una vuelta de mejora: para aquí
            break

    nota = {"cuando": ahora, "semilla": semilla, "pregunta": pregunta, "respuesta": idea.strip()[:500],
            "seguridad": "alta" if mejor else "media", "duda": mejor is None,
            "fuente": "estudiado" if info else "lo que sé", "tipo": "ciclo",
            "rondas": len(historial), "historial": historial, "experimento": mejor}
    anotar(estado, nota)
    consolidar(estado, nota)      # si el ciclo dio una versión que funciona, se guarda como solución y limpia el tema
    return nota


def texto_cuaderno(estado, n=15):
    notas = estado.get("notas", [])[-n:]
    if not notas:
        return "El cuaderno está vacío. Cuando Kira piense, aquí verás sus preguntas y lo que fue entendiendo."
    marca = {"alta": "✔", "media": "~", "baja": "?"}
    out = [f"Cuaderno de Kira — {len(estado.get('notas', []))} pensamiento(s):"]
    for nt in notas:
        m = marca.get(nt.get("seguridad"), "~")
        etq = {"ciclo": " [ciclo de mejora]", "experimento": " [experimento]"}.get(
            nt.get("tipo"), " [duda]" if nt.get("duda") else "")
        resp = (nt.get("respuesta", "") or "").replace("\n", " ")[:160]
        out.append(f"\n{m}{etq} {nt.get('pregunta', '')}\n   -> {resp} ({nt.get('fuente', '')})")
        for h in nt.get("historial", []):
            comp = f" | comparé: {h['comparacion'][:60]}" if h.get("comparacion") else ""
            out.append(f"   . ronda {h.get('ronda')}: {'OK' if h.get('ok') else 'falló'} "
                       f"{str(h.get('resultado', ''))[:90]}{comp}")
        exp = nt.get("experimento")
        if exp and not nt.get("historial"):
            out.append(f"   . prueba: {'OK' if exp.get('ok') else 'fallo'} - {str(exp.get('resultado', ''))[:120]}")
        comp = nt.get("comparacion")
        if comp:
            out.append(f"   . comparé con {comp.get('fuente', 'otra fuente')}: {str(comp.get('resumen', ''))[:140]}")
    sols = estado.get("soluciones", {})
    if sols:
        out.append(f"\n({len(sols)} tema(s) ya resuelto(s) y guardado(s) como solución; di «tus soluciones».)")
    return "\n".join(out)


def resumen(estado):
    notas = estado.get("notas", [])
    if not notas:
        return "Kira aún no ha pensado nada. Dile «piensa» para que empiece a cuestionarse las cosas."
    exps = sum(1 for n in notas if n.get("tipo") == "experimento")
    dudas = sum(1 for n in notas if n.get("duda"))
    sols = len(estado.get("soluciones", {}))
    extra = f" Ya tiene {sols} solución(es) guardada(s) (di «tus soluciones»)." if sols else ""
    return (f"Kira lleva {len(notas)} pensamiento(s): {exps} con experimento y {dudas} duda(s) por resolver.{extra} "
            "Dile «tu cuaderno» para leer qué se ha ido preguntando. (Son notas suyas; nada se aplica solo.)")
