# -*- coding: utf-8 -*-
"""
herramientas_kira.py - Las HERRAMIENTAS que Kira da a los módulos que programa (solo librería estándar; va en el APK).

Un comando de módulo puede declararse con dos parámetros y recibirá este objeto como segundo:

    def registrar():
        def mezclar(texto, kira):                    # 'kira' = Herramientas
            kira.ffmpeg(["pista1.mp3", "pista2.mp3"], "mezcla.mp3",
                        ["-filter_complex", "[0:a]volume=0.8[a];[1:a]volume=0.5[b];[a][b]amix=inputs=2:duration=longest", "-ac", "2"])
            return "Mezcla lista: mezcla.mp3"
        return {"mezclar": mezclar}

Con esto un módulo puede trabajar con archivos y ffmpeg SIN subprocess ni rutas libres:
  - todo ocurre en la carpeta de trabajo (<datos>/trabajo): nombres simples, sin rutas, sin '..';
  - solo puede traer archivos que estén en la mediateca (importar) y sacarlos a Descargas (exportar);
  - ffmpeg es el RESTRINGIDO de ffmpeg_seguro.py: aquí si el equipo lo tiene, si no en el laboratorio del PC.
El módulo sigue necesitando probarse en el laboratorio y tu aprobación; esto solo reduce lo que puede hacer mal.
"""
import json
import os
import re
import shutil

import ffmpeg_seguro as fs

NOMBRE_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]{0,80}$")
EXT_TEXTO = (".txt", ".json", ".md", ".csv")
MAX_TEXTO = 200_000
MAX_TRABAJO = 1024 * 1024 * 1024        # 1 GB de carpeta de trabajo


class HerramientaError(RuntimeError):
    """Algo no permitido o imposible; el mensaje se puede mostrar tal cual."""


