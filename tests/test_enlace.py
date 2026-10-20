# -*- coding: utf-8 -*-
"""Pasarela sin líos: el laboratorio se anuncia en la WiFi (faro), Kira lo encuentra, se empareja UNA vez con el
código de 6 cifras (dicho de palabra o escrito) y después se conecta sola, aunque el PC cambie de dirección."""
import json, os, socket, stat, sys, tempfile, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(RAIZ, "kira_laboratorio")
sys.path.insert(0, RAIZ); sys.path.insert(0, LAB)
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
TOKEN = "token-del-laboratorio-de-prueba-0123456789"
os.environ["KIRA_LAB_TOKEN"] = TOKEN
import servidor_lab as sl, lab_enlace as le, iniciar_laboratorio as il
import enlace_lab_kira as el, pasarela_cliente as pc
from http.server import ThreadingHTTPServer
os.environ.pop("KIRA_LAB_TOKEN", None)               # el móvil NO tiene el token: lo consigue emparejándose
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- el código y sus límites (reloj falso) ----------
ahora = [0.0]
avisos = []
E = le.Emparejador(TOKEN, reloj=lambda: ahora[0], avisar=avisos.append, nombre="PC-PRUEBA")
c = E.codigo_actual()
ok(len(c) == 6 and c.isdigit() and E.codigo_actual() == c, "código de 6 cifras, estable mientras vale")
ok(E.mostrar("Kira desde 192.168.1.34") and "CÓDIGO PARA CONECTAR A KIRA" in avisos[-1] and c[:3] + " " + c[3:] in avisos[-1],
   "se enseña bien grande en la ventana del laboratorio")
otro = "000000" if c != "000000" else "111111"
r = E.probar(otro)
ok(r == (False, "Ese código no es. Quedan 4 intentos."), "código malo: cuántos intentos quedan")
ok(E.probar("4 8") [0] is False, "a medias no vale")
ok(E.probar(" ".join(c)) == (True, TOKEN), "el bueno (aunque venga con espacios) da el token")
ok(E.probar(c)[0] is False, "un solo uso")
ahora[0] += le.CADUCA + 1
ok("caducó" in E.probar("123456")[1], "caduca")
c2 = E.codigo_actual()
ok(c2 and ahora[0] < E.hasta, "tras caducar sale uno nuevo")
for _ in range(le.INTENTOS):
    r = E.probar("999999" if c2 != "999999" else "888888")
ok("no quedan intentos" in r[1] and E.codigo is None, "5 fallos: el código se anula")
for _ in range(le.CODIGOS_MAX - 1):
    E.codigo_actual()
    for _ in range(le.INTENTOS):
        r = E.probar("x")
ok(E.cerrado and "cerrado" in r[1] and E.codigo_actual() is None and not E.mostrar(), "3 códigos fallados: se cierra")
ok(any("adivinarlo" in a for a in avisos), "y avisa en la ventana")
ok(le.id_lab(TOKEN) == le.id_lab(TOKEN) and TOKEN not in le.id_lab(TOKEN) and le.id_lab("otro") != le.id_lab(TOKEN), "id estable sin revelar el token")

# ---------- laboratorio de verdad en esta máquina ----------
sl.EMPAREJADOR = le.Emparejador(TOKEN, avisar=avisos.append, nombre="PC-PRUEBA")
def servidor():
    s = ThreadingHTTPServer(("127.0.0.1", 0), sl.Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s
SRV = servidor(); PUERTO = SRV.server_address[1]
FARO = le.Faro(PUERTO, nombre="PC-PRUEBA", host="127.0.0.1", puerto=0); FARO.start(); FARO.listo.wait(3)
ok(not FARO.error and FARO.puerto > 0, "el faro escucha: " + FARO.error)
# el faro contesta sin el token
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2)
s.sendto(le.PREGUNTA, ("127.0.0.1", FARO.puerto)); datos, _ = s.recvfrom(1024)
s.sendto(b"otra cosa", ("127.0.0.1", FARO.puerto))
r = json.loads(datos)
ok(r == {"kira_lab": 1, "puerto": PUERTO, "nombre": "PC-PRUEBA"} and TOKEN.encode() not in datos, "el faro dice puerto y nombre, nunca el token")
try:
    s.recvfrom(1024); ok(False, "no contesta a otra cosa")
