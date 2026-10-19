# -*- coding: utf-8 -*-
"""
pasarela_cliente.py  -  VA DENTRO DEL APK (solo librería estándar, sin requirements extra)

Flujo:
  1. Kira genera código de mejora.
  2. Promotor.preparar() lo envía al laboratorio (pasarela) y recibe el resultado de las pruebas.
  3. La interfaz muestra al usuario: diff, avisos y resultado de las pruebas.
  4. SOLO si el usuario escribe  "APLICAR <id>"  se llama a Promotor.aplicar().
  5. aplicar() hace copia de seguridad, instala, comprueba que carga y, si falla, revierte solo.

El laboratorio nunca envía código al móvil: solo devuelve un veredicto.
Las mejoras se guardan en KIRA_DATA_DIR/modulos (carpeta escribible), nunca sobre el núcleo.

Configuración (KIRA_DATA_DIR/pasarela.json), el token NO va escrito en el código:
  {"url": "http://192.168.1.50:8765", "token": "TU_TOKEN_LARGO"}
"""
import ast
import difflib
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import time
import types
import urllib.error
import urllib.request

NOMBRE_OK = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
MAX_CODIGO = 200_000  # bytes


def carpeta_datos():
    base = os.environ.get("KIRA_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".kira")
    os.makedirs(base, exist_ok=True)
    return base


def _sha(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class PasarelaCliente:
    def __init__(self, url=None, token=None):
        cfg = {}
        ruta = os.path.join(carpeta_datos(), "pasarela.json")
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                cfg = json.load(f)
        self.url = (url or cfg.get("url") or "").rstrip("/")
        self.token = token or cfg.get("token") or os.environ.get("KIRA_LAB_TOKEN", "")

    def probar(self, nombre, codigo, timeout=90):
        """Envía el código al laboratorio. Devuelve siempre un dict con 'ok'."""
        if not self.url or not self.token:
            return {"ok": False, "error": "Pasarela sin configurar (falta url o token)."}
        datos = json.dumps({"nombre": nombre, "codigo": codigo}).encode("utf-8")
        req = urllib.request.Request(
            self.url + "/probar", data=datos, method="POST",
            headers={"Content-Type": "application/json", "X-Kira-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read(1_000_000).decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"ok": False, "error": f"El laboratorio respondió {e.code}."}
        except Exception as e:
            return {"ok": False, "error": f"Laboratorio no alcanzable: {e}"}


class Pendiente:
    """Mejora probada, a la espera de que el usuario la apruebe."""

    def __init__(self, nombre, codigo, resultado, diff):
        self.id = secrets.token_hex(3)
        self.nombre = nombre
        self.codigo = codigo
        self.sha = _sha(codigo)
        self.resultado = resultado
        self.diff = diff
        self.usado = False

    @property
    def aprobable(self):
        # Solo se puede aprobar si el laboratorio dio OK sobre ESTE código exacto
        return bool(self.resultado.get("ok")) and self.resultado.get("sha256") == self.sha

    def frase_confirmacion(self):
        return f"APLICAR {self.id}"

    def resumen(self):
        r = self.resultado
        lineas = [f"Mejora '{self.nombre}'  (id {self.id})",
                  f"Pruebas del laboratorio: {'OK' if self.aprobable else 'FALLÓ'}"]
        for e in r.get("etapas", []):
            lineas.append(f"  - {e.get('nombre')}: {'OK' if e.get('ok') else 'FALLÓ'}  {e.get('detalle', '')}")
        if r.get("error"):
            lineas.append(f"  Error: {r['error']}")
        for a in r.get("avisos", []):
            lineas.append(f"  AVISO: {a}")
        lineas.append("--- Cambios ---")
        lineas.append(self.diff or "(módulo nuevo, sin versión anterior)")
        if self.aprobable:
            lineas.append(f"\nPara aplicar escribe exactamente: {self.frase_confirmacion()}")
        else:
            lineas.append("\nNo se puede aplicar: no superó las pruebas.")
        return "\n".join(lineas)


class Promotor:
    def __init__(self, pasarela=None):
        self.pasarela = pasarela or PasarelaCliente()
        base = carpeta_datos()
        self.dir_modulos = os.path.join(base, "modulos")
        self.dir_respaldos = os.path.join(base, "respaldos")
        self.registro = os.path.join(base, "registro_mejoras.jsonl")
        os.makedirs(self.dir_modulos, exist_ok=True)
        os.makedirs(self.dir_respaldos, exist_ok=True)

    # ---------- utilidades ----------
    def _ruta(self, nombre):
        return os.path.join(self.dir_modulos, nombre + ".py")

    def _log(self, evento, nombre, extra=None):
        reg = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "evento": evento, "modulo": nombre}
        if extra:
            reg.update(extra)
        with open(self.registro, "a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")

    @staticmethod
    def _cargar(ruta, nombre):
        """Carga SIEMPRE desde el texto fuente (sin caché de bytecode): con la caché de Python, un archivo
        nuevo del mismo tamaño escrito en el mismo segundo podía cargarse con el código VIEJO."""
        mod = types.ModuleType("kira_mod_" + nombre)
        mod.__file__ = ruta
        with open(ruta, "r", encoding="utf-8") as f:
            fuente = f.read()
        exec(compile(fuente, ruta, "exec"), mod.__dict__)
        return mod

    # ---------- paso 1: preparar (NO instala nada) ----------
    def preparar(self, nombre, codigo):
        if not NOMBRE_OK.match(nombre or ""):
            return None, "Nombre no válido (minúsculas, números y _; máx. 31 caracteres)."
        if len(codigo.encode("utf-8")) > MAX_CODIGO:
            return None, "Código demasiado grande."
        try:
            ast.parse(codigo)
        except SyntaxError as e:
            return None, f"Error de sintaxis antes de enviar: {e}"
        actual = ""
        if os.path.exists(self._ruta(nombre)):
            with open(self._ruta(nombre), encoding="utf-8") as f:
                actual = f.read()
        diff = "".join(difflib.unified_diff(
            actual.splitlines(True), codigo.splitlines(True),
            fromfile="actual/" + nombre, tofile="propuesta/" + nombre))
        resultado = self.pasarela.probar(nombre, codigo)
        pend = Pendiente(nombre, codigo, resultado, diff)
        self._log("preparada", nombre, {"id": pend.id, "ok_lab": pend.aprobable})
        return pend, None

    # ---------- paso 2: aplicar (solo con aprobación humana) ----------
    def aplicar(self, pend, confirmacion_usuario):
        """confirmacion_usuario debe ser el texto que ESCRIBIÓ el usuario en la interfaz."""
        if pend is None or pend.usado:
            return False, "Esta mejora ya se usó o no existe."
        if not pend.aprobable:
            return False, "La mejora no superó las pruebas del laboratorio."
        if (confirmacion_usuario or "").strip() != pend.frase_confirmacion():
            return False, "Confirmación incorrecta. No se aplicó nada."
        if _sha(pend.codigo) != pend.sha:
            return False, "El código cambió después de probarse. No se aplicó."
        pend.usado = True  # un solo uso

        destino = self._ruta(pend.nombre)
        respaldo = None
        if os.path.exists(destino):
            respaldo = os.path.join(self.dir_respaldos, f"{pend.nombre}.{int(time.time())}.py")
            shutil.copy2(destino, respaldo)

        tmp = destino + ".nuevo"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(pend.codigo)
        os.replace(tmp, destino)

        try:
            self._cargar(destino, pend.nombre)  # comprobación de arranque
        except Exception as e:
            if respaldo:
                shutil.copy2(respaldo, destino)
            else:
                os.remove(destino)
            self._log("revertida_auto", pend.nombre, {"id": pend.id, "error": repr(e)})
            return False, f"La mejora falló al cargar y se revirtió sola: {e}"

        self._log("aplicada", pend.nombre, {"id": pend.id, "sha": pend.sha, "respaldo": respaldo})
        return True, f"Mejora '{pend.nombre}' aplicada."

    # ---------- reversión manual ----------
    def revertir(self, nombre):
        if not NOMBRE_OK.match(nombre or ""):
            return False, "Nombre no válido."
        copias = sorted(f for f in os.listdir(self.dir_respaldos)
                        if f.startswith(nombre + ".") and f.endswith(".py"))
        if not copias:
            return False, "No hay copias de seguridad de ese módulo."
        shutil.copy2(os.path.join(self.dir_respaldos, copias[-1]), self._ruta(nombre))
        self._log("revertida_manual", nombre, {"desde": copias[-1]})
        return True, f"Restaurada la versión {copias[-1]}."

    # ---------- arranque ----------
    def cargar_modulos(self):
        """Carga los módulos aprobados. Si uno falla, intenta su última copia; si no, lo omite."""
        cargados, errores = {}, {}
        for f in sorted(os.listdir(self.dir_modulos)):
            if not f.endswith(".py"):
                continue
            nombre = f[:-3]
            try:
                cargados[nombre] = self._cargar(self._ruta(nombre), nombre)
            except Exception as e:
                ok, _ = self.revertir(nombre)
                try:
                    if ok:
                        cargados[nombre] = self._cargar(self._ruta(nombre), nombre)
                        errores[nombre] = f"falló ({e}); restaurada copia anterior"
                        continue
                except Exception as e2:
                    e = e2
                errores[nombre] = f"omitido: {e}"
                self._log("modulo_omitido", nombre, {"error": repr(e)})
        return cargados, errores
