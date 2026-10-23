# -*- coding: utf-8 -*-
"""
apk_juegos_kira.py - Tus juegos de Kira como APP DE VERDAD (un APK que se instala solo, sin Kira), compilada en
GitHub igual que la propia Kira.

  1. Una vez: «config github: TU_CLAVE» (una clave «classic» de GitHub con los permisos public_repo y workflow).
  2. «Kira, conviértelo en una app de verdad» (con el juego abierto o recién jugado):
       - crea (si no está) tu repositorio público «kira-juegos» y le pone la receta de compilar;
       - sube el juego a juegos/<nombre>/ (el motor, tu juego, sus dibujos, un reproductor con Kivy y su buildozer.spec);
       - pide a GitHub que lo compile (15-30 minutos la primera vez; luego menos) y va mirando cómo va;
       - al terminar baja el APK a Descargas/Kira: ábrelo desde Archivos e instálalo.
  Cada juego firma siempre con la MISMA firma (se crea la primera vez y se guarda en el repositorio), así una versión
  nueva del juego se instala encima de la anterior.

Lógica pura (sin Kivy ni Android): la red entra por una función, así se prueba en el PC con un GitHub falso.
"""
import hashlib
import json
import os
import re
import time
import unicodedata

REPO = "kira-juegos"
FLUJO = "compilar_juego.yml"
API = "https://api.github.com"
ESPERA_MAX = 75 * 60            # segundos que se espera a GitHub como mucho
AQUI = os.path.dirname(os.path.abspath(__file__))


class ApkError(RuntimeError):
    pass


def _plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def id_de(titulo):
    """'¡Pong contra Kira!' -> 'pong_contra_kira' (vale como carpeta y como nombre de paquete de Android)."""
    t = re.sub(r"[^a-z0-9]+", "_", _plano(titulo)).strip("_")[:40] or "juego"
    return t if t[0].isalpha() else "j" + t[:39]


def es_token(t):
    t = str(t or "").strip()
    return bool(re.fullmatch(r"(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|gho_[A-Za-z0-9]{30,})", t))