except socket.timeout:
    ok(True, "a cualquier otra cosa no contesta")
s.close()
# rutas nuevas del servidor
cod, r = el._pedir(f"http://127.0.0.1:{PUERTO}", "/hola")
ok(cod == 401, "/hola sin token: 401")
cod, r = el._pedir(f"http://127.0.0.1:{PUERTO}", "/hola", token=TOKEN)
ok(cod == 200 and r["id"] == le.id_lab(TOKEN), "/hola con token: quién es")
cod, r = el._pedir(f"http://127.0.0.1:{PUERTO}", "/probar", {"nombre": "x", "codigo": "x"})
ok(cod == 401, "probar sigue exigiendo el token")

def buscar_aqui():
    return el.buscar(espera=0.6, destinos=["127.0.0.1"], puerto_faro=FARO.puerto, recorrer=False)
labs = buscar_aqui()
ok(labs == [{"url": f"http://127.0.0.1:{PUERTO}", "ip": "127.0.0.1", "nombre": "PC-PRUEBA"}], f"Kira lo encuentra: {labs}")
ok(el.buscar(espera=0.3, destinos=["127.0.0.1"], puerto_faro=1, recorrer=False) == [], "sin faro, nada")

# ---------- emparejar con la voz ----------
EN = el.Enlace(buscar_fn=buscar_aqui)
r = EN.conectar()
ok("He encontrado el laboratorio en «PC-PRUEBA»" in r and "6 cifras" in r and EN.esperando_codigo(), "pide el código")
ok("CÓDIGO PARA CONECTAR A KIRA" in avisos[-1] and "Kira desde 127.0.0.1" in avisos[-1], "el código sale en el ordenador")
ok(EN.con_codigo("qué hora es") is None, "si no es un código, sigue a lo suyo")
ok("6 cifras" in EN.con_codigo("el código es cuatro dos"), "a medias: pide las 6")
codigo = sl.EMPAREJADOR.codigo
malo = "".join(str((int(x) + 1) % 10) for x in codigo)
ok("Quedan 4 intentos" in EN.con_codigo(malo), "código equivocado")
NUM = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
r = EN.con_codigo("vale, " + " ".join(NUM[int(x)] for x in codigo))
ok(r.startswith("[OK] ¡Conectada al laboratorio de PC-PRUEBA!"), "dicho de palabra: conectada — " + r)
cfg = pc.leer_config()
ok(cfg["url"] == f"http://127.0.0.1:{PUERTO}" and cfg["token"] == TOKEN and cfg["nombre"] == "PC-PRUEBA", "guarda la conexión")
if os.name == "posix":
    ok(stat.S_IMODE(os.stat(pc.ruta_config()).st_mode) == 0o600, "solo legible por la app")
ok(not EN.esperando_codigo(), "ya no espera código")
ok(EN.conectar().startswith("[OK] Ya estoy conectada"), "la siguiente vez: sin código")
ok(EN.estado()[0] and "PC-PRUEBA" in EN.estado()[1], "estado real")

# los clientes que ya existían ven la conexión nueva sin reiniciar
P = pc.PasarelaCliente()
ok(P.url == cfg["url"] and P.token == TOKEN and P.nombre == "PC-PRUEBA", "PasarelaCliente lee la conexión")
MOD = "def registrar():\n    return {'hola': lambda t: 'hola'}\n"
ok(P.probar("hola_mod", MOD)["ok"], "y las mejoras se prueban de verdad en el laboratorio")
import video_cliente_kira as vc
ok(vc.ClienteVideo().url == cfg["url"], "el cliente de vídeo también")

