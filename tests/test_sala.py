import sys, os, tempfile, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import habitacion_kira as hk, programacion_kira as pk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m
W, H = 360, 640
esc = hk.construir_escena()
ok(300 < len(esc) < 450, f"nº de caras razonable ({len(esc)})")
# proyección: un punto delante del centro cae en el centro; a la derecha cae a la derecha; detrás no se proyecta
pose = (0, 1.5, 0, 0, 0)
pc = hk.a_camara((0, 1.5, 4), pose); ok(abs(pc[0]) < 1e-9 and abs(pc[2] - 4) < 1e-9, "delante")
ok(hk.proyectar(pc, W, H, 0.9 * W) == (W / 2, H / 2), "centro")
ok(hk.proyectar(hk.a_camara((1, 1.5, 4), pose), W, H, 324)[0] > W / 2, "derecha a la derecha")
ok(hk.proyectar(hk.a_camara((0, 2.5, 4), pose), W, H, 324)[1] > H / 2, "arriba hacia arriba")
ok(hk.a_camara((0, 1.5, -3), pose)[2] < 0, "detrás tiene z negativa")
# girar 90° a la derecha: lo que estaba a la derecha (x+) pasa a estar delante
pc = hk.a_camara((3, 1.5, 0), (0, 1.5, 0, 90, 0)); ok(pc[2] > 2.9 and abs(pc[0]) < 1e-6, "yaw +90 mira a +x")
pc = hk.a_camara((-3, 1.5, 0), (0, 1.5, 0, -90, 0)); ok(pc[2] > 2.9 and abs(pc[0]) < 1e-6, "yaw -90 mira a -x")
# recorte contra el plano cercano
tri = [(-1, 0, -1), (1, 0, 2), (0, 1, 2)]
rec = hk._recortar(tri); ok(len(rec) >= 3 and all(p[2] >= hk.NEAR - 1e-9 for p in rec), "recorte")
ok(hk._recortar([(0, 0, -1), (1, 0, -2), (0, 1, -1)]) == [], "todo detrás -> vacío")
# render: de atrás hacia delante por capas, sin puntos NaN y dentro de límites razonables
for nombre, p in (("entrada", hk.POSE_ENTRADA), ("mesa", hk.POSE_MESA), ("biblio", hk.POSE_BIBLIOTECA), ("salida", hk.POSE_SALIDA), ("pc", hk.POSE_ORDENADOR)):
    caras = hk.render_caras(esc, p, W, H)
    ok(8 < len(caras) <= len(esc), f"caras visibles {nombre}: {len(caras)}")
    ok(all(len(pp) >= 3 and all(math.isfinite(v) and abs(v) < 1e5 for q in pp for v in q) for pp, _, _ in caras), "coords finitas " + nombre)
    ok(all(all(0 <= c <= 1 for c in col) for _, col, _ in caras), "colores válidos " + nombre)
