# -*- coding: utf-8 -*-
"""
motor_video_kira.py - MOTOR GRÁFICO DE VÍDEO REAL de Kira (sin Kivy).

Convierte un guion de videoclip (diseno_kira.normalizar_guion) en un archivo MP4 de verdad:
  1. Cada escena se dibuja por código (escena_kira) y se anima con movimiento de cámara (zoom / paneo).
  2. Entre escenas hay fundidos encadenados; cada escena lleva su título/texto; hay entrada y salida a negro.
  3. Los fotogramas se renderizan con Pillow y se envían a ffmpeg (códec H.264, o MPEG-4 si no hay libx264).
  4. Opcionalmente se mezcla una pista de audio (con fundidos de entrada y salida).

Qué necesita: Pillow y un ffmpeg ejecutable (en PATH, en la variable KIRA_FFMPEG, o el que trae imageio-ffmpeg).
  - En el PC del laboratorio funciona seguro.
  - En el móvil solo si el APK incluye ffmpeg y Pillow (no está incluido por defecto): el móvil usa entonces el PC.
Qué NO es: no genera imagen real ni "IA de vídeo"; son escenas procedurales estilizadas. No edita vídeos ajenos
          (eso es el editor, aún por hacer).

Seguridad: ffmpeg se lanza SIN shell y con lista de argumentos; la salida solo se escribe en la ruta indicada;
          el audio de entrada debe tener una extensión de audio conocida; hay límites de duración/resolución.
"""
import math
import os
import shutil
import subprocess
import tempfile
import threading

import diseno_kira as dk
import escena_kira as ek

FORMATOS = {"16:9": (16, 9), "9:16": (9, 16), "4:3": (4, 3)}
CALIDADES = {"borrador": (360, 15), "normal": (540, 24), "alta": (720, 30)}     # (lado corto en px, fotogramas/s)
TRANSICION = 0.8          # segundos de fundido encadenado entre escenas
ENTRADA, SALIDA = 0.5, 0.8
MAX_SEGUNDOS = 180
MAX_FOTOGRAMAS = 180 * 30
AUDIO_OK = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".aac", ".opus")


class MotorError(RuntimeError):
    """Error explicable al usuario (falta ffmpeg, parámetros inválidos, fallo de codificación…)."""


# =====================================================================================
#  HERRAMIENTAS
# =====================================================================================
def ffmpeg_ruta():
    """Ruta de un ffmpeg utilizable o None. Orden: KIRA_FFMPEG, PATH, imageio-ffmpeg."""
    env = os.environ.get("KIRA_FFMPEG", "").strip()
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    ruta = shutil.which("ffmpeg")
    if ruta:
        return ruta
    try:
        import imageio_ffmpeg
        r = imageio_ffmpeg.get_ffmpeg_exe()
        return r if r and os.path.isfile(r) else None
    except Exception:
        return None


def _codec(ffmpeg):
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for c in ("libx264", "mpeg4"):
        if f" {c} " in out:
            return c
    return None


def info_motor():
    """Qué puede hacer este equipo: {'listo': bool, 'ffmpeg': ruta|None, 'codec': str|None, 'pillow': bool, 'motivo': str}."""
    try:
        import PIL  # noqa: F401
        pillow = True
    except ImportError:
        pillow = False
    ff = ffmpeg_ruta()
    codec = _codec(ff) if ff else None
    if not pillow:
        motivo = "Falta Pillow (pip install pillow)."
    elif not ff:
        motivo = "No se encontró ffmpeg."
    elif not codec:
        motivo = "Este ffmpeg no tiene códec H.264 ni MPEG-4."
    else:
        motivo = ""
    return {"listo": not motivo, "ffmpeg": ff, "codec": codec, "pillow": pillow, "motivo": motivo}