# ---------- el PC cambia de dirección: Kira lo vuelve a encontrar sola ----------
SRV2 = servidor(); P2 = SRV2.server_address[1]
SRV.shutdown(); SRV.server_close(); FARO.parar()
FARO2 = le.Faro(P2, nombre="PC-PRUEBA", host="127.0.0.1", puerto=0); FARO2.start(); FARO2.listo.wait(3)
original = el.buscar
el.buscar = lambda *a, **k: original(espera=0.6, destinos=["127.0.0.1"], puerto_faro=FARO2.puerto, recorrer=False)
r = P.probar("hola_mod", MOD)
ok(r.get("ok") and P.url == f"http://127.0.0.1:{P2}" and pc.leer_config()["url"] == P.url, "cambió el puerto/IP: lo busca, lo usa y lo guarda")
ok(pc.leer_config()["token"] == TOKEN, "con el mismo token (sin emparejar otra vez)")
EN2 = el.Enlace(buscar_fn=lambda: original(espera=0.6, destinos=["127.0.0.1"], puerto_faro=FARO2.puerto, recorrer=False))
ok(EN2.conectar().startswith("[OK] Ya estoy conectada"), "conectar con todo bien")
# un laboratorio con OTRO token no se acepta al reubicar
ok(el.reubicar("token-que-no-es-de-nadie-000000", buscar_fn=EN2._buscar) is None, "otro token: no se cuela")
el.buscar = original

# ---------- números dichos ----------
casos = {"cuatro ocho dos uno nueve siete": "482197", "cuarenta y ocho veintiuno noventa y siete": "482197",
         "cuatrocientos ochenta y dos ciento noventa y siete": "482197", "48 21 97": "482197",
         "el código es 482197": "482197", "seis cero cero cien": "600100", "dieciséis treinta y tres cero": "16330"}
for frase, esperado in casos.items():
    ok(el.cifras_dichas(frase) == esperado, f"«{frase}» -> {el.cifras_dichas(frase)}")
ok(el.codigo_de("cuatro ocho dos") is None and el.codigo_de("482197") == "482197", "codigo_de exige 6 cifras")

# ---------- iniciar_laboratorio: por la WiFi por defecto, y arrancar con Windows ----------
ok(il.argumentos([]) == (["--host", "0.0.0.0"], None), "por defecto, por la WiFi")
ok(il.argumentos(["--solo-este-equipo"]) == (["--host", "127.0.0.1"], None), "solo este equipo")
ok(il.argumentos(["--con-windows", "--permitir-instalar"]) == (["--permitir-instalar", "--host", "0.0.0.0"], True), "opciones")
txt = il.contenido_inicio(python=r"C:\Python312\python.exe", aqui=r"C:\Kira\kira_laboratorio")
ok(txt.startswith("@echo off\r\n") and r'cd /d "C:\Kira\kira_laboratorio"' in txt and "/min" in txt and txt.endswith("\r\n"),
   "el .bat de inicio arranca minimizado")
if os.name != "nt":
    ok(il.con_windows(True) == (False, "Esto solo funciona en Windows."), "fuera de Windows lo dice")
for bat in ("Arrancar laboratorio.bat", "Arrancar con Windows.bat"):
    contenido = open(os.path.join(LAB, bat), "rb").read()
    ok(b"\r\n" in contenido and b"\n" not in contenido.replace(b"\r\n", b"") and b"iniciar_laboratorio.py" in contenido,
       f"{bat}: doble clic en Windows (saltos CRLF)")

