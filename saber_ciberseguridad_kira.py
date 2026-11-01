# -*- coding: utf-8 -*-
"""
saber_ciberseguridad_kira.py - CIBERSEGURIDAD DEFENSIVA para Kira (recetas probadas + fichas + fuentes oficiales).

SOLO DEFENSA: prevenir, reconocer y contrarrestar ataques, y detección de anomalías («adelantarse a lo raro»). Las
recetas corren en el laboratorio/editor seguro (sin red, sin sistema): enseñan la FORMA de defenderse, no a atacar.
Nada ofensivo, nada de malware.

- RECETAS: como las de saber_avanzado (id, titulo, area, temas, idea, complejidad, codigo con registrar(), prueba).
- CONCEPTOS: fichas de teoría para el baúl.
- fichas(): (tema, texto) para guardar en el baúl (lo estudia sola, sin internet).
- FUENTES_OFICIALES: sitios OFICIALES y legales de donde Kira puede estudiar al pulsar el botón (INCIBE, OWASP…).
"""

RECETAS = [
    {"id": "fuerza_contrasena", "titulo": "Medir la fuerza de una contraseña", "area": "Ciberseguridad",
     "temas": "contraseña clave password fuerza segura debil robusta mayusculas numeros simbolos longitud",
     "idea": "Una contraseña es fuerte si es LARGA y mezcla tipos (mayúsculas, minúsculas, números, símbolos). Se "
             "puntúa cada cosa y se avisa de lo que falta. No se guarda en ningún sitio.", "complejidad": "O(largo)",
     "codigo": '''
import re


def registrar():
    def clave(texto):
        p = texto.strip()
        puntos, consejos = 0, []
        if len(p) >= 12:
            puntos += 2
        elif len(p) >= 8:
            puntos += 1
        else:
            consejos.append("hazla más larga (12+)")
        if re.search(r"[a-z]", p) and re.search(r"[A-Z]", p):
            puntos += 1
        else:
            consejos.append("mezcla mayúsculas y minúsculas")
        if re.search(r"\\d", p):
            puntos += 1
        else:
            consejos.append("añade números")
        if re.search(r"[^A-Za-z0-9]", p):
            puntos += 1
        else:
            consejos.append("añade símbolos")
        nivel = "FUERTE" if puntos >= 5 else "MEDIA" if puntos >= 3 else "DÉBIL"
        return f"«{p}»: {nivel} ({puntos}/5)" + ("; consejos: " + ", ".join(consejos) if consejos else "")
    return {"clave": clave}
''',
     "prueba": [("clave", "abc", "«abc»: DÉBIL"), ("clave", "Xy9$muylarga123", "FUERTE")]},

    {"id": "deteccion_anomalias", "titulo": "Detección de anomalías (adelantarse a lo raro)", "area": "Ciberseguridad",
     "temas": "anomalia anomalias normal media desviacion pico raro detectar adelantarse vigilancia trafico outlier z",
     "idea": "Aprende qué es lo NORMAL (media y desviación de lo visto) y avisa de lo que se sale mucho (un pico). Es "
             "cómo se «adelanta» a un ataque sin nombre: no lo conoce, pero ve que algo es raro.", "complejidad": "O(n)",
     "codigo": '''
import re
import statistics


def registrar():
    def normal(texto):
        nums = [float(x) for x in re.findall(r"-?\\d+\\.?\\d*", texto)]
        if len(nums) < 3:
            return "Dame al menos 3 números (lo normal y, al final, el nuevo)."
        base, ultimo = nums[:-1], nums[-1]
        media = statistics.mean(base)
        desv = statistics.pstdev(base) or 1.0
        z = abs(ultimo - media) / desv
        if z >= 3:
            return f"ANOMALÍA: {ultimo:g} se sale de lo normal (media {media:g}, z={z:.1f})"
        return f"Normal: {ultimo:g} dentro de lo habitual (media {media:g}, z={z:.1f})"
    return {"normal": normal}
''',
     "prueba": [("normal", "10 11 9 10 12 200", "ANOMALÍA"), ("normal", "10 11 9 10 12 11", "Normal:")]},

    {"id": "deteccion_fuerza_bruta", "titulo": "Detectar fuerza bruta en los accesos", "area": "Ciberseguridad",
     "temas": "fuerza bruta login intentos contraseña fallidos bloquear ip ataque accesos registro log",
     "idea": "Si una misma IP falla el login muchas veces seguidas, es fuerza bruta: se marca para bloquearla un rato. "
             "Así se contrarresta sin molestar al uso normal.", "complejidad": "O(n)",
     "codigo": '''
def registrar():
    def logins(texto):
        res = []
        for par in texto.split(","):
            if ":" in par:
                ip, n = par.split(":", 1)
                try:
                    n = int(n)
                except ValueError:
                    continue
                if n >= 10:
                    res.append(f"{ip.strip()}: FUERZA BRUTA ({n} intentos) -> bloquear")
                else:
                    res.append(f"{ip.strip()}: normal ({n})")
        return "\\n".join(res) if res else "Sin datos."
    return {"logins": logins}
''',
     "prueba": [("logins", "1.1.1.1:30, 2.2.2.2:3", "1.1.1.1: FUERZA BRUTA (30 intentos) -> bloquear"),
                ("logins", "1.1.1.1:30, 2.2.2.2:3", "2.2.2.2: normal (3)")]},

    {"id": "sanear_entrada", "titulo": "Validar/sanear una entrada (evitar inyecciones)", "area": "Ciberseguridad",
     "temas": "sanear validar entrada inyeccion sql xss script escapar formulario seguridad web owasp",
     "idea": "Antes de usar lo que escribe un usuario, se revisa si trae trampas típicas (inyección SQL, XSS, rutas) y "
             "se avisa. La defensa real es validar y escapar siempre; esto lo detecta.", "complejidad": "O(largo)",
     "codigo": '''
import re


def registrar():
    def entrada(texto):
        bajo = texto.lower()
        señales = []
        if re.search(r"('|\\bor\\b).{0,8}=|union\\s+select|--|;\\s*drop", bajo):
            señales.append("inyección SQL")
        if re.search(r"<script|onerror=|javascript:", bajo):
            señales.append("XSS")
        if re.search(r"\\.\\./|/etc/passwd", bajo):
            señales.append("ruta peligrosa")
        if señales:
            return "PELIGROSA: parece " + ", ".join(señales) + ". No la uses tal cual; valida y escapa."
        return "Parece segura (aun así, valida y escapa siempre)."
    return {"entrada": entrada}
''',
     "prueba": [("entrada", "' OR 1=1 --", "PELIGROSA: parece inyección SQL"),
                ("entrada", "Juan Pérez", "Parece segura")]},

    {"id": "huella_integridad", "titulo": "Huella (hash) para comprobar integridad", "area": "Ciberseguridad",
     "temas": "hash sha256 integridad huella comprobar cambio manipulado verificar fichero firma",
     "idea": "La «huella» (hash SHA-256) de un texto/archivo cambia si cambia aunque sea una coma. Sirve para saber si "
             "algo ha sido manipulado: guardas la huella y la vuelves a calcular.", "complejidad": "O(largo)",
     "codigo": '''
import hashlib


def registrar():
    def huella(texto):
        h = hashlib.sha256(texto.strip().encode("utf-8")).hexdigest()
        return f"SHA-256: {h[:16]}… (si el texto cambia, la huella cambia)"
    return {"huella": huella}
''',
     "prueba": [("huella", "hola", "SHA-256:"), ("huella", "hola", "la huella cambia")]},

    {"id": "cifrado_cesar", "titulo": "Cifrado César (ejemplo educativo)", "area": "Ciberseguridad",
     "temas": "cifrado cesar desplazamiento clasico educativo reversible texto criptografia basica aprender",
     "idea": "El cifrado César mueve cada letra N posiciones. Es DÉBIL (solo para aprender cómo funciona cifrar y "
             "descifrar), no para proteger de verdad: para eso están AES y compañía.", "complejidad": "O(largo)",
     "codigo": '''
import re


def registrar():
    def cesar(texto):
        m = re.match(r"\\s*(.+?)\\s+(-?\\d+)\\s*$", texto)
        if not m:
            return "Dime el texto y el desplazamiento (ej: hola 3)."
        msg, d = m.group(1), int(m.group(2))

        def mueve(c):
            if c.isalpha():
                base = ord("a") if c.islower() else ord("A")
                return chr((ord(c) - base + d) % 26 + base)
            return c
        cifrado = "".join(mueve(c) for c in msg)
        return f"{msg} -> {cifrado} (descífralo con -{d})"
    return {"cesar": cesar}
''',
     "prueba": [("cesar", "hola 3", "hola -> krod"), ("cesar", "abc 1", "abc -> bcd")]},
]