# toques: en la mesa, el centro del monitor es ORDENADOR; mirando a la izquierda, BIBLIOTECA; a la derecha, SALIDA
c = hk.render_caras(esc, hk.POSE_MESA, W, H)
mx, my = hk.proyectar(hk.a_camara((0, 1.28, 6.88), hk.POSE_MESA), W, H, 0.9 * W)
ok(hk.hotspot_en(c, mx, my) == "ordenador", "toque en el monitor: " + str(hk.hotspot_en(c, mx, my)))
ok(hk.hotspot_en(c, 5, 5) is None, "suelo no es hotspot")
c = hk.render_caras(esc, hk.POSE_BIBLIOTECA, W, H); ok(hk.hotspot_en(c, W / 2, H / 2) == "biblioteca", "libros")
c = hk.render_caras(esc, hk.POSE_SALIDA, W, H); ok(hk.hotspot_en(c, W / 2, H / 2 - 100) == "salida", "puerta")
ok(any(t == "BIBLIOTECA" for t, *_ in hk.etiquetas(hk.POSE_BIBLIOTECA, W, H)) and any(t == "SALIDA" for t, *_ in hk.etiquetas(hk.POSE_SALIDA, W, H)), "carteles")
ok(hk.punto_en_poligono(5, 5, [(0, 0), (10, 0), (10, 10), (0, 10)]) and not hk.punto_en_poligono(15, 5, [(0, 0), (10, 0), (10, 10), (0, 10)]), "punto en polígono")
# recorrido: el paseo termina en la mesa y queda libre
r = hk.Recorrido(esc); ok(r.estado == "caminando", "empieza caminando")
t = 0
while r.estado == "caminando" and t < 20: ev = r.paso(0.05); t += 0.05
ok(r.estado == "libre" and ev is None and abs(r.pose[2] - hk.POSE_MESA[2]) < 1e-6, f"llega a la mesa en {t:.1f}s")
ok(abs(t - hk.DURACION_PASEO) < 0.3, "duración del paseo")
r.paso(5.0); ok(r.estado == "libre", "libre no cambia solo")
# mirar alrededor
y0 = r.pose[3]; r.arrastrar(-200, 0, W); ok(r.pose[3] > y0, "arrastrar izquierda gira a la derecha (como agarrar el mundo)")
r.arrastrar(99999, 0, W); ok(r.pose[3] == -hk.LIMITE_YAW, "límite de giro")
r.arrastrar(0, -99999, W); ok(r.pose[4] == -hk.LIMITE_PITCH, "límite vertical")
r.pose = hk.POSE_MESA
# ir al ordenador emite 'ordenador' una sola vez y queda dentro; volver regresa a libre
ok(r.ordenar("ordenador"), "ordenar"); ok(not r.ordenar("ordenador"), "no se puede ordenar dos veces a la vez")
evs = []
for _ in range(100):
    e = r.paso(0.05)
    if e: evs.append(e)
ok(evs == ["ordenador"] and r.estado == "dentro", f"evento único {evs}")
ok(r.paso(1.0) is None, "dentro no repite")
r.volver(); [r.paso(0.05) for _ in range(60)]; ok(r.estado == "libre" and abs(r.pose[2] - hk.POSE_MESA[2]) < 1e-6, "vuelve a la mesa")
for destino in ("biblioteca", "salida"):
    r.ordenar(destino); e = None
    for _ in range(100): e = r.paso(0.05) or e
    ok(e == destino, destino); r.volver(); [r.paso(0.05) for _ in range(60)]
ok(not r.ordenar("cocina"), "destino inexistente")
# tocar durante el paseo: el ordenador salta el paseo
r2 = hk.Recorrido(esc); r2.paso(1.0)
px, py = hk.proyectar(hk.a_camara((0, 1.28, 6.88), r2.pose), W, H, 0.9 * W)
ok(r2.tocar(px, py, W, H) == "ordenador", "tocar el ordenador durante el paseo")
[r2.paso(0.05) for _ in range(20)]; ok(r2.estado == "libre" and abs(r2.pose[2] - hk.POSE_MESA[2]) < 1e-6, "y salta el paseo")
r3 = hk.Recorrido(esc); [r3.paso(0.05) for _ in range(100)]
r3.mirar("izquierda"); [r3.paso(0.05) for _ in range(40)]; ok(r3.estado == "libre" and r3.pose[3] == -75, "mirar izquierda")
r3.reiniciar(); ok(r3.estado == "caminando" and r3.pose == hk.POSE_ENTRADA, "reiniciar")
# intenciones
for frase, esperado in (("hackear", "ordenador"), ("Vamos a hacer programación", "ordenador"), ("quiero aprender programación", "ordenador"),
                        ("mejorar a Kira", "ordenador"), ("abre el ordenador", "ordenador"), ("la biblioteca", "biblioteca"),
                        ("enséñame mis libros", "biblioteca"), ("salir", "salida"), ("quiero volver al menú", "salida"),
                        ("qué tiempo hace", None), ("", None)):
    ok(hk.intencion_sala(frase) == esperado, f"{frase!r} -> {hk.intencion_sala(frase)}")