# ---------- el núcleo: órdenes ----------
pc.olvidar_config()
import kira_god
core = kira_god.KiraGodCore()
core.enlace = el.Enlace(buscar_fn=EN2._buscar)
r = core.procesar_orden("Kira, conéctate al ordenador")
ok("Dime el código" in r, "«conéctate al ordenador» -> pide el código: " + r)
codigo = sl.EMPAREJADOR.codigo
r = core.procesar_orden(codigo)
ok(r.startswith("[OK] ¡Conectada") and codigo not in " ".join(map(str, core.volatile_ram_buffer)), "el código conecta y no se queda en el búfer")
ok("Estoy conectada" in core.procesar_orden("¿estás conectada al laboratorio?"), "estado")
ok("Ya estoy conectada" in core.procesar_orden("entra en el laboratorio"), "«entra en el laboratorio»")
ok("He olvidado" in core.procesar_orden("desconéctate del laboratorio") and pc.leer_config() == {}, "olvidar")
core.enlace = el.Enlace(buscar_fn=lambda: [])
ok("No encuentro el laboratorio" in core.procesar_orden("conecta con el pc") and "Arrancar laboratorio" in core.procesar_orden("conecta con el pc"),
   "sin laboratorio encendido: dice qué hacer")

# ---------- pantalla Pasarela ----------
core.enlace = el.Enlace(buscar_fn=EN2._buscar)
core.conversar = lambda t, h=(), al_trozo=None: "charla"
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
def correr(seg=3.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.05)
        if cond and cond():
            return True
        time.sleep(0.01)
    return bool(cond and cond())
correr(1)
def boton(txt, raiz):
    return next(w for w in raiz.walk() if type(w).__name__ == "Button" and w.text == txt)
pas = sm.get_screen("pasarela")
def texto_pas():
    return " ".join(w.text for w in pas.walk() if type(w).__name__ == "Label")
sm.ir("pasarela")
ok("no hace falta" in texto_pas() and "Ya no necesito el ordenador" in texto_pas() and "Arrancar laboratorio" in texto_pas(),
   "explica que el ordenador es opcional y los 3 pasos")
campo = next(w for w in pas.walk() if type(w).__name__ == "TextInput" and "6 cifras" in w.hint_text)
fila = next(w for w in pas.walk() if campo in getattr(w, "children", []))
ok(fila.disabled and fila.opacity == 0, "el campo del código solo sale cuando hace falta")
boton("Conectar con el ordenador", pas).press()
ok(correr(5, lambda: "Dime el código" in texto_pas()), "botón «Conectar»: lo encuentra y pide el código")
ok(not fila.disabled and fila.opacity == 1, "ahora sí sale el campo")
campo.text = sl.EMPAREJADOR.codigo
boton("Enviar código", pas).press()
ok(correr(5, lambda: "Conectada al laboratorio de PC-PRUEBA" in texto_pas()), "con el código: conectada")
ok(sm.control.pasarela.url == f"http://127.0.0.1:{P2}", "el panel de mejoras ya usa esa conexión")
boton("Comprobar la conexión", pas).press()
ok(correr(5, lambda: "Estoy conectada" in texto_pas()), "comprobar")
boton("Olvidar este laboratorio", pas).press()
ok("He olvidado" in texto_pas() and not sm.control.pasarela.url, "olvidar desde la pantalla")
# por voz/texto desde el botón de Kira: el código se contesta sin decir «Kira» otra vez
sm.ir("inicio")
entrada = next(w for w in sm.walk() if type(w).__name__ == "TextInput" and "Escríbele" in getattr(w, "hint_text", ""))
entrada.text = "Kira, conéctate al ordenador"
next(w for w in sm.walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
burbuja = lambda: " ".join(w.text for w in sm.get_screen("inicio").walk() if type(w).__name__ == "Label")
ok(correr(6, lambda: "Dime el código" in burbuja()), "por la portada: pide el código")
entrada.text = " ".join(sl.EMPAREJADOR.codigo)
next(w for w in sm.walk() if type(w).__name__ == "Button" and w.text == "Enviar").press()
ok(correr(6, lambda: "Conectada al laboratorio" in burbuja()), "y con el código, conectada")
SRV2.shutdown(); FARO2.parar()
print("ENLACE OK", n)
