# -*- coding: utf-8 -*-
"""
ayuda_ias_kira.py — v3.35: cuando Kira NO SABE hacer un código (falla dos veces seguidas), PREGUNTA A OTRAS IA
(Claude, Gemini, ChatGPT, DeepSeek, Mistral, Groq, OpenRouter, Grok…), PRUEBA lo que le recomiendan y se queda con lo
que funciona.

Lo pidió el dueño: «si tiene que hacer un código complejo y falla 2 veces seguidas, que pregunte a varias IA como
Claude, Gemini, ChatGPT y todas las que haya, hasta encontrar la respuesta satisfactoria, pero solo si no sabe; copia
lo que le recomienden, lo estudia en la máquina virtual y lo prueba; si sale bien, lo implanta».

Cómo va:
  1. SOLO tras dos fallos seguidos de su propio cerebro (quien llama decide cuándo: taller de kernel, programas…).
  2. Pregunta a las IA que TÚ has configurado, una detrás de otra (cada una puede corregirse una vez con el error):
     la tarea, el código que falló y el error. Nada más: ni tus archivos, ni tus claves, ni tus datos.
  3. Cada respuesta se PRUEBA con lo que diga quien llama: el kernel en QEMU; un programa en la máquina virtual de
     KiraOS (o el modo seguro). La primera que pasa, gana. Si ninguna, lo dice.
  4. Lo recomendado se guarda en el baúl («lo que me recomendó Gemini para…, funcionó/no funcionó») para aprender.
  5. «Implantar»: un programa va al editor / su icono, el kernel se queda con el cambio. Una MEJORA de Kira sigue
     pasando por el laboratorio y tus dos toques (o la auto-mejora con su interruptor): eso no cambia.

Claves: cada IA necesita la suya (de tu cuenta en esa empresa; algunas cuestan dinero por uso). Se guardan en
`ias_claves.json` (0600) en la carpeta de datos de Kira, nunca se enseñan, nunca viajan al móvil ni a la máquina
virtual (las llamadas salen directas del portátil). Claude usa la clave que ya tiene Kira (api_key.txt).
Órdenes: «config gemini <clave>», «mi clave de chatgpt es <clave>», «config chatgpt modelo <modelo>», «quita la
clave de gemini», «qué IA tengo», «pregunta a las IA: …», «pregunta a gemini: …», «desactiva / activa la ayuda de
otras IA». Los modelos por defecto pueden quedarse viejos: cámbialos con «config X modelo …».

`pedir(prov, system, usuario)` se inyecta en las pruebas (sin red).
"""
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request

PROVEEDORES = {
    "claude": {"nombre": "Claude", "tipo": "anthropic", "url": "https://api.anthropic.com/v1/messages",
               "modelo": "claude-sonnet-5-5"},
    "gemini": {"nombre": "Gemini", "tipo": "gemini",
               "url": "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
               "modelo": "gemini-2.5-flash"},
    "chatgpt": {"nombre": "ChatGPT", "tipo": "openai", "url": "https://api.openai.com/v1/chat/completions",
                "modelo": "gpt-4o-mini"},
    "deepseek": {"nombre": "DeepSeek", "tipo": "openai", "url": "https://api.deepseek.com/chat/completions",
                 "modelo": "deepseek-chat"},
    "mistral": {"nombre": "Mistral", "tipo": "openai", "url": "https://api.mistral.ai/v1/chat/completions",
                "modelo": "mistral-large-latest"},
    "groq": {"nombre": "Groq", "tipo": "openai", "url": "https://api.groq.com/openai/v1/chat/completions",
             "modelo": "llama-3.3-70b-versatile"},
    "openrouter": {"nombre": "OpenRouter", "tipo": "openai", "url": "https://openrouter.ai/api/v1/chat/completions",
                   "modelo": "openrouter/auto"},
    "grok": {"nombre": "Grok", "tipo": "openai", "url": "https://api.x.ai/v1/chat/completions", "modelo": "grok-3-mini"},
}
ORDEN = ("claude", "gemini", "chatgpt", "deepseek", "mistral", "grok", "groq", "openrouter")
ALIAS = {"openai": "chatgpt", "gpt": "chatgpt", "chat gpt": "chatgpt", "chatgpt": "chatgpt", "geminis": "gemini",
         "gemini": "gemini", "google": "gemini", "bard": "gemini", "claude": "claude", "anthropic": "claude",
         "deepseek": "deepseek", "deep seek": "deepseek", "mistral": "mistral", "groq": "groq",
         "openrouter": "openrouter", "open router": "openrouter", "grok": "grok", "xai": "grok", "x ai": "grok"}
