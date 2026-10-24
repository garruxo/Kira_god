# -*- coding: utf-8 -*-
"""El candado de entrada de KiraOS (bloqueo_kira): crear el PIN, acertar, fallar, el límite de intentos y que el PIN
no se guarde en claro. Con un archivo temporal, sin tocar el de verdad."""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import bloqueo_kira as bl

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


tmp = tempfile.mkdtemp()
R = os.path.join(tmp, "pin_kira.txt")

ok(not bl.hay_pin(R), "al principio no hay PIN")
ok(bl.estado(R)["hay_pin"] is False, "estado dice que no hay PIN")

# crear
for malo in ("123", "12345", "12ab", "", "    "):
    try:
        bl.crear_pin(malo, R)
        ok(False, f"«{malo}» debería dar error (no son 4 cifras)")
    except bl.BloqueoError:
        ok(True, f"«{malo}» rechazado: el PIN son 4 cifras")

ok(bl.crear_pin("2468", R) and bl.hay_pin(R), "se crea un PIN de 4 cifras")

# el PIN NO está en claro en el archivo
contenido = open(R, encoding="utf-8").read()
ok("2468" not in contenido, "el PIN no se guarda en claro")
ok("sal" in contenido and "hash" in contenido, "se guarda sal + hash")
# permisos 0600 (solo el dueño)
modo = os.stat(R).st_mode & 0o777
ok(modo == 0o600, f"el archivo del PIN es solo del dueño (0600), es {oct(modo)}")

# acertar / fallar
ok(bl.comprobar("2468", R) is True, "acierta con el PIN correcto")
ok(bl.comprobar("0000", R) is False, "falla con el PIN incorrecto")
ok(bl.comprobar("246", R) is False, "un PIN mal formado no acierta (no rompe)")

# acertar resetea los fallos
bl.comprobar("1111", R)
bl.comprobar("2468", R)
ok(bl.estado(R)["fallos"] == 0, "acertar pone los fallos a cero")

# límite de intentos: tras varios fallos, obliga a esperar
for _ in range(6):
    bl.comprobar("9999", R)
st = bl.estado(R)
ok(st["fallos"] >= 6 and st["espera"] > 0, "tras muchos fallos hay que esperar")
# aun con el PIN bueno, mientras hay espera no entra
ok(bl.comprobar("2468", R) is False, "durante la espera ni el PIN bueno entra")

# cambiar el PIN
ok(bl.crear_pin("1357", R) and bl.comprobar("1357", R) and not bl.comprobar("2468", R),
   "se puede cambiar el PIN y el viejo deja de valer")

ok(bl.biometria_disponible() is False, "la biometría (huella/cara) de momento la pone el sistema, no esta reserva")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