# =====================================================================================
#  EL PROYECTO QUE SE SUBE
# =====================================================================================
REPRODUCTOR = r'''# -*- coding: utf-8 -*-
"""Reproductor de un juego de Kira (lo genera Kira: apk_juegos_kira.py). El juego está en juego.py."""
import os
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Mesh, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget

import motor_juegos_kira as mj

AQUI = os.path.dirname(os.path.abspath(__file__))
Window.clearcolor = (0.06, 0.09, 0.16, 1)


class Lienzo(Widget):
    def __init__(self, juego, **kw):
        super().__init__(**kw)
        self.juego, self._textos, self._imgs, self._previo = juego, {}, {}, None

    def escala(self):
        g = self.juego
        s = min(self.width / g.ancho, self.height / g.alto)
        return s, self.x + (self.width - g.ancho * s) / 2, self.y + (self.height - g.alto * s) / 2

    def a_juego(self, x, y):
        s, ox, oy = self.escala()
        return (x - ox) / s, (y - oy) / s

    def textura(self, texto, tam):
        clave = (texto, tam)
        if clave not in self._textos:
            if len(self._textos) > 200:
                self._textos.clear()
            lb = CoreLabel(text=texto, font_size=tam)
            lb.refresh()
            self._textos[clave] = lb.texture
        return self._textos[clave]

    def imagen(self, nombre):
        if nombre not in self._imgs:
            ruta = os.path.join(AQUI, "sprites", str(nombre) + ".png")
            try:
                from kivy.core.image import Image as CoreImage
                self._imgs[nombre] = CoreImage(ruta).texture if os.path.isfile(ruta) else None
            except Exception:
                self._imgs[nombre] = None
        return self._imgs[nombre]

    def dibujar(self):
        g = self.juego
        if self.width < 10:
            return
        s, ox, oy = self.escala()
        self.canvas.clear()
        with self.canvas:
            Color(*mj.color(g.fondo))
            Rectangle(pos=(ox, oy), size=(g.ancho * s, g.alto * s))
            for forma, x, y, w, h, col, texto, tam, puntos in g.dibujo():
                Color(*col)
                if forma == "rect":
                    Rectangle(pos=(ox + x * s, oy + y * s), size=(w * s, h * s))
                elif forma == "circulo":
                    Ellipse(pos=(ox + (x - w / 2) * s, oy + (y - h / 2) * s), size=(w * s, h * s))
                elif forma == "linea" and len(puntos) >= 2:
                    Line(points=[v for px, py in puntos for v in (ox + px * s, oy + py * s)], width=max(1.0, tam * s / 2))
                elif forma == "poligono" and len(puntos) >= 3:
                    vs = [ox + x * s, oy + y * s, 0, 0]
                    for px, py in puntos + puntos[:1]:
                        vs += [ox + px * s, oy + py * s, 0, 0]
                    Mesh(vertices=vs, indices=list(range(len(vs) // 4)), mode="triangle_fan")
                elif forma == "imagen":
                    tex = self.imagen(texto)
                    if tex is not None:
                        Color(1, 1, 1, col[3])
                        Rectangle(texture=tex, pos=(ox + x * s, oy + y * s), size=(w * s, h * s))
                    else:
                        Color(col[0] * 0.6, col[1] * 0.7, col[2] * 0.8, 0.5)
                        Rectangle(pos=(ox + x * s, oy + y * s), size=(w * s, h * s))
                elif forma == "texto" and texto:
                    tx = self.textura(texto, max(8, int(tam * s)))
                    Rectangle(texture=tx, pos=(ox + x * s, oy + y * s), size=tx.size)

    def on_touch_down(self, t):
        if self.collide_point(*t.pos):
            self._previo = self.a_juego(t.x, t.y)
            self.juego.tocar(*self._previo)
            return True
        return super().on_touch_down(t)

    def on_touch_move(self, t):
        if self._previo is not None:
            x, y = self.a_juego(t.x, t.y)
            self.juego.mover_dedo(x, y, x - self._previo[0], y - self._previo[1])
            if abs(x - self._previo[0]) + abs(y - self._previo[1]) > 25:
                self._previo = (x, y)
            return True
        return False

    def on_touch_up(self, t):
        if self._previo is not None:
            self._previo = None
            self.juego.soltar(*self.a_juego(t.x, t.y))
            return True
        return False


class JuegoApp(App):
    def build(self):
        raiz = BoxLayout(orientation="vertical")
        arriba = BoxLayout(size_hint_y=None, height=dp(48), padding=(dp(8), dp(4)), spacing=dp(6))
        self.marcador = Label(text="", font_size=sp(14), halign="left", valign="middle", shorten=True)
        self.marcador.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        arriba.add_widget(self.marcador)
        try:
            import juego
            clase = mj.buscar_juego(vars(juego))
            if clase is None:
                raise RuntimeError("el programa no define ningún juego (una clase que herede de Juego)")
            self.juego = clase()
            self.title = self.juego.titulo
        except Exception as e:
            self.juego = None
            self.marcador.text = f"No arranca: {type(e).__name__}: {e}"
            raiz.add_widget(arriba)
            raiz.add_widget(Label(text=traceback.format_exc()[-800:], font_size=sp(11)))
            return raiz
        for texto, accion in (("Pausa", lambda *_: self.juego.pausar()), ("Otra vez", lambda *_: self.otra())):
            arriba.add_widget(Button(text=texto, size_hint_x=None, width=dp(92), on_release=accion))
        raiz.add_widget(arriba)
        self.lienzo = Lienzo(self.juego)
        raiz.add_widget(self.lienzo)
        self.marcador.text = self.juego.instrucciones or self.juego.titulo
        Clock.schedule_interval(self.paso, 1 / 60.0)
        return raiz

    def otra(self):
        self.juego.reiniciar()
        self.juego.estado = "jugando"

    def paso(self, dt):
        try:
            self.juego.paso(dt)
        except Exception as e:
            self.marcador.text = f"Error en el juego: {type(e).__name__}: {e}"
            return False
        self.marcador.text = self.juego.marcador()
        self.lienzo.dibujar()


if __name__ == "__main__":
    JuegoApp().run()
'''

ESPEC = """[app]
title = {titulo}
package.name = {id}
package.domain = org.kirajuegos
source.dir = .
source.include_exts = py,png
source.exclude_dirs = bin, .buildozer
version = 1.{n}
requirements = python3,kivy
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icono.png
android.presplash_color = #0f172a
android.api = 33
android.minapi = 24
android.numeric_version = {n}
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = False
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 0
build_dir = {build_dir}
"""