class Herramientas:
    def __init__(self, dir_datos, cliente_lab=None, usar_local=True):
        self.dir_datos = dir_datos
        self.usar_local = usar_local                  # False: siempre en el laboratorio (útil para probar)
        self.trabajo = os.path.join(dir_datos, "trabajo")
        self._cliente = cliente_lab

    # ---- carpeta de trabajo ----
    def ruta(self, nombre):
        """Ruta absoluta de un archivo de la carpeta de trabajo. Rechaza rutas, '..' y nombres raros."""
        nombre = str(nombre)
        if not NOMBRE_OK.match(nombre) or ".." in nombre:
            raise HerramientaError(f"Nombre de archivo no válido: '{nombre[:40]}' (solo letras, números, espacio, _ . -).")
        os.makedirs(self.trabajo, exist_ok=True)
        return os.path.join(self.trabajo, nombre)

    def _espacio(self):
        total = 0
        for r, _d, fs_ in os.walk(self.trabajo):
            total += sum(os.path.getsize(os.path.join(r, f)) for f in fs_)
        return total

    def listar(self):
        os.makedirs(self.trabajo, exist_ok=True)
        return sorted(f for f in os.listdir(self.trabajo) if os.path.isfile(os.path.join(self.trabajo, f)))

    def existe(self, nombre):
        return os.path.isfile(self.ruta(nombre))

    def leer(self, nombre):
        r = self.ruta(nombre)
        if os.path.splitext(r)[1].lower() not in EXT_TEXTO:
            raise HerramientaError("Solo se leen archivos de texto (.txt .json .md .csv).")
        with open(r, "r", encoding="utf-8") as f:
            return f.read(MAX_TEXTO)

    def escribir(self, nombre, texto):
        r = self.ruta(nombre)
        if os.path.splitext(r)[1].lower() not in EXT_TEXTO:
            raise HerramientaError("Solo se escriben archivos de texto (.txt .json .md .csv).")
        if len(str(texto)) > MAX_TEXTO:
            raise HerramientaError("Texto demasiado largo.")
        with open(r, "w", encoding="utf-8") as f:
            f.write(str(texto))
        return nombre

    def borrar(self, nombre):
        r = self.ruta(nombre)
        if os.path.isfile(r):
            os.remove(r)
            return True
        return False

    # ---- mediateca ----
    def medios(self, tipo=None):
        """Lista de {'titulo','tipo','estado','ruta'} de la mediateca del usuario."""
        import diseno_kira as dk
        return dk.Mediateca(os.path.join(self.dir_datos, "mediateca.json")).listar(tipo=tipo)

    def importar(self, titulo, nombre=None):
        """Copia un medio de la mediateca (por título exacto) a la carpeta de trabajo. Devuelve el nombre del archivo copiado."""
        for m in self.medios():
            if m["titulo"] == titulo and os.path.isfile(m["ruta"]):
                nombre = nombre or re.sub(r"[^A-Za-z0-9._\-]+", "_", os.path.basename(m["ruta"]))[:80]
                destino = self.ruta(nombre)
                if os.path.splitext(destino)[1].lower() not in fs.EXT_ENTRADA:
                    raise HerramientaError("Ese tipo de archivo no se puede importar.")
                if self._espacio() + os.path.getsize(m["ruta"]) > MAX_TRABAJO:
                    raise HerramientaError("La carpeta de trabajo está llena (1 GB).")
                shutil.copyfile(m["ruta"], destino)
                return nombre
        raise HerramientaError(f"No hay ningún medio llamado '{titulo[:40]}' en la mediateca.")

    def exportar(self, nombre):
        """Copia un resultado a Descargas y lo añade a la mediateca como 'creado'. Devuelve (ok, mensaje)."""
        import diseno_kira as dk
        r = self.ruta(nombre)
        if not os.path.isfile(r):
            raise HerramientaError(f"'{nombre}' no existe en la carpeta de trabajo.")
        destino = os.path.join(self.dir_datos, "diseno", "videos" if fs_es_video(r) else "audios")
        os.makedirs(destino, exist_ok=True)
        propio = os.path.join(destino, os.path.basename(r))
        n = 1
        while os.path.exists(propio):
            n += 1
            b, e = os.path.splitext(os.path.basename(r))
            propio = os.path.join(destino, f"{b}_{n}{e}")
        shutil.copyfile(r, propio)
        med = dk.Mediateca(os.path.join(self.dir_datos, "mediateca.json"))
        med.anadir(os.path.splitext(nombre)[0], propio, None, "creado")
        _ok, msg = dk.Proyectos(self.dir_datos).exportar(propio)
        return True, f"Guardado en la mediateca. {msg}"

    # ---- ffmpeg restringido ----
    def _lab(self):
        if self._cliente is None:
            import video_cliente_kira as vc
            self._cliente = vc.ClienteVideo()
        return self._cliente

    def donde_ffmpeg(self):
        """('local'|'laboratorio'|None, motivo)."""
        ff = None
        if self.usar_local:
            try:
                import motor_video_kira as mv
                ff = mv.ffmpeg_ruta()
            except Exception:
                ff = None
        if ff:
            return "local", ""
        info = self._lab().info()
        if info.get("ffmpeg"):
            return "laboratorio", ""
        return None, "No hay ffmpeg aquí ni en el laboratorio. Instálalo en el PC (pip install imageio-ffmpeg) y arranca el laboratorio."

    def ffmpeg(self, entradas, salida, args, progreso=None, cancelar=None):
        """ffmpeg restringido sobre archivos de la carpeta de trabajo. Devuelve el mensaje de éxito; lanza HerramientaError."""
        if isinstance(entradas, str):
            entradas = [entradas]
        rutas = [self.ruta(e) for e in entradas]
        for r in rutas:
            if not os.path.isfile(r):
                raise HerramientaError(f"No existe '{os.path.basename(r)}' en la carpeta de trabajo.")
        destino = self.ruta(salida)
        try:
            fs.construir_comando("ffmpeg", rutas, destino, args)        # valida ya, antes de buscar dónde ejecutar
        except fs.FfmpegError as e:
            raise HerramientaError(str(e))
        if self._espacio() > MAX_TRABAJO:
            raise HerramientaError("La carpeta de trabajo está llena (1 GB).")
        donde, motivo = self.donde_ffmpeg()
        if donde is None:
            raise HerramientaError(motivo)
        if donde == "local":
            import motor_video_kira as mv
            ok, msg = fs.ejecutar(mv.ffmpeg_ruta(), rutas, destino, args)
            if not ok:
                raise HerramientaError(msg)
            return msg
        import video_cliente_kira as vc
        try:
            self._lab().ffmpeg(rutas, destino, args, progreso=progreso, cancelar=cancelar)
        except vc.VideoError as e:
            raise HerramientaError(str(e))
        return f"Creado {os.path.basename(destino)} en el laboratorio ({os.path.getsize(destino) // 1024} KB)"


def fs_es_video(ruta):
    return os.path.splitext(ruta)[1].lower() in (".mp4", ".webm")
