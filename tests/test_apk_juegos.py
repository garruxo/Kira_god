# -*- coding: utf-8 -*-
"""La app de verdad de un juego: el proyecto que se sube, la receta de GitHub y todo el camino con un GitHub falso."""
import ast
import base64
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import apk_juegos_kira as apk
import inicio_kira as ik
import juegos_kira as jk
import web_juegos_kira as w

fallos = 0


def ok(c, msg):
    global fallos
    print(("[OK] " if c else "[FALLA] ") + msg)
    if not c:
        fallos += 1


TOKEN = "ghp_" + "a1B2" * 9
COD = jk.JUEGOS[0]["codigo"]

# ---------- nombres, clave y orden ----------
ok(apk.id_de("¡Pong contra Kira!") == "pong_contra_kira" and apk.id_de("3 en raya") == "j3_en_raya", "nombres válidos")
ok(apk.es_token(TOKEN) and not apk.es_token("hola") and not apk.es_token("sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxx"),
   "reconoce una clave de GitHub")
ok(ik.ocultar_secretos("config github: " + TOKEN) == "config github: (oculto)" and TOKEN not in ik.ocultar_secretos(
    "mi clave es " + TOKEN), "la clave de GitHub no se guarda en el historial")
ok(w.pedido_app("conviértelo en una app de verdad") == "apk" and w.pedido_app("haz un apk del juego") == "apk",
   "«conviértelo en una app de verdad» pide el APK")

# ---------- el proyecto ----------
jid, arch = apk.proyecto(COD, "Rompeladrillos", 3, {"heroe": b"\x89PNG.."})
base = "juegos/rompeladrillos/"
ok(jid == "rompeladrillos" and {base + x for x in ("main.py", "juego.py", "motor_juegos_kira.py", "buildozer.spec",
                                                   "icono.png", "sprites/heroe.png")} <= set(arch), "archivos del juego")
espec = arch[base + "buildozer.spec"].decode()
ok("package.name = rompeladrillos" in espec and "android.numeric_version = 3" in espec and "version = 1.3" in espec
   and "requirements = python3,kivy" in espec, "buildozer.spec con la versión que sube")
ast.parse(arch[base + "main.py"].decode())
ok(b"buscar_juego" in arch[base + "main.py"] and arch[base + "icono.png"][:8] == b"\x89PNG\r\n\x1a\n",
   "el reproductor y el icono")
rb = apk.repo_base()
import yaml
flujo = yaml.safe_load(rb[".github/workflows/" + apk.FLUJO])
ok("juego" in flujo[True]["workflow_dispatch"]["inputs"] and flujo["permissions"]["contents"] == "write",
   "la receta de GitHub se lanza a mano con el nombre del juego")
pasos = " ".join(str(p) for p in flujo["jobs"]["apk"]["steps"])
ok("${{ inputs.juego }}" not in pasos and "gh release create" in pasos, "el nombre entra por variable (no en el código)")
with tempfile.TemporaryDirectory() as d:
    apk.escribir(d, rb)
    r = subprocess.run(["bash", "-n", os.path.join(d, "compilar_juego.sh")], capture_output=True, text=True)
    ok(r.returncode == 0, "compilar_juego.sh está bien escrito " + r.stderr[:200])
    r = subprocess.run(["bash", os.path.join(d, "compilar_juego.sh"), "compilar", "juegos/../../etc"],
                       capture_output=True, text=True)
    ok(r.returncode != 0, "no compila carpetas raras")


