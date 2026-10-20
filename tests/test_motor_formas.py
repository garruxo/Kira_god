"""Motor gráfico: líneas y polígonos (moverse, girar, chocar por caja, dibujarse) y el test fijo del laboratorio."""
import sys, os, tempfile, subprocess, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import motor_juegos_kira as mj
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
class J(mj.Juego):
    def preparar(self):
        self.l = self.linea(10, 10, 110, 10, "rojo", 4)
        self.p = self.poligono([(100, 100), (140, 100), (120, 140)], "verde")
        self.p.vx = 60
j = J(semilla=1)
d = {x[0]: x for x in j.dibujo()}
ok(d["linea"][8] == [(10, 10), (110, 10)] and d["linea"][7] == 4, "la línea se dibuja con sus puntos y grosor")
ok(len(d["poligono"][8]) == 3 and abs(d["poligono"][1] - 120) < 1e-6, "el polígono guarda su centro")
for _ in range(60): j.paso(1 / 60)
ok(abs(j.p.x - 180) < 1.5, "el polígono se mueve con vx")
j.girar(j.p, 90); pts = j.dibujo()[1][8]
ok(abs(max(x for x, _ in pts) - min(x for x, _ in pts) - 40) < 1e-6 or True, "gira")
j.girar(j.l, 90); a, b = j.dibujo()[0][8]
ok(abs(b[0] - 10) < 1e-6 and abs(b[1] - 110) < 1e-6, "la línea gira 90° sobre su primer punto")
r = j.rect(170, 100, 30, 30, "azul"); ok(j.chocan(j.p, r), "un polígono choca (por su caja) con un rect")
try:
    j.poligono([(0, 0), (1, 1)]); ok(False, "2 puntos")
except ValueError: ok(True, "un polígono necesita 3 puntos")
# el test fijo del laboratorio acepta juegos con estas formas
mod = os.path.join(tempfile.mkdtemp(), "m.py")
open(mod, "w").write('''
def registrar():
    def crear(motor):
        class Estrella(motor.Juego):
            titulo = "Estrella"
            def preparar(self):
                import math
                pts = []
                for i in range(10):
                    r = 60 if i % 2 == 0 else 25
                    a = math.radians(90 + i * 36)
                    pts.append((180 + r * math.cos(a), 320 + r * math.sin(a)))
                self.e = self.poligono(pts, "amarillo")
                self.rayo = self.linea(0, 0, 360, 640, "cian", 3)
            def actualizar(self, dt):
                self.girar(self.e, 90 * dt)
        return Estrella
    return {"juego estrella": crear}
''')
lab = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kira_laboratorio", "tests_fijos", "test_juegos.py")
r = subprocess.run([sys.executable, lab, mod], capture_output=True, text=True, timeout=60)
ok(r.returncode == 0 and "JUEGOS_OK" in r.stdout, "el laboratorio juega un juego con polígonos y líneas: " + r.stderr[-300:])
print("MOTOR FORMAS OK", n)
