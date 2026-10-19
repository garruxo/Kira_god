# -*- coding: utf-8 -*-
"""
KiraOS - Núcleo Supremo Permanente (Kira God)
Escucha RAM, Memoria Anti-Redundancia, Ciberseguridad, Control de Procesos,
Visión, Auditoría y Gestión de Archivos.

Cambios de esta versión:
- Rutas de datos/logs en KIRA_DATA_DIR (en Android la carpeta del APK no sirve), sin fallar al importar.
- 'destruir' y 'matar proceso' piden confirmación; 'matar proceso' ahora coincide por nombre EXACTO.
- Módulos aprobados (KIRA_DATA_DIR/modulos): añaden comandos, pero NO pueden pisar los del núcleo.
- generar_mejora(pedido): pide el código a la API de Claude (clave con 'config clave: ...').
- El núcleo NO tiene el promotor: proponer mejoras sí, aplicarlas solo lo hace main.py con tu frase.
"""

import time
import os
import re
import json
import logging
import types
import urllib.request
import urllib.error

# Control seguro de psutil para evitar fallos si no está instalado
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger("KiraGodCore")

MODELO_POR_DEFECTO = "claude-sonnet-5-5"
NOMBRE_OK = re.compile(r"^[a-z][a-z0-9_]{0,30}$")