ok(hk.intencion_sala("salir de la biblioteca") == "salida", "salir manda sobre biblioteca")
# --- programación ---
ok(pk.comprobar_sintaxis("def f(:\n pass")[0] is False and "línea" in pk.comprobar_sintaxis("def f(:")[1], "sintaxis mala")
ok(pk.comprobar_sintaxis("x = 1\nprint(x)")[0], "sintaxis buena")
ok(pk.comprobar_sintaxis("while True: pass")[0], "no ejecuta (while True solo se analiza)")
# el curso: todos los ejemplos se EJECUTAN de verdad en un proceso aparte con límite de tiempo
for l in pk.CURSO:
    with tempfile.TemporaryDirectory() as t:
        p = subprocess.run([sys.executable, "-I", "-c", l["codigo"]], cwd=t, capture_output=True, text=True, timeout=10)
        ok(p.returncode == 0, f"ejemplo '{l['id']}' funciona: {p.stderr[-120:]}")
ok(len({l["id"] for l in pk.CURSO}) == len(pk.CURSO) == 8, "curso")
T = tempfile.mkdtemp()
b = pk.Biblioteca(os.path.join(T, "b.json"))
ok(b.anadir("apunte", "  Mi truco ", "usa enumerate")[0] and not b.anadir("apunte", "", "x")[0] and not b.anadir("raro", "a", "b")[0], "añadir/validar")
i2 = b.anadir("apunte", "mi truco", "usa zip")[2]; ok(len(b.listar("apunte")) == 1 and b.obtener(i2)["texto"] == "usa zip", "mismo título actualiza")
ok(b.anadir("leccion", "mi truco", "otra clase")[0] and len(b.listar()) == 2, "misma clave, otra clase")
ok(b.borrar(i2) and not b.borrar(i2), "borrar")
ok(len(pk.Biblioteca(os.path.join(T, "b.json")).listar()) == 1, "persiste")
open(os.path.join(T, "mal.json"), "w").write("{rota"); ok(pk.Biblioteca(os.path.join(T, "mal.json")).listar() == [], "corrupta")
for k in range(250): b.anadir("apunte", f"t{k}", "x")
ok(len(b.items) <= pk.MAX_LIBROS, "tope de libros")
ok(len(b.anadir("apunte", "largo", "z" * 9000)[0:1]) == 1 and max(len(i["texto"]) for i in b.items) <= pk.MAX_TEXTO, "recorta texto")
import cerebro_local as cl
con = cl.Conocimiento(os.path.join(T, "c.json"))
b = pk.Biblioteca(os.path.join(T, "b2.json"))
ok(pk.guardar_leccion(b, con, "Bucles", "for recorre.\n\nEjemplo:\nfor i in range(3): pass")[1].endswith("recordará."), "guarda y Kira recuerda")
ok("for recorre" in con.listar()[0]["texto"] and "Ejemplo" not in con.listar()[0]["texto"] and con.listar()[0]["fuente"] == "biblioteca", "resumen en la memoria")
# núcleo: generar_leccion con API simulada
os.environ["KIRA_DATA_DIR"] = T
import kira_god
k = kira_god.KiraGodCore()
try: k.generar_leccion("recursión"); ok(False, "pide clave")
except RuntimeError as e: ok("clave" in str(e), "pide clave")
open(os.path.join(T, "api_key.txt"), "w").write("sk-ant-test-123456789")
k._llamar_api = lambda c, s, u, max_tokens=4000, mensajes=None: "TITULO: Recursión\nEXPLICACION: Una función que se llama a sí misma.\n```python\ndef f(n):\n    return 1 if n<2 else n*f(n-1)\n```"
t_, e_, c_ = k.generar_leccion("recursión"); ok(t_ == "Recursión" and "sí misma" in e_ and "def f" in c_, "parsea lección")
k._llamar_api = lambda *a, **kw: "hola sin formato"
try: k.generar_leccion("x"); ok(False, "formato")
except ValueError: ok(True, "formato inválido")
print("SALA OK", n)
