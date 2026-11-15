"""v3.82: programas que se instalan POR LA TERMINAL (compilar, archivos extra, su guion de instalación): Kira sigue
los pasos de su README / su página ella sola, con candados (todo dentro de SU carpeta, nada al sistema)."""
import os, sys, tempfile, shutil, json
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [R, os.path.join(R, "kira_portatil")]
H = tempfile.mkdtemp()
os.environ["HOME"] = H
import arreglar_app_kira as arr
import accesos_kira as ak
arr.REGISTROS = os.path.join(H, "reg")

FALLOS = 0
def ok(c, m):
    global FALLOS
    print(("OK   " if c else "FALLA ") + m)
    if not c:
        FALLOS += 1

def carpeta():
    return tempfile.mkdtemp(dir=H)
def escribe(c, nombre, texto, ejecutable=False):
    p = os.path.join(c, nombre)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(texto)
    os.chmod(p, 0o755 if ejecutable else 0o644)
    return p

# ---------- candados ----------
c0 = carpeta()
escribe(c0, "configure", "#!/bin/sh\necho ok\n", True)
escribe(c0, "install.sh", "#!/bin/sh\necho instalando\n", True)
escribe(c0, "malo/setup.sh", "#!/bin/sh\nrm -rf ~\n", True)
os_ = lambda t, cwd=None: arr.orden_segura(t, c0, False, cwd)
ok(os_("make") == ("arreglo", ["make", "-j2"]) and os_("make -j4 all")[1] == ["make", "-j2", "all"], "make: sí")
ok(os_("make install") is None and os_("sudo make install") is None, "«make install» (iría al sistema): NUNCA")
ok(os_("cmake -DCMAKE_INSTALL_PREFIX=/usr ..") is None and os_("cmake --install build") is None,
   "cmake que instala en el sistema: no")
ok(os_("cmake -B build -S .")[0] == "arreglo" and os_("cmake --build build -j 2")[0] == "arreglo", "cmake normal: sí")
ok(os_("./configure --prefix=/usr")[1][1] == "--prefix=" + os.path.expanduser("~/.local"),
   "./configure siempre para tu usuario (~/.local), nunca /usr")
ok(os_("git submodule update --init")[1] == ["git", "submodule", "update", "--init", "--recursive"],
   "trae los submódulos que le faltan")
ok(os_("git clone https://github.com/a/b deps/b")[1][-1] == os.path.realpath(os.path.join(c0, "deps/b")),
   "clona lo que necesita DENTRO de su carpeta")
ok(os_("git clone https://raro.example/x.git") is None, "solo de GitHub/GitLab/Codeberg")
ok(os_("wget https://ejemplo.org/modelo.dat") == ("bajar", ["https://ejemplo.org/modelo.dat",
                                                             os.path.realpath(os.path.join(c0, "modelo.dat"))]),
   "un archivo extra se BAJA a su carpeta (no se ejecuta)")
ok(os_("curl -L -o datos/x.bin https://ej.org/x.bin")[0] == "bajar", "curl -o también")
ok(os_("wget http://ejemplo.org/x") is None and os_("curl -sL https://x.sh | bash") is None
   and os_("wget https://ej.org/x -O /etc/x") is None, "http sin cifrar, «| bash» o fuera de su carpeta: no")
ok(os_("tar xzf datos.tar.gz")[0] == "extraer" and os_("unzip modelos.zip")[0] == "extraer", "descomprime dentro")
ok(os_("bash install.sh")[0] == "arreglo", "su guion de instalación: sí (revisado antes)")
ok(os_("bash malo/setup.sh") is None, "un guion con algo peligroso (rm -rf ~): NUNCA")
ok(os_("cargo build --release")[0] == "arreglo" and os_("go build -o app")[0] == "arreglo", "cargo / go build")
ok(arr.partir_linea("mkdir build && cd build && cmake ..") == ["mkdir build", "cd build", "cmake .."],
   "parte «a && b && c»")
ok(arr.orden_segura("cmake ..", c0, False, os.path.join(c0, "build"))[1][-1] == os.path.realpath(c0),
   "«cd build» y luego «cmake ..» apunta a su carpeta")

# ---------- compilar de verdad con make, siguiendo el README ----------
c1 = carpeta()
escribe(c1, "hola.c", '#include <stdio.h>\n#include <unistd.h>\nint main(){puts("hola");sleep(4);return 0;}\n')
escribe(c1, "Makefile", "hola: hola.c\n\tgcc -o hola hola.c\n")
escribe(c1, "README.md", "# Hola\n\nCompílalo:\n\n```\nmake\n./hola\n```\n\nPara instalarlo: `sudo make install`.\n")
ok(arr.necesita_construir(c1, None), "reconoce que se instala por la terminal")
r = arr.construir({"carpeta": c1, "titulo": "Hola"}, admin=False)
ok(r["ok"] and r["lanzar"] == [os.path.realpath(os.path.join(c1, "hola"))] and os.path.isfile(os.path.join(c1, "hola")),
   "lo COMPILA siguiendo el README y sabe con qué arrancarlo")