def _dir_datos():
    # Fuera de la carpeta del proyecto: así memoria, claves y logs nunca acaban empaquetados en el APK.
    d = os.environ.get("KIRA_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".kira")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


class KiraGodCore:
    def __init__(self):
        self.dir = _dir_datos()
        self.memory_file = os.path.join(self.dir, "kira_memory.json")
        self._configurar_log()
        print("[OK] Iniciando Núcleo Supremo: Kira God...")
        logger.info("Iniciando el Núcleo Permanente y Activo de KiraOS.")
        self.memory = self.load_memory()
        self.volatile_ram_buffer = []  # Memoria temporal de conversación
        self.accion_pendiente = None   # ('destruir', ruta) o ('matar', nombre)
        self.comandos_modulos = {}
        self.errores_modulos = {}
        self.juegos_modulos = {}              # juegos que añaden las mejoras: {nombre: ClaseJuego}
        import api_modulos_kira
        self.avisos = api_modulos_kira.Avisos()
        import bitacora_kira
        self.bitacora = bitacora_kira.Bitacora(os.path.join(self.dir, "bitacora.json"))
        import cerebro_ia_kira
        self.cerebro_ia = cerebro_ia_kira.Cerebro(self.dir)
        try:                                       # baúl de recuerdos en disco (carpeta privada, firmada)
            import recuerdos_kira
            self.recuerdos = recuerdos_kira.Recuerdos(os.path.join(self.dir, "recuerdos"))
            self.recuerdos.ampliar = self._ampliar_con_modelo
            import estudio_kira
            self.estudio = estudio_kira.Estudiante(self.recuerdos, os.path.join(self.dir, "estudio.json"))
            self.estudio.arrancar()                # si le dijiste «aprende sola», sigue estudiando
        except Exception as e:
            self.recuerdos = None
            self.estudio = None
            logger.error(f"No se pudo abrir el baúl de recuerdos: {e}")
        self.cargar_modulos()

    def registrar_error(self, origen, texto):
        """Apunta un fallo real en la bitácora (sin claves) y devuelve una línea con el arreglo conocido ('' si no hay).
        Nunca lanza: así cualquier pantalla puede enseñar el consejo justo debajo del error."""
        try:
            self.bitacora.registrar_error(origen, texto)
            import bitacora_kira
            return bitacora_kira.consejo_corto(texto)
        except Exception:
            return ""

    # ---------- registro de auditoría ----------
    def _configurar_log(self):
        if logger.handlers:
            return
        logger.setLevel(logging.INFO)
        try:
            h = logging.FileHandler(os.path.join(self.dir, "kira_audit.log"), encoding="utf-8")
            h.setFormatter(logging.Formatter(
                '%(asctime)s - [KIRA-GOD-AUDIT] - %(levelname)s - %(message)s'))
            logger.addHandler(h)
        except Exception:
            logger.addHandler(logging.NullHandler())  # sin log, pero el núcleo arranca

    # ---------- memoria ----------
    def load_memory(self):
        """Carga la memoria persistente del sistema."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando memoria: {e}")
                return {}
        return {}

    def save_memory(self):
        """Guarda la información validada en la memoria permanente."""
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=4, ensure_ascii=False)

    def aprender_inteligentemente(self, clave: str, valor: str) -> str:
        """Sistema anti-redundancia: si el dato ya existe idéntico, lo desecha."""
        clave_limpia = clave.strip().lower()
        valor_nuevo = valor.strip()
        if clave_limpia in self.memory:
            valor_actual = self.memory[clave_limpia]
            if valor_actual.lower() == valor_nuevo.lower():
                msg = f"Concepto '{clave}' ya archivado. Desechando redundancia."
                logger.info(msg)
                return f"[OK] {msg}"
            else:
                self.memory[clave_limpia] = valor_nuevo
                self.save_memory()
                msg = f"Actualizada información para '{clave}' con nuevos datos."
                logger.info(msg)
                return f"[OK] {msg}"
        else:
            self.memory[clave_limpia] = valor_nuevo
            self.save_memory()
            msg = f"Nuevo conocimiento integrado de forma permanente: '{clave}'"
            logger.info(msg)
            return f"[OK] {msg}"

    def registrar_buffer_volatil(self, texto: str):
        """Mantiene un búfer efímero en RAM que no satura el disco duro."""
        self.volatile_ram_buffer.append(texto)
        if len(self.volatile_ram_buffer) > 15:
            self.volatile_ram_buffer.pop(0)

    def limpiar_buffer_volatil(self):
        """Destruye por completo la conversación temporal de la RAM."""
        self.volatile_ram_buffer.clear()
        logger.info("Búfer volátil de RAM purgado y destruido con éxito.")

    # ---------- módulos aprobados ----------
    def cargar_modulos(self):
        """Carga KIRA_DATA_DIR/modulos/*.py. Cada módulo define registrar() -> {prefijo: funcion(texto)->str}."""
        self.comandos_modulos, self.errores_modulos, self.juegos_modulos = {}, {}, {}
        carpeta = os.path.join(self.dir, "modulos")
        if not os.path.isdir(carpeta):
            return 0
        for f in sorted(os.listdir(carpeta)):
            if not f.endswith(".py"):
                continue
            nombre = f[:-3]
            try:
                ruta_mod = os.path.join(carpeta, f)
                mod = types.ModuleType("kira_mod_" + nombre)  # desde el fuente: sin caché de bytecode obsoleta
                mod.__file__ = ruta_mod
                with open(ruta_mod, "r", encoding="utf-8") as fh:
                    exec(compile(fh.read(), ruta_mod, "exec"), mod.__dict__)
                reg = getattr(mod, "registrar", None)
                tabla = reg() if callable(reg) else {}
                if not isinstance(tabla, dict):
                    raise TypeError("registrar() debe devolver un diccionario")
                for prefijo, fn in tabla.items():
                    if not (isinstance(prefijo, str) and prefijo.strip() and callable(fn)):
                        continue
                    prefijo = prefijo.strip().lower()
                    if prefijo.startswith("juego "):          # {"juego naves": crear(motor) -> clase de Juego}
                        import motor_juegos_kira as mj
                        clase = fn(mj)
                        if not (isinstance(clase, type) and issubclass(clase, mj.Juego)):
                            raise TypeError(f"'{prefijo}' debe devolver una clase que herede de motor.Juego")
                        self.juegos_modulos[prefijo[6:].strip()] = clase
                    else:
                        self.comandos_modulos[prefijo] = (nombre, fn)
            except Exception as e:
                self.errores_modulos[nombre] = repr(e)
                logger.error(f"Módulo '{nombre}' no cargó: {e}")
                self.registrar_error("módulos", f"Módulo '{nombre}' no cargó: {e}")
        return len(self.comandos_modulos)

    @property
    def herramientas(self):
        """Herramientas (carpeta de trabajo, mediateca, ffmpeg restringido) que reciben los comandos de módulo de 2 parámetros."""
        if getattr(self, "_herramientas", None) is None:
            import herramientas_kira
            self._herramientas = herramientas_kira.Herramientas(self.dir)
        return self._herramientas

    @staticmethod
    def _acepta_kira(fn):
        import inspect
        try:
            ps = [p for p in inspect.signature(fn).parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            return len(ps) >= 2 or any(p.kind == p.VAR_POSITIONAL for p in inspect.signature(fn).parameters.values())
        except (TypeError, ValueError):
            return False

    def api_para(self, nombre):
        """El objeto 'kira' que recibe un módulo: herramientas + sus datos, recuerdos y avisos (con límites)."""
        import api_modulos_kira
        return api_modulos_kira.ApiModulo(nombre, self.herramientas, self.dir, getattr(self, "recuerdos", None),
                                          getattr(self, "avisos", None))

    def _comando_modulo(self, cmd_lower, command):
        for prefijo, (nombre, fn) in self.comandos_modulos.items():
            if cmd_lower.startswith(prefijo):
                try:
                    texto = command[len(prefijo):].strip()
                    if self._acepta_kira(fn):
                        return str(fn(texto, self.api_para(nombre)))
                    return str(fn(texto))
                except Exception as e:
                    logger.error(f"Módulo '{nombre}' falló: {e}")
                    self.registrar_error("módulos", f"Módulo '{nombre}' falló: {e}")
                    return f"[x] El módulo '{nombre}' falló: {e}"
        return None

    def hechos_capacidades(self, consultar_laboratorio=True):
        """Lo que hay ahora, para comparar con el catálogo de capacidades (ffmpeg local o en el laboratorio, módulos…)."""
        h = {"prefijos": list(self.comandos_modulos), "ffmpeg": None, "lab": False, "lab_instalar": False}
        try:
            import motor_video_kira as mv
            if mv.ffmpeg_ruta():
                h["ffmpeg"] = "local"
        except Exception:
            pass
        if consultar_laboratorio:
            try:
                import video_cliente_kira as vc
                i = vc.ClienteVideo().info()
                h["lab"], h["lab_instalar"] = bool(i.get("ok") or i.get("ffmpeg")), bool(i.get("instalar"))
                if h["ffmpeg"] is None and i.get("ffmpeg"):
                    h["ffmpeg"] = "laboratorio"
            except Exception:
                pass
        return h

    # ---------- conversación (solo habla; NO ejecuta ni instala nada) ----------
    NO_RECONOCIDA = "[i] No reconozco la orden"

    @staticmethod
    def armar_mensajes(historial, texto):
        """historial: [(rol 'tu'|'kira', texto)]. Devuelve mensajes que alternan user/assistant y acaban en user."""
        msgs = []
        for rol, t in list(historial)[-8:]:
            r = "user" if rol == "tu" else "assistant"
            t = str(t)[:400]
            if msgs and msgs[-1]["role"] == r:
                msgs[-1]["content"] += "\n" + t
            else:
                msgs.append({"role": r, "content": t})
        while msgs and msgs[0]["role"] != "user":
            msgs.pop(0)
        texto = str(texto)[:1000]
        if msgs and msgs[-1]["role"] == "user":
            msgs[-1]["content"] += "\n" + texto
        else:
            msgs.append({"role": "user", "content": texto})
        return msgs

    def _contexto_recuerdos(self, texto):
        try:
            return self.recuerdos.contexto(texto) if getattr(self, "recuerdos", None) else ""
        except Exception:
            return ""

    SISTEMA_SINONIMOS = ("Para cada palabra en español escribe hasta 5 sinónimos o palabras de significado muy parecido. "
                         "Responde SOLO con una línea por palabra, así:\npalabra: sinonimo1, sinonimo2, sinonimo3")

    def _ampliar_con_modelo(self, lista):
        """Pide al MODELO DEL MÓVIL palabras parecidas (nunca a Claude: no gasta API). {} si el modelo está apagado."""
        cer = getattr(self, "cerebro_ia", None)
        if cer is None or not lista or not cer.local_disponible():
            return {}
        r = cer.chat_local(self.SISTEMA_SINONIMOS, [{"role": "user", "content": "\n".join(lista)}],
                           max_tokens=150, timeout=90)
        pedidas = {w.lower() for w in lista}
        salida = {}
        for linea in r.splitlines():
            m = re.match(r"^\W*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)\W*\s*[:=\-]\s*(.+)$", linea.strip())
            if m and m.group(1).lower() in pedidas:
                salida[m.group(1).lower()] = [w.strip(" .") for w in re.split(r"[,;/]", m.group(2)) if w.strip(" .")][:5]
        return salida

    def aprender_de_ia(self, pregunta, respuesta, tema=""):
        """Guarda en el baúl lo que explicó CLAUDE (el «profesor»), para no tener que preguntárselo otra vez.
        Las respuestas del modelo local no se guardan: se equivoca más y no queremos que repita sus errores."""
        rec = getattr(self, "recuerdos", None)
        if rec is None:
            return None
        try:
            import recuerdos_kira
            if len(recuerdos_kira.palabras(pregunta)) < 2 or len(respuesta) < 30 or respuesta.startswith("[x]"):
                return None                        # saludos y charla corta: no son recuerdos útiles
            return rec.guardar(respuesta, tema=tema, fuente="claude", pregunta=pregunta)
        except Exception:
            return None

    def conversar(self, texto, historial=()):
        """Respuesta hablada de Kira (modelo local o API de Claude). Lanza RuntimeError si falta cerebro o falla la red.
        Antes de responder, la IA recibe los recuerdos del baúl que vengan al caso."""
        import cerebro_ia_kira
        clave = self._leer_clave()
        if not clave:
            raise RuntimeError(self._sin_cerebro())
        system = ("Eres Kira, la asistente de esta app. Responde en español, en 1 a 3 frases cortas, sin markdown ni listas, "
                  "porque tu respuesta se lee en voz alta. No tienes acceso a internet ni a los archivos del usuario y no "
                  "puedes cambiar tu propio código: si lo pide, dile que use 'mejorar' en la Sala Hacker. "
                  "No afirmes haber hecho acciones que no has hecho.")
        ctx = self._contexto_recuerdos(texto)
        if ctx:
            system += "\n\n" + ctx
        r = self._llamar_api(clave, system, "", max_tokens=300, mensajes=self.armar_mensajes(historial, texto))
        r = " ".join(r.split())[:1200] or "…"
        if clave != cerebro_ia_kira.LOCAL:
            self.aprender_de_ia(texto, r)
        return r

    def generar_leccion(self, tema):
        """Mini-lección de programación (API de Claude). Devuelve (titulo, explicacion, codigo). No ejecuta nada."""
        clave = self._leer_clave()
        if not clave:
            raise RuntimeError(self._sin_cerebro())
        tema = " ".join(str(tema).split())[:120]
        if not tema:
            raise ValueError("Indica un tema.")
        system = ("Eres un profesor de programación paciente. Responde SOLO con este formato:\n"
                  "TITULO: <título corto>\nEXPLICACION: <3 a 6 frases en español, claras, sin markdown>\n"
                  "```python\n<ejemplo corto y comentado, solo librería estándar>\n```\n"
                  "No escribas nada fuera del formato.")
        texto = self._llamar_api(clave, system, f"Tema: {tema}", max_tokens=900)
        m_t = re.search(r"TITULO:\s*(.+)", texto)
        m_e = re.search(r"EXPLICACION:\s*(.+?)(?:```|$)", texto, re.S)
        m_c = re.search(r"```(?:python)?\n(.*?)```", texto, re.S)
        if not (m_t and m_e and m_c):
            raise ValueError("La respuesta de la IA no tiene el formato esperado.")
        return (" ".join(m_t.group(1).split())[:80], " ".join(m_e.group(1).split())[:1500], m_c.group(1).strip()[:3000])

    def explicar_defensa(self, pregunta):
        """Sala de Ciberseguridad: explica una amenaza SOLO desde la defensa. Devuelve (texto, origen 'ia'|'local').
        Sin clave (o sin red) responde con la biblioteca local si la encuentra. Nunca ejecuta nada."""
        import ciber_kira as ck
        pregunta = ck.limpiar_pregunta(pregunta)
        local = ck.respuesta_local(pregunta)
        clave = self._leer_clave()
        if clave:
            try:
                r = self._llamar_api(clave, ck.SISTEMA_DEFENSA, pregunta, max_tokens=500)
                r = " ".join(r.split())[:1800]
                if r and clave != __import__("cerebro_ia_kira").LOCAL:
                    self.aprender_de_ia(pregunta, r, tema="ciberseguridad")
                if r:
                    return r + "\n\n(Kira solo explica la defensa; esta sala no ejecuta ni guarda nada peligroso.)", "ia"
            except RuntimeError:
                pass
        if local:
            return local, "local"
        return ("No tengo eso en mi biblioteca y sin la clave de la API no puedo explicarlo. Mira los temas de ESTUDIAR o "
                "«SI TE PASA», o pon la clave con «config clave: …»."), "local"

    def generar_diseno(self, tipo, descripcion):
        """Sala de Diseño. tipo: 'web' | 'app' | 'clip'. Devuelve (contenido_validado, origen) con origen 'ia' o 'local'.
        Con clave de API pide a la IA el CONTENIDO en JSON (nunca HTML ni código); sin clave, o si la IA falla,
        usa las plantillas locales. No escribe archivos."""
        import diseno_kira as dk
        if tipo not in dk.SISTEMAS:
            raise ValueError("Tipo de diseño desconocido.")
        descripcion = " ".join(str(descripcion).split())[:300]
        if not descripcion:
            raise ValueError("Describe lo que quieres crear.")
        clave = self._leer_clave()
        if clave:
            try:
                texto = self._llamar_api(clave, dk.SISTEMAS[tipo], f"Petición: {descripcion}", max_tokens=1500)
                return dk.interpretar_respuesta(tipo, texto), "ia"
            except (RuntimeError, ValueError):
                pass                                   # sin red o respuesta inútil: plantilla local
        return dk.LOCALES[tipo](descripcion), "local"

    # ---------- generación de mejoras (solo PROPONE; no aplica nada) ----------
    def _leer_clave(self, tarea="general"):
        """Lo que se pasa a _llamar_api: la clave de Claude, o la marca del cerebro LOCAL si toca usar el modelo del
        móvil (según «cerebro auto|local|claude»). Cadena vacía si no hay ningún cerebro disponible."""
        clave = self._leer_clave_api()
        cer = getattr(self, "cerebro_ia", None)
        if cer is None:
            return clave
        import cerebro_ia_kira
        uso = cer.elegir(clave, tarea)
        return cerebro_ia_kira.LOCAL if uso == "local" else (clave if uso == "claude" else "")

    def _clave_para(self, tarea):
        """Como _leer_clave(tarea), tolerando versiones simplificadas sin parámetro (p. ej. en pruebas)."""
        try:
            return self._leer_clave(tarea)
        except TypeError:
            return self._leer_clave()

    def _sin_cerebro(self):
        cer = getattr(self, "cerebro_ia", None)
        return cer.motivo_sin_cerebro(self._leer_clave_api()) if cer else "Falta la clave de la API. Usa: config clave: TU_CLAVE"

    def cerebro_activo(self):
        """'local' | 'claude' | None: quién respondería ahora mismo."""
        import cerebro_ia_kira
        c = self._leer_clave()
        return "local" if c == cerebro_ia_kira.LOCAL else ("claude" if c else None)

    def _leer_clave_api(self):
        clave = os.environ.get("KIRA_API_KEY", "").strip()
        ruta = os.path.join(self.dir, "api_key.txt")
        if not clave and os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                clave = f.read().strip()
        return clave

    def tiene_clave(self) -> bool:
        """True si Kira tiene algún cerebro de IA ahora mismo (modelo local encendido o clave de Claude)."""
        return bool(self._leer_clave())

    def _llamar_api(self, clave, system, usuario, max_tokens=4000, mensajes=None):
        import cerebro_ia_kira
        if clave == cerebro_ia_kira.LOCAL:                      # modelo local (llama-server en el móvil o en casa)
            return self.cerebro_ia.chat_local(system, mensajes or [{"role": "user", "content": usuario}], max_tokens)
        ruta_modelo = os.path.join(self.dir, "modelo.txt")
        modelo = MODELO_POR_DEFECTO
        if os.path.exists(ruta_modelo):
            with open(ruta_modelo, encoding="utf-8") as f:
                modelo = f.read().strip() or MODELO_POR_DEFECTO
        cuerpo = json.dumps({
            "model": modelo, "max_tokens": int(max_tokens), "system": system,
            "messages": mensajes or [{"role": "user", "content": usuario}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=cuerpo, method="POST",
            headers={"content-type": "application/json", "x-api-key": clave,
                     "anthropic-version": "2023-06-01"})
        try:
            import red_kira
            with red_kira.abrir(req, timeout=90) as r:
                datos = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"La API respondió {e.code} (revisa clave y modelo)")
        except Exception as e:
            raise RuntimeError(f"No se pudo contactar con la API: {e}")
        return "".join(b.get("text", "") for b in datos.get("content", []) if b.get("type") == "text")

    def generar_mejora(self, pedido: str):
        """Devuelve (nombre, codigo). main.py lo envía al laboratorio; aquí NO se instala nada.
        Con el modelo local usa instrucciones cortas con ejemplos (los modelos pequeños se pierden con textos largos)."""
        import cerebro_ia_kira
        import mejoras_ia_kira as mi
        clave = self._clave_para("codigo")
        if not clave:
            raise RuntimeError(self._sin_cerebro())
        local = clave == cerebro_ia_kira.LOCAL
        existentes = ", ".join(sorted(n for n, _ in set(self.comandos_modulos.values()))) or "ninguno"
        usuario = f"Módulos ya instalados: {existentes}\nMejora pedida: {pedido}"
        texto = self._llamar_api(clave, mi.SISTEMA_MEJORA_LOCAL if local else mi.SISTEMA_MEJORA, usuario)
        return mi.extraer_modulo(texto)

    def cerebro_para_codigo(self):
        """'local' | 'claude' | None: quién programaría una mejora ahora mismo."""
        import cerebro_ia_kira
        c = self._clave_para("codigo")
        return "local" if c == cerebro_ia_kira.LOCAL else ("claude" if c else None)

    def _orden_recuerdos(self, command, cmd_lower):
        import recuerdos_kira
        rec = getattr(self, "recuerdos", None)
        if rec is None:
            return "[x] El baúl de recuerdos no está disponible (no se pudo abrir la carpeta)."
        m = re.match(r"^guarda recuerdo\s*:?\s*(.*)$", command.strip(), re.I | re.S)
        if m:
            n = rec.guardar(m.group(1), fuente="usuario")
            return f"[OK] Guardado en el baúl como recuerdo #{n}." if n else "[x] Dime qué guardar: guarda recuerdo: …"
        m = re.match(r"^olvida recuerdo\s*#?\s*(\d+)\s*$", cmd_lower)
        if m:
            return (f"[OK] Recuerdo #{m.group(1)} olvidado." if rec.olvidar(int(m.group(1)))
                    else f"[x] No tengo el recuerdo #{m.group(1)}.")
        m = re.match(r"^parecido\s*:?\s*([^=]+?)\s*=\s*(.+)$", command.strip(), re.I)
        if m:
            k = rec.aprender_sinonimos(m.group(1), re.split(r"[,;]", m.group(2)))
            return (f"[OK] Aprendido: «{m.group(1).strip()}» se parece a {m.group(2).strip()}." if k
                    else "[i] Ya lo sabía (o no entendí las palabras). Usa: parecido: minino = gato, felino")
        if cmd_lower.startswith("parecido"):
            return "[i] Usa: parecido: minino = gato, felino"
        if cmd_lower.startswith("olvida recuerdo"):
            return "[i] Usa: olvida recuerdo N (el número sale en «qué recuerdas de …»)."
        m = re.match(r"^(?:qu[eé] recuerdas de|recuerdos de|busca en tus recuerdos)\s*:?\s*(.+?)\??$", command.strip(), re.I)
        if m:
            return recuerdos_kira.texto_lista(rec.buscar(m.group(1), n=5))
        return rec.estado_texto()

    def _orden_estudio(self, command, cmd_lower):
        est = getattr(self, "estudio", None)
        if est is None:
            return "[x] No puedo estudiar: el baúl de recuerdos no está disponible."
        if cmd_lower.startswith("aprende sola"):
            est.poner_sola(True)
            return ("[OK] Voy a estudiar sola: un tema del plan cada 10 minutos mientras la app esté abierta, y lo "
                    "guardo en mi baúl. «deja de aprender» para parar; «plan de estudio» para ver por dónde voy.")
        if cmd_lower.startswith("deja de aprender"):
            est.poner_sola(False)
            return "[OK] Dejo de estudiar sola. Lo aprendido se queda en mi baúl."
        if cmd_lower.startswith("plan de estudio"):
            return est.texto_plan()
        m = re.match(r"^estudia\s+python\s*:?\s*([a-z_.]*)\s*$", cmd_lower)
        if m:
            try:
                n = est.estudiar_python(m.group(1) or None)
            except ValueError as e:
                return f"[x] {e}"
            return (f"[OK] He leído la documentación de Python{' de ' + m.group(1) if m.group(1) else ''} que trae el "
                    f"móvil: {n} ficha(s) nuevas. Pregúntame, por ejemplo: «qué hace json.loads».")
        m = re.match(r"^estudia\s*:?\s*(.+)$", command.strip(), re.I)
        if m:
            try:
                titulos = est.estudiar(m.group(1))
            except ValueError as e:
                return f"[x] {e}"
            except Exception as e:
                return f"[x] No pude conectar con la Wikipedia ({str(e)[:120]}). ¿Hay internet?"
            if not titulos:
                return "[i] No he encontrado nada nuevo sobre eso (o ya lo sabía)."
            return ("[OK] He estudiado y guardado: " + "; ".join(titulos) + ". (Fuente: Wikipedia.) "
                    "Pregúntame sobre ello cuando quieras.")
        return est.estado_texto() + "\n" + (self.recuerdos.estado_texto() if self.recuerdos else "")

    # ---------- acciones con confirmación ----------
    def _ejecutar_pendiente(self):
        tipo, arg = self.accion_pendiente
        self.accion_pendiente = None
        if tipo == "destruir":
            if os.path.isfile(arg):
                os.remove(arg)
                logger.warning(f"Archivo destruido de forma permanente: {arg}")
                return f"[!] Documento destruido permanentemente: {arg}"
            return f"[x] El archivo '{arg}' ya no existe."
        if tipo == "matar":
            cerrados = 0
            for proc in psutil.process_iter(['name']):
                if (proc.info['name'] or "").lower() == arg.lower():
                    try:
                        proc.kill()
                        cerrados += 1
                    except Exception as e:
                        logger.error(f"No se pudo cerrar {arg}: {e}")
            logger.warning(f"Proceso finalizado por orden directa: {arg} ({cerrados} instancias)")
            return f"[!] Proceso '{arg}' finalizado ({cerrados} cerrados)."
        return "[x] Acción desconocida."

    # ---------- núcleo ----------
    def procesar_orden(self, command: str) -> str:
        """Núcleo universal de ejecución rápida y control."""
        cmd_lower = command.lower().strip()

        # La clave de API nunca pasa por el búfer ni por el log
        if cmd_lower.startswith("config clave:"):
            clave = command.split(":", 1)[1].strip()
            if len(clave) < 20:
                return "[x] La clave parece demasiado corta."
            ruta = os.path.join(self.dir, "api_key.txt")
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(clave)
            try:
                os.chmod(ruta, 0o600)
            except Exception:
                pass
            logger.info("Clave de API actualizada (valor no registrado).")
            return "[OK] Clave guardada. Ya puedes usar: mejorar <lo que quieres>"

        self.registrar_buffer_volatil(command)

        # Bitácora: pasos que recuerda, diagnóstico de fallos, notas
        import bitacora_kira
        r = bitacora_kira.responder(self.bitacora, command)
        if r is not None:
            return r

        # Confirmación de acciones destructivas
        if self.accion_pendiente:
            if cmd_lower == "confirmar":
                return self._ejecutar_pendiente()
            self.accion_pendiente = None  # cualquier otra cosa cancela

        if "auditar" in cmd_lower or "seguridad" in cmd_lower:
            logger.info("Auditoría solicitada.")
            fallos = f" Fallaron: {', '.join(self.errores_modulos)}." if self.errores_modulos else ""
            return (f"[i] Estado real (no es un análisis de seguridad completo): clave API "
                    f"{'guardada' if self._leer_clave_api() else 'NO guardada'} (cerebro de IA: {self.cerebro_activo() or 'ninguno'}); {len(self.comandos_modulos)} comando(s) de "
                    f"módulos cargados.{fallos} psutil {'disponible' if PSUTIL_AVAILABLE else 'no disponible'}. "
                    "Las mejoras solo se aplican con tu confirmación en el panel.")
        elif cmd_lower.startswith("acuérdate de:") or cmd_lower.startswith("aprender:"):
            try:
                partes = command.split(":", 1)[1].split("=", 1)
                if len(partes) == 2:
                    clave, valor = partes[0].strip(), partes[1].strip()
                    return self.aprender_inteligentemente(clave, valor)
                else:
                    return "[!] Formato incorrecto. Usa: acuérdate de: [tema] = [información]"
            except Exception as e:
                return f"[x] Error en procesamiento de memoria: {e}"
        elif cmd_lower.startswith("consultar memoria:") or cmd_lower.startswith("qué sabes de:"):
            clave = command.split(":", 1)[1].strip().lower()
            return self.memory.get(clave, "No tengo constancia de ese dato en mi memoria permanente.")
        elif cmd_lower.startswith("listar procesos"):
            if not PSUTIL_AVAILABLE:
                return "[x] El módulo 'psutil' no está instalado en este entorno para listar procesos."
            procesos = [p.info['name'] for p in psutil.process_iter(['name']) if p.info['name']][:10]
            return f"[OK] Procesos activos principales: {', '.join(procesos)}"
        elif cmd_lower.startswith("matar proceso:"):
            if not PSUTIL_AVAILABLE:
                return "[x] El módulo 'psutil' no está instalado para gestionar procesos."
            nombre_proc = command.split(":", 1)[1].strip()
            if not nombre_proc:
                return "[x] Indica el nombre exacto del proceso."
            n = sum(1 for p in psutil.process_iter(['name'])
                    if (p.info['name'] or "").lower() == nombre_proc.lower())
            if n == 0:
                return f"[x] No hay procesos con el nombre exacto '{nombre_proc}'."
            self.accion_pendiente = ("matar", nombre_proc)
            return f"[!] Se cerrarán {n} proceso(s) llamados '{nombre_proc}'. Escribe: confirmar"
        elif cmd_lower.startswith("analizar vision:") or cmd_lower.startswith("ver archivo:"):
            path_img = command.split(":", 1)[1].strip()
            if os.path.exists(path_img):
                logger.info(f"Escaneo de visión ejecutado sobre: {path_img}")
                return f"[OK] El archivo existe: '{path_img}'. (Todavía no se analiza su contenido.)"
            return f"[x] El archivo visual '{path_img}' no existe."
        elif cmd_lower.startswith("crear carpeta:"):
            folder = command.split(":", 1)[1].strip()
            os.makedirs(folder, exist_ok=True)
            logger.info(f"Carpeta creada: {folder}")
            return f"[OK] Carpeta creada: {folder}"
        elif cmd_lower.startswith("destruir archivo:") or cmd_lower.startswith("destruir:"):
            target = command.split(":", 1)[1].strip()
            if os.path.isfile(target):
                self.accion_pendiente = ("destruir", target)
                return f"[!] Se borrará PARA SIEMPRE: {target}. Escribe: confirmar"
            return f"[x] El archivo '{target}' no se encuentra."
        elif cmd_lower == "terminar charla" or cmd_lower == "cerrar sesión":
            self.limpiar_buffer_volatil()
            return "[OK] Conversación finalizada. Búfer volátil de RAM purgado y destruido."
        elif cmd_lower == "cerebro" or cmd_lower.startswith("cerebro "):
            import cerebro_ia_kira
            arg = command.strip()[7:].strip()
            try:
                if arg.lower() in cerebro_ia_kira.MOTORES:
                    self.cerebro_ia.poner_motor(arg.lower())
                    return "[OK] Cerebro en modo «" + arg.lower() + "».\n" + self.cerebro_ia.estado_texto(self._leer_clave_api())
                if arg.lower().startswith("mejoras "):
                    self.cerebro_ia.poner_codigo(arg[8:].strip().lower())
                    return "[OK] Para programar mejoras: «" + self.cerebro_ia.codigo + "».\n" + self.cerebro_ia.estado_texto(self._leer_clave_api())
                if arg.lower().startswith("url:") or arg.lower().startswith("url "):
                    self.cerebro_ia.poner_url(arg[4:].strip())
                    return "[OK] Dirección guardada.\n" + self.cerebro_ia.estado_texto(self._leer_clave_api())
                if arg:
                    return "[i] Usa: cerebro | cerebro local | cerebro claude | cerebro auto | cerebro url: http://127.0.0.1:8080"
            except cerebro_ia_kira.CerebroError as e:
                return f"[x] {e}"
            return self.cerebro_ia.estado_texto(self._leer_clave_api())
        elif cmd_lower in ("recuerdos", "baul", "baúl", "baúl de recuerdos", "baul de recuerdos") or \
                re.match(r"^(?:guarda recuerdo|qu[eé] recuerdas de|recuerdos de|busca en tus recuerdos|olvida recuerdo|parecido)\b", cmd_lower):
            return self._orden_recuerdos(command, cmd_lower)
        elif re.match(r"^(?:estudia|aprende sola|deja de aprender|plan de estudio|qu[eé] has aprendido|estudio)\b", cmd_lower):
            return self._orden_estudio(command, cmd_lower)
        elif cmd_lower in ("avisos", "mis avisos"):
            pend = self.avisos.pendientes()
            if not pend:
                return "[i] No hay avisos pendientes."
            return "Avisos pendientes:\n" + "\n".join(f"- dentro de {max(0, s) // 60} min {max(0, s) % 60} s ({m}): {t}"
                                                       for s, m, t in pend)
        elif cmd_lower in ("capacidades", "que te falta", "qué te falta"):
            import capacidades_kira as cap
            return cap.texto_informe(cap.informe(self.hechos_capacidades()))
        elif cmd_lower.startswith("preparar "):
            import capacidades_kira as cap
            c = cap.buscar(cmd_lower[9:])
            if c is None:
                return "[i] No sé a qué capacidad te refieres. Escribe «capacidades» para ver la lista."
            return cap.texto_plan(c, self.hechos_capacidades())
        elif cmd_lower == "recargar modulos":
            n = self.cargar_modulos()
            fallos = f" Fallaron: {', '.join(self.errores_modulos)}." if self.errores_modulos else ""
            juegos = f" Juegos: {', '.join(sorted(self.juegos_modulos))}." if self.juegos_modulos else ""
            return f"[OK] {n} comando(s) de módulos cargados.{juegos}{fallos}"
        else:
            r = self._comando_modulo(cmd_lower, command)
            if r is not None:
                return r
            logger.info(f"Orden general procesada: {command}")
            return f"{self.NO_RECONOCIDA} '{command[:60]}'. Usa 'mejorar <idea>' para pedir una función nueva."

    def run_permanent_loop(self):
        print("\n=== KIRAOS: NÚCLEO SUPREMO (KIRA GOD) ACTIVO ===")
        while True:
            try:
                command = input("[Kira God] >>> ").strip()
                if not command:
                    continue
                if command.lower() == "salir":
                    self.limpiar_buffer_volatil()
                    print("[OK] Apagando el núcleo permanente de Kira de forma segura.")
                    break
                print(self.procesar_orden(command))
            except KeyboardInterrupt:
                self.limpiar_buffer_volatil()
                print("\n[!] Interrupción detectada. Purgando RAM.")
                break


if __name__ == "__main__":
    kira_god = KiraGodCore()
    kira_god.run_permanent_loop()