def dimensiones(formato="16:9", calidad="normal"):
    if formato not in FORMATOS or calidad not in CALIDADES:
        raise MotorError(f"Formato o calidad no válidos (formatos: {', '.join(FORMATOS)}; calidades: {', '.join(CALIDADES)}).")
    a, b = FORMATOS[formato]
    corto, fps = CALIDADES[calidad]
    if a >= b:
        h, w = corto, round(corto * a / b)
    else:
        w, h = corto, round(corto * b / a)
    return w - w % 2, h - h % 2, fps


def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# =====================================================================================
#  CÁMARA, TEXTO Y COMPOSICIÓN (Pillow)
# =====================================================================================
def vista(i, p):
    """Movimiento de cámara de la escena i en el progreso p (0..1): (zoom, ux, uy) con ux,uy en [-1,1]."""
    k = _suave(p)
    modo = i % 4
    if modo == 1:
        return max(1.0, 1.16 - 0.16 * k), 0.0, 0.0
    if modo == 0:
        return 1.0 + 0.16 * k, 0.0, 0.0                       # zoom hacia dentro
    if modo == 2:
        return 1.14, -1.0 + 2.0 * k, 0.0                      # paneo a la derecha
    return 1.14, 1.0 - 2.0 * k, 0.3 * math.sin(k * math.pi)   # paneo a la izquierda


def _fuente(tam):
    from PIL import ImageFont
    for nombre in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arialbd.ttf", "arial.ttf", "Roboto-Regular.ttf",
                   "/system/fonts/Roboto-Regular.ttf", "/system/fonts/DroidSans.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except (OSError, ValueError):
            continue
    try:
        return ImageFont.load_default(tam)
    except TypeError:
        return ImageFont.load_default()


def _lineas(dr, texto, fuente, ancho_max):
    palabras, lineas, actual = str(texto).split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if dr.textlength(prueba, font=fuente) <= ancho_max or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas[:4]


def _capa_texto(w, h, titulo, texto, grande=False):
    """(color RGB, máscara L) con el texto de la escena; la máscara se atenúa para los fundidos."""
    from PIL import Image, ImageDraw
    color = Image.new("RGB", (w, h), (255, 255, 255))
    mascara = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(mascara)
    if grande:
        f = _fuente(max(18, int(min(w, h) * 0.085)))
        lin = _lineas(dr, titulo, f, w * 0.86)
        alto = sum(f.size * 1.25 for _ in lin)
        y = h * 0.40 - alto / 2
        sombra = Image.new("L", (w, h), 0)
        sd = ImageDraw.Draw(sombra)
        sd.rectangle([w * 0.04, y - f.size * 0.6, w * 0.96, y + alto + f.size * 0.4], fill=110)
        mascara = Image.composite(sombra, mascara, sombra)
        dr = ImageDraw.Draw(mascara)
        for l in lin:
            dr.text(((w - dr.textlength(l, font=f)) / 2, y), l, font=f, fill=255)
            y += f.size * 1.25
        return color, mascara
    ft = _fuente(max(12, int(min(w, h) * 0.05)))
    fs = _fuente(max(10, int(min(w, h) * 0.038)))
    lin_t = _lineas(dr, titulo, ft, w * 0.88)[:1]
    lin_s = _lineas(dr, texto, fs, w * 0.88)[:2]
    alto = sum(ft.size * 1.2 for _ in lin_t) + sum(fs.size * 1.2 for _ in lin_s)
    y0 = h - alto - h * 0.07
    fondo = Image.new("L", (w, h), 0)
    ImageDraw.Draw(fondo).rectangle([0, y0 - h * 0.025, w, h], fill=120)
    mascara = Image.composite(fondo, mascara, fondo)
    dr = ImageDraw.Draw(mascara)
    y = y0
    for l in lin_t:
        dr.text((w * 0.06, y), l, font=ft, fill=255)
        y += ft.size * 1.2
    for l in lin_s:
        dr.text((w * 0.06, y), l, font=fs, fill=215)
        y += fs.size * 1.2
    return color, mascara


