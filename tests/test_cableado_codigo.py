"""Cableado: editor de código, lista de juegos, pantalla de juego y niveles del curso en la terminal."""
import sys, os, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
import kira_god
core = kira_god.KiraGodCore()
core.conversar = lambda t, h=(): "ok"
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
def en(pantalla): return sm.get_screen(pantalla)
def boton(txt, raiz=None):
    return next(w for w in (raiz or sm).walk() if type(w).__name__ == "Button" and w.text == txt)
def botones(raiz): return [w for w in raiz.walk() if type(w).__name__ == "Button"]
def labels(raiz=None): return [w.text for w in (raiz or sm).walk() if type(w).__name__ == "Label"]
def esperar(cond, seg=4):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.05)
        if cond(): return True
        time.sleep(0.01)
    return False

# ---------- menú ----------
sm.ir("menu")
tiles = [w.text for w in sm.walk() if type(w).__name__ == "Button" and "[b]" in w.text]
ok(any("Juegos" in t for t in tiles) and any("Editor de código" in t for t in tiles), "Juegos y Editor en el menú principal")

# ---------- editor ----------
sm.ir("editor_codigo"); ed = en("editor_codigo")
area = next(w for w in ed.walk() if type(w).__name__ == "TextInput" and getattr(w, "multiline", False))
area.text = "nombre = input()\nprint('Hola', nombre)\nprint(sum(range(10)))"
next(w for w in ed.walk() if type(w).__name__ == "TextInput" and "Entrada" in getattr(w, "hint_text", "")).text = "Kira"
boton("Ejecutar", ed).press()
ok(esperar(lambda: any("Hola Kira" in l and "45" in l and "[OK] Terminado" in l for l in labels(ed))), "ejecuta y enseña la salida")
area.text = "import os"; boton("Comprobar", ed).press()
ok(any("modo seguro" in l for l in labels(ed)), "comprobar avisa del modo seguro")
area.text = "while True:\n    pass"; boton("Ejecutar", ed).press()
ok(esperar(lambda: any("bucle infinito" in l for l in labels(ed)), 9), "un bucle infinito se corta")
area.text = "print('guardado')"
nombre = next(w for w in ed.walk() if type(w).__name__ == "TextInput" and getattr(w, "hint_text", "") == "nombre_del_programa")
nombre.text = "Mi Prueba"; boton("Guardar", ed).press()
ok(nombre.text == "mi_prueba" and os.path.isfile(os.path.join(T, "programas", "mi_prueba.py")), "guarda el programa")
boton("Nuevo", ed).press(); ok(area.text == "", "nuevo vacía el editor")
boton("Abrir…", ed).press(); ok(sm.current == "abrir_codigo", "abre la lista")
boton("mi_prueba", en("abrir_codigo")).press(); ok(sm.current == "editor_codigo" and area.text == "print('guardado')", "abre tu programa")
boton("Ejemplos…", ed).press()
ej_b = [b.text for b in botones(en("abrir_codigo"))]
ok(any(t.startswith("[Avanzado] Decoradores") for t in ej_b) and any(t.startswith("[Código] Búsqueda de caminos") for t in ej_b)
   and any(t.startswith("[Juego] Serpiente") for t in ej_b), "ejemplos de todos los niveles")
boton("[Código] Resolver sudokus", en("abrir_codigo")).press(); boton("Ejecutar", ed).press()
ok(esperar(lambda: any("[1, 9, 8, 3, 4, 2, 5, 6, 7]" in l for l in labels(ed)), 6), "ejecuta un ejemplo avanzado")

# ---------- juegos ----------
sm.ir("juegos"); lj = en("juegos")
nombres = [b.text for b in botones(lj)]
ok(all(t in nombres for t in ("Rompeladrillos", "Serpiente", "Esquiva meteoritos", "Saltarín", "Pong contra Kira")), "los 5 juegos")
boton("Rompeladrillos", lj).press()
ok(sm.current == "jugar", "abre la pantalla de juego")
vista = next(w for w in sm.walk() if type(w).__name__ == "JuegoWidget")
ok(vista.juego.titulo == "Rompeladrillos", "carga el juego")
class Toque:
    def __init__(s, x, y): s.x, s.y, s.pos = x, y, (x, y)
vista.on_touch_down(Toque(10, 50)); Clock.correr(30, 1 / 60)
ok(vista.juego.pala.x < 100, "el dedo mueve la pala")
ok(any("Puntos" in l for l in labels(en("jugar"))), "marcador")
boton("Pausa", en("jugar")).press(); ok(vista.juego.estado == "pausa", "pausa")
boton("Reiniciar", en("jugar")).press(); ok(vista.juego.estado == "jugando" and vista.juego.puntos == 0, "reinicia")
boton("Salir", en("jugar")).press(); ok(sm.current == "juegos", "salir vuelve a la lista")
boton("Código", lj).press()
ok(sm.current == "editor_codigo" and "class Rompeladrillos(Juego)" in area.text, "ver el código del juego")
area.text = area.text.replace('"azul"', '"rosa"'); boton("Jugar", ed).press()
ok(sm.current == "jugar" and vista.juego.pala.color[0] == 1.0, "un juego cambiado en el editor se juega")
sm.ir("menu"); Clock.correr(5, 0.05)
area.text = "from motor_juegos_kira import Juego\nclass J(Juego):\n    def actualizar(self, dt):\n        while True: pass"
boton("Jugar", ed).press(); esperar(lambda: any("colgado" in l for l in labels(en("jugar"))), 4)
ok(any("colgado" in l for l in labels(en("jugar"))), "un juego colgado se para sin colgar la app")
area.text = "print(1)"; boton("Jugar", ed).press()
ok(sm.current == "editor_codigo" and any("no define ningún juego" in l for l in labels(ed)), "sin juego: lo explica")
sm.ir("juegos"); boton("+ Programar un juego nuevo", lj).press()
ok("class MiJuego(Juego)" in area.text, "plantilla de juego nuevo")

# ---------- terminal: niveles y abrir en el editor ----------
sm.ir("terminal"); term = en("terminal")
boton("Avanzado", term).press()
ok(any(b.text == "Decoradores" for b in botones(term)), "nivel avanzado en la terminal")
boton("Decoradores", term).press(); boton("Abrir en el editor", term).press()
ok(sm.current == "editor_codigo" and "contar_llamadas" in area.text, "la lección se abre en el editor")
boton("Códigos", sm.get_screen("terminal")).press()
ok(any(b.text == "Juego de la vida" for b in botones(term)), "nivel de códigos")
print("CABLEADO CODIGO OK", n)
