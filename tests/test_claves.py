# -*- coding: utf-8 -*-
"""Claves fuertes (claves_kira): generar frases y claves aleatorias fuertes, y auditar la fuerza de una contraseña."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import claves_kira as ck

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


# frase-contraseña
f = ck.generar_frase(5)
ok(f.count("-") == 5 and len(f) > 15, "la frase tiene 5 palabras + un número, y es larga")
ok(ck.generar_frase(5) != ck.generar_frase(5), "cada frase es distinta (azar)")
ok(ck.fuerza(f)["nivel"] in ("fuerte", "muy fuerte"), "una frase de 5 palabras es fuerte")

# clave aleatoria fuerte
c = ck.generar_fuerte(20)
ok(len(c) == 20, "la clave aleatoria tiene el largo pedido")
import re
ok(re.search(r"[A-Z]", c) and re.search(r"[a-z]", c) and re.search(r"\d", c) and re.search(r"[^A-Za-z0-9]", c),
   "la clave aleatoria lleva mayúscula, minúscula, número y símbolo")
ok(ck.fuerza(c)["nivel"] in ("fuerte", "muy fuerte"), "una clave aleatoria de 20 es fuerte")

# auditar fuerza
ok(ck.fuerza("123456")["nivel"] == "floja", "«123456» es floja")
ok(ck.fuerza("password")["nivel"] == "floja" and any("usadas" in x for x in ck.fuerza("password")["consejos"]),
   "«password» es floja y avisa de que es de las más usadas")
ok(ck.fuerza("Kira2024")["bits"] > 0 and ck.fuerza("Kira2024")["nivel"] in ("floja", "aceptable"),
   "una clave corta normalita no es fuerte")
lar = ck.fuerza("faro-tigre-nube-remo-sal-42")
ok(lar["bits"] >= 60, "una frase larga tiene muchos bits de dificultad")
ok(ck.fuerza("aaa")["consejos"], "una clave mala trae consejos para mejorarla")
# no guarda nada
ok(not os.path.isfile(os.path.join(RAIZ, "kira_portatil", "claves_guardadas.txt")), "no guarda las claves en ningún sitio")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
