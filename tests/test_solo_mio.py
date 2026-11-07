# -*- coding: utf-8 -*-
"""v3.02 (decisión del dueño):
- «estudia solo lo que yo te mande»: Kira piensa SOLO en lo tuyo (encargos, foco, lo que le mandaste estudiar); si no
  queda nada tuyo, se queda quieta. «piensa libre» lo quita. En el móvil, además se lo dice a KiraOS.
- Órdenes FUERA de casa por Tailscale: solo las tranquilas (estudiar, investigar, pensar, programar). Lo que toca el
  portátil o la casa espera. El portátil lo vuelve a comprobar (403).
- activar_fuera.sh desactiva los registros técnicos que Tailscale manda a su empresa."""
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
T = tempfile.mkdtemp()
os.environ["HOME"] = T
import solo_mio_kira as sm  # noqa: E402
import mando_kira as mk  # noqa: E402
import estudio_kira as ek  # noqa: E402
import tablero_kira as tbk  # noqa: E402

n = 0


def ok(c, m):
    global n
    n += 1
    print(("[OK] " if c else "[X] ") + m)
    if not c:
        sys.exit(1)


# ---------- el interruptor ----------
for f in ("estudia solo lo que yo te mande", "Kira, solo lo que te mando", "solo lo mío", "solo mis temas",
          "no estudies por tu cuenta", "céntrate solo en lo que te encargo"):
    ok(sm.es_orden(f) == "on", f"«{f}» lo enciende")
for f in ("piensa libre", "puedes estudiar lo que quieras", "piensa en lo que quieras", "vuelve a pensar libre"):
    ok(sm.es_orden(f) == "off", f"«{f}» lo apaga")
for f in ("estudia python", "piensa", "solo dime la hora", "investiga lo que quieras saber de redes"):
    ok(sm.es_orden(f) is None, f"«{f}» no es el interruptor")
ok(ek.es_estudia_general("estudia solo lo que yo te mande") is None and ek.es_estudia_general("estudia python"),
   "no se confunde con «estudia X»")
D = os.path.join(T, "d")
ok(not sm.encendido(D), "viene APAGADO")
sm.encender(D, True)
ok(sm.encendido(D) and oct(os.stat(os.path.join(D, sm.ARCHIVO)).st_mode & 0o777) == "0o600", "se guarda en disco (0600)")
sm.apuntar_tema(D, "Python")
sm.apuntar_tema(D, "redes neuronales")
sm.apuntar_tema(D, "python")
ok(sm.temas(D) == ["python", "redes neuronales"], "apunta lo que le mandas estudiar, sin repetir, lo último primero")

# ---------- fuera de casa: solo lo tranquilo ----------
SI = ["estudia python", "investiga qué es un trie", "pregúntate cómo funciona un compilador", "hazme un juego de naves",
      "escríbeme un programa que ordene una lista", "piensa en la caché hasta resolverlo", "experimenta con grafos",
      "escribe un programa que sume y pruébalo en tu máquina", "estudia redes neuronales", "busca cursos de Kivy",
      "estudia esta página y sus enlaces: https://a.es/b", "estudia solo lo que yo te mande", "sincronízate"]
NO = ["apaga el portátil", "reinicia", "busca redes wifi", "conéctate a la wifi Casa", "enciende tu máquina",
      "deja tu máquina como nueva", "hazme una foto", "lee la pantalla", "mira con tu cámara",
      "conviértelo en una app de verdad", "instala la librería numpy", "prepara una mejora para el móvil: x",
      "pasa tu memoria al portátil", "escanea mi red", "qué aparatos hay en casa", "dame el código de emparejar",
      "cambia el aspecto del móvil a bosque", "ejecuta rm -rf", "modo mando"]
for f in SI:
    ok(mk.permitida_fuera(f)[0], f"fuera de casa SÍ: «{f}»")
for f in NO:
    ok(not mk.permitida_fuera(f)[0], f"fuera de casa NO: «{f}»")
ok("al volver" not in mk.permitida_fuera("apaga")[1] and "misma WiFi" in mk.permitida_fuera("apaga")[1],
   "y dice por qué")

src_n = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("fk_.es_ip_tailscale(self.client_address[0])" in src_n and "mk_.permitida_fuera(orden)" in src_n,
   "el PORTÁTIL lo vuelve a comprobar: desde Tailscale, lo no permitido = 403")
ok("self.core.es_kiraos = True" in src_n, "KiraOS sabe que es KiraOS (no se reenvía órdenes a sí misma)")

# ---------- el núcleo ----------
import kira_god  # noqa: E402

core = kira_god.KiraGodCore()
core.dir = os.path.join(T, "kira")
os.makedirs(core.dir, exist_ok=True)
ok(not core.solo_lo_mio() and core._semillas_pensar(), "apagado: piensa también en sus temas")
preguntas = []
core._pensar_preguntar = lambda p: (preguntas.append(p), "Es una estructura que guarda datos. Seguro.")[1]
core._estudiar_pensando = lambda *a, **k: ""
core._experimentar_pensando = lambda *a, **k: None
core._comparar_codigo = lambda *a, **k: None
core.recuerdos = None