class Composicion:
    """Prepara las escenas una vez y compone cualquier fotograma t (segundos). Pillow necesario."""

    def __init__(self, guion, w, h):
        from PIL import Image
        self.Image = Image
        self.guion = dk.normalizar_guion(guion)
        self.w, self.h = w, h
        self.aspecto = w / h
        self.escenas = self.guion["escenas"]
        self.inicios, t = [], 0.0
        for e in self.escenas:
            self.inicios.append(t)
            t += e["dur"]
        self.total = t
        base_w = int(min(1920, max(w, h * 4 / 3) * 1.18))
        base_w += base_w % 2
        self.base = []
        for i, e in enumerate(self.escenas):
            self.base.append(ek.render_pil(dk.formas_escena(e, i), base_w).convert("RGB"))
        self._texto, self._mascaras = {}, {}

    def _recorte(self, i, p):
        im = self.base[i]
        W0, H0 = im.size
        z, ux, uy = vista(i, p)
        z = max(1.0, z)
        if self.aspecto >= W0 / H0:
            vw = W0 / z
            vh = vw / self.aspecto
        else:
            vh = H0 / z
            vw = vh * self.aspecto
        x0 = (W0 - vw) * (0.5 + 0.5 * ux)
        y0 = (H0 - vh) * (0.5 + 0.5 * uy)
        return im.resize((self.w, self.h), self.Image.BILINEAR, box=(x0, y0, x0 + vw, y0 + vh))

    def _indice(self, t):
        for i in range(len(self.escenas) - 1, -1, -1):
            if t >= self.inicios[i]:
                return i
        return 0

    def _capa(self, clave, titulo, texto, grande):
        if clave not in self._texto:
            self._texto[clave] = _capa_texto(self.w, self.h, titulo, texto, grande)
        return self._texto[clave]

    def _pegar_texto(self, fr, clave, titulo, texto, grande, factor):
        if factor <= 0.01:
            return
        color, mascara = self._capa(clave, titulo, texto, grande)
        nivel = int(round(factor * 10))
        k = (clave, nivel)
        if k not in self._mascaras:
            self._mascaras[k] = mascara if nivel >= 10 else mascara.point(lambda v, f=nivel / 10: int(v * f))
        fr.paste(color, (0, 0), self._mascaras[k])

    def fotograma(self, t):
        t = max(0.0, min(t, self.total - 1e-6))
        i = self._indice(t)
        e = self.escenas[i]
        local = t - self.inicios[i]
        fr = self._recorte(i, local / e["dur"])
        restante = e["dur"] - local
        if i < len(self.escenas) - 1 and restante < TRANSICION:       # fundido encadenado con la siguiente
            a = _suave(1 - restante / TRANSICION)
            fr = self.Image.blend(fr, self._recorte(i + 1, 0.0), a)
        # texto: aparece 0.4 s después de empezar la escena y se va 0.4 s antes de acabar
        fade = min(_suave((local - 0.35) / 0.4), _suave((restante - 0.1) / 0.4))
        if i == 0 and local < 2.4:                                    # tarjeta de título del videoclip
            self._pegar_texto(fr, ("titulo",), self.guion["titulo"], "", True, min(_suave(local / 0.5), _suave((2.4 - local) / 0.5)))
        self._pegar_texto(fr, (i,), e["titulo"] + (f" · {e['plano']}" if e["plano"] else ""), e["texto"], False, fade)
        # entrada y salida a negro
        negro = min(_suave(t / ENTRADA), _suave((self.total - t) / SALIDA))
        if negro < 0.999:
            fr = self.Image.blend(self.Image.new("RGB", fr.size, (0, 0, 0)), fr, negro)
        return fr