# ---------- todo el camino con un GitHub falso ----------
class GitHubFalso:
    def __init__(self, fallar=False):
        self.repo = False
        self.archivos, self.puts, self.lanzado, self.consultas, self.fallar = {}, [], None, 0, fallar

    def __call__(self, metodo, url, token, cuerpo=None):
        ruta = url.replace(apk.API, "")
        if token != TOKEN:
            return 401, {"message": "Bad credentials"}
        if ruta == "/user":
            return 200, {"login": "garruxo"}
        if ruta == "/repos/garruxo/kira-juegos":
            return (200, {"default_branch": "main", "private": False}) if self.repo else (404, {})
        if ruta == "/user/repos" and metodo == "POST":
            self.repo = True
            return 201, {}
        if "/contents/" in ruta:
            p = ruta.split("/contents/", 1)[1].split("?")[0]
            if metodo == "GET":
                return (200, {"sha": apk.blob_sha(self.archivos[p])}) if p in self.archivos else (404, {})
            self.archivos[p] = base64.b64decode(cuerpo["content"])
            self.puts.append(p)
            return 201, {}
        if ruta.endswith("/dispatches"):
            self.lanzado = cuerpo
            return 204, {}
        if "/actions/runs?" in ruta:
            return 200, {"workflow_runs": [{"id": 7, "display_title": "Juego x " + self.lanzado["inputs"]["marca"]}]}
        if ruta.endswith("/actions/runs/7"):
            self.consultas += 1
            if self.consultas < 3:
                return 200, {"status": "in_progress"}
            return 200, {"status": "completed", "conclusion": "failure" if self.fallar else "success"}
        if ruta.endswith("/runs/7/jobs"):
            return 200, {"jobs": [{"id": 70}]}
        if ruta.endswith("/check-runs/70/annotations"):
            return 200, [{"annotation_level": "failure", "message": "No se pudo compilar: falta algo"}]
        return 404, {"message": "no"}


with tempfile.TemporaryDirectory() as d:
    falso = GitHubFalso()
    gh = apk.GitHub(TOKEN, http=falso, dormir=lambda s: None)
    reg = apk.Registro(os.path.join(d, "apk.json"))
    avances = []
    r = apk.compilar(gh, COD, "Rompeladrillos", reg, progreso=lambda f, t: avances.append((f, t)))
    ok(falso.repo and ".github/workflows/compilar_juego.yml" in falso.archivos and base + "juego.py" in falso.archivos,
       "crea el repositorio y sube la receta y el juego")
    ok(falso.lanzado["inputs"]["juego"] == "rompeladrillos" and falso.lanzado["ref"] == "main", "pide compilarlo")
    ok(r["url_apk"] == "https://github.com/garruxo/kira-juegos/releases/download/juego-rompeladrillos/rompeladrillos.apk"
       and r["n"] == 1, "el APK queda en Releases")
    ok(avances and all(0 <= f < 1 for f, _ in avances) and any("GitHub" in t for _, t in avances), "va contando cómo va")
    antes = len(falso.puts)
    falso.consultas = 0
    r2 = apk.compilar(gh, COD, "Rompeladrillos", apk.Registro(os.path.join(d, "apk.json")))
    nuevos = falso.puts[antes:]
    ok(r2["n"] == 2 and nuevos == [base + "buildozer.spec"], f"la 2.ª vez solo sube lo cambiado (la versión): {nuevos}")
    falso2 = GitHubFalso(fallar=True)
    falso2.repo = True
    try:
        apk.compilar(apk.GitHub(TOKEN, http=falso2, dormir=lambda s: None), COD, "Rompeladrillos",
                     apk.Registro(os.path.join(d, "otro.json")))
        ok(False, "un fallo de GitHub debería avisar")
    except apk.ApkError as e:
        ok("falta algo" in str(e) and "actions/runs/7" in str(e), "si GitHub falla, dice por qué y dónde mirarlo")
    try:
        apk.compilar(apk.GitHub("ghp_" + "z" * 36, http=GitHubFalso(), dormir=lambda s: None), COD, "X",
                     apk.Registro(os.path.join(d, "x.json")))
        ok(False, "una clave mala debería avisar")
    except apk.ApkError as e:
        ok("no acepta tu clave" in str(e), "clave rechazada: se dice claro")
    try:
        apk.compilar(gh, COD, "Rompeladrillos", reg, cancelado=lambda: True)
        ok(False, "cancelado")
    except apk.ApkError as e:
        ok("Cancelado" in str(e), "se puede cancelar")

src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kira_god.py"), encoding="utf-8").read()
ok('startswith("config github:")' in src and src.index('startswith("config github:")') < src.index(
    "self.registrar_buffer_volatil(command)"), "la clave de GitHub no pasa por el búfer ni por el registro")

print("\nTODO BIEN" if not fallos else f"\n{fallos} FALLOS")
sys.exit(1 if fallos else 0)