COMPILAR = r"""#!/usr/bin/env bash
# Receta de Kira para compilar un juego (la usa .github/workflows/compilar_juego.yml).
#   bash compilar_juego.sh firma                 -> la firma fija de tus juegos (la crea la primera vez)
#   bash compilar_juego.sh compilar juegos/<id>  -> compila, firma y deja salida/<id>.apk
set -uo pipefail
RAIZ=$(cd "$(dirname "$0")" && pwd)
case "${1:-}" in
  firma)
    mkdir -p "$RAIZ/firma" ~/.android
    if [ ! -f "$RAIZ/firma/juegos.keystore" ]; then
      keytool -genkeypair -keystore "$RAIZ/firma/juegos.keystore" -storepass android -alias androiddebugkey \
        -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Juegos de Kira,O=Kira,C=ES" || exit 1
      echo "Firma nueva creada (se guarda en el repositorio para las próximas veces)."
    fi
    cp "$RAIZ/firma/juegos.keystore" ~/.android/debug.keystore
    ;;
  compilar)
    DIR="${2:-}"
    if ! [[ "$DIR" =~ ^juegos/[a-z][a-z0-9_]{0,39}$ ]] || [ ! -f "$RAIZ/$DIR/buildozer.spec" ]; then
      echo "::error title=Juego::No encuentro el juego «$DIR»"; exit 1
    fi
    ID=$(basename "$DIR")
    rm -rf ~/.kira_build/android/app            # (la carpeta de compilar se comparte: sin restos de otro juego)
    cd "$RAIZ/$DIR"
    yes | buildozer -v android debug > "$RAIZ/compilacion.log" 2>&1; rc=${PIPESTATUS[1]}
    tail -n 40 "$RAIZ/compilacion.log"
    if [ "$rc" -ne 0 ]; then
      grep -E "Error|ERROR|error:|Traceback|FAILED" "$RAIZ/compilacion.log" | tail -n 12 | tr '\n' ' ' | cut -c1-3500 \
        | sed 's/^/::error title=No se pudo compilar el juego::/'
      exit "$rc"
    fi
    APK=$(ls bin/*.apk | head -1)
    SIGNER=$(ls ~/.buildozer/android/platform/android-sdk/build-tools/*/apksigner \
                /usr/local/lib/android/sdk/build-tools/*/apksigner 2>/dev/null | sort -V | tail -1)
    if [ -z "$SIGNER" ]; then echo "::error title=Firma::No encuentro apksigner"; exit 1; fi
    "$SIGNER" sign --ks ~/.android/debug.keystore --ks-pass pass:android --ks-key-alias androiddebugkey \
      --key-pass pass:android "$APK" || exit 1
    mkdir -p "$RAIZ/salida"
    cp "$APK" "$RAIZ/salida/$ID.apk"
    echo "::notice title=Listo::$ID.apk ($(du -h "$RAIZ/salida/$ID.apk" | cut -f1))"
    ;;
  *) echo "uso: compilar_juego.sh firma | compilar juegos/<id>"; exit 1 ;;
esac
"""

FLUJO_YML = """# Compila un juego de Kira y lo publica como APK (lo lanza Kira con tu clave; también a mano en Actions).
name: Compilar juego
run-name: "Juego ${{ inputs.juego }} ${{ inputs.marca }}"

on:
  workflow_dispatch:
    inputs:
      juego:
        description: "Nombre de la carpeta en juegos/"
        required: true
      marca:
        description: "Marca de Kira para encontrar esta compilación"
        required: false
        default: ""

permissions:
  contents: write

concurrency:
  group: compilar-juegos
  cancel-in-progress: false

jobs:
  apk:
    runs-on: ubuntu-24.04
    timeout-minutes: 120
    env:
      JUEGO: ${{ inputs.juego }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"
      - name: Dependencias del sistema
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip autoconf libtool pkg-config zlib1g-dev libncurses5-dev \\
            libncursesw5-dev libtinfo6 cmake libffi-dev libltdl-dev libssl-dev automake autopoint gettext
      - name: Buildozer
        run: pip install buildozer setuptools cython==0.29.34
      - name: Recuperar lo ya descargado y compilado (acelera mucho)
        uses: actions/cache/restore@v4
        with:
          path: |
            ~/.buildozer
            ~/.kira_build
          key: juegos-${{ runner.os }}-v1-${{ github.run_id }}
          restore-keys: juegos-${{ runner.os }}-v1-
      - name: Firma fija de tus juegos
        run: |
          bash compilar_juego.sh firma
          if [ -n "$(git status --porcelain firma)" ]; then
            git config user.name "Kira"
            git config user.email "kira@users.noreply.github.com"
            git add firma && git commit -m "Firma fija de tus juegos" && git push
          fi
      - name: Compilar el juego
        run: bash compilar_juego.sh compilar "juegos/$JUEGO"
      - name: Guardar lo descargado y compilado
        if: always()
        uses: actions/cache/save@v4
        with:
          path: |
            ~/.buildozer
            ~/.kira_build
          key: juegos-${{ runner.os }}-v1-${{ github.run_id }}
      - name: Publicar el APK
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release delete "juego-$JUEGO" --yes --cleanup-tag || true
          gh release create "juego-$JUEGO" "salida/$JUEGO.apk" --title "$JUEGO" --notes "Juego hecho con Kira."
"""

