"""Saber de mejoras: las recetas son módulos que funcionan, se buscan bien y llegan al cerebro al programar."""
import sys, os, tempfile, types, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import saber_mejoras_kira as sm_, mejoras_ia_kira as mi
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(RAIZ, "kira_laboratorio", "tests_fijos", "test_juegos.py")
ok(len(sm_.RECETAS) >= 15 and len({r["id"] for r in sm_.RECETAS}) == len(sm_.RECETAS), "hay recetas y sin repetir")
# cada receta: pasa la revisión, carga, sus juegos pasan el laboratorio y sus órdenes responden
for r in sm_.RECETAS:
    ok(all(r.get(k) for k in ("id", "titulo", "temas", "idea", "codigo")), f"{r['id']}: ficha completa")
    ok(mi.precomprobar(r["codigo"]) is None, f"{r['id']}: pasa la revisión previa")
    m = types.ModuleType("r"); exec(compile(r["codigo"], r["id"], "exec"), m.__dict__)
    tabla = m.registrar()
    if any(k.startswith("juego ") for k in tabla):
        f = os.path.join(tempfile.mkdtemp(), "m.py"); open(f, "w").write(r["codigo"])
        p = subprocess.run([sys.executable, LAB, f], capture_output=True, text=True, timeout=60)
        ok(p.returncode == 0, f"{r['id']}: el laboratorio lo juega 20 s sin fallos: {p.stderr[-300:]}")
    for orden, arg, espera in r.get("prueba", []):
        ok(espera in tabla[orden](arg), f"{r['id']}: «{orden} {arg}»")
    ok(r.get("prueba") or any(k.startswith("juego ") for k in tabla), f"{r['id']}: tiene prueba")
# búsqueda
ok(sm_.buscar("hazme un juego de fuegos artificiales con explosiones")[0][1]["id"] == "particulas", "busca partículas")
ok(sm_.buscar("quiero ver un cubo girando en 3D")[0][1]["id"] == "cubo_3d", "busca 3D")
ok(sm_.buscar("un laberinto en primera persona")[0][1]["id"] in ("raycaster", "laberinto_dfs"), "busca laberintos")
ok(sm_.buscar("convierte colores a hexadecimal y dame una paleta")[0][1]["id"] == "colores", "busca colores")
ok(sm_.buscar("") == [] and sm_.buscar("zzzz qqqq") == [], "sin parecido, nada")
ok(sm_.receta("cubo 3d")["id"] == "cubo_3d" and sm_.receta("particulas")["id"] == "particulas", "receta por nombre")
c = sm_.contexto_para("juego de partículas", local=True)
ok("Técnica ya probada" in c and "def registrar" in c, "el contexto lleva la técnica y su código")
class R:
    def contexto(s, q, n=2, maximo=500): return "Una partícula es un punto con vida." if "part" in q else ""
ok("Lo que sabes" in sm_.contexto_para("juego de partículas", R()), "y lo que Kira ha estudiado")
# llega al cerebro al programar una mejora
import kira_god
core = kira_god.KiraGodCore()
enviados = []
core._clave_para = lambda tarea: "clave"
core._llamar_api = lambda clave, sistema, usuario, *a, **k: (enviados.append(usuario),
    "NOMBRE: fuegos\n```python\ndef registrar():\n    return {}\n```")[1]
core.generar_mejora("hazme un juego de fuegos artificiales")
ok("Técnica ya probada" in enviados[-1] and "Fuegos artificiales" in enviados[-1], "el pedido de mejora lleva la receta")
ok("Recetas" in core.procesar_orden("recetas") or "Técnicas probadas" in core.procesar_orden("recetas"), "«recetas»")
ok("def registrar" in core.procesar_orden("receta cubo 3d"), "«receta cubo 3d» enseña el código")
ok("[x]" in core.procesar_orden("receta zzzz"), "receta desconocida")
# «abre la receta» la lleva al editor
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
for _ in range(10): Clock.correr(1, 0.1)
sm.ir("inicio")
campo = next(w for w in sm.walk() if type(w).__name__ == "TextInput" and "Escríbele" in getattr(w, "hint_text", ""))
campo.text = "abre la receta cubo 3d"
next(w for w in sm.walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
area = next(w for w in sm.get_screen("editor_codigo").walk() if type(w).__name__ == "TextInput" and getattr(w, "multiline", False))
ok(sm.current == "editor_codigo" and "proyectar" in area.text, "«abre la receta cubo 3d» la abre en el editor")
print("SABER OK", n)
