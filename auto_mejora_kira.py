# -*- coding: utf-8 -*-
"""
auto_mejora_kira.py — la AUTO-MEJORA de Kira, con RED DE SEGURIDAD.

Lo pidió el dueño (v2.79): «quiero que lo implemente ella sola, sin decir nada; que haga pruebas/ensayos de
verificación hasta que dé OK; que programe un retorno (si falla, que vuelva atrás); que me informe lo que ha
implementado y me lleve a donde está el código». Eligió: «Auto SOLO si pasa TODO + retorno», con un interruptor
que enciende él (viene APAGADO).

Qué NO cambia (seguridad): una mejora SOLO se aplica sola si PASA el laboratorio del móvil y sus pruebas. Eso lo
decide el PROMOTOR (no este módulo). Este módulo es lógica PURA (sin Kivy, se prueba sin pantalla) y solo lleva:
  - el interruptor on/off (apagado por defecto),
  - el estado de VERIFICACIÓN al arrancar (para el RETORNO: si la última vez la app se cayó, se revierte),
  - el REGISTRO de lo implementado (para avisarte y para «llévame al código»).
Nada aquí ejecuta ni instala código: solo guarda decisiones en disco.
"""
import json
import os
import time

AJUSTES = "auto_mejora.json"            # {"on": bool}
VERIFICAR = "auto_mejora_verificar.json"  # la última mejora aplicada sola, a la espera de confirmar el arranque
LOG = "auto_mejoras_hechas.json"        # historial [{nombre, resumen, cuando, estado, ruta}]


def _ruta(dir_, nombre):
    return os.path.join(dir_, nombre)


def _leer(ruta, por_defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return por_defecto


def _guardar(ruta, dato):
    try:
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dato, f, ensure_ascii=False)
        os.replace(tmp, ruta)
        os.chmod(ruta, 0o600)
    except OSError:
        pass


# ---------- interruptor (viene APAGADO; lo enciende el dueño) ----------
def encendido(dir_):
    return bool(_leer(_ruta(dir_, AJUSTES), {}).get("on"))


def encender(dir_, on=True):
    _guardar(_ruta(dir_, AJUSTES), {"on": bool(on)})
    return bool(on)


# ---------- registro de lo aplicado + verificación al arrancar (retorno) ----------
def marcar_aplicada(dir_, nombre, resumen="", ruta_codigo=""):
    """Acaba de aplicarse SOLA una mejora que pasó TODO. Queda a la espera de confirmar que la app arranca bien;
    si no, en el próximo arranque se revierte (retorno)."""
    cuando = int(time.time())
    _guardar(_ruta(dir_, VERIFICAR), {"nombre": nombre, "resumen": str(resumen)[:400],
                                      "cuando": cuando, "confirmada": False})
    hechas = _leer(_ruta(dir_, LOG), [])
    if not isinstance(hechas, list):
        hechas = []
    hechas.append({"nombre": nombre, "resumen": str(resumen)[:400], "cuando": cuando,
                   "estado": "aplicada", "ruta": str(ruta_codigo)})
    _guardar(_ruta(dir_, LOG), hechas[-100:])


def pendiente_verificar(dir_):
    """La mejora aplicada sola que aún no se ha confirmado (o None)."""
    v = _leer(_ruta(dir_, VERIFICAR), None)
    if isinstance(v, dict) and v.get("nombre") and not v.get("confirmada"):
        return v
    return None


def decidir_al_arrancar(dir_, hubo_crash):
    """PURO. Al arrancar, ¿qué hacer con una mejora aplicada sola sin confirmar? Si la última vez la app se CAYÓ,
    esa mejora es sospechosa -> REVERTIR (retorno). Si arrancó bien -> CONFIRMAR. Devuelve (accion, nombre):
    accion es 'revertir', 'confirmar' o 'nada'."""
    v = pendiente_verificar(dir_)
    if not v:
        return ("nada", "")
    return ("revertir" if hubo_crash else "confirmar", v["nombre"])


def confirmar(dir_, nombre):
    """La app arrancó bien con la mejora: queda confirmada (no se revertirá)."""
    _guardar(_ruta(dir_, VERIFICAR), {"nombre": nombre, "confirmada": True})
    _marcar_estado(dir_, nombre, "confirmada")


def revertida(dir_, nombre, motivo=""):
    """La mejora se revirtió (retorno) porque la app se cayó."""
    _guardar(_ruta(dir_, VERIFICAR), {"nombre": nombre, "confirmada": True, "revertida": True,
                                      "motivo": str(motivo)[:200]})
    _marcar_estado(dir_, nombre, "revertida")


def _marcar_estado(dir_, nombre, estado):
    hechas = _leer(_ruta(dir_, LOG), [])
    if not isinstance(hechas, list):
        return
    for h in reversed(hechas):
        if h.get("nombre") == nombre and h.get("estado") == "aplicada":
            h["estado"] = estado
            break
    _guardar(_ruta(dir_, LOG), hechas)


# ---------- para avisarte y llevarte al código ----------
def lista_hechas(dir_, n=20):
    h = _leer(_ruta(dir_, LOG), [])
    return h[-n:] if isinstance(h, list) else []


def ultima_hecha(dir_):
    h = lista_hechas(dir_, 1)
    return h[0] if h else None


def texto_hechas(dir_, n=10):
    h = lista_hechas(dir_, n)
    if not h:
        return ("Aún no he implementado nada yo sola. Con la auto-mejora encendida, cuando una mejora pase todas mis "
                "pruebas la aplico y la verás aquí (y en la Sala Hacker ▸ Biblioteca ▸ Módulos).")
    icono = {"aplicada": "•", "confirmada": "✔", "revertida": "↩"}
    out = ["Lo que he implementado yo sola:"]
    for x in reversed(h):
        est = x.get("estado", "aplicada")
        extra = {"confirmada": " (funcionó)", "revertida": " (fallaba al arrancar: la quité)"}.get(est, " (recién puesta)")
        out.append(f"\n{icono.get(est, '•')} {x.get('nombre', '')}{extra}\n   {str(x.get('resumen', ''))[:140]}")
    out.append("\n\nPara ver el código: «llévame al código» (Sala Hacker ▸ Biblioteca ▸ Módulos).")
    return "\n".join(out)