LEEME = """# Juegos de Kira

Aquí Kira guarda tus juegos y GitHub los convierte en apps (APK) que se instalan solas.

- `juegos/<nombre>/`: cada juego (tu código en `juego.py`, el motor de Kira y un reproductor con Kivy).
- Cada APK sale en **Releases** como `juego-<nombre>`.
- `firma/`: la firma fija de tus juegos (así una versión nueva se instala encima de la anterior).
"""


def blob_sha(datos):
    """El sha que GitHub da a un archivo (para no subir lo que ya está igual)."""
    return hashlib.sha1(b"blob %d\0" % len(datos) + datos).hexdigest()


def icono_png(titulo, lado=192):
    """Un icono: círculo de color con un borde claro (PNG en Python puro)."""
    import sprites_kira as spk
    paleta = [(37, 99, 235), (219, 39, 119), (5, 150, 105), (217, 119, 6), (124, 58, 237), (220, 38, 38), (8, 145, 178)]
    r, g, b = paleta[sum(map(ord, titulo)) % len(paleta)]
    c, px = lado / 2.0, bytearray()
    for y in range(lado):
        for x in range(lado):
            d = ((x - c + 0.5) ** 2 + (y - c + 0.5) ** 2) ** 0.5
            if d <= c - 14:
                px += bytes((r, g, b, 255))
            elif d <= c - 2:
                px += bytes((255, 255, 255, 255))
            else:
                px += bytes((0, 0, 0, 0))
    return spk.escribir_png(lado, lado, bytes(px))


def proyecto(codigo, titulo, n=1, dibujos=None, build_dir="/home/runner/.kira_build"):
    """{ruta en el repositorio: bytes} del juego (carpeta juegos/<id>/)."""
    jid = id_de(titulo)
    with open(os.path.join(AQUI, "motor_juegos_kira.py"), "rb") as f:
        motor = f.read()
    base = f"juegos/{jid}/"
    tit = re.sub(r"[\r\n=]", " ", titulo).strip()[:40] or "Juego de Kira"
    archivos = {base + "main.py": REPRODUCTOR.encode("utf-8"), base + "motor_juegos_kira.py": motor,
                base + "juego.py": codigo.encode("utf-8"), base + "icono.png": icono_png(titulo),
                base + "buildozer.spec": ESPEC.format(titulo=tit, id=jid, n=int(n),
                                                      build_dir=build_dir).encode("utf-8")}
    for nombre, datos in (dibujos or {}).items():
        archivos[base + f"sprites/{nombre}.png"] = datos
    return jid, archivos


def repo_base():
    return {".github/workflows/" + FLUJO: FLUJO_YML.encode("utf-8"), "compilar_juego.sh": COMPILAR.encode("utf-8"),
            "README.md": LEEME.encode("utf-8")}


def escribir(carpeta, archivos):
    for ruta, datos in archivos.items():
        dest = os.path.join(carpeta, *ruta.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(datos)


# =====================================================================================
#  GITHUB
# =====================================================================================
def _http_real(metodo, url, token, cuerpo=None):
    import urllib.error
    import urllib.request
    import red_kira
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method=metodo, headers={
        "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Kira", "Content-Type": "application/json"})
    try:
        with red_kira.abrir(req, timeout=60) as r:
            texto = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(texto) if texto.strip() else {})
    except urllib.error.HTTPError as e:
        try:
            texto = e.read().decode("utf-8", "replace")
            return e.code, (json.loads(texto) if texto.strip() else {})
        except ValueError:
            return e.code, {}


