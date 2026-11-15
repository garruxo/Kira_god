"""v3.88: programas que para arrancar necesitan OTRO programa (un servidor, un «puente») encendido en otra terminal.
Kira lo enciende aparte, espera a que esté listo, arranca el programa y al cerrarlo apaga el puente."""
import os, sys, tempfile, subprocess, socket, time, stat
RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path[:0] = [RAIZ, os.path.join(RAIZ, "kira_portatil")]
T = tempfile.mkdtemp()
os.environ["HOME"] = T
import arreglar_app_kira as ar
ar.REGISTROS = os.path.join(T, "registros")

ok = mal = 0
def mira(c, t):
    global ok, mal
    if c: ok += 1; print("  ok ", t)
    else: mal += 1; print("FALLA", t)

def libre():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

# ---- reconocer ----
mira(ar.es_puente("python3 server.py"), "server.py es un puente")
mira(ar.es_puente("npm run backend"), "npm run backend es un puente")
mira(not ar.es_puente("pip3 install -r requirements.txt"), "instalar no es un puente")
mira(not ar.es_puente("python3 cliente.py"), "un cliente sin pistas no es puente")
readme_ctx = "## Uso\nEn otra terminal, deja esto funcionando:\n\n    $ python3 motor.py\n"
mira(ar.es_puente("python3 motor.py", readme_ctx), "«en otra terminal» lo marca como puente")
mira(ar.puerto_de("python3 server.py --port 8123") == 8123, "puerto de --port")
mira(ar.puerto_de("python3 motor.py", "abre http://localhost:9001 cuando $ python3 motor.py") == 9001,
     "puerto del README")

# ---- un programa de verdad: cliente que necesita al servidor ----
puerto = libre()
app = os.path.join(T, "apps", "chat"); os.makedirs(app)
open(os.path.join(app, "server.py"), "w").write(f"""
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", {puerto})); s.listen(5)
print("servidor listo", flush=True)
while True:
    c, _ = s.accept(); c.sendall(b"hola desde el puente\\n"); c.close()
""")
open(os.path.join(app, "cliente.py"), "w").write(f"""
import socket, sys
try:
    c = socket.create_connection(("127.0.0.1", {puerto}), timeout=3)
except OSError:
    print("SIN PUENTE: no hay servidor"); sys.exit(3)
print("CLIENTE:", c.recv(100).decode().strip())
nombre = input("tu nombre? ")
print("adios", nombre)
""")
open(os.path.join(app, "README.md"), "w").write(
    "# Chat\n\nPrimero arranca el servidor en otra terminal y déjalo abierto:\n\n```\npython3 server.py\n```\n\n"
    "Luego, en esta terminal:\n\n```\npython3 cliente.py\n```\n")
acceso = {"id": "chat", "titulo": "Chat", "carpeta": app, "lanzar": ["python3", os.path.join(app, "cliente.py")]}

pasos = ar.pasos_terminal(acceso)
mira(len(pasos) == 1 and ar.es_puente_linea(pasos[0][1]), f"un paso, y es el puente: {pasos}")
mira(ar.tiene_puente(acceso) and ar.es_de_terminal(acceso), "con puente → se abre en la terminal")
mira("puente" in ar._texto_pasos("Chat", pasos, "mi Terminal").lower(), "el aviso lo dice")

guion, _p = ar.guion_para(acceso, admin=False)
r = subprocess.run(["bash", guion], input="Papi\n\n", capture_output=True, text=True, timeout=60,
                   env=dict(os.environ, KIRA_VER_PUENTE="0"))
out = r.stdout
mira("puente encendido" in out, "el puente se enciende y Kira espera a que esté listo")
mira("CLIENTE: hola desde el puente" in out, "el programa arranca y habla con el puente")
mira("adios Papi" in out, "el programa te pregunta en la terminal")
time.sleep(0.5)
try:
    socket.create_connection(("127.0.0.1", puerto), timeout=1).close(); apagado = False
except OSError:
    apagado = True
mira(apagado, "al cerrar el programa, el puente se apaga")

# segunda vez (ya preparado: marca): el puente vuelve a arrancar
open(os.path.join(app, ar.MARCA), "w").close()
pasos2 = ar.pasos_terminal(acceso)
mira(len(pasos2) == 1 and ar.es_puente_linea(pasos2[0][1]), "ya preparado: el puente se arranca igual cada vez")

# un puente que se cae: lo dice
open(os.path.join(app, "server.py"), "w").write("import sys; print('error: falta el modelo'); sys.exit(1)\n")
os.remove(os.path.join(app, ar.MARCA))
guion, _p = ar.guion_para(acceso, admin=False)
r = subprocess.run(["bash", guion], input="x\n\n", capture_output=True, text=True, timeout=60)
mira("el puente se ha cerrado" in r.stdout and "falta el modelo" in r.stdout, "si el puente se cae, enseña por qué")

# puentes del sistema solo si están instalados
mira(ar._puente_sistema("ollama serve", which=lambda x: None) is None, "ollama no instalado: no")
mira(ar._puente_sistema("ollama serve", which=lambda x: "/usr/bin/" + x) == ["/usr/bin/ollama", "serve"],
     "ollama serve instalado: sí")
mira(ar._puente_sistema("ollama run llama3", which=lambda x: "/usr/bin/" + x) is None, "otra orden de ollama: no")

# en la terminal de Xubuntu, el puente se ve en OTRA ventana
lineas = ar._bash_puentes(which=lambda x: "/usr/bin/xfce4-terminal" if x == "xfce4-terminal" else None)
mira(any("Kira · puente" in l and "tail -n +1 -f" in l for l in lineas), "otra ventana de terminal para el puente")
lanzado = {}
ar.abrir_en_terminal(acceso, popen=lambda o, **k: lanzado.update(k) or type("P", (), {"pid": 1})(),
                     which=lambda x: "/usr/bin/" + x if x == "xfce4-terminal" else None, admin=False, subir=False)
mira(lanzado.get("env", {}).get("KIRA_VER_PUENTE") == "1", "la terminal de Xubuntu pide ver el puente")

# si la ÚNICA orden del README es «python3 servidor.py», ese servidor ES el programa (no un puente)
solo = os.path.join(T, "apps", "solo"); os.makedirs(solo)
open(os.path.join(solo, "servidor.py"), "w").write("print('hola')\n")
open(os.path.join(solo, "README.md"), "w").write("# Solo\n\n```\npython3 servidor.py\n```\n")
mira(not ar.tiene_puente({"id": "solo", "carpeta": solo, "lanzar": ["python3", os.path.join(solo, "otro.py")]}),
     "un servidor que es la única orden no es puente")

print(f"test_puente_apps: {ok} bien, {mal} mal")
sys.exit(1 if mal else 0)