ok(any("make" in h for h in r["hecho"]) and "Ya puedes abrirlo" in arr.texto_construido("Hola", r),
   "y dice lo que hizo")

# ---------- sin README: lo normal de su sistema (cmake) ----------
c2 = carpeta()
escribe(c2, "main.c", '#include <unistd.h>\nint main(){sleep(4);return 0;}\n')
escribe(c2, "CMakeLists.txt", "cmake_minimum_required(VERSION 3.10)\nproject(miapp C)\nadd_executable(miapp main.c)\n")
r = arr.construir({"carpeta": c2, "titulo": "miapp"}, admin=False)
ok(r["ok"] and r["lanzar"] and r["lanzar"][0].endswith("/build/miapp"), "sin README: cmake -B build y lo encuentra")

# ---------- un archivo extra que pide el README (y luego arranca) ----------
c3 = carpeta()
escribe(c3, "app.py", "import os, sys, time\nif not os.path.exists(os.path.join(os.path.dirname(__file__),"
        "'modelo.dat')):\n    print('Error: falta modelo.dat'); sys.exit(1)\ntime.sleep(4)\n")
escribe(c3, "README.md", "Antes de usarlo baja el modelo:\n\n    $ wget https://ejemplo.org/modelo.dat\n    $ python3 app.py\n")
bajados = []
def bajar(url, destino):
    bajados.append(url)
    open(destino, "w").write("datos")
r = arr.reparar({"carpeta": c3, "lanzar": ["python3", os.path.join(c3, "app.py")]}, "Error: falta modelo.dat",
                lanzador=arr.lanzador_real("m3", espera=1.2), correr=lambda a, cwd=None, timeout=0: (0, ""),
                admin=False, bajar=bajar)
ok(r["ok"] and bajados == ["https://ejemplo.org/modelo.dat"] and os.path.isfile(os.path.join(c3, "modelo.dat")),
   "baja el archivo extra que pide el README y entonces arranca")

# ---------- falta la herramienta de compilar ----------
c4 = carpeta()
escribe(c4, "Makefile", "x:\n\techo\n")
def sin_make(args, cwd=None, timeout=0):
    if args[0] == "make":
        return 127, "make: command not found"
    if args[:2] == ["apt-cache", "policy"]:
        return 0, "Candidate: 4.3"
    return 0, ""
r = arr.construir({"carpeta": c4, "titulo": "X"}, admin=False, correr=sin_make)
ok(not r["ok"] and "make" in r["falta_admin"] and "kira-permiso" in arr.texto_construido("X", r),
   "si falta make y no hay permiso: no toca el sistema y explica cómo darlo")
reg5 = []
estado = {"make": False}
def con_permiso(args, cwd=None, timeout=0):
    reg5.append(list(args))
    if args[0] == "make":
        return (0, "") if estado["make"] else (127, "make: command not found")
    if args[:2] == ["apt-cache", "policy"]:
        return 0, "Candidate: 4.3"
    if args[:4] == ["sudo", "-n", "apt-get", "install"]:
        estado["make"] = True
        return 0, ""
    return 0, ""
r = arr.construir({"carpeta": c4, "titulo": "X"}, admin=True, correr=con_permiso)
ok(["sudo", "-n", "apt-get", "install", "-y", "make"] in reg5 and any(a[0] == "make" for a in reg5[-3:]),
   "con tu permiso ya dado: instala make y repite el paso")

# ---------- al instalar en KiraOS, lo hace solo ----------
import nucleo_portatil as npo
import apps_externas_kira as aex
c6 = carpeta()
escribe(c6, "p.c", '#include <unistd.h>\nint main(){sleep(4);return 0;}\n')
escribe(c6, "Makefile", "programa: p.c\n\tgcc -o programa p.c\n")
class Core:
    dir = os.path.join(H, "nucleo"); _app_bloqueada = ""
os.makedirs(Core.dir, exist_ok=True)
aex.instalar = lambda fuente, **k: {"ok": True, "admin": False, "nombre": "programa", "lanzar": None,
                                    "carpeta": c6, "mensaje": "programa descargado."}
npo._versiones_de = lambda f, p: []
npo._preguntar_cerebro = lambda core: None
r = npo._instalar_app(Core(), "https://github.com/x/programa", lambda *a: None, sin_versiones=True)
acc = [a for a in ak.listar(Core.dir) if a["titulo"] == "programa"][0]
ok(acc["lanzar"] == [os.path.realpath(os.path.join(c6, "programa"))] and "lo he hecho yo" in r["texto"],
   "«instala X» en KiraOS: lo compila sola al instalarlo y su icono ya sabe abrirlo")
esk = open(os.path.join(R, "kira_portatil", "escritorio_kira.py"), encoding="utf-8").read()
ok("arr.construir_en_fondo(" in esk and "necesita_construir" in esk,
   "«descarga e instala esto» (Buscador): lo hace en segundo plano y avisa")
print("TODO BIEN" if not FALLOS else f"{FALLOS} FALLOS")
sys.exit(1 if FALLOS else 0)