class GitHub:
    def __init__(self, token, http=None, dormir=time.sleep):
        if not es_token(token):
            raise ApkError("Esa clave de GitHub no tiene buena pinta (empieza por «ghp_» o «github_pat_»).")
        self.token, self.http, self.dormir = token.strip(), http or _http_real, dormir
        self.login = None

    def _pedir(self, metodo, ruta, cuerpo=None, vale=(200, 201, 204)):
        codigo, datos = self.http(metodo, API + ruta, self.token, cuerpo)
        if codigo in vale:
            return codigo, datos
        msg = (datos or {}).get("message", "") if isinstance(datos, dict) else ""
        if codigo == 401:
            raise ApkError("GitHub no acepta tu clave (¿caducó o la copiaste mal?). Dame otra con «config github: …».")
        if codigo == 403 and "workflow" in msg.lower():
            raise ApkError("A tu clave de GitHub le falta el permiso «workflow». Crea otra con «public_repo» y "
                           "«workflow» marcados.")
        if codigo in (403, 404) and ruta.startswith("/user/repos"):
            raise ApkError("Tu clave de GitHub no deja crear repositorios: márcale el permiso «public_repo».")
        raise ApkError(f"GitHub respondió {codigo} a {metodo} {ruta.split('?')[0]}: {msg[:200]}")

    def usuario(self):
        if self.login is None:
            self.login = self._pedir("GET", "/user")[1].get("login") or ""
            if not self.login:
                raise ApkError("GitHub no me dice tu usuario.")
        return self.login

    def preparar_repo(self):
        """El repositorio «kira-juegos» (lo crea si no existe). Devuelve su rama principal."""
        u = self.usuario()
        codigo, datos = self._pedir("GET", f"/repos/{u}/{REPO}", vale=(200, 404))
        if codigo == 404:
            self._pedir("POST", "/user/repos", {"name": REPO, "description": "Mis juegos hechos con Kira",
                                                 "private": False, "auto_init": True, "has_wiki": False})
            for _ in range(10):                          # GitHub tarda un poco en tenerlo listo
                self.dormir(2)
                codigo, datos = self._pedir("GET", f"/repos/{u}/{REPO}", vale=(200, 404))
                if codigo == 200:
                    break
            else:
                raise ApkError("GitHub no termina de crear el repositorio kira-juegos.")
        if datos.get("private"):
            raise ApkError("Tu repositorio kira-juegos es privado: GitHub solo compila gratis los públicos. "
                           "Hazlo público en su configuración.")
        return datos.get("default_branch") or "main"

    def subir(self, archivos, rama, mensaje="Kira", progreso=None):
        """Sube lo que haya cambiado. Devuelve cuántos archivos subió."""
        u, hechos = self.usuario(), 0
        for i, (ruta, datos) in enumerate(sorted(archivos.items())):
            if progreso:
                progreso(i / max(1, len(archivos)), ruta)
            codigo, actual = self._pedir("GET", f"/repos/{u}/{REPO}/contents/{ruta}?ref={rama}", vale=(200, 404))
            sha = actual.get("sha") if codigo == 200 and isinstance(actual, dict) else None
            if sha == blob_sha(datos):
                continue
            import base64
            cuerpo = {"message": f"{mensaje}: {ruta}", "content": base64.b64encode(datos).decode("ascii"),
                      "branch": rama}
            if sha:
                cuerpo["sha"] = sha
            self._pedir("PUT", f"/repos/{u}/{REPO}/contents/{ruta}", cuerpo)
            hechos += 1
        return hechos

    def lanzar(self, jid, marca, rama):
        u = self.usuario()
        for intento in range(6):                         # recién subido el flujo, GitHub puede tardar en verlo
            codigo, _ = self._pedir("POST", f"/repos/{u}/{REPO}/actions/workflows/{FLUJO}/dispatches",
                                    {"ref": rama, "inputs": {"juego": jid, "marca": marca}}, vale=(204, 404, 422))
            if codigo == 204:
                return
            self.dormir(5)
        raise ApkError("GitHub no encuentra la receta de compilar (¿están activadas las Actions en kira-juegos?).")

    def buscar_ejecucion(self, marca, intentos=12):
        u = self.usuario()
        for _ in range(intentos):
            _, datos = self._pedir("GET", f"/repos/{u}/{REPO}/actions/runs?event=workflow_dispatch&per_page=15")
            for r in datos.get("workflow_runs", []):
                if marca in (r.get("display_title") or ""):
                    return r
            self.dormir(5)
        raise ApkError("He pedido la compilación pero GitHub no la enseña. Mírala en la pestaña Actions de kira-juegos.")

    def ejecucion(self, run_id):
        return self._pedir("GET", f"/repos/{self.usuario()}/{REPO}/actions/runs/{run_id}")[1]

    def motivo_fallo(self, run_id):
        u = self.usuario()
        try:
            trabajos = self._pedir("GET", f"/repos/{u}/{REPO}/actions/runs/{run_id}/jobs")[1].get("jobs", [])
            for t in trabajos:
                notas = self._pedir("GET", f"/repos/{u}/{REPO}/check-runs/{t['id']}/annotations")[1]
                for n in notas if isinstance(notas, list) else []:
                    if n.get("annotation_level") == "failure" and n.get("message"):
                        return n["message"][:400]
        except ApkError:
            pass
        return ""

    def url_apk(self, jid):
        return f"https://github.com/{self.usuario()}/{REPO}/releases/download/juego-{jid}/{jid}.apk"

    def url_ejecucion(self, run_id):
        return f"https://github.com/{self.usuario()}/{REPO}/actions/runs/{run_id}"


