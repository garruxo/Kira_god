# -*- coding: utf-8 -*-
"""Kira y Claude en equipo (v2.17): uno propone, el otro revisa, el laboratorio (del móvil) prueba, y se ponen de
acuerdo en mejoras, programas, diseños y estudio. Instalar una mejora sigue necesitando tus dos toques."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import acuerdo_kira as ak
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- leer lo que dice quien revisa ----------
r = ak.interpretar_revision("ACUERDO: SÍ\nMOTIVOS: Hace lo pedido y avisa si falta el nombre.")
ok(r["acuerdo"] is True and "avisa" in r["motivos"] and r["codigo"] is None, "acuerdo con motivos")
import mejoras_ia_kira as mi
BUENO = 'def registrar():\n    def f(texto):\n        return "hola " + texto\n    return {"saluda": f}\n'
r = ak.interpretar_revision("ACUERDO: NO\nMOTIVOS: Si no hay nombre saluda a nadie.\nNOMBRE: saluda\n```python\n" + BUENO + "```",
                            mi.extraer_modulo)
ok(r["acuerdo"] is False and "nadie" in r["motivos"] and r["codigo"] == BUENO and r["nombre"] == "saluda", "desacuerdo con su versión")
ok(ak.interpretar_revision("SÍ")["acuerdo"] is True, "Kira dice SÍ")
r = ak.interpretar_revision("NO: no comprueba que el número sea positivo")
ok(r["acuerdo"] is False and "positivo" in r["motivos"], "Kira dice NO: motivo")
ok(ak.interpretar_revision("Bueno, depende de muchas cosas")["acuerdo"] is None, "si no se entiende, no cuenta")
ok(ak.interpretar_revision("**ACUERDO:** **NO**\nMOTIVOS: x")["acuerdo"] is False, "aunque venga con negritas")

# ---------- negociar ----------
def neg(propuestas, lab, revisiones, revisor="claude", **kw):
    prop, rev, vistos = list(propuestas), list(revisiones), []
    def proponer(aviso):
        vistos.append(aviso)
        x = prop.pop(0)
        if isinstance(x, Exception):
            raise x
        return x
    def probar(nombre, codigo):
        return lab(codigo)
    def revisar(rol, nombre, codigo, dato, objecion):
        vistos.append((rol, codigo, objecion))
        return rev.pop(0) if rev else None
    r = ak.negociar(proponer, probar, revisar if revisor else None, autor="local", revisor=revisor, **kw)
    return r, vistos
pasa = lambda c: ("malo" not in c, "no pasa" if "malo" in c else "", {"c": c})
r, _ = neg([("a", "uno")], pasa, [], revisor=None)
ok(r["ok"] and r["acuerdo"] is None and r["codigo"] == "uno", "sin nadie con quien acordar: trabaja sola (como antes)")
r, v = neg([("a", "malo"), ("a", "dos")], pasa, [{"acuerdo": True, "motivos": "bien"}])
ok(r["ok"] and r["acuerdo"] is True and r["codigo"] == "dos" and r["intentos"] == 2, "falla el laboratorio, corrige y Claude está de acuerdo")
ok(v[1].startswith("El intento anterior falló: no pasa"), "a Kira se le explica el fallo del laboratorio")
r, v = neg([("a", "uno")], pasa, [{"acuerdo": False, "motivos": "le falta X", "codigo": "tres", "nombre": "a"},
                                   {"acuerdo": True, "motivos": ""}])
ok(r["acuerdo"] is True and r["codigo"] == "tres" and r["de"] == "claude", "Claude trae su versión, pasa y Kira la acepta")
ok(v[-1][0] == "autor" and v[-1][2] == "le falta X", "Kira revisa la versión de Claude sabiendo por qué la cambió")
r, v = neg([("a", "uno"), ("a", "cuatro")], pasa,
           [{"acuerdo": False, "motivos": "le falta X", "codigo": "tres"}, {"acuerdo": False, "motivos": "rompe Y"},
            {"acuerdo": True, "motivos": "ahora sí"}])
ok(r["acuerdo"] is True and r["codigo"] == "cuatro", "Kira no acepta la de Claude, hace otra con las dos cosas y acuerdan")
ok("le falta X" in v[3] and "rompe Y" in v[3], "la nueva propuesta tiene en cuenta lo que dijeron los dos")
r, v = neg([("a", "uno"), ("a", "dos"), ("a", "tres"), ("a", "cuatro")], pasa,
           [{"acuerdo": False, "motivos": "no"}] * 5, rondas=3)
ok(r["ok"] and r["acuerdo"] is False and r["codigo"] == "tres" and "Sin acuerdo" in r["historial"][-1],
   "tras 3 rondas sin acuerdo: queda la última que pasa y decides tú")
r, v = neg([("a", "uno")], pasa, [{"acuerdo": False, "motivos": "x", "codigo": "malo"}, ], intentos=1)
ok(r["ok"] and r["codigo"] == "uno" and r["acuerdo"] is False, "si la versión de Claude no pasa el laboratorio, no se usa")
r, v = neg([("a", "uno")], pasa, [None])
ok(r["ok"] and r["acuerdo"] is None and "no pudo revisarla" in r["historial"][-1], "Claude sin red: vale la de Kira y lo dice")
r, _ = neg([ak.Parar("sin cerebro")], pasa, [])
ok(not r["ok"] and r["error"] == "sin cerebro", "parar")
r, v = neg([ak.Reintentar("formato"), ("a", "uno")], pasa, [{"acuerdo": True}])
ok(r["ok"] and v[1] == "El intento anterior falló: formato", "reintentar con el motivo")
ok("ACUERDO entre Kira y Claude" in ak.texto_historial({"acuerdo": True, "historial": ["x"]}), "texto para el usuario")

# ---------- ajuste y órdenes ----------
A = ak.Ajuste(os.path.join(T, "ac.json"))
ok(A.activo and not A.poner(False) and ak.Ajuste(os.path.join(T, "ac.json")).activo is False, "activo por defecto y se guarda")
ok(all(ak.es_orden(x) for x in ("acuerdo con claude", "activa el acuerdo con Claude", "desactiva el acuerdo con claude.")),
   "órdenes del acuerdo")
ok(not ak.es_orden("acuerdo") and not ak.es_orden("hablemos de claude"), "solo esas órdenes")

# ---------- el núcleo reparte el trabajo ----------
import kira_god, cerebro_ia_kira as ci
core = kira_god.KiraGodCore()
core.cerebro_ia.local_disponible = lambda forzar=False: True
ok(core.reparto("codigo") == ("local", None), "solo cerebro del móvil: Kira sola")
open(os.path.join(T, "api_key.txt"), "w").write("clave-de-prueba-123456")
ok(core.reparto("codigo") == ("local", "claude"), "los dos: propone Kira y revisa Claude")
ok(core.reparto("general") == ("local", "claude"), "también para diseñar")
core.cerebro_ia.poner_codigo("claude")
ok(core.reparto("codigo") == ("claude", "local"), "«cerebro mejoras claude»: propone Claude y revisa Kira")
core.cerebro_ia.poner_codigo("auto")
r = core.procesar_orden("desactiva el acuerdo con claude")
ok(r.startswith("[OK] Acuerdo con Claude: NO") and core.reparto("codigo")[1] is None, "desactivar el acuerdo")
r = core.procesar_orden("activa el acuerdo con claude")
ok("trabajamos en equipo" in r and "propone Kira" in r, "activarlo y ver quién hace qué")
core.cerebro_ia.poner_motor("local")
ok(core.reparto("codigo") == ("local", None), "«cerebro local» = nada a internet: sin Claude")
core.cerebro_ia.poner_motor("auto")
core.cerebro_ia.local_disponible = lambda forzar=False: False
ok(core.reparto("codigo") == ("claude", None) and "falta mi cerebro encendido" in core.procesar_orden("acuerdo con claude"),
   "sin el cerebro del móvil: Claude solo, y lo explica")
core.cerebro_ia.local_disponible = lambda forzar=False: True

# ---------- mejora EN EQUIPO, probada en el MÓVIL (sin ordenador) ----------
KIRA_MOD = 'def registrar():\n    def f(texto):\n        return "hola " + texto\n    return {"saluda": f}\n'
CLAUDE_MOD = ('def registrar():\n    def f(texto):\n        nombre = texto.strip()\n        if not nombre:\n'
              '            raise ValueError("Dime a quién saludo.")\n        return f"¡Hola, {nombre}!"\n    return {"saluda": f}\n')
llamadas = []
def api(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None):
    quien = "kira" if clave == ci.LOCAL else "claude"
    llamadas.append((quien, system[:40], usuario))
    if system == mi.SISTEMA_MEJORA_LOCAL:
        return "NOMBRE: saluda\n```python\n" + KIRA_MOD + "```"
    if system.startswith(ak.SISTEMA_REVISION[:40]) and quien == "claude":
        return "ACUERDO: NO\nMOTIVOS: Si no le dices el nombre, saluda al vacío.\nNOMBRE: saluda\n```python\n" + CLAUDE_MOD + "```"
    if system == ak.SISTEMA_REVISION_LOCAL:
        return "SÍ"
    raise AssertionError("llamada inesperada: " + system[:60])
core._llamar_api = api
import panel_kira, laboratorio_movil_kira as lm
ctl = panel_kira.PanelControl(core)
ok(isinstance(ctl.promotor.pasarela, lm.LaboratorioDoble), "el panel prueba en el laboratorio del móvil (y del PC si está)")
r = ctl.enviar_orden("Mejora para Kira: saluda a la gente por su nombre")
ok(r["aprobable"] and r["acuerdo"] is True, f"mejora acordada sin ordenador: {r['texto'][-300:]}")
ok(ctl.pendiente.codigo == CLAUDE_MOD, "se queda la versión en la que están de acuerdo (la de Claude, aceptada por Kira)")
ok("móvil" in r["texto"] and "ACUERDO entre Kira y Claude" in r["texto"] and "Kira: acepta la versión de Claude" in r["texto"],
   "te enseña dónde se probó y la conversación")
ok([q for q, _s, _u in llamadas] == ["kira", "claude", "kira"], "propone Kira, revisa Claude, Kira acepta")
ok("saluda a la gente" in llamadas[1][2] and "Pasa las pruebas" in llamadas[1][2], "Claude ve el pedido y lo que dijo el laboratorio")
ok(not os.path.isfile(os.path.join(T, "modulos", "saluda.py")), "nada instalado todavía: falta tu decisión")
ok(not ctl.aplicar()["ok"], "sin tu confirmación no se aplica")
r = ctl.aplicar(True)
ok(r["ok"] and "saluda" in core.comandos_modulos and "Kira ya sabe usarla" in r["texto"], "con tu confirmación se instala")
ok(core.procesar_orden("saluda Ana") == "¡Hola, Ana!", "y funciona")
ok(core.recuerdos.buscar("saluda", n=3) and any("Sé hacer algo nuevo" in x["texto"] for x in core.recuerdos.buscar("habilidad saluda", n=3)),
   "Kira apunta su habilidad nueva en el baúl")
vistos = []
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None: (vistos.append(system), "Vale.")[1]
core.conversar("qué sabes hacer")
ok("«saluda»" in vistos[-1], "y en la charla sabe que tiene esa orden nueva")
ok("Termux" not in vistos[-1] and "aprende a" in vistos[-1], "sabe cómo se le piden mejoras, programas y diseños")

# ---------- programa para el editor, acordado ----------
PROG_K = "notas = [7, 8.5, 6]\nprint(sum(notas) / len(notas))\n"
llamadas.clear()
def api2(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None):
    quien = "kira" if clave == ci.LOCAL else "claude"
    llamadas.append((quien, system[:30], usuario))
    import programar_kira as pk
    if system == pk.SISTEMA_PROGRAMA_LOCAL:
        return "NOMBRE: media\n```python\n" + PROG_K + "```"
    if system.startswith(ak.SISTEMA_REVISION[:40]):
        return "ACUERDO: SÍ\nMOTIVOS: Calcula bien la media."
    raise AssertionError(system[:60])
core._llamar_api = api2
r = core.programa_acordado("programa que calcule la media de mis notas")
ok(r["ok"] and r["acuerdo"] is True and r["codigo"] == PROG_K and r["nombre"] == "media", "programa probado y acordado")
ok("7.1666" in llamadas[1][2], "Claude ve lo que mostró el programa en la prueba")
ok("ACUERDO" in r["texto"], "texto para enseñar")
def api3(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None):
    return "NOMBRE: roto\n```python\nimport os\nprint(1)\n```"
core._llamar_api = api3
r = core.programa_acordado("programa que borre cosas")
ok(not r["ok"] and r["texto"].startswith("[x]"), "si nunca pasa el modo seguro, lo dice y no abre nada")

# ---------- diseño: con lo estudiado y repasado por Claude ----------
core.recuerdos.guardar("Las tapas de la Barceloneta son famosas por las bombas de patata.", tema="tapas Barceloneta")
pet = []
def api4(clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None):
    pet.append(("kira" if clave == ci.LOCAL else "claude", usuario))
    if clave == ci.LOCAL:
        return json.dumps({"titulo": "Bar", "secciones": [{"titulo": "A", "texto": "B"}]})
    return json.dumps({"titulo": "Bar de tapas La Bomba", "subtitulo": "En la Barceloneta",
                       "secciones": [{"titulo": "Bombas", "texto": "Nuestra especialidad"}]})
core._llamar_api = api4
c, origen = core.generar_diseno("web", "web de un bar de tapas en la Barceloneta")
ok(origen == "acuerdo" and c["titulo"] == "Bar de tapas La Bomba", "Kira propone el diseño y Claude lo mejora")
ok("bombas de patata" in pet[0][1], "Kira diseña con lo que ha estudiado del tema")
ok("Propuesta de Kira" in pet[1][1], "Claude ve la propuesta de Kira")
core._llamar_api = lambda clave, *a, **k: (_ for _ in ()).throw(RuntimeError("sin red")) if clave != ci.LOCAL else api4(clave, *a, **k)
ok(core.generar_diseno("web", "web de un bar")[1] == "ia", "si Claude no responde, vale el de Kira")

# ---------- estudiar: Claude repasa las fichas ----------
core.estudio.estudiar = lambda tema, n=5: (core.recuerdos.guardar("El Teide es un volcán de Tenerife.", tema="Teide"), ["Teide"])[1]
rep = []
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, **k: (rep.append((system, usuario)),
    "El Teide es un volcán de Tenerife y el pico más alto de España, con 3715 metros. Es parque nacional.")[1]
r = core.procesar_orden("estudia el Teide")
ok("repasado con Claude" in r and rep and rep[0][0] == ak.SISTEMA_REPASO and "volcán de Tenerife" in rep[0][1],
   "Claude lee las fichas de Kira y las repasa")
ok(any("3715" in x["texto"] for x in core.recuerdos.buscar("Teide", n=5)), "la ficha repasada queda en el baúl")
core.procesar_orden("desactiva el acuerdo con claude"); rep.clear()
ok("repasado" not in core.procesar_orden("estudia el Teide") and not rep, "con el acuerdo desactivado no gasta a Claude")
print("ACUERDO OK", n)
