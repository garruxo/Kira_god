# -*- coding: utf-8 -*-
"""
espacio_kira.py - El ESPACIO AISLADO de Kira en el portátil: una carpeta cerrada donde puede experimentar y probar
programas a su aire, SIN poder tocar su propio código, tus archivos ni el sistema.

Reglas (las del dueño):
  - Lo que haga aquí SE QUEDA aquí. Nada se aplica solo a la Kira de verdad: para eso, laboratorio + dos toques.
  - SIN RED por defecto (más seguro), y con LÍMITES de tiempo, memoria y tamaño (no llena el disco ni se cuelga).
  - Caja fuerte DE VERDAD si el portátil tiene firejail o bubblewrap (sin red, solo su carpeta). Si no, son límites
    que protegen de accidentes, no una caja fuerte — y se dice claro (`nivel` en el resultado).

Solo librería estándar. La lógica se prueba (tests/test_espacio.py): la orden de aislamiento con herramientas de
mentira, y ejecutar de verdad un programa sencillo con los límites.
"""
import argparse
import os
import resource
import shutil
import subprocess

BASE = os.environ.get("KIRA_ESPACIO", os.path.join(os.path.expanduser("~"), "kira_portatil", "espacio"))
TOPE_SEG = 30             # tiempo máximo por ejecución
MEM_MB = 768             # memoria máxima
FSIZE_MB = 50            # tamaño máximo de un archivo que escriba
MAX_MB = 500             # tope de todo el espacio (si se pasa, no deja ejecutar hasta limpiar)
_EXP = "_experimento.py"


def preparar(base=None):
    base = base or BASE
    os.makedirs(base, exist_ok=True)
    return base


def tamano_mb(base=None):
    base = base or BASE
    total = 0
    for raiz, _, archivos in os.walk(base):
        for a in archivos:
            try:
                total += os.path.getsize(os.path.join(raiz, a))
            except OSError:
                pass
    return total / (1024 * 1024)


def listar(base=None):
    base = base or BASE
    if not os.path.isdir(base):
        return []
    return sorted(os.listdir(base))


def limpiar(base=None):
    """Vacía el espacio (lo deja como nuevo). No toca nada de fuera."""
    base = base or BASE
    if not os.path.isdir(base):
        return True
    for n in os.listdir(base):
        p = os.path.join(base, n)
        try:
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        except OSError:
            pass
    return True


def _limites():
    """Se aplica en el proceso hijo ANTES de ejecutar: límites de CPU, memoria, tamaño de archivo y nº de archivos."""
    def pre():
        try:
            os.setsid()
        except OSError:
            pass
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (TOPE_SEG, TOPE_SEG + 2))
        except (ValueError, OSError):
            pass
        try:
            b = MEM_MB * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (b, b))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_FSIZE, (FSIZE_MB * 1024 * 1024, FSIZE_MB * 1024 * 1024))
        except (ValueError, OSError):
            pass
    return pre


def orden_aislada(base, guion, red=False, which=shutil.which):
    """Construye la orden para ejecutar `guion` aislado. Devuelve (orden, nivel_texto). Usa firejail o bubblewrap si
    están; si no, ejecución básica (solo con los límites de arriba)."""
    if which("firejail"):
        o = ["firejail", "--quiet", "--private=" + base, "--whitelist=" + base]
        o += ([] if red else ["--net=none"])
        o += ["python3", "-I", guion]
        return o, ("caja fuerte (firejail: solo su carpeta" + (", con red" if red else ", sin red") + ")")
    if which("bwrap"):
        o = ["bwrap", "--die-with-parent", "--unshare-pid"]
        o += ([] if red else ["--unshare-net"])
        for d in ("/usr", "/bin", "/lib", "/lib64", "/etc"):
            if os.path.exists(d):
                o += ["--ro-bind", d, d]
        o += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--bind", base, base, "--chdir", base,
              "python3", "-I", os.path.join(base, os.path.basename(guion))]
        return o, ("caja fuerte (bubblewrap: solo su carpeta" + (", con red" if red else ", sin red") + ")")
    return ["python3", "-I", guion], "básico (límites de tiempo/memoria; la red NO está bloqueada)"


def ejecutar(codigo=None, archivo=None, entrada="", red=False, base=None, correr=None, which=shutil.which):
    """Ejecuta código Python DENTRO del espacio aislado. `codigo` (texto) o `archivo` (ya dentro del espacio).
    Devuelve {ok, salida, error, nivel, cortado}. Nunca toca nada de fuera del espacio."""
    base = preparar(base)
    if tamano_mb(base) > MAX_MB:
        return {"ok": False, "salida": "", "error": f"El espacio ya ocupa más de {MAX_MB} MB. Límpialo antes de seguir.",
                "nivel": "", "cortado": False}
    if codigo is not None:
        guion = os.path.join(base, _EXP)
        with open(guion, "w", encoding="utf-8") as f:
            f.write(codigo)
    elif archivo:
        guion = archivo if os.path.isabs(archivo) else os.path.join(base, archivo)
        # candado: el archivo tiene que estar DENTRO del espacio
        if os.path.commonpath([os.path.realpath(base), os.path.realpath(guion)]) != os.path.realpath(base):
            return {"ok": False, "salida": "", "error": "Solo puedo ejecutar archivos de dentro del espacio.",
                    "nivel": "", "cortado": False}
    else:
        return {"ok": False, "salida": "", "error": "No me has dado código ni archivo.", "nivel": "", "cortado": False}

    orden, nivel = orden_aislada(base, guion, red=red, which=which)
    correr = correr or subprocess.run
    try:
        r = correr(orden, cwd=base, input=entrada, capture_output=True, text=True, timeout=TOPE_SEG,
                   preexec_fn=_limites())
        return {"ok": r.returncode == 0, "salida": (r.stdout or "")[-20000:], "error": (r.stderr or "")[-8000:],
                "nivel": nivel, "cortado": False}
    except subprocess.TimeoutExpired:
        return {"ok": False, "salida": "", "error": f"Se pasó del tiempo ({TOPE_SEG}s) y lo paré.",
                "nivel": nivel, "cortado": True}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "salida": "", "error": f"No pude ejecutar: {e}", "nivel": nivel, "cortado": False}


def estado(base=None):
    base = base or BASE
    _, nivel = orden_aislada(base, "x.py")
    return {"carpeta": base, "ocupado_mb": round(tamano_mb(base), 1), "tope_mb": MAX_MB,
            "archivos": listar(base), "aislamiento": nivel}


def main(argv=None):
    ap = argparse.ArgumentParser(description="El espacio aislado de Kira")
    ap.add_argument("--ejecutar", metavar="ARCHIVO", help="ejecuta un archivo que esté dentro del espacio")
    ap.add_argument("--con-red", action="store_true", help="permite internet en la prueba (por defecto NO)")
    ap.add_argument("--limpiar", action="store_true")
    ap.add_argument("--estado", action="store_true")
    a = ap.parse_args(argv)
    preparar()
    if a.limpiar:
        limpiar(); print("Espacio vaciado."); return
    if a.estado or not (a.ejecutar):
        import json; print(json.dumps(estado(), ensure_ascii=False, indent=1)); return
    r = ejecutar(archivo=a.ejecutar, red=a.con_red)
    print(f"[aislamiento: {r['nivel']}]")
    if r["salida"]:
        print(r["salida"])
    if r["error"]:
        print("[errores]\n" + r["error"])


if __name__ == "__main__":
    main()
