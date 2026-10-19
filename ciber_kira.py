# -*- coding: utf-8 -*-
"""
ciber_kira.py - Lógica PURA (sin Kivy ni red) de la SALA DE CIBERSEGURIDAD de Kira. SOLO DEFENSA.

Qué hace esta sala, y SOLO esto (es un búnker de lectura y aprendizaje):
  1. DISPOSITIVO: lee el estado real del aparato que Kira gobierna (RAM, CPU, disco, red, batería, sistema). Solo lee.
  2. REVISIÓN: comprueba hábitos de seguridad del propio Kira y del dispositivo con datos que ya tiene (permisos del
     archivo de la clave, si el laboratorio está expuesto, módulos con avisos, copias, actualizaciones…). Solo lee.
  3. APRENDIZAJE: una biblioteca de CONCEPTOS de amenazas explicados de forma DEFENSIVA (qué son, señales de alarma y
     cómo protegerse) y un registro de cuáles has estudiado o ya aplicas. Son textos educativos, no archivos.

Qué NO hace, a propósito: no analiza, guarda ni ejecuta código malicioso; no hace ataques ni pruebas de intrusión;
no escanea redes ajenas; no es un antivirus. Nada de aquí puede dañar el dispositivo ni a terceros: solo informa y enseña.
"""
import json
import os
import re
import shutil
import sys
import threading
import unicodedata

ESTADOS = ("por_estudiar", "estudiado", "aplicado")
_SECRETO = re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}|(?i:\b(token|api[_ ]?key|clave)\b\s*[:=]\s*[A-Za-z0-9_\-]{16,})")


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# =====================================================================================
#  1. ESTADO DEL DISPOSITIVO (solo lectura)
# =====================================================================================
def info_dispositivo():
    """Lista de (etiqueta, valor) con el estado real del aparato. No cambia nada."""
    datos = []
    # memoria
    mem = _memoria()
    datos.append(("Memoria RAM", mem))
    # CPU
    try:
        import psutil
        datos.append(("Procesador", f"{psutil.cpu_percent(interval=0.2):.0f}% en uso, {psutil.cpu_count() or '?'} núcleos"))
    except Exception:
        datos.append(("Procesador", f"{os.cpu_count() or '?'} núcleos"))
    # disco
    try:
        u = shutil.disk_usage(os.environ.get("KIRA_DATA_DIR") or os.path.expanduser("~"))
        datos.append(("Almacenamiento", f"{u.free / 1024**3:.1f} GB libres de {u.total / 1024**3:.1f} GB"))
    except OSError:
        datos.append(("Almacenamiento", "no disponible"))
    # batería
    try:
        import psutil
        b = psutil.sensors_battery()
        if b is not None:
            datos.append(("Batería", f"{b.percent:.0f}%" + (" (cargando)" if b.power_plugged else "")))
    except Exception:
        pass
    # red (solo si hay interfaces activas; no consulta internet)
    datos.append(("Red", _red()))
    datos.append(("Sistema", f"Python {sys.version.split()[0]} en {sys.platform}"))
    return datos


def _memoria():
    try:
        import psutil
        m = psutil.virtual_memory()
        return f"{m.available / 1024**3:.1f} GB libres de {m.total / 1024**3:.1f} GB"
    except Exception:
        pass
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            d = {l.split(":")[0]: int(l.split()[1]) for l in f if ":" in l and len(l.split()) > 1}
        return f"{d['MemAvailable'] / 1024**2:.1f} GB libres de {d['MemTotal'] / 1024**2:.1f} GB"
    except Exception:
        return "no disponible"


def _red():
    """¿Hay alguna interfaz de red activa? (no se conecta a ningún sitio)."""
    try:
        import psutil
        act = [n for n, s in psutil.net_if_stats().items() if s.isup and n.lower() not in ("lo", "lo0")]
        return ("conectado por " + ", ".join(act[:3])) if act else "sin interfaces activas"
    except Exception:
        return "no disponible"