# =====================================================================================
#  TODO EL CAMINO
# =====================================================================================
class Registro:
    """Cuántas veces se ha compilado cada juego (la versión sube sola: así el APK nuevo se instala encima)."""

    def __init__(self, ruta):
        self.ruta = ruta
        try:
            with open(ruta, encoding="utf-8") as f:
                self.datos = json.load(f)
        except (OSError, ValueError):
            self.datos = {}

    def siguiente(self, jid):
        return int(self.datos.get(jid, {}).get("n", 0)) + 1

    def apuntar(self, jid, n, url=""):
        self.datos[jid] = {"n": n, "url": url, "t": time.time()}
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.datos, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)

    def duracion(self):
        """Lo que se espera que tarde: la primera vez mucho más (GitHub prepara todo)."""
        return 12 * 60 if self.datos else 30 * 60


def compilar(gh, codigo, titulo, registro, dibujos=None, progreso=None, cancelado=None, reloj=time.monotonic):
    """Sube el juego, lo compila en GitHub y espera. Devuelve {'id', 'url_apk', 'n', 'run'}. Lanza ApkError.
    progreso(fraccion, texto)."""
    def avisa(f, t):
        if progreso:
            progreso(max(0.0, min(0.99, f)), t)

    def mira_cancelado():
        if cancelado and cancelado():
            raise ApkError("Cancelado (si GitHub ya estaba compilando, terminará igual: el APK quedará en Releases).")

    avisa(0.01, "Conecto con tu GitHub…")
    rama = gh.preparar_repo()
    mira_cancelado()
    n = registro.siguiente(id_de(titulo))
    jid, archivos = proyecto(codigo, titulo, n, dibujos)
    todo = dict(repo_base())
    todo.update(archivos)
    gh.subir(todo, rama, f"Kira: {titulo}", progreso=lambda f, r: avisa(0.02 + 0.06 * f, f"Subo {r}…"))
    mira_cancelado()
    marca = "k" + hashlib.sha1(f"{jid}{time.time()}".encode()).hexdigest()[:10]
    avisa(0.09, "Pido a GitHub que lo compile…")
    gh.lanzar(jid, marca, rama)
    run = gh.buscar_ejecucion(marca)
    esperado, inicio = registro.duracion(), reloj()
    while True:
        mira_cancelado()
        r = gh.ejecucion(run["id"])
        pasado = reloj() - inicio
        if r.get("status") == "completed":
            break
        if pasado > ESPERA_MAX:
            raise ApkError("GitHub está tardando muchísimo. Lo dejo: si termina, el APK estará en Releases de "
                           f"kira-juegos ({gh.url_ejecucion(run['id'])}).")
        estado = "en cola" if r.get("status") in ("queued", "waiting", "pending") else "compilando"
        avisa(0.10 + 0.88 * min(1.0, pasado / esperado), f"GitHub {estado} «{titulo}»… ({int(pasado // 60)} min)")
        gh.dormir(20)
    if r.get("conclusion") != "success":
        motivo = gh.motivo_fallo(run["id"])
        raise ApkError("GitHub no ha podido compilar el juego" + (f": {motivo}" if motivo else "")
                       + f". Detalle: {gh.url_ejecucion(run['id'])}")
    url = gh.url_apk(jid)
    registro.apuntar(jid, n, url)
    return {"id": jid, "url_apk": url, "n": n, "run": run["id"]}