CONCEPTOS = [
    {"id": "cb_phishing", "area": "Ciberseguridad", "titulo": "Phishing (engaño)",
     "temas": "phishing engaño correo enlace falso robar contraseña suplantacion banco urgencia",
     "texto": "El phishing es un engaño: un correo, SMS o web que se hace pasar por alguien de confianza (tu banco, "
              "una empresa) para que piques y des tu contraseña o tus datos. Señales: prisa o amenaza («tu cuenta será "
              "bloqueada»), enlaces raros que no coinciden con el sitio real, faltas de ortografía, remitente extraño. "
              "Defensa: no pulses enlaces de correos que no esperabas, entra tú al sitio escribiendo la dirección, y "
              "activa el doble factor (así robar la contraseña no basta)."},
    {"id": "cb_fuerza_bruta", "area": "Ciberseguridad", "titulo": "Ataque de fuerza bruta",
     "temas": "fuerza bruta contraseña probar intentos login bloquear limite diccionario",
     "texto": "La fuerza bruta es probar contraseñas una tras otra hasta acertar (a mano una máquina prueba millones). "
              "Por eso una contraseña corta cae en segundos. Defensa: contraseñas largas y únicas, un gestor de "
              "contraseñas, doble factor, y en los servicios, LIMITAR los intentos (tras varios fallos, esperar o "
              "bloquear un rato esa IP). Si ves muchos intentos fallidos seguidos desde un sitio, es fuerza bruta."},
    {"id": "cb_escaneo", "area": "Ciberseguridad", "titulo": "Escaneo de puertos",
     "temas": "escaneo puertos nmap sondeo buscar servicios abiertos rendija firewall",
     "texto": "Un escaneo de puertos es cuando alguien «llama» a muchos puertos de tu equipo para ver cuáles están "
              "abiertos y qué servicios corren, buscando una rendija. En sí mirar no hace daño, pero suele ser el paso "
              "previo a un ataque. Defensa: un cortafuegos que solo deje abiertos los puertos que de verdad usas, "
              "mantener los servicios actualizados, y vigilar si alguien está sondeando (muchos puertos tocados de "
              "golpe desde una IP)."},
    {"id": "cb_mfa", "area": "Ciberseguridad", "titulo": "Doble factor (MFA) y contraseñas",
     "temas": "mfa 2fa doble factor contraseña gestor autenticador codigo seguridad cuenta",
     "texto": "El doble factor (MFA/2FA) pide, además de la contraseña, un segundo paso: un código de una app, una "
              "huella, una llave. Así, aunque te roben la contraseña, no entran. Es de las mejores defensas y casi "
              "gratis. Júntalo con contraseñas LARGAS y DISTINTAS en cada sitio (un gestor de contraseñas las recuerda "
              "por ti) y tendrás cubierto el 90% de los ataques a cuentas."},
    {"id": "cb_cifrado_hash", "area": "Ciberseguridad", "titulo": "Cifrar vs. hashear",
     "temas": "cifrado hash sha256 aes reversible integridad contraseñas guardar diferencia",
     "texto": "Cifrar y hashear no son lo mismo. CIFRAR (p. ej. AES) oculta algo de forma REVERSIBLE: con la clave se "
              "vuelve a leer; sirve para proteger datos. HASHEAR (p. ej. SHA-256) hace una «huella» de un solo sentido: "
              "no se puede volver atrás; sirve para comprobar que algo no ha cambiado y para guardar contraseñas (se "
              "guarda la huella con «sal», no la contraseña). Regla: datos que debes recuperar → cifrar; comprobar "
              "integridad o guardar contraseñas → hashear."},
    {"id": "cb_minimo_privilegio", "area": "Ciberseguridad", "titulo": "Mínimo privilegio y defensa en profundidad",
     "temas": "minimo privilegio permisos defensa en profundidad capas usuario admin reducir superficie",
     "texto": "Dos ideas clave de defensa. MÍNIMO PRIVILEGIO: cada programa o persona tiene solo los permisos que "
              "necesita y nada más; así, si algo se cuela, hace poco daño. DEFENSA EN PROFUNDIDAD: no te fías de una "
              "sola barrera, pones varias (cortafuegos + antivirus + actualizaciones + copias + doble factor); si una "
              "falla, las otras aguantan. Juntas reducen mucho lo que un atacante puede conseguir."},
    {"id": "cb_actualizar", "area": "Ciberseguridad", "titulo": "Actualizaciones y parches",
     "temas": "actualizar parche vulnerabilidad version software sistema seguridad zero day",
     "texto": "La mayoría de ataques aprovechan fallos YA conocidos y YA arreglados: entran por equipos sin actualizar. "
              "Mantener el sistema y las apps al día (poner los parches pronto) cierra esas puertas. Un fallo nuevo que "
              "aún no tiene parche se llama «día cero» (zero-day) y es raro y caro; defenderse de lo conocido "
              "(actualizar) te quita de encima casi todo el peligro real."},
    {"id": "cb_copias", "area": "Ciberseguridad", "titulo": "Copias de seguridad (contra el ransomware)",
     "temas": "copia seguridad backup ransomware cifrar rescate restaurar 3 2 1 recuperar",
     "texto": "El ransomware cifra tus archivos y pide un rescate. La mejor defensa no es pagar, es tener COPIAS de "
              "seguridad: si pasa, restauras y listo. Regla 3-2-1: 3 copias, en 2 soportes distintos, 1 de ellas fuera "
              "del equipo (y desconectada, para que el ransomware no la cifre también). Prueba de vez en cuando que la "
              "copia se puede restaurar de verdad."},
    {"id": "cb_anomalias", "area": "Ciberseguridad", "titulo": "Detección de anomalías",
     "temas": "anomalia deteccion comportamiento normal base linea pico raro adelantarse vigilancia aprender",
     "texto": "No todos los ataques se conocen de antemano. Por eso una defensa potente es aprender qué es lo NORMAL "
              "(cuánto tráfico sueles tener, qué aparatos hay en tu red, a qué horas) y avisar de lo que se SALE de lo "
              "normal: un pico enorme, un dispositivo nuevo, una conexión a horas raras. No predice el ataque exacto, "
              "pero «huele» lo anómalo y te adelanta. Cuanto más observa, mejor afina su idea de lo normal."},
    {"id": "cb_ingenieria_social", "area": "Ciberseguridad", "titulo": "Ingeniería social",
     "temas": "ingenieria social engaño persona llamada confianza suplantar urgencia manipular",
     "texto": "El eslabón más débil suele ser la persona, no la máquina. La ingeniería social manipula a alguien para "
              "que abra una puerta: una llamada haciéndose pasar por soporte técnico, un «jefe» pidiendo una "
              "transferencia urgente, un USB «perdido» que pica la curiosidad. Defensa: desconfía de la urgencia y la "
              "autoridad no verificada, confirma por otro canal, y nunca des contraseñas ni códigos por teléfono o "
              "correo, por muy oficial que parezca quien lo pide."},
]

