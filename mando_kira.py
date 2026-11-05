# -*- coding: utf-8 -*-
"""
mando_kira.py - El MÓVIL COMO MANDO de la Kira del portátil (v2.84). VA EN EL APK; puro, sin red ni Kivy.

Cuando la Kira completa del portátil está en casa (kira_portatil/nucleo_portatil.py), el móvil le PASA las órdenes de
trabajo (estudiar, pensar, investigar, programar, experimentar, charlar con memoria…) y solo enseña la barra y la
respuesta. Lo que es DEL MÓVIL se queda en el móvil: moverse por la app, la cámara, la pantalla, llamar o abrir apps,
el volumen, «para», las mejoras (laboratorio + dos toques), el pintor y los PDF/juegos que tienes aquí.

  orden_control(texto) -> 'on' | 'off' | 'memoria' | 'estado' | None
  es_local(texto)      -> True si esa orden se hace SIEMPRE en el móvil
"""
import re
import unicodedata


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", t)
    return re.sub(r"\s+", " ", t).strip(" .!¡?¿")


_ON = re.compile(r"^(?:activa|enciende|pon)\s+(?:el\s+)?modo\s+mando$|^modo\s+mando$|"
                 r"^(?:trabaja|piensa|hazlo|hazlo todo)\s+(?:en|con)\s+(?:el|mi|tu)\s+portatil$|"
                 r"^usa\s+(?:el|mi|tu)\s+portatil(?:\s+para\s+todo)?$|^que lo haga (?:el|tu|mi) portatil$")
_OFF = re.compile(r"^(?:desactiva|apaga|quita)\s+(?:el\s+)?modo\s+mando$|"
                  r"^(?:trabaja|piensa|hazlo)\s+(?:en|con)\s+(?:el\s+)?movil$|^trabaja aqui$|^hazlo (?:tu )?aqui$|"
                  r"^no uses (?:el|mi|tu) portatil$")
_MEM = re.compile(r"^(?:pasa|envia|manda|copia|lleva|sincroniza)(?:le)?\s+(?:toda\s+)?(?:tu|la|mi)\s+memoria"
                  r"(?:\s+(?:al|a\s+tu|a\s+mi)\s+portatil)?$|^sincroniza(?:te)?\s+con\s+(?:el|tu)\s+portatil$")
_EST = re.compile(r"^(?:estado del portatil|como esta (?:el|tu|mi) portatil|que (?:hace|esta haciendo) "
                  r"(?:el|tu) portatil|esta (?:el|tu|mi) portatil)$")


def orden_control(texto):
    t = _norm(texto)
    if _ON.match(t):
        return "on"
    if _OFF.match(t):
        return "off"
    if _MEM.match(t):
        return "memoria"
    if _EST.match(t):
        return "estado"
    return None


# Lo que SIEMPRE se hace en el móvil (es del aparato que tienes en la mano)
_LOCAL = re.compile(
    r"^(?:abre|ve a|vete a|vuelve|atras|inicio|pantalla de inicio|menu|cierra|sal$|salir|juega\b|jugar\b|"
    r"llama|marca|whatsapp|mensaje a|pon (?:la )?musica|musica|sube|baja|volumen|alarma|temporizador|"
    r"recuerdame|foto|haz(?:me)? una foto|saca una foto|que ves|mira (?:esto|la camara|la pantalla)|camara|"
    r"lee (?:la )?pantalla|que hay en (?:la )?pantalla|captura|graba|linterna|"
    r"para$|parate|cancela|calla|silencio|habla (?:mas|menos)|"
    r"pinta|dibuja|disena|implementa|mejora(?:te)?\b(?!\s+(?:sin parar|constantemente))|aprende a\b|instala|desinstala|"
    r"(?:cerebro|oido|voz) |descarga (?:el|tu) cerebro|configuracion|ajustes|config\b)")


def es_de_maquina(texto):
    """v2.85: ¿habla de la MÁQUINA VIRTUAL de Kira? Esa vive en el portátil: siempre se le pasa allí."""
    return bool(re.search(r"\b(?:tu|la|mi)\s+maquina\b", _norm(texto)))


def es_local(texto):
    t = _norm(texto)
    if not t:
        return True
    if orden_control(texto):
        return True
    if es_de_maquina(texto):
        return False
    return bool(_LOCAL.match(t))