# =====================================================================================
#  2. REVISIÓN DE HÁBITOS DE SEGURIDAD (solo lectura; del propio Kira y del aparato)
# =====================================================================================
def revision(dir_datos, errores_modulos=None, pasarela=None):
    """[(nivel, texto, consejo)] nivel: 'ok' | 'aviso' | 'info'. Solo mira; no cambia nada."""
    res = []
    # clave de la API: debería estar y con permisos restringidos
    clave = os.path.join(dir_datos, "api_key.txt")
    if os.path.isfile(clave):
        modo = os.stat(clave).st_mode & 0o077
        if modo and os.name == "posix":
            res.append(("aviso", "El archivo de la clave de la API es legible por otros usuarios.",
                        "Kira ya intenta ponerlo en modo privado (chmod 600); si lo copiaste a mano, hazlo privado."))
        else:
            res.append(("ok", "La clave de la API está guardada de forma privada.", ""))
    else:
        res.append(("info", "No hay clave de la API guardada.", "Sin clave Kira no charla ni programa; ponla con «config clave: …»."))
    # laboratorio/pasarela
    cfg = pasarela if isinstance(pasarela, dict) else _leer_pasarela(dir_datos)
    if cfg.get("url"):
        if "0.0.0.0" in cfg["url"]:
            res.append(("aviso", "El laboratorio parece abierto a toda la red (0.0.0.0).",
                        "Déjalo en 127.0.0.1 salvo que necesites el móvil por WiFi, y usa siempre un token largo."))
        if len(str(cfg.get("token", ""))) < 16:
            res.append(("aviso", "El token del laboratorio es corto o falta.", "Usa un token de 16+ caracteres, igual en el PC y en el móvil."))
        else:
            res.append(("ok", "El laboratorio usa un token suficientemente largo.", ""))
    # módulos con avisos de carga
    if errores_modulos:
        res.append(("aviso", f"Hay {len(errores_modulos)} módulo(s) que no cargaron bien.",
                    "Revísalos en Estado; un módulo que falla puede quitarse o volver a pedirse como mejora."))
    # módulos instalados: corren con los permisos de Kira
    carpeta_mod = os.path.join(dir_datos, "modulos")
    try:
        mods = [f for f in os.listdir(carpeta_mod) if f.endswith(".py")]
    except OSError:
        mods = []
    if mods:
        res.append(("info", f"Tienes {len(mods)} módulo(s) instalados: {', '.join(m[:-3] for m in mods[:6])}.",
                    "Cada módulo corre con los mismos permisos que Kira: deja solo los que uses (se quitan desde Mejoras)."))
    # secretos que no deberían estar en los archivos de Kira (historial, notas, bitácora…)
    sospechosos = []
    for nombre in ("conversacion.json", "notas.json", "bitacora.json", "biblioteca.json", "conocimiento.json"):
        try:
            with open(os.path.join(dir_datos, nombre), encoding="utf-8") as f:
                if _SECRETO.search(f.read(2_000_000)):
                    sospechosos.append(nombre)
        except OSError:
            continue
    if sospechosos:
        res.append(("aviso", f"Parece haber una clave o token guardado en: {', '.join(sospechosos)}.",
                    "Bórralo de ahí (o borra esa nota/conversación) y cambia esa clave por si acaso."))
    else:
        res.append(("ok", "No hay claves ni tokens guardados en el historial, notas o bitácora.", ""))
    # espacio
    try:
        u = shutil.disk_usage(dir_datos)
        if u.free < 1 * 1024**3:
            res.append(("aviso", f"Queda poco espacio ({u.free / 1024**3:.1f} GB).", "Borra vídeos o archivos grandes que ya no uses."))
    except OSError:
        pass
    # recordatorios defensivos generales (siempre útiles)
    res.append(("info", "Buenas costumbres: instala apps solo de fuentes de confianza y revisa sus permisos.",
                "Esta misma app viene fuera de la tienda; asegúrate de que el APK lo compilaste tú o viene de quien confías."))
    res.append(("info", "Ten copias de seguridad de lo que te importa.", "Fotos, vídeos y documentos, en más de un sitio."))
    return res