# Sitios OFICIALES y legales de donde Kira puede estudiar al pulsar el botón (todo defensivo).
FUENTES_OFICIALES = [
    {"titulo": "INCIBE — Protege tu empresa (guías)", "url": "https://www.incibe.es/empresas/guias",
     "tema": "ciberseguridad defensa empresa guia incibe"},
    {"titulo": "INCIBE — Ciudadanía", "url": "https://www.incibe.es/ciudadania",
     "tema": "ciberseguridad ciudadania phishing contraseñas incibe"},
    {"titulo": "OWASP Top 10 (riesgos web)", "url": "https://owasp.org/www-project-top-ten/",
     "tema": "owasp top 10 seguridad web vulnerabilidades defensa"},
    {"titulo": "Wikipedia — Seguridad informática", "url": "https://es.wikipedia.org/wiki/Seguridad_informática",
     "tema": "seguridad informatica conceptos defensa"},
    {"titulo": "Wikipedia — Phishing", "url": "https://es.wikipedia.org/wiki/Phishing",
     "tema": "phishing engaño correo defensa"},
]


def demo(r):
    import recetas_ingenieria_kira as ri
    return ri.demo(r)


def leccion(r):
    return {"id": "cb_" + r["id"], "titulo": r["titulo"], "nivel": "ciberseguridad defensiva",
            "texto": f"{r['idea']} Coste: {r['complejidad']}.", "codigo": demo(r)}


def fichas():
    """(tema, texto) para el baúl: recetas + conceptos de ciberseguridad defensiva (sin internet)."""
    res = []
    for r in RECETAS:
        res.append((r["titulo"], f"{r['titulo']} (Ciberseguridad): {r['idea']} Coste: {r['complejidad']}. "
                                 f"Kira tiene una receta probada: «receta {r['id'].replace('_', ' ')}»."))
    for c in CONCEPTOS:
        res.append((c["titulo"], f"{c['titulo']}: {c['texto']}"))
    return res
