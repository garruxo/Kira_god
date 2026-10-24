# -*- coding: utf-8 -*-
"""
claves_kira.py - Claves fuertes para proteger lo tuyo (WiFi, accesos…). SOLO DEFENSA.

  - generar_frase(palabras): una contraseña LARGA y fácil de recordar hecha de palabras al azar (estilo «diceware»),
    muy difícil de adivinar. Recomendada para la WiFi.
  - generar_fuerte(largo): una contraseña aleatoria fuerte (letras, números y símbolos) para donde no haga falta
    recordarla (un gestor de contraseñas).
  - fuerza(clave): audita una contraseña y dice si es floja o fuerte, los «bits» de dificultad y consejos. NO guarda
    la clave en ningún sitio (solo la mira un momento).

Usa `secrets` (azar criptográfico, de la librería estándar). Nada de internet.
"""
import math
import re
import secrets

# Palabras cortas y comunes en español (sin tildes ni ambigüedades) para las frases-contraseña.
PALABRAS = (
    "ancla arbol barco bote brisa cabra calle campo canto casa cebra cielo cima clave coco cofre coral cuerda "
    "dado dardo dedo delfin diente duna eco faro fecha fila flor fresa fuego gato globo grano gris hielo hilo "
    "hoja hongo huevo isla jardin jarra juego kiwi lago lapiz leon libro lima limon lince luna lupa malla mango "
    "mapa mar melon menta mesa miel mono monte mora nido nieve nube nuez ola olivo onda oso pato pera perla pez "
    "pino pluma pozo prado puente queso rama rana rayo remo rio roca rosa rueda sal salto selva sol sopa surco "
    "taza techo tela tigre tinta torre trigo trueno tuna uva vaca vela vid viento zorro zumo"
).split()


def generar_frase(palabras=5, separador="-"):
    """Una contraseña de varias palabras al azar, p. ej. «faro-tigre-nube-remo-sal». Fácil de recordar, muy fuerte."""
    palabras = max(3, min(10, int(palabras)))
    elegidas = [secrets.choice(PALABRAS) for _ in range(palabras)]
    # un número al final para cumplir reglas que piden dígitos
    return separador.join(elegidas) + separador + str(secrets.randbelow(90) + 10)


def generar_fuerte(largo=20):
    """Una contraseña aleatoria con letras (may/min), números y símbolos. Para un gestor de contraseñas."""
    largo = max(8, min(128, int(largo)))
    may = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    minu = "abcdefghijkmnpqrstuvwxyz"
    num = "23456789"
    sim = "!@#$%&*?-_+="
    todo = may + minu + num + sim
    # al menos uno de cada tipo, el resto al azar
    base = [secrets.choice(may), secrets.choice(minu), secrets.choice(num), secrets.choice(sim)]
    base += [secrets.choice(todo) for _ in range(largo - 4)]
    # barajar sin sesgo
    for i in range(len(base) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        base[i], base[j] = base[j], base[i]
    return "".join(base)


_COMUNES = {"123456", "password", "contrasena", "contraseña", "qwerty", "111111", "123456789", "12345678",
            "admin", "iloveyou", "000000", "1234", "12345", "abc123", "kira", "qwertyuiop", "1q2w3e"}


def fuerza(clave):
    """Audita una contraseña. Devuelve {nivel, bits, consejos}. No la guarda. `bits` ≈ dificultad para adivinarla a
    fuerza bruta (más es mejor: <40 flojo, 60 bien, 80+ muy fuerte)."""
    clave = clave or ""
    consejos = []
    conjunto = 0
    if re.search(r"[a-z]", clave):
        conjunto += 26
    if re.search(r"[A-Z]", clave):
        conjunto += 26
    if re.search(r"\d", clave):
        conjunto += 10
    if re.search(r"[^A-Za-z0-9]", clave):
        conjunto += 20
    bits = round(len(clave) * math.log2(conjunto)) if conjunto and clave else 0

    if len(clave) < 12:
        consejos.append("Hazla más larga (12 o más; mejor 16+).")
    if not re.search(r"[A-Z]", clave) or not re.search(r"[a-z]", clave):
        consejos.append("Mezcla mayúsculas y minúsculas.")
    if not re.search(r"\d", clave):
        consejos.append("Añade algún número.")
    if not re.search(r"[^A-Za-z0-9]", clave):
        consejos.append("Añade algún símbolo (p. ej. ! ? - _).")
    if clave.lower() in _COMUNES:
        consejos.append("Es una de las contraseñas más usadas del mundo: cámbiala ya.")
        bits = min(bits, 10)
    if re.search(r"(.)\1\1", clave):
        consejos.append("Evita repetir el mismo carácter varias veces seguidas.")
    if re.search(r"(0123|1234|2345|3456|4567|5678|6789|abcd|qwer|asdf)", clave.lower()):
        consejos.append("Evita secuencias fáciles (1234, qwerty…).")

    if bits < 40 or clave.lower() in _COMUNES:
        nivel = "floja"
    elif bits < 60:
        nivel = "aceptable"
    elif bits < 80:
        nivel = "fuerte"
    else:
        nivel = "muy fuerte"
    return {"nivel": nivel, "bits": bits, "largo": len(clave), "consejos": consejos}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "frase":
        print(generar_frase(int(sys.argv[2]) if len(sys.argv) > 2 else 5))
    elif len(sys.argv) > 1 and sys.argv[1] == "fuerte":
        print(generar_fuerte(int(sys.argv[2]) if len(sys.argv) > 2 else 20))
    elif len(sys.argv) > 2 and sys.argv[1] == "mira":
        import json
        print(json.dumps(fuerza(sys.argv[2]), ensure_ascii=False, indent=1))
    else:
        print("Uso: claves_kira.py frase [palabras] | fuerte [largo] | mira <clave>")
