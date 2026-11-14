# -*- coding: utf-8 -*-
"""
actualizar_kira.py - v3.06: «implementa las mejoras» / «actualízate» / «hay mejoras nuevas».

Las mejoras del CÓDIGO de Kira las prepara Claude, se prueban y se suben a GitHub (garruxo/Kira_god). Antes había
que ponerlas a mano en el portátil (`git pull`); ahora, en KiraOS, se lo pides a Kira y lo hace ella:
  · mira si hay mejoras nuevas (git fetch) y te dice cuáles (el título de cada una);
  · con «implementa / aplica / instala las mejoras» o «actualízate», las pone (git pull --ff-only: solo avanza, nunca
    mezcla ni borra cambios tuyos; si algo lo impide, lo dice y no toca nada);
  · te dice qué versión tenías y cuál tienes, y que reinicies para usarlas;
  · si esta vez cambió algo de la instalación que pide tu contraseña, te dice qué lanzar (p. ej. «bash solo» + Tab).
Solo se hace cuando TÚ lo pides (nunca sola). En el móvil no hay repositorio: allí las mejoras llegan como APK nuevo.
Puro y testeable: `correr(args, espera)` -> (codigo, salida, error) se inyecta.
"""
import os
import re
import subprocess
import unicodedata

RAIZ = os.path.dirname(os.path.abspath(__file__))
MAX_LISTA = 12

# lo que pide tu contraseña y no puede hacer Kira sola: archivo cambiado -> qué lanzar en la terminal
PASOS_A_MANO = {
    "kira_portatil/solo_kira.sh": "«bash solo» + Tab (dentro de kira_god/kira_portatil): el arranque solo con Kira",
    "kira_portatil/arreglar_inicio.sh": "«bash arr» + Tab (dentro de kira_god/kira_portatil): la entrada automática",
    "kira_portatil/activar_fuera.sh": "«bash act» + Tab (dentro de kira_god/kira_portatil): Kira fuera de casa",
}


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", t)
    return re.sub(r"\s+", " ", t).strip(" .!¡?¿")


_PONER = re.compile(
    r"^(?:implementa|aplica|instala|pon|mete|carga|baja|descarga|actualiza)(?:me|te|las)?\s+"
    r"(?:las\s+|tus\s+|todas\s+las\s+|esas\s+|estas\s+)?(?:nuevas\s+|ultimas\s+)?(?:mejoras|actualizaciones|"
    r"novedades)(?:\s+(?:nuevas|pendientes|de\s+claude|de\s+github|del\s+codigo))?$|"
    r"^actualiza(?:te)?(?:\s+(?:kira|kiraos|kira\s+os|el\s+sistema|tu\s+codigo|el\s+codigo))?$|"
    r"^ponte\s+al\s+dia$|^actualizacion$")
_MIRAR = re.compile(
    r"^(?:hay|tienes|tengo)\s+(?:alguna\s+)?(?:mejoras?|actualizaci(?:on|ones)|novedades)(?:\s+(?:nuevas?|pendientes))?$|"
    r"^(?:que\s+)?(?:mejoras|actualizaciones|novedades)\s+(?:hay|tienes|pendientes|nuevas)$|"
    r"^que\s+(?:mejoras|actualizaciones|novedades)\s+(?:hay|tienes)(?:\s+(?:nuevas|pendientes))?$|"
    r"^(?:busca|mira\s+si\s+hay|comprueba\s+si\s+hay)\s+(?:mejoras|actualizaciones|novedades)(?:\s+nuevas)?$")


def es_orden(texto):
    """'poner' (implementa/actualízate), 'mirar' (¿hay mejoras?) o None."""
    t = _norm(texto)
    if _PONER.match(t):
        return "poner"
    if _MIRAR.match(t):
        return "mirar"
    return None


def _correr_real(args, espera=120):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=espera)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "no está git"
    except subprocess.TimeoutExpired:
        return 124, "", "tardó demasiado (¿internet lento?)"


def version_de(raiz=RAIZ):
    try:
        with open(os.path.join(raiz, "version_kira.py"), encoding="utf-8") as f:
            m = re.search(r'VERSION\s*=\s*"([^"]+)"', f.read())
        return m.group(1) if m else "?"
    except OSError:
        return "?"


def hay_repo(raiz=RAIZ):
    return os.path.isdir(os.path.join(raiz, ".git"))


def _limpio(titulo):
    t = re.sub(r"\s+", " ", str(titulo or "")).strip()
    return t[:140] + ("…" if len(t) > 140 else "")


_PERMISOS = re.compile(r"permis|permission|insufficient|denegado|denied", re.I)


