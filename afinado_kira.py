# -*- coding: utf-8 -*-
"""
afinado_kira.py - Kira APRENDE DE SUS MEJORAS (y se puede afinar de verdad con LoRA).

Tres niveles, de más fácil a más potente:
  1. EJEMPLOS PROPIOS (ya, en el móvil): cada mejora que apruebas (pasó el laboratorio y tú la instalaste) se convierte
     en una «receta propia». Cuando le pides algo parecido, su cerebro recibe ESA mejora como ejemplo: copia lo que
     a ti te gustó. (saber_mejoras_kira.contexto_para la usa.)
  2. DATOS DE ENTRENAMIENTO: «prepara datos de entrenamiento» junta tus mejoras aprobadas y sus recetas probadas en un
     archivo JSONL (formato de chat), listo para el ajuste fino; «guárdalos en descargas» los saca del móvil.
  3. AJUSTE FINO CON LoRA (en un PC con tarjeta gráfica o en Google Colab, con herramientas_pc/afinar_lora.py): sale un
     adaptador .gguf de unos megas. «instala mi ajuste: enlace» lo descarga y el cerebro del móvil lo carga
     (llama.cpp --lora). «quita mi ajuste» vuelve al cerebro normal.
Entrenar el modelo en el propio móvil no es posible (haría falta mucha más memoria y una tarjeta gráfica).
Lógica pura (sin Kivy): se prueba en el PC.
"""
import json
import os
import re
import time
import unicodedata


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def carpeta_datos():
    return os.environ.get("KIRA_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".kira")


# =====================================================================================
#  1. RECETAS PROPIAS: las mejoras que aprobaste
# =====================================================================================
def recetas_propias(base=None):
    """[{id, titulo, temas, idea, codigo, propia: True}] de las mejoras instaladas con el pedido con que se aprobaron."""
    base = base or carpeta_datos()
    carpeta = os.path.join(base, "modulos")
    try:
        with open(os.path.join(base, "lecciones_panel.json"), encoding="utf-8") as f:
            lecciones = json.load(f)
    except (OSError, ValueError):
        lecciones = []
    pedidos = {}
    for l in lecciones if isinstance(lecciones, list) else []:
        if isinstance(l, dict) and l.get("resultado") == "aprobada" and l.get("mejora"):
            pedidos[l["mejora"]] = l.get("pedido") or ""
    res = []
    if not os.path.isdir(carpeta):
        return res
    for f in sorted(os.listdir(carpeta)):
        if not f.endswith(".py"):
            continue
        nombre = f[:-3]
        try:
            with open(os.path.join(carpeta, f), encoding="utf-8") as fh:
                codigo = fh.read(20000)
        except OSError:
            continue
        pedido = re.sub(r"^Mejora para [^:]{1,40}:\s*", "", pedidos.get(nombre, "")) or nombre.replace("_", " ")
        res.append({"id": nombre, "titulo": pedido[:120], "temas": pedido + " " + nombre.replace("_", " "),
                    "idea": "Una mejora TUYA que el dueño aprobó (pasó el laboratorio y la instaló).", "codigo": codigo,
                    "propia": True})
    return res


# =====================================================================================
#  2. DATOS DE ENTRENAMIENTO (JSONL, formato de chat)
# =====================================================================================
def ejemplos(base=None):
    """Pares pedido -> respuesta buena para el ajuste fino: tus mejoras aprobadas (lo más valioso) y las recetas
    probadas que son módulos de Kira."""
    import mejoras_ia_kira as mi
    import saber_mejoras_kira as sm_
    sistema = mi.SISTEMA_MEJORA_LOCAL_CORTO
    sal = []
    for r in recetas_propias(base):
        sal.append(("propia", r["titulo"], r["id"], r["codigo"]))
    for r in sm_.RECETAS:
        if "def registrar" in r["codigo"] and len(r["codigo"]) < 6000:
            sal.append(("receta", r["titulo"], r["id"], r["codigo"].strip()))
    filas = []
    for origen, pedido, nombre, codigo in sal:
        filas.append({"messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": f"Mejora pedida: {pedido}"},
            {"role": "assistant", "content": f"NOMBRE: {nombre}\n```python\n{codigo.strip()}\n```"}],
            "origen": origen})
    return filas


def exportar(ruta, base=None):
    """Escribe el JSONL. Devuelve (nº de ejemplos, de ellos tuyos)."""
    filas = ejemplos(base)
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for fila in filas:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    os.replace(tmp, ruta)
    return len(filas), sum(1 for x in filas if x["origen"] == "propia")


# =====================================================================================
#  3. EL AJUSTE (LoRA en formato GGUF para llama.cpp)
# =====================================================================================
def es_gguf(ruta):
    try:
        with open(ruta, "rb") as f:
            return f.read(4) == b"GGUF"
    except OSError:
        return False


_PREPARA = re.compile(r"^(?:kira[\s,]+)?(?:prepara|exporta|genera|haz(?:me)?|saca)\s+(?:mis\s+|los\s+|tus\s+)?"
                      r"(?:datos|ejemplos)\s+(?:de|para\s+el)\s+(?:entrenamiento|entrenar|ajuste\s+fino|fine[\s-]?tuning)"
                      r"(?P<desc>\s+(?:y\s+)?(?:gu[aá]rdalos\s+)?(?:en|a)\s+(?:las?\s+)?descargas)?\s*$", re.I)
_INSTALA = re.compile(r"^(?:kira[\s,]+)?(?:instala|carga|pon(?:me)?|descarga)\s+(?:mi|el|tu)\s+(?:ajuste|adaptador|lora)"
                      r"(?:\s+fino)?\s*:?\s*(?P<url>https?://\S+)\s*$", re.I)
_QUITA = re.compile(r"^(?:kira[\s,]+)?(?:quita|borra|desactiva)\s+(?:mi|el|tu)\s+(?:ajuste|adaptador|lora)(?:\s+fino)?\s*$", re.I)
_ESTADO = re.compile(r"^(?:kira[\s,]+)?(?:mi|tu|el)\s+(?:ajuste|adaptador|lora)(?:\s+fino)?\s*\??$", re.I)


def interpretar(texto):
    t = " ".join(str(texto or "").split()).strip(" ¿?¡!.")
    m = _PREPARA.match(t)
    if m:
        return {"accion": "datos", "descargas": bool(m.group("desc"))}
    m = _INSTALA.match(t)
    if m:
        return {"accion": "instalar", "url": m.group("url").rstrip(".,;")}
    if _QUITA.match(t):
        return {"accion": "quitar"}
    if _ESTADO.match(t):
        return {"accion": "estado"}
    return None