_NOMBRES_RE = r"(chat\s?gpt|openai|gpt|g[eé]minis?|google|bard|claude|anthropic|deep\s?seek|mistral|groq|open\s?router|grok|x\s?ai)"
ARCHIVO = "ias_claves.json"
AJUSTE = "ayuda_ias.json"
ESPERA = 120


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def prov_de(nombre):
    """«Géminis» → 'gemini', «chat gpt» → 'chatgpt'… o None. Puro."""
    n = re.sub(r"\s+", " ", _norm(nombre)).strip(" .:")
    return ALIAS.get(n) or ALIAS.get(n.replace(" ", ""))


# ---------------------------------------------------------------- claves y ajustes (en disco, 0600)
def _ruta(dir_, nombre):
    return os.path.join(dir_, nombre)


def _leer(dir_, nombre):
    try:
        with open(_ruta(dir_, nombre), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _escribir(dir_, nombre, datos):
    os.makedirs(dir_, exist_ok=True)
    ruta = _ruta(dir_, nombre)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, ruta)


def clave_claude(dir_):
    try:
        with open(os.path.join(dir_, "api_key.txt"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def es_clave(texto):
    """¿Parece una clave de API? (larga, sin espacios). Puro."""
    t = str(texto or "").strip()
    return bool(re.fullmatch(r"[A-Za-z0-9_\-.:]{20,200}", t))


def poner_clave(dir_, prov, clave):
    d = _leer(dir_, ARCHIVO)
    d.setdefault(prov, {})["clave"] = str(clave).strip()
    _escribir(dir_, ARCHIVO, d)


def poner_modelo(dir_, prov, modelo):
    d = _leer(dir_, ARCHIVO)
    d.setdefault(prov, {})["modelo"] = str(modelo).strip()[:80]
    _escribir(dir_, ARCHIVO, d)


def quitar_clave(dir_, prov):
    d = _leer(dir_, ARCHIVO)
    hubo = bool(d.pop(prov, None))
    _escribir(dir_, ARCHIVO, d)
    return hubo


def configuradas(dir_):
    """[(prov, clave, modelo)] de las IA con clave, en el orden de preguntar."""
    d = _leer(dir_, ARCHIVO)
    fuera = []
    for p in ORDEN:
        clave = (d.get(p) or {}).get("clave") or (clave_claude(dir_) if p == "claude" else "")
        if clave:
            fuera.append((p, clave, (d.get(p) or {}).get("modelo") or PROVEEDORES[p]["modelo"]))
    return fuera


def activa(dir_):
    return bool(_leer(dir_, AJUSTE).get("activa", True))


def poner_activa(dir_, si):
    _escribir(dir_, AJUSTE, {"activa": bool(si)})


# ---------------------------------------------------------------- preguntar a una IA
def _post(url, cuerpo, cabeceras, espera=ESPERA):
    datos = json.dumps(cuerpo).encode("utf-8")
    req = urllib.request.Request(url, data=datos, headers=dict({"Content-Type": "application/json",
                                                                 "User-Agent": "KiraOS"}, **cabeceras))
    with urllib.request.urlopen(req, timeout=espera) as r:
        return json.loads(r.read(4_000_000).decode("utf-8", "ignore"))


def pedir_http(prov, clave, modelo, system, usuario, max_tokens=4000):
    """Pregunta de verdad a la IA `prov`. Devuelve el texto. Lanza RuntimeError con un motivo claro si falla."""
    info = PROVEEDORES[prov]
    try:
        if info["tipo"] == "anthropic":
            r = _post(info["url"], {"model": modelo, "max_tokens": max_tokens, "system": system,
                                    "messages": [{"role": "user", "content": usuario}]},
                      {"x-api-key": clave, "anthropic-version": "2023-06-01"})
            return "".join(b.get("text", "") for b in r.get("content", []) if isinstance(b, dict))
        if info["tipo"] == "gemini":
            r = _post(info["url"].format(modelo=modelo),
                      {"systemInstruction": {"parts": [{"text": system}]},
                       "contents": [{"role": "user", "parts": [{"text": usuario}]}],
                       "generationConfig": {"maxOutputTokens": max_tokens}},
                      {"x-goog-api-key": clave})
            partes = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            return "".join(p.get("text", "") for p in partes if isinstance(p, dict))
        r = _post(info["url"], {"model": modelo, "max_tokens": max_tokens,
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": usuario}]},
                  {"Authorization": "Bearer " + clave})
        return ((r.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    except urllib.error.HTTPError as e:
        motivo = {401: "la clave no vale", 403: "la clave no tiene permiso", 404: f"no existe el modelo «{modelo}»",
                  429: "límite de uso o sin saldo"}.get(e.code, f"error {e.code}")
        raise RuntimeError(f"{info['nombre']}: {motivo}") from None
    except Exception as e:                            # noqa: BLE001 - sin internet, tiempo agotado…
        raise RuntimeError(f"{info['nombre']}: no contesta ({e})") from None


def preguntar_todas(dir_, system, usuario, solo=None, pedir=None):
    """Pregunta lo mismo a todas (o a `solo`). [(nombre, texto|None, error|None)]."""
    pedir = pedir or (lambda p, c, m, s, u: pedir_http(p, c, m, s, u))
    fuera = []
    for p, clave, modelo in configuradas(dir_):
        if solo and p != solo:
            continue
        try:
            fuera.append((PROVEEDORES[p]["nombre"], pedir(p, clave, modelo, system, usuario), None))
        except Exception as e:                        # noqa: BLE001
            fuera.append((PROVEEDORES[p]["nombre"], None, str(e)))
    return fuera


# ---------------------------------------------------------------- la ayuda: preguntar, probar, quedarse con lo bueno
def ayuda(dir_, tarea, codigo, error, probar, system, formato="python", al_paso=None, parar=None, pedir=None,
          por_ia=2, guardar=None):
    """Pregunta a las IA configuradas, una tras otra, y PRUEBA cada respuesta con `probar(texto) -> (ok, motivo)`.
    Devuelve {ok, ia, texto, motivo, historial:[(ia, ok, motivo)], sin_ias}. `guardar(tema, texto)` apunta lo
    aprendido en el baúl."""
    paso = al_paso or (lambda t: None)
    parar = parar or (lambda: False)
    pedir = pedir or (lambda p, c, m, s, u: pedir_http(p, c, m, s, u))
    ias = configuradas(dir_) if activa(dir_) else []
    if not ias:
        return {"ok": False, "sin_ias": True, "historial": [], "texto": "", "ia": "",
                "motivo": ("no tengo ninguna otra IA configurada" if activa(dir_) else
                           "la ayuda de otras IA está desactivada")}
    hist = []
    base = (f"Tarea: {tarea}\n\nMi código (no funciona):\n```{formato}\n{str(codigo or '').strip()[:6000]}\n```\n\n"
            f"Error:\n{str(error or '').strip()[:2500]}\n\nDame la solución completa y que funcione.")
    for p, clave, modelo in ias:
        nombre = PROVEEDORES[p]["nombre"]
        usuario, ultimo = base, ""
        for intento in range(1, por_ia + 1):
            if parar():
                return {"ok": False, "historial": hist, "texto": "", "ia": "", "motivo": "parado", "sin_ias": False}
            paso(f"Le pregunto a {nombre}" + (" otra vez, con su error…" if intento > 1 else "…"))
            try:
                texto = pedir(p, clave, modelo, system, usuario)
            except Exception as e:                    # noqa: BLE001
                hist.append((nombre, False, str(e)))
                break
            paso(f"Pruebo lo que me dice {nombre}…")
            try:
                ok, motivo = probar(texto)
            except Exception as e:                    # noqa: BLE001
                ok, motivo = False, f"no pude probarlo: {e}"
            hist.append((nombre, ok, motivo))
            if guardar:
                try:
                    guardar(f"lo que me recomendó {nombre} para: {tarea[:80]}",
                            f"{'FUNCIONÓ' if ok else 'NO funcionó'} al probarlo ({motivo}).\n{texto[:3000]}")
                except Exception:                     # noqa: BLE001
                    pass
            if ok:
                return {"ok": True, "ia": nombre, "texto": texto, "motivo": motivo, "historial": hist, "sin_ias": False}
            ultimo = motivo
            usuario = base + f"\n\nTu propuesta anterior tampoco funcionó al probarla:\n{str(ultimo)[:1500]}\nCorrígela."
    return {"ok": False, "ia": "", "texto": "", "historial": hist, "sin_ias": False,
            "motivo": "ninguna propuesta funcionó al probarla"}


def texto_historial(hist):
    return "; ".join(f"{ia} {'✓' if ok else '✗'}" + ("" if ok else f" ({str(m)[:80]})") for ia, ok, m in hist)


# ---------------------------------------------------------------- órdenes
def orden(texto):
    """(accion, prov, valor) o None. accion: clave|modelo|quitar|lista|activar|desactivar|preguntar. Puro."""
    t = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(texto or ""), flags=re.I).strip()
    low = _norm(t).rstrip(" .!?¿¡")
    m = re.match(r"^(?:config|configura)\s+" + _NOMBRES_RE + r"\s*:?\s+modelo\s*:?\s*(\S+)$", low)
    if m:
        return ("modelo", prov_de(m.group(1)), t.split()[-1])
    m = re.match(r"^(?:config|configura)\s+" + _NOMBRES_RE + r"\s*:?\s*(\S+)$", low) or \
        re.match(r"^(?:mi|la)\s+clave\s+(?:de|del?)\s+" + _NOMBRES_RE + r"\s+es\s*:?\s*(\S+)$", low)
    if m:
        return ("clave", prov_de(m.group(1)), t.split()[-1].strip(" .:\"'"))
    m = re.match(r"^(?:quita|borra|olvida|elimina)\s+(?:la\s+)?clave\s+(?:de|del?)\s+" + _NOMBRES_RE + r"$", low)
    if m:
        return ("quitar", prov_de(m.group(1)), "")
    if re.match(r"^(?:que|cuales|a\s+que)\s+(?:ias?|inteligencias\s+artificiales|otras\s+ias?)\s+(?:tengo|tienes|hay|"
                r"puedes\s+preguntar|conoces|configuradas)|^(?:mis|tus|las)\s+ias?(?:\s+configuradas)?$", low):
        return ("lista", "", "")
    if re.match(r"^(?:desactiva|apaga|quita)\s+(?:la\s+)?ayuda\s+de\s+(?:otras\s+|las\s+)?ias?$|"
                r"^no\s+(?:preguntes|le\s+preguntes)\s+a\s+(?:otras\s+|las\s+)?ias?$", low):
        return ("desactivar", "", "")
    if re.match(r"^(?:activa|enciende|pon)\s+(?:la\s+)?ayuda\s+de\s+(?:otras\s+|las\s+)?ias?$|"
                r"^pregunta\s+a\s+otras\s+ias?\s+cuando\s+no\s+sepas$", low):
        return ("activar", "", "")
    m = re.match(r"^preg[uú]nta(?:le)?s?\s+a\s+(?:las\s+|otras\s+|todas\s+las\s+)?ias?\s*[:,]?\s*(.+)$", _norm(t)) or \
        re.match(r"^preg[uú]nta(?:le)?\s+a\s+" + _NOMBRES_RE + r"\s*[:,]?\s*(.+)$", _norm(t))
    if m:
        prov = prov_de(m.group(1)) if m.lastindex == 2 else ""
        pregunta = t[m.start(m.lastindex):] if len(t) == len(_norm(t)) else m.group(m.lastindex)
        return ("preguntar", prov or "", pregunta.strip())
    return None


def hacer(dir_, accion, prov="", valor="", pedir=None, guardar=None):
    """Hace la orden (texto para enseñar). Nunca repite una clave en la respuesta."""
    if accion in ("clave", "modelo", "quitar") and prov not in PROVEEDORES:
        return "[x] No conozco esa IA. Conozco: " + ", ".join(PROVEEDORES[p]["nombre"] for p in ORDEN) + "."
    nombre = PROVEEDORES.get(prov, {}).get("nombre", prov)
    if accion == "clave":
        if not es_clave(valor):
            return f"[x] Eso no parece una clave de {nombre} (suelen ser largas, sin espacios)."
        if prov == "claude":
            return ("La clave de Claude ya la tengo aparte (la de siempre, «config api: …»). Para las demás IA sí uso "
                    "esta forma.")
        poner_clave(dir_, prov, valor)
        return (f"[OK] Clave de {nombre} guardada (no la enseño a nadie ni sale del portátil). Cuando no sepa hacer un "
                f"código tras dos intentos, le preguntaré, probaré lo que diga y me quedaré con lo que funcione. "
                f"Modelo: {PROVEEDORES[prov]['modelo']} («config {prov} modelo …» para cambiarlo).")
    if accion == "modelo":
        poner_modelo(dir_, prov, valor)
        return f"[OK] Para {nombre} usaré el modelo «{valor}»."
    if accion == "quitar":
        return f"Clave de {nombre} borrada." if quitar_clave(dir_, prov) else f"No tenía clave de {nombre}."
    if accion == "activar":
        poner_activa(dir_, True)
        return "[OK] Si no sé hacer un código tras dos intentos, preguntaré a las otras IA que tengas configuradas."
    if accion == "desactivar":
        poner_activa(dir_, False)
        return "[OK] Ya no preguntaré a otras IA: me apaño sola (o te digo que no me sale)."
    if accion == "lista":
        ias = configuradas(dir_)
        estado = "activada" if activa(dir_) else "DESACTIVADA («activa la ayuda de otras IA»)"
        if not ias:
            return ("No tengo ninguna otra IA configurada. Pon la clave de la que quieras: «config gemini <clave>», "
                    "«config chatgpt <clave>», «config deepseek <clave>», «config mistral <clave>», «config groq "
                    "<clave>», «config openrouter <clave>», «config grok <clave>» (la de Claude es la de siempre). "
                    "Cada clave es de TU cuenta en esa empresa; algunas cobran por uso.")
        return (f"La ayuda de otras IA está {estado}. Preguntaría, por este orden, a: " +
                ", ".join(f"{PROVEEDORES[p]['nombre']} ({m})" for p, _c, m in ias) + ". Solo cuando no sé hacer un "
                "código tras dos intentos; pruebo lo que digan antes de quedármelo.")
    if accion == "preguntar":
        if not configuradas(dir_):
            return "No tengo ninguna otra IA configurada («qué IA tengo» te dice cómo poner una)."
        res = preguntar_todas(dir_, "Responde en español, claro y concreto.", valor, solo=prov or None, pedir=pedir)
        lin = []
        for ia, txt, err in res:
            lin.append(f"— {ia}: " + (txt.strip()[:1500] if txt else f"(no pude: {err})"))
            if txt and guardar:
                try:
                    guardar(f"lo que dice {ia} sobre: {valor[:80]}", txt[:3000])
                except Exception:                     # noqa: BLE001
                    pass
        return "\n\n".join(lin) or "Nadie contestó."
    return ""