def _leer_pasarela(dir_datos):
    try:
        with open(os.path.join(dir_datos, "pasarela.json"), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def texto_revision(items):
    if not items:
        return "No hay nada que revisar ahora mismo."
    marca = {"ok": "[OK]", "aviso": "[!]", "info": "[i]"}
    l = ["Revisión de seguridad (solo lectura):"]
    for nivel, texto, consejo in items:
        l.append(f"  {marca.get(nivel, '·')} {texto}")
        if consejo:
            l.append(f"       {consejo}")
    avisos = sum(1 for n, _, _ in items if n == "aviso")
    l.append("")
    l.append(f"{avisos} aviso(s) que conviene mirar." if avisos else "Sin avisos. Buen trabajo.")
    return "\n".join(l)


# =====================================================================================
#  3. BIBLIOTECA DE CONCEPTOS (educación DEFENSIVA; textos, no archivos)
# =====================================================================================
CONCEPTOS = [
    {"id": "malware", "claves": ('malware', 'virus', 'troyano', 'gusano', 'software danino', 'dano', 'infect'), "nombre": "Software dañino (malware)", "categoria": "dispositivo",
     "que_es": "Programas hechos para colarse en un aparato y causar daño o robar información.",
     "senales": "Lentitud repentina, apps que no instalaste, gasto de datos o batería raro, anuncios por todas partes.",
     "protegerse": ["Instala solo desde tiendas oficiales o fuentes que conozcas.",
                    "Mantén el sistema y las apps actualizados.",
                    "Revisa los permisos que pide cada app y quita los que no tengan sentido."]},
    {"id": "phishing", "claves": ('phishing', 'engano', 'enlace', 'correo falso', 'suplant', 'estafa'), "nombre": "Phishing (engaño para robar datos)", "categoria": "engaño",
     "que_es": "Mensajes o webs que se hacen pasar por alguien de confianza para que des contraseñas o datos de pago.",
     "senales": "Urgencia («tu cuenta se cerrará»), enlaces raros, faltas de ortografía, te piden la contraseña.",
     "protegerse": ["No pulses enlaces de mensajes que no esperabas; entra tú a la web oficial.",
                    "Comprueba el remitente y la dirección real del enlace.",
                    "Activa la verificación en dos pasos (2FA) en tus cuentas importantes."]},
    {"id": "ransomware", "claves": ('ransomware', 'secuestro', 'cifra', 'rescate', 'encript'), "nombre": "Secuestro de archivos (ransomware)", "categoria": "dispositivo",
     "que_es": "Un tipo de malware que cifra tus archivos y pide dinero para devolvértelos.",
     "senales": "No puedes abrir tus archivos, aparecen con extensiones raras, un mensaje pide un rescate.",
     "protegerse": ["Haz copias de seguridad frecuentes y guarda alguna desconectada.",
                    "No abras adjuntos ni enlaces de origen dudoso.",
                    "Mantén todo actualizado: muchos ataques usan fallos ya corregidos."]},
    {"id": "contrasenas", "claves": ('contrasena', 'contrasenas', 'password', 'credencial', 'robar la contrasena', 'clave de acceso', 'login'), "nombre": "Contraseñas y robo de credenciales", "categoria": "cuentas",
     "que_es": "Contraseñas débiles o repetidas que facilitan que alguien entre en tus cuentas.",
     "senales": "Inicios de sesión que no reconoces, avisos de «nueva sesión», no poder entrar de repente.",
     "protegerse": ["Usa contraseñas largas y distintas en cada sitio; ayuda un gestor de contraseñas.",
                    "Activa la verificación en dos pasos.",
                    "Cambia la contraseña si un servicio avisa de una filtración."]},
    {"id": "wifi", "claves": ('wifi', 'wi-fi', 'red publica', 'red abierta', 'hotspot', 'vpn'), "nombre": "Redes WiFi públicas", "categoria": "red",
     "que_es": "En una WiFi abierta, otros pueden intentar ver o modificar lo que envías.",
     "senales": "Redes sin contraseña, nombres parecidos a los de verdad, webs sin el candado (HTTPS).",
     "protegerse": ["Evita la banca y las compras en WiFi abierta; mejor datos móviles.",
                    "Fíjate en el candado y en que la dirección empiece por https.",
                    "Si la usas a menudo, una VPN de confianza ayuda."]},
    {"id": "permisos", "claves": ('permiso', 'permisos', 'acceso de la app', 'microfono', 'ubicacion'), "nombre": "Apps con permisos excesivos", "categoria": "dispositivo",
     "que_es": "Apps que piden acceso a cosas que no necesitan (contactos, micrófono, ubicación) y pueden abusar de ellos.",
     "senales": "Una linterna que pide tus contactos, un juego que quiere el micrófono siempre.",
     "protegerse": ["Revisa los permisos en los ajustes del móvil y quita los que sobren.",
                    "Instala solo lo que de verdad usas.",
                    "Prefiere apps con buena reputación y muchas opiniones."]},
    {"id": "ingenieria", "claves": ('ingenieria social', 'manipul', 'enganan', 'me llaman', 'timo'), "nombre": "Ingeniería social", "categoria": "engaño",
     "que_es": "Manipular a una persona (no a la máquina) para que dé acceso o información.",
     "senales": "Alguien mete prisa, apela a la autoridad o al miedo, pide datos «para ayudarte».",
     "protegerse": ["Desconfía de las urgencias y de quien pide datos sensibles.",
                    "Verifica por otro canal antes de hacer nada (llama tú al número oficial).",
                    "Nadie legítimo te pide la contraseña completa."]},
    {"id": "actualizaciones", "claves": ('actualiza', 'parche', 'version antigua', 'update'), "nombre": "Actualizaciones al día", "categoria": "dispositivo",
     "que_es": "Las actualizaciones tapan fallos de seguridad que ya son conocidos y aprovechables.",
     "senales": "Avisos de actualización que se van posponiendo, versiones muy antiguas.",
     "protegerse": ["Activa las actualizaciones automáticas del sistema y de las apps.",
                    "No uses durante mucho tiempo dispositivos que ya no reciben parches."]},
    {"id": "copias", "claves": ('copia', 'copias', 'backup', 'respaldo', 'perder datos'), "nombre": "Copias de seguridad", "categoria": "datos",
     "que_es": "Tener copias de tus datos para no perderlos por un fallo, un robo o un secuestro de archivos.",
     "protegerse": ["Regla sencilla: 3 copias, en 2 soportes, 1 fuera de casa o en la nube.",
                    "Automatiza la copia para no depender de acordarte.",
                    "Comprueba de vez en cuando que una copia se puede restaurar."]},
    {"id": "apk", "claves": ('apk', 'fuera de la tienda', 'instalar app', 'sideload', 'fuente desconocida'), "nombre": "Instalar apps fuera de la tienda", "categoria": "dispositivo",
     "que_es": "Instalar un APK suelto (como esta app compilada) salta los controles de la tienda, para bien y para mal.",
     "protegerse": ["Instala solo APK que hayas compilado tú o que vengan de quien confías del todo.",
                    "Después de instalar, revisa qué permisos pide la app.",
                    "Mantén esa app también actualizada por tu cuenta."]},
]
CONCEPTOS += [
    {"id": "smishing", "claves": ("sms", "smishing", "mensaje de texto", "paquete pendiente", "correos te ha"), "nombre": "Estafas por SMS (smishing)", "categoria": "engaño",
     "que_es": "Mensajes de texto que imitan a un banco, una empresa de paquetería o un organismo para que pulses un enlace o llames.",
     "senales": "«Tu paquete está retenido», «pago pendiente», enlaces acortados, remitentes con números raros.",
     "protegerse": ["No pulses enlaces de SMS inesperados; entra tú en la app o web oficial.",
                    "Nunca des códigos que te lleguen por SMS a nadie que te los pida.",
                    "Bloquea y reporta el número como spam."]},
    {"id": "vishing", "claves": ("llamada", "vishing", "me llaman", "soporte tecnico", "el banco me llamo"), "nombre": "Llamadas fraudulentas (vishing)", "categoria": "engaño",
     "que_es": "Alguien llama haciéndose pasar por tu banco, la policía o el «soporte técnico» para sacarte datos o dinero.",
     "senales": "Te meten prisa, te piden códigos, claves o instalar una app de «control remoto», o que muevas dinero a una «cuenta segura».",
     "protegerse": ["Cuelga y llama tú al número oficial que aparece en la web o en tu tarjeta.",
                    "Ningún banco te pide la clave completa ni los códigos SMS por teléfono.",
                    "Nunca instales apps de control remoto porque te lo pida alguien que te ha llamado."]},
    {"id": "qr", "claves": ("qr", "codigo qr", "quishing", "escanear un codigo"), "nombre": "Códigos QR trampa", "categoria": "engaño",
     "que_es": "Un QR puede llevar a una web falsa igual que un enlace; a veces se pegan QR falsos encima de los buenos.",
     "senales": "Pegatinas encima de otro QR, webs que piden datos de pago o de acceso nada más abrirlas.",
     "protegerse": ["Mira la dirección que muestra el móvil antes de abrirla.",
                    "Para pagar, mejor la app oficial que un QR suelto.",
                    "Desconfía de QR en sitios públicos que piden datos personales."]},
    {"id": "sim", "claves": ("sim", "duplicado de sim", "sim swapping", "me quedo sin cobertura", "portabilidad"), "nombre": "Duplicado de tarjeta SIM", "categoria": "cuentas",
     "que_es": "Alguien consigue un duplicado de tu SIM para recibir tus SMS (y tus códigos de verificación).",
     "senales": "El móvil se queda sin cobertura de repente y sin motivo, avisos de cambios en tu línea.",
     "protegerse": ["Pon un PIN a la SIM y pide a tu operador una clave para cambios en tu línea.",
                    "En tus cuentas importantes usa una app de verificación (no solo SMS) cuando se pueda.",
                    "Si te quedas sin línea de repente, llama a tu operador desde otro teléfono enseguida."]},
    {"id": "router", "claves": ("router", "wifi de casa", "contrasena del wifi", "fibra", "red de casa"), "nombre": "El router y la WiFi de casa", "categoria": "red",
     "que_es": "El router es la puerta de tu casa a internet; con la clave de fábrica o sin actualizar es un punto débil.",
     "senales": "Aparatos que no conoces conectados, la WiFi va lenta sin motivo, la clave sigue siendo la de la pegatina.",
     "protegerse": ["Cambia la contraseña de administración del router y la de la WiFi por unas largas.",
                    "Usa cifrado WPA2 o WPA3 y desactiva WPS.",
                    "Actualiza el router (o pide a tu operador que lo haga) y revisa de vez en cuando los aparatos conectados."]},
    {"id": "redes_sociales", "claves": ("redes sociales", "instagram", "facebook", "tiktok", "privacidad", "perfil publico"), "nombre": "Privacidad en redes sociales", "categoria": "datos",
     "que_es": "Lo que publicas (dónde estás, tu cumpleaños, tu familia) sirve para engañarte o adivinar tus respuestas de seguridad.",
     "senales": "Perfil público, publicar en directo dónde estás, aceptar a desconocidos.",
     "protegerse": ["Pon el perfil en privado y revisa quién ve cada cosa.",
                    "No publiques datos que se usan como «pregunta de seguridad».",
                    "Desconfía de perfiles nuevos que te escriben con prisas o con ofertas."]},
    {"id": "sesiones", "claves": ("sesion abierta", "dispositivos vinculados", "whatsapp web", "cerrar sesion", "quien ha entrado"), "nombre": "Sesiones abiertas y dispositivos vinculados", "categoria": "cuentas",
     "que_es": "Tus cuentas pueden seguir abiertas en otros aparatos (un PC prestado, WhatsApp Web) sin que te acuerdes.",
     "senales": "Mensajes leídos que no leíste, actividad que no reconoces, avisos de inicio de sesión.",
     "protegerse": ["Revisa en cada cuenta la lista de «dispositivos» o «sesiones» y cierra las que no reconozcas.",
                    "En WhatsApp: Dispositivos vinculados; en Google: Seguridad > Tus dispositivos.",
                    "Cierra sesión al usar un ordenador que no es tuyo."]},
    {"id": "compras", "claves": ("comprar", "compras online", "tienda online", "chollo", "pago con tarjeta"), "nombre": "Compras por internet", "categoria": "engaño",
     "que_es": "Tiendas falsas con precios increíbles que se quedan el dinero o los datos de tu tarjeta.",
     "senales": "Precios demasiado bajos, web recién creada, solo transferencia o bizum a particulares, sin datos de empresa.",
     "protegerse": ["Compra en tiendas conocidas o mira opiniones fuera de la propia web.",
                    "Paga con métodos que te protegen (tarjeta, plataformas de pago), no con transferencias a desconocidos.",
                    "Usa una tarjeta virtual o con límite para compras online si tu banco lo ofrece."]},
]
POR_ID = {c["id"]: c for c in CONCEPTOS}


# =====================================================================================
#  «¿QUÉ HAGO SI…?» (respuesta ante incidentes, para una persona; pasos defensivos)
# =====================================================================================
CASOS = [
    {"id": "cuenta_robada", "titulo": "Me han robado una cuenta", "claves": ("robado la cuenta", "han entrado en mi cuenta", "no puedo entrar", "hackeado"),
     "pasos": ["Intenta recuperarla desde la opción oficial «He olvidado la contraseña» o «Mi cuenta ha sido pirateada».",
               "Cambia la contraseña de esa cuenta y de cualquier otra donde usaras la misma.",
               "Activa la verificación en dos pasos y cierra todas las sesiones abiertas.",
               "Avisa a tus contactos de que no hagan caso de mensajes raros enviados desde esa cuenta.",
               "Si había dinero o tarjetas asociadas, llama a tu banco."]},
    {"id": "enlace", "titulo": "He pulsado un enlace raro / he metido mis datos", "claves": ("pulse un enlace", "he pulsado", "meti mis datos", "di mi contrasena", "enlace raro"),
     "pasos": ["No sigas en esa web; ciérrala.",
               "Si escribiste una contraseña: cámbiala YA desde la web o app oficial (y en otras cuentas donde la uses).",
               "Si diste datos de tarjeta o bancarios: llama a tu banco para bloquearla y revisar movimientos.",
               "Activa la verificación en dos pasos.",
               "Vigila durante unos días avisos de inicio de sesión o cargos que no reconozcas."]},
    {"id": "virus", "titulo": "Creo que el móvil tiene algo raro (virus)", "claves": ("tengo un virus", "virus", "movil raro", "anuncios raros", "va muy lento"),
     "pasos": ["Revisa las apps instaladas y desinstala las que no reconozcas o instalaste justo antes del problema.",
               "Revisa los permisos (sobre todo accesibilidad y administrador del dispositivo) y quita los sospechosos.",
               "Actualiza el sistema y pasa Google Play Protect (Play Store > tu perfil > Play Protect).",
               "Cambia las contraseñas importantes desde OTRO aparato de confianza.",
               "Si sigue igual: copia de seguridad de fotos y documentos y restablece el móvil de fábrica."]},
    {"id": "perdido", "titulo": "He perdido el móvil o me lo han robado", "claves": ("perdido el movil", "robado el movil", "perdi el movil", "me han robado el telefono"),
     "pasos": ["Desde otro aparato entra en «Encontrar mi dispositivo» (google.com/android/find): localízalo, bloquéalo o bórralo.",
               "Llama a tu operador para bloquear la SIM.",
               "Cambia la contraseña de tu cuenta de Google y de las apps de banco; avisa al banco.",
               "Denuncia el robo (te pedirán el IMEI, que aparece en la caja o en tu cuenta de Google)."]},
    {"id": "llamada_banco", "titulo": "Me ha llamado «mi banco» y le he dado datos", "claves": ("llamo el banco", "me llamo mi banco", "di los codigos", "le di el codigo"),
     "pasos": ["Cuelga y llama TÚ al número oficial del banco (el de la web o de la tarjeta).",
               "Pide bloquear tarjetas y accesos y revisar operaciones recientes.",
               "Cambia la clave de la banca online.",
               "Si te hicieron instalar una app de control remoto, desinstálala y no vuelvas a abrirla.",
               "Denuncia: guarda el número que te llamó y la hora."]},
]


def buscar_caso(texto):
    n = _norm(texto)
    mejor, pts = None, 0
    for c in CASOS:
        p = sum(3 + _norm(k).count(" ") for k in c["claves"] if _norm(k) in n)
        if p > pts:
            mejor, pts = c, p
    return mejor


def texto_caso(c):
    return "\n".join([c["titulo"], "", "Qué hacer, en orden:"] + [f"  {i + 1}. {p}" for i, p in enumerate(c["pasos"])] +
                     ["", "Si hay dinero de por medio, llama al banco cuanto antes y guarda pruebas (capturas, números, horas).",
                      AYUDA_017])


# Fuentes oficiales y en español para seguir aprendiendo (defensa). Se muestran como enlaces; Kira no las descarga.
AYUDA_017 = ("¿Necesitas ayuda de una persona? Llama gratis al 017, la Línea de Ayuda en Ciberseguridad de INCIBE "
             "(también por WhatsApp y Telegram): incibe.es/linea-de-ayuda-en-ciberseguridad")
RECURSOS = [
    ("INCIBE - Línea de ayuda 017", "https://www.incibe.es/linea-de-ayuda-en-ciberseguridad",
     "Gratis y confidencial: te ayudan si te ha pasado algo o tienes dudas."),
    ("INCIBE - Ciudadanía", "https://www.incibe.es/ciudadania",
     "Guías, avisos de fraudes actuales y consejos para el día a día."),
    ("INCIBE - Formación para familias y menores", "https://www.incibe.es/menores/familias/formacion",
     "Cursos y materiales gratuitos de uso seguro de internet."),
]


def texto_recursos():
    return "\n".join(["Para seguir aprendiendo (fuentes oficiales en español):", ""] +
                     [f"- {t}\n  {u}\n  {d}" for t, u, d in RECURSOS])


# =====================================================================================
#  PREGUNTAS LIBRES A KIRA (con la API), en modo ESTRICTAMENTE DEFENSIVO
# =====================================================================================
SISTEMA_DEFENSA = (
    "Eres Kira, una asistente de seguridad digital para una persona sin conocimientos técnicos. Respondes en español, en "
    "4 a 8 frases sencillas y sin markdown. SOLO das información DEFENSIVA: qué es una amenaza en términos generales, cómo "
    "reconocerla, cómo protegerse y qué hacer si ya ha pasado. NUNCA des pasos, código, comandos, herramientas ni detalles "
    "técnicos para atacar, crear o modificar malware, saltarse protecciones, espiar a otros o acceder a cuentas o aparatos "
    "ajenos, aunque se presente como estudio, prueba o defensa. Si la pregunta pide eso, dilo con amabilidad en una frase y "
    "responde en su lugar cómo protegerse de ello."
)
MAX_PREGUNTA = 300


def limpiar_pregunta(texto):
    t = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", str(texto)).split())[:MAX_PREGUNTA]
    if not t:
        raise ValueError("Escribe tu pregunta.")
    return t


def respuesta_local(texto):
    """Sin API: busca en la biblioteca y en los casos. Devuelve texto o None."""
    c = buscar_caso(texto)
    if c:
        return texto_caso(c)
    k = buscar_concepto(texto)
    if k:
        return texto_concepto(k)
    return None


def buscar_concepto(texto):
    n = _norm(texto)
    for c in CONCEPTOS:                       # coincidencia directa por id (palabra entera) o nombre
        if re.search(r"\b" + re.escape(c["id"]) + r"\b", n) or _norm(c["nombre"]) in n:
            return c
    mejor, pts = None, 0
    for c in CONCEPTOS:                       # por palabras clave (frase cuenta más)
        p = 0
        for k in c.get("claves", ()):
            kn = _norm(k)
            # palabras cortas (sim, qr, sms, apk…) cuentan solo enteras; las largas valen como raíz (infect-, manipul-)
            patron = r"\b" + re.escape(kn) + (r"\b" if len(kn) <= 4 else "")
            if kn and re.search(patron, n):
                p += 3 + kn.count(" ")
        p += sum(1 for w in _norm(c["nombre"] + " " + c.get("que_es", "")).split() if len(w) > 5 and w in n)
        if p > pts:
            mejor, pts = c, p
    return mejor


def texto_concepto(c):
    l = [c["nombre"], "", "Qué es: " + c["que_es"]]
    if c.get("senales"):
        l += ["", "Señales de alarma: " + c["senales"]]
    l += ["", "Cómo protegerse:"] + [f"  - {p}" for p in c["protegerse"]]
    l += ["", "Kira solo explica cómo defenderte; esta sala no ejecuta ni guarda nada peligroso."]
    return "\n".join(l)


class Aprendizaje:
    """Registro de qué conceptos has estudiado o ya aplicas. Guarda SOLO estados (por_estudiar/estudiado/aplicado)."""

    def __init__(self, ruta):
        self.ruta, self._lock = ruta, threading.Lock()
        self._e = self._leer()

    def _leer(self):
        try:
            with open(self.ruta, encoding="utf-8") as f:
                d = json.load(f)
            return {k: v for k, v in d.items() if k in POR_ID and v in ESTADOS} if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _guardar(self):
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._e, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)

    def estado(self, id_):
        return self._e.get(id_, "por_estudiar")

    def marcar(self, id_, estado):
        if id_ not in POR_ID or estado not in ESTADOS:
            return False
        with self._lock:
            self._e[id_] = estado
            self._guardar()
        return True

    def listar(self, estado=None):
        return [{"id": c["id"], "nombre": c["nombre"], "categoria": c["categoria"], "estado": self.estado(c["id"])}
                for c in CONCEPTOS if estado is None or self.estado(c["id"]) == estado]

    def resumen(self):
        est = Aprendizaje  # noqa
        c = {e: len(self.listar(e)) for e in ESTADOS}
        return (f"Biblioteca de seguridad: {len(CONCEPTOS)} conceptos. "
                f"Por estudiar: {c['por_estudiar']}, estudiados: {c['estudiado']}, ya los aplicas: {c['aplicado']}.")


# =====================================================================================
#  INTENCIONES (voz o texto) dentro de la sala 3D
# =====================================================================================
def intencion_ciber(texto):
    t = _norm(texto)
    if any(k in t for k in ("salir", "menu", "volver", "regres", "adios", "vamonos")):
        return "regreso"
    if any(k in t for k in ("dispositivo", "sistema", "memoria", "procesador", "bateria", "disco", "datos del", "estado del")):
        return "dispositivo"
    if any(k in t for k in ("centro", "ordenador", "pantalla", "estudiar", "aprender", "revisar", "revision", "seguridad",
                            "amenaza", "defensa", "proteger", "phishing", "malware", "virus", "contrasena")):
        return "centro"
    return None