class Casa:
    via = "casa"

    def __init__(self):
        self.mandadas = []

    def nucleo_disponible(self, fuera=False):
        return True

    def orden_empezar(self, o):
        self.mandadas.append(o)
        return "t1"


casa = Casa()
core._casa = lambda: casa
r = core.procesar_orden("estudia solo lo que yo te mande")
ok(core.solo_lo_mio() and "SOLO lo que tú me mandes" in r, "«estudia solo lo que yo te mande» lo enciende: " + r[:60])
import time  # noqa: E402
time.sleep(0.3)
ok(casa.mandadas == ["estudia solo lo que yo te mande"] and "KiraOS" in r, "y el móvil se lo dice a KiraOS")
ok(core._semillas_pensar() == [], "sin nada tuyo, no tiene temas")
ok(core.pensar_una() is None and not preguntas, "y se queda QUIETA (no piensa en temas suyos)")
ok(core.ciclo_una() is None, "tampoco el ciclo de mejora")
core.encargar("qué es un árbol binario")
core._apuntar_tema_mio("Kivy")
sem = core._semillas_pensar()
ok("qué es un árbol binario" in sem and "Kivy" in sem, "con encargos y temas tuyos, piensa en ESOS")
nota = core.pensar_una()
ok(nota and nota["semilla"] in sem and preguntas, "piensa sobre algo tuyo: «" + str((nota or {}).get("semilla")) + "»")
ok(core.actividad()["solo_mio"] and "SOLO lo que tú me mandas" in tbk.tarjeta_movil({"movil": core.actividad()})["texto"],
   "el panel del móvil lo enseña")
t = tbk.tarjeta_movil({"movil": core.actividad()})
ok(("Pensar también libre", "solo_mio") in t["botones"], "con un botón para cambiarlo")
r = core.procesar_orden("piensa libre")
ok(not core.solo_lo_mio() and len(core._semillas_pensar()) > 2, "«piensa libre» lo apaga")
core.es_kiraos = True
casa.mandadas.clear()
core.procesar_orden("solo lo mío")
time.sleep(0.2)
ok(core.solo_lo_mio() and casa.mandadas == [], "KiraOS no se lo reenvía a sí misma")
del core.es_kiraos

# las órdenes apuntadas: fuera de casa, solo las tranquilas
import ordenes_kira as ok_  # noqa: E402
core.dir = os.path.join(T, "kira2")
os.makedirs(core.dir)
ok_.apuntar(core.dir, "apaga el portátil", "kiraos", "pendiente")
ok_.apuntar(core.dir, "hazme un juego de naves", "kiraos", "pendiente")
casa.mandadas.clear()
r = core.ordenes_a_kiraos(fuera=True)
ok(casa.mandadas == ["hazme un juego de naves"], "fuera: se salta «apaga el portátil» y pasa el juego")
ok([o["texto"] for o in ok_.pendientes_kiraos(core.dir)] == ["apaga el portátil"], "lo otro sigue esperando a casa")
itf = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
ok("core.kiraos_fuera()" in itf and "permitida_fuera(orden)" in itf, "la app pasa lo tranquilo por Tailscale al momento")
ok('a == "solo_mio"' in itf, "el botón del panel funciona")

# ---------- Tailscale sin registros técnicos ----------
sh = os.path.join(RAIZ, "kira_portatil", "activar_fuera.sh")
fb = os.path.join(T, "bin")
os.makedirs(fb)
for nombre, cuerpo in {"tailscale": 'if [ "$1" = ip ]; then echo 100.101.102.103; fi',
                       "sudo": 'exec "$@"', "systemctl": "exit 0", "ufw": "exit 0", "sleep": "exit 0"}.items():
    with open(os.path.join(fb, nombre), "w") as f:
        f.write("#!/bin/bash\n" + cuerpo + "\n")
    os.chmod(os.path.join(fb, nombre), 0o755)
dflt = os.path.join(T, "tailscaled")
open(dflt, "w").write('PORT="41641"\nFLAGS=""\n')
env = dict(os.environ, PATH=fb + ":" + os.environ["PATH"], KIRA_TAILSCALED_DEFAULT=dflt)
r1 = subprocess.run(["bash", sh], capture_output=True, text=True, env=env)
ok(r1.returncode == 0 and "100.101.102.103" in r1.stdout, "activar_fuera.sh funciona (con Tailscale de mentira)")
ok('FLAGS="--no-logs-no-support' in open(dflt).read(), "y desactiva los registros técnicos a la empresa de Tailscale")
subprocess.run(["bash", sh], capture_output=True, text=True, env=env)
ok(open(dflt).read().count("--no-logs-no-support") == 1, "otra vez no lo repite")

print("\nTODO BIEN", n)
