# -*- coding: utf-8 -*-
"""
mando_kira.py - El MÓVIL COMO MANDO de la Kira del portátil (v2.84). VA EN EL APK; puro, sin red ni Kivy.

Cuando la Kira completa del portátil está en casa (kira_portatil/nucleo_portatil.py), el móvil le PASA las órdenes de
trabajo (estudiar, pensar, investigar, programar, experimentar, charlar con memoria…) y solo enseña la barra y la
respuesta. Lo que es DEL MÓVIL se queda en el móvil: moverse por la app, la cámara, la pantalla, llamar o abrir apps,
el volumen, «para», las mejoras (laboratorio + dos toques), el pintor y los PDF/juegos que tienes aquí.

  orden_control(texto) -> 'on' | 'off' | 'memoria' | 'estado' | None
  es_local(texto)      -> True si esa orden se hace SIEMPRE en el móvil
  es_trabajo(texto)    -> v2.87: True si es TRABAJO para KiraOS (programar, juegos, apps, diseños, pintar, experimentar,
                          mejoras, librerías, su máquina). Fuera de casa, el móvil lo APUNTA y se lo pasa al volver.
  orden_modo_app(texto)-> 'sencillo' | 'completo' | None («modo completo» = las pantallas de antes, por si acaso)
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


# ---------- v2.87: la app del móvil en DOS pantallas; el trabajo lo hace KiraOS ----------
_SIEMPRE = re.compile(
    r"^(?:experimenta|inventa(?:me)?|implementa(?:me)?|compila(?:me)?|disena(?:me)?|pinta(?:me)?|dibuja(?:me)?|"
    r"programa(?:me)?|desarrolla(?:me)?|conviertelo|conviertela|convierte(?:lo|la)?|exporta(?:lo|la)?|"
    r"pon el juego|prepara(?:me)? una mejora|instala(?:me)?\s+(?:la\s+)?libreria|ilustra(?:me)?)\b")
_OBJETO = (r"(?:programa|juego|app|aplicacion|apk|web|pagina|maqueta|diseno|videoclip|dibujo|imagen|foto de|"
           r"ilustracion|logo|sprites?|algoritmo|script|codigo|funcion|calculadora|herramienta|mejora|modulo|"
           r"libreria|bot|videojuego|interfaz)")
_HAZ = re.compile(r"^(?:por favor\s+)?(?:haz(?:me)?|crea(?:me)?|escribe(?:me)?|genera(?:me)?|construye(?:me)?|"
                  r"monta(?:me)?|fabrica(?:me)?|prepara(?:me)?|quiero)\s+(?:que\s+hagas\s+)?(?:un|una|unos|unas|"
                  r"el|la|mi|otro|otra)?\s*(?:[a-z]+\s+){0,2}?" + _OBJETO + r"\b")
_CAMARA = re.compile(r"^(?:haz(?:me)?|saca(?:me)?)\s+una\s+(?:foto|captura|llamada)(?:\s+(?:a|al|a la)\b.*)?$")
_MODO_COMPLETO = re.compile(r"^(?:pon|activa|vuelve a)\s+(?:el\s+)?modo\s+completo$|^modo completo$|"
                            r"^(?:pon|devuelveme|vuelve a poner)\s+(?:las\s+)?(?:pantallas|salas)\s+(?:antiguas|de antes)$")
_MODO_SENCILLO = re.compile(r"^(?:pon|activa|vuelve a)\s+(?:el\s+)?modo\s+sencillo$|^modo sencillo$|"
                            r"^(?:solo|deja solo)\s+(?:las\s+)?dos\s+pantallas$")


def orden_modo_app(texto):
    t = _norm(texto)
    if _MODO_COMPLETO.match(t):
        return "completo"
    if _MODO_SENCILLO.match(t):
        return "sencillo"
    return None


def es_trabajo(texto):
    t = _norm(texto)
    if not t or orden_control(texto) or orden_modo_app(texto):
        return False
    if es_de_maquina(texto):
        return True
    if _CAMARA.match(t):
        return False
    return bool(_SIEMPRE.match(t) or _HAZ.match(t))


def mejora_es_de_kiraos(texto):
    """v3.07: «mejora KiraOS: …» / «mejora el portátil…» es una mejora para KiraOS (se la pasa tal cual)."""
    return bool(re.match(r"^(?:por favor\s+)?(?:mejora|prepara(?:le)?\s+una\s+mejora\s+(?:a|para))\s+(?:a\s+)?"
                         r"(?:kira ?os|el portatil|el sistema del portatil)\b", _norm(texto)))


def orden_de_mejora(pedido):
    """Una mejora para el móvil la escribe y la prueba KiraOS (la orden que entiende su núcleo)."""
    return "prepara una mejora para el móvil: " + str(pedido or "").strip()


# ---------- v2.88: la WiFi del PORTÁTIL (la maneja KiraOS) ----------
_WIFI = re.compile(r"\b(?:wifi|wi-fi|wi fi|redes? inalambricas?|internet)\b")
_DE_KIRAOS = re.compile(r"\b(?:portatil|kira ?os|ordenador|pc|packard)\b")
_WIFI_PELIGRO = re.compile(r"\b(?:apaga|desactiva|desconecta|desconectate|olvida|borra|elimina|quita|clave|"
                           r"contrasena|password)\b")


def es_wifi_kiraos(texto):
    """¿Habla de la WiFi del portátil? («qué wifi tiene el portátil», «arregla la wifi de KiraOS»…)."""
    t = _norm(texto)
    return bool(_WIFI.search(t) and _DE_KIRAOS.search(t))


def wifi_solo_en_portatil(texto):
    """Apagar, desconectar, olvidar o dar una clave: eso se hace EN el portátil (desde el móvil te quedarías sin
    KiraOS, y la clave viajaría)."""
    return bool(_WIFI_PELIGRO.search(_norm(texto)))


# ---------- v3.02: órdenes FUERA DE CASA (por Tailscale), solo las tranquilas ----------
# Decisión del dueño (v3.02, cambia la de la v2.88): desde fuera de casa SÍ puede mandarle a KiraOS lo que solo
# estudia, investiga, piensa o programa en modo seguro / en su máquina. Lo que toca el portátil, la casa, la WiFi,
# la cámara, instalar, claves o GitHub sigue esperando a que vuelva a casa. El portátil lo comprueba OTRA VEZ.
_Y_PRUEBALO = re.compile(r"\s*,?\s*y\s+pruebalo\s+en\s+(?:tu|la)\s+maquina(?:\s+virtual)?$")
_NO_FUERA = re.compile(
    r"\b(?:wifi|wi-fi|wi fi|router|aparatos|puertos?\s+abiertos|camara|webcam|microfono|apk|github|compila(?:me|lo|la|r)?|"
    r"libreria\w*|clave|contrasena|password|token|cebo|honeypot|emparejar)\b|"
    r"\b(?:mi|tu|nuestra)\s+red\b|\bred\s+de\s+casa\b|app\s+de\s+verdad|\bandroid\b|\binstalable\b|^anadete\b|"
    r"^(?:apaga\w*|reinicia\w*|enciende\w*|arranca\w*|instala\w*|desinstala\w*|ejecuta\w*|borra\w*|elimina\w*|"
    r"cambia\s+el\s+aspecto|pon\s+el\s+tema|prepara(?:me)?\s+una\s+mejora|mejora(?:te)?\b)|"
    r"^(?:lee|mira|que\s+(?:hay|pone))\b.{0,20}\bpantalla\b|^(?:haz|saca)(?:me)?\s+una\s+(?:foto|captura)|"
    r"^que\s+(?:ves|tengo\s+delante)|(?:pasa|envia|manda|copia)(?:le)?\s+(?:tu|la|mi)\s+memoria")
_SI_FUERA = re.compile(
    r"^(?:estudia|aprende|investiga|preguntate|pregunta|averigua|mira\s+a\s+ver|busca(?:me)?|lee(?:me)?|"
    r"resume(?:me)?|guarda|piensa|ponte\s+a\s+pensar|centrate|concentrate|enfocate|resuelve(?:me)?|retoma|dejalo|"
    r"aparca|vuelve\s+al\s+tema|experimenta|programa(?:me)?|desarrolla(?:me)?|sincroniza(?:te)?|"
    r"tu\s+cuaderno|tus\s+(?:soluciones|preguntas)|que\s+has\s+(?:pensado|resuelto)|"
    r"(?:estudia\s+)?solo\s+lo\s+(?:que\s+yo\s+te\s+mande|mio)|piensa\s+libre)\b")
_HAZ_FUERA = re.compile(r"\b(?:programa|juego|videojuego|algoritmo|script|codigo|funcion|calculadora|herramienta|"
                        r"bot|app|aplicacion|web|pagina|maqueta|diseno)\b")


def permitida_fuera(texto):
    """¿Esta orden se la puedo pasar a KiraOS FUERA de casa (por Tailscale)? -> (bool, motivo para decírtelo).
    Solo lo tranquilo: estudiar, investigar, pensar, buscar y programar (en modo seguro o en su máquina)."""
    t = _Y_PRUEBALO.sub("", _norm(texto))
    no = ("Eso, fuera de casa, no se lo paso: toca el portátil o tu casa. Te lo apunto y se lo doy en cuanto "
          "volvamos a estar en la misma WiFi.")
    if not t:
        return False, no
    if _NO_FUERA.search(t) or es_de_maquina(t) or orden_control(t) or orden_modo_app(t):
        return False, no
    if _SI_FUERA.match(t) or (_HAZ.match(t) and _HAZ_FUERA.search(t)):
        return True, ""
    return False, no