# =====================================================================================
#  RENDER A MP4
# =====================================================================================
def renderizar(guion, salida, formato="16:9", calidad="normal", audio=None, progreso=None, cancelar=None):
    """Genera el MP4 en 'salida'. Devuelve {'ok', 'ruta', 'segundos', 'fotogramas', 'bytes', 'ancho', 'alto', 'fps', 'codec'}.
    progreso(fraccion 0..1) se llama sin bloquear; cancelar es un threading.Event. Lanza MotorError si no se puede."""
    info = info_motor()
    if not info["listo"]:
        raise MotorError(f"Este equipo no puede crear vídeo: {info['motivo']}")
    try:
        guion = dk.normalizar_guion(guion)
    except ValueError as e:
        raise MotorError(f"Guion no válido: {e}")
    w, h, fps = dimensiones(formato, calidad)
    total = dk.duracion_total(guion)
    n = int(round(total * fps))
    if total > MAX_SEGUNDOS or n > MAX_FOTOGRAMAS or n < 2:
        raise MotorError(f"Duración no admitida ({total:.0f} s; máximo {MAX_SEGUNDOS} s).")
    if audio is not None:
        if os.path.splitext(str(audio))[1].lower() not in AUDIO_OK or not os.path.isfile(audio):
            raise MotorError("El audio no existe o no tiene un formato de audio conocido.")
    salida = os.path.abspath(str(salida))
    if not salida.lower().endswith(".mp4"):
        raise MotorError("El archivo de salida debe terminar en .mp4.")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    parcial = salida + ".part.mp4"

    comp = Composicion(guion, w, h)
    cmd = [info["ffmpeg"], "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if audio is not None:
        cmd += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
                "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={max(0.0, total - 1.5):.2f}:d=1.5,apad",
                "-c:a", "aac", "-b:a", "160k"]
    else:
        cmd += ["-an"]
    cmd += (["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"] if info["codec"] == "libx264" else ["-c:v", "mpeg4", "-q:v", "4"])
    cmd += ["-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", f"{total:.3f}", "-f", "mp4", parcial]

    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err)
        try:
            for k in range(n):
                if cancelar is not None and cancelar.is_set():
                    raise MotorError("Cancelado.")
                proc.stdin.write(comp.fotograma(k / fps).tobytes())
                if progreso and (k % max(1, fps // 2) == 0):
                    progreso(0.95 * k / n)
            proc.stdin.close()
            proc.wait(timeout=600)
        except BrokenPipeError:
            proc.wait(timeout=30)
        except MotorError:
            proc.kill()
            proc.wait()
            _borrar(parcial)
            raise
        except Exception:
            proc.kill()
            proc.wait()
            _borrar(parcial)
            raise
        if proc.returncode != 0 or not os.path.isfile(parcial) or os.path.getsize(parcial) == 0:
            err.seek(0)
            detalle = err.read().decode("utf-8", "replace").strip()[-400:]
            _borrar(parcial)
            raise MotorError(f"ffmpeg falló: {detalle or 'sin detalle'}")
    os.replace(parcial, salida)
    if progreso:
        progreso(1.0)
    return {"ok": True, "ruta": salida, "segundos": round(total, 2), "fotogramas": n, "bytes": os.path.getsize(salida),
            "ancho": w, "alto": h, "fps": fps, "codec": info["codec"]}


def _borrar(ruta):
    try:
        os.remove(ruta)
    except OSError:
        pass


if __name__ == "__main__":                      # uso en el PC:  python motor_video_kira.py guion.clip.json salida.mp4 [16:9] [normal] [audio.mp3]
    import sys
    if len(sys.argv) < 3:
        sys.exit("Uso: python motor_video_kira.py GUION.clip.json SALIDA.mp4 [formato] [calidad] [audio]")
    g = dk.Proyectos.leer_clip(sys.argv[1])
    r = renderizar(g, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "16:9", sys.argv[4] if len(sys.argv) > 4 else "normal",
                   sys.argv[5] if len(sys.argv) > 5 else None, progreso=lambda f: print(f"\r{f * 100:3.0f}%", end="", flush=True))
    print("\n", r)