def texto_permisos(raiz=RAIZ):
    """v3.38: git no puede escribir en mi carpeta porque hay archivos del administrador (de algún «sudo»). Puro salvo
    leer el nombre del usuario."""
    import getpass
    try:
        usuario = getpass.getuser()
    except Exception:                                   # noqa: BLE001
        usuario = "tu_usuario"
    casa = os.path.expanduser("~")
    carpeta = os.path.relpath(raiz, casa) if raiz.startswith(casa + os.sep) else raiz
    return (f"No puedo escribir en mi propia carpeta: hay archivos que son del administrador (seguramente de algún "
            f"comando que se lanzó con sudo). Arréglalo UNA vez en la Terminal: escribe  cd  (Intro) y luego  "
            f"sudo chown -R {usuario} {carpeta}  (Intro; te pedirá TU contraseña). Después dime otra vez «implementa "
            f"las mejoras». No he cambiado nada.")


def actualizar(raiz=RAIZ, poner=True, correr=None):
    """Mira (y si `poner`, pone) las mejoras de GitHub. Devuelve {"ok", "texto", "nuevas", "antes", "despues"}."""
    correr = correr or _correr_real
    antes = version_de(raiz)
    if not hay_repo(raiz):
        return {"ok": False, "texto": "Aquí no tengo mi código como repositorio, así que no puedo ponerme las mejoras "
                                      "yo sola.", "nuevas": [], "antes": antes, "despues": antes}
    g = ["git", "-C", raiz]
    c, _o, e = correr(g + ["fetch", "--quiet", "origin"], 180)
    if c != 0 and _PERMISOS.search(e or ""):
        return {"ok": False, "texto": texto_permisos(raiz), "nuevas": [], "antes": antes, "despues": antes,
                "permisos": True}
    if c != 0:
        return {"ok": False, "texto": "No he podido mirar si hay mejoras: " + (_limpio(e.splitlines()[0]) if e.strip()
                                      else "no contesta GitHub") + ". ¿Hay internet?", "nuevas": [],
                "antes": antes, "despues": antes}
    c, rama, _e = correr(g + ["rev-parse", "--abbrev-ref", "HEAD"], 30)
    rama = (rama or "").strip() or "main"
    if rama == "HEAD":
        rama = "main"
    c, log, _e = correr(g + ["log", "--format=%s", f"HEAD..origin/{rama}"], 30)
    nuevas = [_limpio(x) for x in (log or "").splitlines() if x.strip()]
    if not nuevas:
        return {"ok": True, "texto": f"Ya tengo todas las mejoras: soy la versión {antes}.", "nuevas": [],
                "antes": antes, "despues": antes}
    lista = "\n".join("- " + x for x in nuevas[:MAX_LISTA]) + (
        f"\n- …y {len(nuevas) - MAX_LISTA} más" if len(nuevas) > MAX_LISTA else "")
    if not poner:
        return {"ok": True, "texto": f"Hay {len(nuevas)} mejora(s) nuevas (yo soy la versión {antes}):\n{lista}\n"
                                     "Dime «implementa las mejoras» y me las pongo.", "nuevas": nuevas,
                "antes": antes, "despues": antes}
    c, viejo, _e = correr(g + ["rev-parse", "HEAD"], 30)
    viejo = (viejo or "").strip()
    c, _o, e = correr(g + ["pull", "--ff-only", "--quiet", "origin", rama], 300)
    if c != 0 and _PERMISOS.search(e or ""):
        return {"ok": False, "texto": texto_permisos(raiz), "nuevas": nuevas, "antes": antes, "despues": antes,
                "permisos": True}
    if c != 0:
        motivo = _limpio((e or "").strip().splitlines()[0] if (e or "").strip() else "sin motivo")
        extra = (" Parece que hay archivos cambiados a mano en el portátil; no los toco. Dímelo y miramos cuáles."
                 if re.search(r"local changes|overwritten|diverg|not possible to fast-forward", e or "", re.I) else "")
        return {"ok": False, "texto": f"No he podido ponerme las mejoras: {motivo}.{extra} No he cambiado nada.",
                "nuevas": nuevas, "antes": antes, "despues": antes}
    despues = version_de(raiz)
    c, cambiados, _e = correr(g + ["diff", "--name-only", f"{viejo}..HEAD"], 30) if viejo else (1, "", "")
    pasos = [v for k, v in PASOS_A_MANO.items() if k in (cambiados or "").splitlines()]
    texto = (f"[OK] Me he puesto {len(nuevas)} mejora(s) (versión {antes} → {despues}):\n{lista}\n"
             "Para que se pongan en marcha, reinicia el portátil (menú K ▸ Reiniciar).")
    if pasos:
        texto += ("\nOjo: esta vez también cambió algo que pide tu contraseña y no puedo hacerlo yo. Antes de "
                  "reiniciar, abre una terminal y lanza " + "; y ".join(pasos) + ".")
    return {"ok": True, "texto": texto, "nuevas": nuevas, "antes": antes, "despues": despues}
