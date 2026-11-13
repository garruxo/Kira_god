# -*- coding: utf-8 -*-
"""
escritorio_kira.py - El ESCRITORIO de KiraOS (v2.90): la pantalla principal «como Windows» que sale después del saludo.

Lo pidió el dueño: al entrar en KiraOS, un escritorio con iconos y una barra abajo (eligió «Escritorio + barra
abajo»); cada ventana con un botón para VOLVER a la pantalla principal; y poder HABLAR CON KIRA EN CUALQUIER PUNTO DEL
SISTEMA: escribes o hablas en la barra de abajo y Kira te responde POR VOZ, con otro botón en la barra para VER EL
TEXTO de la conversación.

La pantalla es `kiraos_web/escritorio.html` (se dibuja con el motor de Ubuntu, como el arranque). Esto es su puente
con Python: `EscritorioMixin`, que se suma a `kiraos.Api` (el mismo objeto sirve al arranque y al escritorio).
Todo lo que devuelve es texto/datos sencillos (JSON) y se prueba sin ventana (tests/test_escritorio_os.py).

  hablar(texto) → id · tarea_hablar(id) → cómo va (la respuesta va llegando) · al acabar, la DICE en voz alta
  escuchar() → lo que dijiste (oído Vosk) · voz(si/no) · callar()
  barra() → nombre, WiFi y voz para la barra · wifi_datos() / wifi_hacer() · app(nombre) / app_hacer(nombre, accion)
  sistema("apagar"|"reiniciar") → apaga o reinicia el portátil (la pantalla pide confirmación con dos toques)
  v2.91: buscar_web(consulta, tipo) / leer_web(url) / es_busqueda(texto) → el BUSCADOR tipo Google; lo busca y lo lee
  DESDE SU MÁQUINA VIRTUAL (por su puerta, sin ver tu casa) si está; si no, desde el portátil, y lo dice.
"""
import os
import re
import subprocess
import threading
import time
import uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS_NUCLEO = os.environ.get("KIRA_DATOS_NUCLEO", os.path.expanduser("~/kira_portatil/kira_datos"))

# «busca …» que NO es buscar en internet: son órdenes de Kira (v2.92, revisando la v2.91)
_TRANSITORIA = re.compile(r"^[\s·•\-*]*(?:En cola\b|Pensando…|Pensando\.\.\.|Sigo con|Leyendo\b|Siguiendo el enlace|"
                         r"Estudiando «|Empiezo\b|Un momento)", re.I)

_NO_ES_WEB = re.compile(
    r"\b(?:wi-?fi|bluetooth|brillo|volumen|salvapantallas|aparatos?|dispositivos?|puertos?|pdfs?|recuerdos?|ba[uú]l|notas|cuaderno|soluciones|"
    r"m[aá]quina|emparejar|actualizaci[oó]n(?:es)?|mejoras|novedades|c[oó]digo\s+de\s+emparejar|en\s+(?:mi|tu|la)\s+red|mis\s+documentos|tus\s+documentos|"
    r"tus\s+recetas|tu\s+receta|recetas?\s+de\s+(?:ingenier|grafo|programaci|ciberseg|dise[nñ]|cadena|compresi|"
    r"compilador|sistemas|redes\s+neuronales))", re.I)

# v3.24: la terminal DE VERDAD de Xubuntu (xfce4-terminal), y poder abrir más de una. Se prueba cada programa por orden.
TERMINALES = ("xfce4-terminal", "x-terminal-emulator", "gnome-terminal", "mate-terminal",
              "lxterminal", "qterminal", "konsole", "xterm")

ICONOS = [
    {"id": "hablar", "titulo": "Hablar con Kira", "sub": "la conversación entera"},
    {"id": "buscador", "titulo": "Buscador", "sub": "internet, como Google"},
    {"id": "wifi", "titulo": "WiFi", "sub": "redes y conexión"},
    {"id": "red", "titulo": "Mi red", "sub": "aparatos de casa"},
    {"id": "mapa", "titulo": "Mapa de ataques", "sub": "de dónde intentan entrar"},
    {"id": "maquina", "titulo": "Máquina virtual", "sub": "su Linux de pruebas"},
    {"id": "cuaderno", "titulo": "Cuaderno", "sub": "lo que piensa"},
    {"id": "programando", "titulo": "Programando", "sub": "verla escribir código"},
    {"id": "movil", "titulo": "Móvil", "sub": "sincronía con Kira app"},
    {"id": "terminal", "titulo": "Terminal", "sub": "Linux sin salir de Kira"},
    {"id": "ajustes", "titulo": "Ajustes", "sub": "cerebro, voz, nacimiento"},
]

try:                                              # v3.17: la versión con la que se ABRIÓ esta pantalla
    import version_kira as _vk
    VERSION_AL_ABRIR = _vk.VERSION
except Exception:                                 # noqa: BLE001
    VERSION_AL_ABRIR = "?"


def version_en_disco(ruta=None):
    """v3.17: la versión que hay DESCARGADA en el disco (tras «implementa las mejoras»), sin importarla otra vez."""
    ruta = ruta or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version_kira.py")
    try:
        m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', open(ruta, encoding="utf-8").read())
        return m.group(1) if m else None
    except OSError:
        return None


def estado_version(pantalla, disco=None, nucleo=None):
    """v3.17 (puro): {"version", "texto", "aviso", "al_dia"} para enseñar en el inicio. Si lo descargado, la
    pantalla y el núcleo no van con la MISMA versión, avisa de reiniciar (pasó en la v3.11: el núcleo seguía viejo)."""
    pantalla = str(pantalla or "?")
    aviso = ""
    if disco and disco != pantalla:
        aviso = (f"Ya tengo descargada la {disco}, pero esta pantalla aún va con la {pantalla}: reinicia el portátil "
                 "para estrenarla.")
    elif nucleo and nucleo != pantalla:
        aviso = (f"Mi núcleo va con la {nucleo} y la pantalla con la {pantalla}: reinicia el portátil para que "
                 "vayan iguales.")
    texto = f"KiraOS versión {pantalla}" + ("" if aviso else (" · todo con la misma versión" if nucleo else ""))
    return {"version": pantalla, "texto": texto, "aviso": aviso, "al_dia": not aviso,
            "disco": disco, "nucleo": nucleo}


def para_voz(texto, maximo=420):
    """Lo que se DICE en voz alta: sin bloques de código, sin enlaces, sin marcas; corto (el resto se lee en el texto)."""
    t = re.sub(r"```.*?(```|$)", " (te dejo el código en el texto) ", str(texto or ""), flags=re.S)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"^\s*[─━=\-]{3,}.*$", "", t, flags=re.M)
    t = t.replace("[x] ", "").replace("[OK] ", "").replace("[i] ", "").replace("·", ",")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= maximo:
        return t
    corte = max(t.rfind(". ", 0, maximo), t.rfind("? ", 0, maximo), t.rfind("! ", 0, maximo))
    return (t[:corte + 1] if corte > maximo // 3 else t[:maximo].rsplit(" ", 1)[0] + "…") + \
        " El resto lo tienes en el texto."


def callar_voz(correr=None):
    """Para lo que esté diciendo (spd-say / espeak)."""
    correr = correr or (lambda orden: subprocess.run(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                     timeout=5))
    for orden in (["spd-say", "-C"], ["pkill", "-f", "espeak"]):
        try:
            correr(orden)
        except Exception:
            pass
    return True


class EscritorioMixin:
    """Se suma a kiraos.Api. Usa: self.cli (el cerebro de casa), self._hablar (la voz)."""

    # ---------- piezas (se pueden cambiar en las pruebas) ----------
    def _ini_escritorio(self):
        if getattr(self, "_esc_listo", False):
            return
        self._esc_listo = True
        self._charlas = {}
        self._lock_charla = threading.Lock()
        self.voz_activa = True

    def _nucleo(self):
        if getattr(self, "nucleo_cli", None) is not None:
            return self.nucleo_cli
        if self.cli is None:
            return None
        try:
            import kira_escritorio as ke
            n = ke.nucleo_para(self.cli)
            return n if n.disponible() else None
        except Exception:
            return None

    def _wifi(self):
        if getattr(self, "wifi_mod", None) is not None:
            return self.wifi_mod
        import wifi_kira
        return wifi_kira

    # ---------- la barra ----------
    def barra(self):
        self._ini_escritorio()
        w = {}
        try:
            w = self._wifi().resumen_corto()
        except Exception:
            pass
        p = {}
        try:
            import nacimiento_kira as nk
            p = nk.cargar(getattr(self, "ruta_nac", None)) or {}
        except Exception:
            pass
        return {"llamar": p.get("llamar", ""), "wifi": w, "voz": self.voz_activa, "iconos": ICONOS,
                "extras": [dict({k: v.get(k, "") for k in ("id", "en", "titulo", "icono")},
                                **({"lugar": v["lugar"], "texto": v.get("texto", ""), "botones": v.get("botones", [])}
                                   if v.get("lugar") in ("arriba", "abajo") else {}))
                           for v in self.ventanas_extra()],
                "accesos": self.accesos(),                    # v3.26: accesos directos de los programas creados
                "aspecto": self.aspecto()}

    # ---------- v3.26: accesos directos de los programas que Kira creó (icono en el escritorio; clic derecho ▸ desinstalar) ----------
    def accesos(self):
        try:
            import accesos_kira as ak
            return [{k: a.get(k) for k in ("id", "titulo", "icono", "tipo", "tiene_html")}
                    for a in ak.listar(DATOS_NUCLEO)]
        except Exception:
            return []

    def abrir_acceso(self, iid):
        """Abre el acceso directo: un programa de Kira se muestra como app web; una app EXTERNA (v3.28) se LANZA en el
        portátil (clic en su icono = abrirla)."""
        try:
            import accesos_kira as ak
            a = ak.uno(DATOS_NUCLEO, iid) or {}
            if a.get("tipo") == "externa":
                try:
                    import apps_externas_kira as aex
                    r = aex.lanzar(a)
                except Exception as e:                    # noqa: BLE001
                    r = {"ok": False, "mensaje": str(e)}
                return {"titulo": a.get("titulo", "App"), "externa": True,
                        "lanzada": bool(r.get("ok")), "mensaje": r.get("mensaje", "")}
            return {"titulo": a.get("titulo", "Programa"), "html": ak.html_de(DATOS_NUCLEO, iid)}
        except Exception as e:
            return {"titulo": "Programa", "html": "", "error": str(e)}

    def desinstalar_acceso(self, iid):
        """Clic derecho ▸ Desinstalar: quita el icono del escritorio y borra su app web."""
        try:
            import accesos_kira as ak
            return {"ok": bool(ak.quitar(DATOS_NUCLEO, iid))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def instalar_web(self, url=None, forzar=False):
        """v3.31: descarga e INSTALA lo que el dueño está viendo en el Buscador (o la URL que se pasa), sea lo que sea
        (AppImage, .deb, comprimido…), y deja su ICONO en el escritorio. Si la URL es una página, busca en ella el
        enlace de descarga. Devuelve el texto para enseñar. Solo con la orden del dueño; sin administrador por defecto."""
        import apps_externas_kira as aex
        import accesos_kira as ak
        if forzar and getattr(self, "_app_bloqueada", ""):   # «instálalo igualmente» tras un aviso
            fuente = self._app_bloqueada
        else:
            url = str(url or getattr(self, "_pagina_vista", "") or "").strip()
            if not url:
                return ("No sé qué instalar: abre antes en el Buscador la página del programa que quieres y dime "
                        "«descarga e instala esto».")
            fuente = url
            if not aex.es_descargable(url) and aex.metodo(url) != "github":   # es una página: busco el archivo en ella
                try:
                    html = aex._traer_texto(url)
                except Exception as e:                # noqa: BLE001
                    return f"No pude abrir «{url}» para buscar la descarga: {e}"
                mejor = aex.elegir_descarga(aex.enlaces_descarga(html, url))
                if not mejor:
                    return ("No encontré en esta página un archivo que sepa instalar (AppImage, .deb, .tar.gz, .zip…). "
                            "Entra en su página de descargas y dímelo ahí, o pégame el enlace directo del archivo.")
                fuente = mejor
        r = aex.instalar(fuente, forzar=forzar)
        if r.get("peligro"):
            self._app_bloqueada = fuente              # para «instálalo igualmente»
            return r.get("mensaje", "No la instalo.")
        if not r.get("ok"):
            return r.get("mensaje", "No pude instalarla.")
        self._app_bloqueada = ""
        iid = ak.anadir_externa(DATOS_NUCLEO, r["nombre"], r.get("lanzar") or [], r.get("carpeta") or "")
        extra = "" if iid else " (ya la tenías)"
        dep_aviso = aex.aviso_dependencias(r.get("dependencias"), r["nombre"])   # v3.32: si le hace falta algo, pregunta
        return (r.get("mensaje", "Instalada.") + extra + " Ya está su icono en el escritorio: púlsalo para abrirla, "
                "clic derecho para desinstalarla." + dep_aviso)

    # ---------- v3.21: lo que el dueño ha cambiado de su sistema (tema, iconos, salvapantallas…) ----------
    def aspecto(self):
        try:
            import sistema_kira
            return sistema_kira.para_pantalla(getattr(self, "ruta_sistema", None))
        except Exception:
            return {}

    # ---------- v3.19: las ventanas/secciones/botones que Kira se añadió (solo datos: texto y botones) ----------
    def ventanas_extra(self):
        ahora = time.time()
        c = getattr(self, "_extras_cache", None)
        if c and ahora - c[0] < 10:
            return c[1]
        lista = []
        n = self._nucleo()
        if n is not None and hasattr(n, "ventanas"):
            try:
                import ventanas_kira as vk
                for v in n.ventanas() or []:
                    try:                                  # se vuelve a validar aquí: la pantalla no se fía de nadie
                        lv = vk.validar(v.get("id"), {k: v.get(k) for k in ("en", "titulo", "texto", "botones", "icono", "lugar")
                                                             if k not in ("icono", "lugar") or v.get(k)})
                        lv["modulo"] = str(v.get("modulo") or "")[:60]
                        lista.append(lv)
                    except Exception:
                        continue
            except Exception:
                lista = []
        self._extras_cache = (ahora, lista)
        return lista

    def _app_extra(self, ident):
        v = next((x for x in self.ventanas_extra() if x["id"] == ident), None)
        if v is None:
            return {"titulo": ident, "texto": "Esta ventana ya no está (puede que se quitara su mejora).", "botones": []}
        nota = (f"\n\n— Me la añadí yo (mejora «{v['modulo']}»). Para cambiarla, dime: «cambia la ventana {v['id']}: "
                "…lo que quieras…». Los botones me dan órdenes, como si me las dijeras tú.")
        return {"titulo": v["titulo"], "texto": (v["texto"] or "") + nota,
                "botones": [{"texto": b["texto"], "accion": "decir:" + b["orden"]} for b in v["botones"]]}

    # ---------- v3.17: la VERSIÓN en el inicio ----------
    def version(self):
        nucleo = None
        n = self._nucleo()
        if n is not None and hasattr(n, "hola"):
            try:
                nucleo = (n.hola() or {}).get("version")
            except Exception:
                nucleo = None
        return estado_version(VERSION_AL_ABRIR, version_en_disco(), nucleo)

    # ---------- v3.17: la TERMINAL (Linux sin salir de Kira; solo en este portátil) ----------
    def _term(self):
        t = getattr(self, "_terminal", None)
        if t is None:
            import terminal_kira
            t = self._terminal = terminal_kira.Terminal()
        return t

    def terminal_abrir(self):
        t = self._term()
        if not t.vivo:
            t.iniciar()
            time.sleep(0.3)
        return t.leer(0)

    def terminal_leer(self, desde=0):
        return self._term().leer(desde)

    def terminal_escribir(self, linea, clave=False):
        self._term().escribir(linea, bool(clave))
        return True

    def terminal_tecla(self, nombre):
        return self._term().tecla(nombre)

    def terminal_completar(self, linea):
        return self._term().completar(linea)

    def terminal_limpiar(self):
        return self._term().limpiar_pantalla()

    def terminal_nueva(self):
        t = getattr(self, "_terminal", None)
        if t is not None:
            t.cerrar()
        self._terminal = None
        return self.terminal_abrir()

    def terminal_externa(self):
        """v3.24: abre la terminal DE VERDAD de Xubuntu (xfce4-terminal) en una VENTANA APARTE. Se puede llamar varias
        veces para abrir más de una. Devuelve {"ok", "cual"} o {"ok": False, "motivo"} si no hay ninguna instalada."""
        import shutil
        env = dict(os.environ)
        env.setdefault("DISPLAY", ":0")
        for prog in TERMINALES:
            ruta = shutil.which(prog)
            if not ruta:
                continue
            try:
                subprocess.Popen([ruta], env=env, start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                return {"ok": False, "motivo": str(e)}
            return {"ok": True, "cual": prog}
        return {"ok": False, "motivo": "no hay ninguna terminal de Xubuntu instalada"}

    # ---------- HABLAR CON KIRA (desde cualquier sitio) ----------
    def hablar(self, texto):
        """Empieza a contestar `texto` (escrito o dicho). Devuelve {"id"}; la respuesta se va leyendo con
        tarea_hablar(id) y, al acabar, Kira la DICE en voz alta (si la voz está puesta)."""
        self._ini_escritorio()
        texto = str(texto or "").strip()
        if not texto:
            return {"error": "vacío"}
        cid = uuid.uuid4().hex[:10]
        t = {"id": cid, "estado": "pensando", "respuesta": "", "lineas": [], "pedir_clave": None, "inicio": time.time()}
        with self._lock_charla:
            self._charlas[cid] = t
            for viejo in sorted(self._charlas, key=lambda k: self._charlas[k]["inicio"])[:-20]:
                self._charlas.pop(viejo, None)
        threading.Thread(target=self._contestar, args=(t, texto), daemon=True).start()
        return {"id": cid}

    def _contestar(self, t, texto):
        try:
            o_s = None
            try:                                                   # v3.21: cambiar el sistema se hace AQUÍ, al
                import sistema_kira                                # momento (no espera en la cola del núcleo)
                o_s = sistema_kira.orden(texto)
            except Exception:
                o_s = None
            inst_esto = False                                      # v3.31: «descarga e instala esto» (lo que ve en el Buscador)
            try:
                import apps_externas_kira as _aex
                inst_esto = bool(_aex.es_orden_instalar_esto(texto) or
                                 (_aex.quiere_forzar(texto) and getattr(self, "_app_bloqueada", "")))
            except Exception:
                inst_esto = False
            if o_s is not None:
                try:
                    ex = [(v["id"], v["titulo"]) for v in self.ventanas_extra() if v.get("en") == "escritorio"]
                except Exception:
                    ex = []
                t["respuesta"] = sistema_kira.hacer(o_s[0], o_s[1], ruta=getattr(self, "ruta_sistema", None),
                                                    equipo=getattr(self, "equipo_sis", None), extras=ex)
                t["aspecto"] = True                                # la pantalla se vuelve a pintar
                if o_s[0] == "salva_ver":
                    t["salvapantallas"] = True
            elif inst_esto:
                t["estado"] = "hablando"
                t["respuesta"] = self.instalar_web(forzar=_aex.quiere_forzar(texto))
                t["barra"] = True                                  # refrescar iconos del escritorio
            elif self.cli is None:
                t["respuesta"] = ("No encuentro mi cerebro de casa (el servidor de Kira). Si acabas de encender, "
                                  "espera un minuto y vuelve a hablarme.")
            else:
                import kira_escritorio as ke
                ctx = {}

                def trozo(x):
                    t["estado"] = "hablando"
                    t["respuesta"] += x
                ke.manejar(self.cli, texto, t["lineas"].append, trozo, nucleo=self._nucleo(), ctx=ctx,
                           wifi=getattr(self, "wifi_mod", None))
                t["pedir_clave"] = ctx.get("pedir_clave")
                self._recordar_codigo(texto, t["lineas"])
                if t["respuesta"].strip() or any(not _TRANSITORIA.match(str(x)) for x in t["lineas"]):  # ya contestó
                    t["lineas"][:] = [x for x in t["lineas"] if not _TRANSITORIA.match(str(x))]
        except Exception as e:                                     # noqa: BLE001 - la pantalla nunca se queda colgada
            t["respuesta"] = f"[x] Algo falló: {e}"
        t["estado"] = "hecho"
        decir = (t["respuesta"].strip() + "\n" + "\n".join(t["lineas"])).strip()
        if self.voz_activa and decir:
            try:
                self._hablar(para_voz(decir))
            except Exception:
                pass

    def _recordar_codigo(self, pedido, lineas):
        """Si Kira acaba de escribir código, lo deja listo para la ventana «Programando» (lo escribe en vivo y lo
        explica línea a línea)."""
        for linea in lineas:
            m = re.match(r"^── código \((?P<n>[^)]*)\) ──\n(?P<c>.+)$", str(linea), flags=re.S)
            if m:
                try:
                    import explicacion_codigo_kira as ex
                    r = ex.explicar(m.group("c"))
                    self.programa = {"pedido": pedido, "archivo": (m.group("n") or "programa") + ".py",
                                     "lineas": r["lineas"], "resumen": r["resumen"], "estado": "listo",
                                     "codigo": m.group("c"), "cuando": time.time()}
                except Exception:
                    pass

    def hay_programa(self):
        """v3.14: también cuando el núcleo está escribiendo código ahora mismo (o ya escribió alguno)."""
        if getattr(self, "programa", None):
            return True
        try:
            return bool(self.programando_vivo())
        except Exception:
            return False

    def programando_vivo(self):
        """v3.14: lo que enseña «Programando»: si Kira está escribiendo código AHORA (en su núcleo), ese código según
        lo escribe (`en_vivo`); si no, el último que escribió; si no, el de esta charla. {} si no hay nada."""
        n = self._nucleo()
        e = {}
        if n is not None and hasattr(n, "estado"):
            try:
                e = n.estado() or {}
            except Exception:
                e = {}
        piz = (e.get("pizarra") or {}) if e.get("ocupada") else {}
        cod = codigo_de_pizarra(piz.get("texto", "")) if piz else ""
        haciendo = str(e.get("haciendo") or "")
        if cod.strip():
            r = _explicado(cod, haciendo, "en_vivo", e.get("avance") or "")
            r["fase"] = fase_cerebro(piz, e.get("inicio"))
            return r
        if e.get("ocupada") and _PROGRAMA.search(haciendo):
            return {"pedido": haciendo, "archivo": "…", "lineas": [], "resumen": "", "estado": "esperando",
                    "avance": e.get("avance") or "", "codigo": "", "fase": fase_cerebro(piz, e.get("inicio"))}
        propio = getattr(self, "programa", None)
        ult = e.get("ultimo_codigo") or {}
        if ult.get("codigo") and (not propio or float(ult.get("cuando") or 0) >= float(propio.get("cuando") or 0)):
            return _explicado(ult["codigo"], ult.get("orden") or "", "listo", "", ult.get("nombre"))
        return propio or {}

    def tarea_hablar(self, cid):
        t = getattr(self, "_charlas", {}).get(str(cid))
        if not t:
            return {"estado": "no existe"}
        r = {k: t[k] for k in ("estado", "respuesta", "lineas", "pedir_clave")}
        for k in ("aspecto", "salvapantallas"):
            if t.get(k):
                r[k] = True
        return r

    def voz_activa_poner(self, encender):
        self._ini_escritorio()
        self.voz_activa = bool(encender)
        if not encender:
            callar_voz()
        return self.voz_activa

    def callar(self):
        return callar_voz()

    def escuchar(self):
        """Pulsaste el micrófono: escucha tu frase y devuelve {"ok", "texto"} o {"ok": False, "error"}."""
        callar_voz()                                  # que no se oiga a sí misma
        oir = getattr(self, "oido", None)
        try:
            if oir is None:
                import oido_portatil as op
                oir = op.escuchar
            texto = oir()
        except Exception as e:                        # noqa: BLE001
            return {"ok": False, "error": str(e)}
        return {"ok": bool(texto), "texto": texto or "", "error": "" if texto else "No te he oído. ¿Lo repites?"}

    # ---------- OCUPADA / COLA / PARAR / PAUSAR (v2.95) ----------
    def trabajo(self):
        """Para la barra: ¿está ocupada?, ¿cuántas tareas esperan?, ¿pausada?, y qué hace por su cuenta. Cacheado
        2,5 s para no machacar al núcleo."""
        ahora = time.time()
        cache = getattr(self, "_trab_cache", None)
        if cache and ahora - cache[0] < 2.5:
            return cache[1]
        n = self._nucleo()
        if n is None or not hasattr(n, "estado"):
            d = {"nucleo": False, "ocupada": False, "en_cola": 0, "pausada": False, "haciendo": "", "que": "", "cola": [],
                 "modo": "Sin tareas", "eta": ""}
        else:
            e = n.estado() or {}
            act = e.get("actividad") or {}
            if e.get("ocupada"):
                que = e.get("haciendo") or "una tarea"
            elif act.get("estudiando"):
                que = "estudiando"
            elif act.get("foco"):
                que = "pensando en: " + str(act.get("foco"))
            elif act.get("pensando"):
                que = "pensando"
            else:
                que = ""
            d = {"nucleo": True, "ocupada": bool(e.get("ocupada")), "en_cola": int(e.get("en_cola") or 0),
                 "pausada": bool(e.get("pausada")), "haciendo": e.get("haciendo", ""), "que": que,
                 "cola": e.get("cola", [])}
            d.update(estado_orbe(e, ahora))
            d["ir"] = destino_orbe(dict(d, actividad=act))
        self._trab_cache = (ahora, d)
        return d

    def parar(self):
        """El botón de PARAR: corta lo que esté haciendo ahora (la cola sigue con lo siguiente)."""
        n = self._nucleo()
        self._trab_cache = None
        if n is None or not hasattr(n, "cancelar"):
            return {"ok": False, "texto": "Ahora mismo no estoy haciendo ninguna tarea."}
        try:
            n.cancelar()
        except Exception:
            pass
        return {"ok": True, "texto": "He parado lo que estaba haciendo."}

    def pausar_trabajo(self, si=True):
        """El botón de PAUSAR / SEGUIR: pausa (deja de empezar tareas y de pensar sola) o reanuda."""
        n = self._nucleo()
        self._trab_cache = None
        if n is None or not hasattr(n, "pausar"):
            return {"ok": False, "pausada": False}
        try:
            r = n.pausar(True) if si else n.seguir()
        except Exception:
            r = {}
        return {"ok": True, "pausada": bool(r.get("pausada", si))}

    # ---------- WiFi ----------
    def wifi_datos(self):
        wk = self._wifi()
        try:
            return {"ok": True, "estado": wk.texto_estado(wk.estado()), "redes": wk.redes()}
        except Exception as e:                        # noqa: BLE001
            return {"ok": False, "estado": f"[x] {e}", "redes": []}

    def wifi_hacer(self, accion, ssid="", clave=None):
        """accion: conectar | desconectar | apagar | encender | arreglar | olvidar. La clave llega solo desde esta
        pantalla (del portátil) y no se guarda en Kira."""
        wk = self._wifi()
        try:
            if accion == "conectar":
                return {"ok": True, "texto": wk.conectar(ssid, clave or None)}
            if accion == "olvidar":
                return {"ok": True, "texto": wk.olvidar(ssid)}
            hacer = {"desconectar": wk.desconectar, "apagar": lambda: wk.radio(False),
                     "encender": lambda: wk.radio(True), "arreglar": wk.reparar}.get(accion)
            if hacer is None:
                return {"ok": False, "texto": "No conozco esa acción de WiFi."}
            return {"ok": True, "texto": hacer()}
        except Exception as e:                        # noqa: BLE001
            return {"ok": False, "texto": f"[x] {e}"}

    # ---------- BUSCADOR tipo Google (v2.91) ----------
    def _red_web(self):
        """Lo que se busca y se lee sale desde su máquina virtual (si puede); se pone una vez."""
        if getattr(self, "red_web", None) is not None or getattr(self, "usar_maquina", True) is False:
            return getattr(self, "red_web", None)
        try:
            import maquina_kira as mq
            import red_kira
            self.red_web = mq.RedMaquina(mq.Maquina())
            red_kira.poner_investigar(self.red_web.abrir)
        except Exception:                             # noqa: BLE001
            self.red_web = None
        return self.red_web

    def _internet(self):
        if getattr(self, "internet_obj", None) is None:
            import internet_kira
            self._red_web()
            self.internet_obj = internet_kira.Internet(os.path.join(DATOS_NUCLEO, "internet"))
        return self.internet_obj

    def _via(self):
        r = getattr(self, "red_web", None)
        return ("Buscado " + r.estado()) if r is not None else "Buscado desde el portátil"

    def es_busqueda(self, texto):
        """¿Lo que dijiste/escribiste en la barra es «busca …» EN INTERNET? Entonces se abre el buscador: {consulta,
        tipo}. Las órdenes de Kira que también empiezan por «busca» (la WiFi, tus aparatos, tus PDF, sus recuerdos,
        sus recetas, su máquina…) NO: siguen yendo a Kira como siempre."""
        import internet_kira as ik
        t = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(texto or ""), flags=re.I).strip()
        if _NO_ES_WEB.search(t) or re.match(r"^(?:busca(?:me)?|buscar)\s+(?:las\s+)?redes\s*$", t, flags=re.I):
            return None
        try:
            import wifi_kira
            if wifi_kira.orden_wifi(t) is not None:
                return None
        except Exception:                             # noqa: BLE001
            pass
        m = re.match(r"^(?:busca(?:me)?|buscar)\s+en\s+google\s+(.+)$", t, flags=re.I)
        if m:
            return {"consulta": m.group(1).strip(" .?¿!¡"), "tipo": "web"}
        d = ik.interpretar(t)
        if d and d.get("accion") == "buscar":
            return {"consulta": d["consulta"], "tipo": d.get("tipo", "web")}
        return None

    def buscar_web(self, consulta, tipo="web"):
        import internet_kira as ik
        net = self._internet()
        tipo = tipo if tipo in ("web", "codigo", "docs") else "web"
        try:
            res = net.buscar(consulta, tipo=tipo, n=10)
        except Exception as e:                        # noqa: BLE001
            return {"ok": False, "error": str(e), "resultados": [], "via": self._via()}
        return {"ok": True, "consulta": consulta, "tipo": tipo, "via": self._via(),
                "avisos": list(getattr(net, "avisos", []) or [])[:2],
                "resultados": [{"titulo": r.get("titulo", ""), "url": r.get("url", ""), "dominio": ik.dominio(r.get("url", "")),
                                "resumen": r.get("resumen", ""), "fuente": r.get("fuente", "")} for r in res]}

    def leer_web(self, url):
        """La página como TEXTO limpio (sin anuncios ni menús). Nunca se ejecuta nada de ella."""
        import internet_kira as ik
        try:
            pag = self._internet().leer(url)
        except Exception as e:                        # noqa: BLE001
            return {"ok": False, "error": str(e), "via": self._via()}
        self._pagina_vista = pag.get("url", url)      # v3.31: la última página que el dueño ve («descarga e instala esto»)
        todos = pag.get("enlaces") or []
        del_tema = ik.elegir_enlaces(pag, pag.get("titulo", ""), n=25)
        vistos = {e["url"] for e in del_tema}
        enlaces = ([{"url": e["url"], "texto": e.get("texto") or ik.dominio(e["url"]), "tema": True} for e in del_tema] +
                   [{"url": e["url"], "texto": e.get("texto") or ik.dominio(e["url"]), "tema": False}
                    for e in todos if e["url"] not in vistos and e.get("texto")][:max(0, 40 - len(del_tema))])
        return {"ok": True, "titulo": pag.get("titulo", ""), "url": pag.get("url", url), "dominio": ik.dominio(url),
                "texto": str(pag.get("texto", ""))[:30000], "codigos": len(pag.get("codigos") or []),
                "tipo": pag.get("tipo", "web"), "via": self._via(), "enlaces": enlaces,
                "total_enlaces": len(todos)}

    # ---------- las demás ventanas (texto + botones) ----------
    def app(self, nombre):
        """Lo que enseña una ventana: {"titulo", "texto", "botones": [{"texto", "accion"}]}.
        accion: «decir:frase» (se la dice a Kira), «app:otra» (abre otra ventana) o «hacer:x» (app_hacer)."""
        if str(nombre).startswith("extra:"):            # v3.19: una ventana que Kira se añadió
            try:
                return self._app_extra(str(nombre)[6:])
            except Exception as e:                    # noqa: BLE001
                return {"titulo": str(nombre)[6:], "texto": f"[x] No he podido abrirla: {e}", "botones": []}
        try:
            return getattr(self, "_app_" + str(nombre))()
        except AttributeError:
            return {"titulo": str(nombre), "texto": "Esta ventana aún no existe.", "botones": []}
        except Exception as e:                        # noqa: BLE001
            return {"titulo": str(nombre), "texto": f"[x] No he podido abrirla: {e}", "botones": []}

    def app_hacer(self, nombre, accion):
        """Botones «hacer:…» de las ventanas (cosas rápidas que no pasan por la charla)."""
        if nombre == "red":
            import kira_consola as kc
            if accion == "alertas":
                return {"texto": kc.formato_avisos(self.cli.defensa("alertas"))}
            return {"texto": kc.formato_defensa(self.cli.defensa("inventario"))}
        if nombre == "ajustes":
            if accion in ("rapido", "grande") and self.cli is not None:
                self.cli.grande = accion == "grande"
                return {"texto": "Ahora pienso con el cerebro " + ("grande." if self.cli.grande else "rápido.")}
            if accion in ("voz_si", "voz_no"):
                self.voz_activa_poner(accion == "voz_si")
                return {"texto": "Voz " + ("puesta: te contesto hablando." if self.voz_activa else
                                           "quitada: te contesto solo por escrito.")}
        if nombre == "mejoras":                       # v3.07: sus propias mejoras (solo aquí, en el portátil)
            return self._mejoras_hacer(accion)
        if nombre == "cuaderno":                      # v3.10: Parar / Borrar / Empezar de la pestaña Tareas
            return self._tareas_hacer(accion)
        if nombre == "movil" and accion == "codigo":
            return {"texto": codigo_movil()}
        if nombre == "maquina" and accion == "visitas":
            import maquina_kira as mq
            v = mq.Maquina().visitas(15)
            return {"texto": ("Lo último que ha pasado por la puerta de mi máquina (solo el sitio, nunca el contenido):\n"
                              + "\n".join(v)) if v else "Mi máquina aún no ha salido a internet."}
        return {"texto": "No conozco ese botón."}

    # ---------- v3.07: MEJORAS de KiraOS (laboratorio + tus dos toques + volver atrás) ----------
    def _app_mejoras(self):
        n = self._nucleo()
        if n is None:
            return {"titulo": "Mejoras", "texto": "No encuentro mi núcleo: sin él no puedo mirar mis mejoras.",
                    "botones": []}
        try:
            d = n.mejoras()
        except Exception as e:                        # noqa: BLE001
            return {"titulo": "Mejoras", "texto": f"[x] No he podido mirarlas: {e}", "botones": []}
        partes, botones = [], []
        pend = d.get("pendiente")
        if pend:
            partes.append(f"ESPERANDO TU PERMISO: «{pend.get('nombre')}»"
                          + (f" — lo que pediste: {pend.get('pedido')}" if pend.get("pedido") else "")
                          + "\nMi laboratorio la ha " + ("APROBADO." if pend.get("aprobable") else "rechazado.")
                          + "\n\nEl código:\n" + str(pend.get("codigo") or ""))
            if pend.get("aprobable"):
                botones.append({"texto": "Instalar", "accion": "hacer:aplicar", "dos": True})
            botones.append({"texto": "Descartar", "accion": "hacer:rechazar"})
        else:
            partes.append("No tengo ninguna mejora esperando. Pídemela en la barra de abajo, por ejemplo: "
                          "«mejórate: que me digas la hora cuando te pregunte qué hora es». La escribo, la pruebo en "
                          "mi laboratorio y aquí la verás con su código; NO se instala hasta que tú pulses «Instalar» "
                          "dos veces (y solo desde este portátil).")
        inst = d.get("instaladas") or []
        if inst:
            partes.append("INSTALADAS:\n" + "\n".join(
                "· " + m.get("nombre", "?") + (" (órdenes: " + ", ".join(m.get("comandos") or []) + ")"
                                                if m.get("comandos") else "") for m in inst))
            for m in inst[:8]:
                nom = m.get("nombre", "")
                botones.append({"texto": f"Volver atrás «{nom}»", "accion": f"hacer:revertir:{nom}", "dos": True})
                botones.append({"texto": f"Quitar «{nom}»", "accion": f"hacer:quitar:{nom}", "dos": True})
        partes.append("Cada vez que instalo una guardo copia de lo de antes: «Volver atrás» deja la versión anterior "
                      "y «Quitar» la saca (también con copia). Mis mejoras añaden órdenes y funciones; no cambian "
                      "mis pantallas.")
        return {"titulo": "Mejoras", "texto": "\n\n".join(partes), "botones": botones}

    def _tareas_hacer(self, accion):
        partes = str(accion or "").split(":")
        self._trab_cache = None
        if partes[:2] == ["kira", "parar"]:
            r = self.parar()
            return {"texto": r.get("texto", ""), "refrescar": True}
        if partes[:2] == ["kira", "seguir"]:
            self.pausar_trabajo(False)
            return {"texto": "Sigo con la cola.", "refrescar": True}
        if len(partes) == 3 and partes[0] == "tarea" and partes[1] in ("parar", "borrar", "empezar"):
            n = self._nucleo()
            if n is None or not hasattr(n, "tarea_accion"):
                return {"texto": "No encuentro mi núcleo.", "refrescar": False}
            try:
                r = n.tarea_accion(partes[2], partes[1])
            except Exception as e:                    # noqa: BLE001
                return {"texto": texto_error_nucleo(e)}
            return {"texto": r.get("texto", "Hecho."), "refrescar": True}
        if len(partes) == 3 and partes[0] in ("nota", "sol") and partes[1] in ("viable", "implementar", "repensar",
                                                                               "amejora"):
            n = self._nucleo()
            if n is None or not hasattr(n, "cuaderno_accion"):
                return {"texto": "No encuentro mi núcleo.", "refrescar": False}
            try:
                r = n.cuaderno_accion(partes[1], partes[2])
            except Exception as e:                    # noqa: BLE001
                return {"texto": texto_error_nucleo(e)}
            return {"texto": r.get("texto", "Hecho."), "refrescar": True}
        if len(partes) == 3 and partes[0] == "encargo" and partes[1] in ("borrar", "empezar"):
            import investigar_kira as iv
            try:
                i = int(partes[2])
            except ValueError:
                return {"texto": "No conozco ese botón."}
            if partes[1] == "borrar":
                t = iv.quitar(DATOS_NUCLEO, i)
                return {"texto": f"Encargo borrado: «{t}»." if t else "Ese encargo ya no está.", "refrescar": True}
            t = iv.adelantar(DATOS_NUCLEO, i)
            return {"texto": (f"«{t}» pasa el primero: lo investigo en cuanto me ponga a pensar (cuando lleves 5 min "
                              "sin pedirme nada)." if t else "Ese encargo ya no está."), "refrescar": True}
        return {"texto": "No conozco ese botón."}

    def _mejoras_hacer(self, accion):
        n = self._nucleo()
        if n is None:
            return {"texto": "No encuentro mi núcleo.", "refrescar": False}
        partes = str(accion or "").split(":", 1)
        que, nombre = partes[0], (partes[1] if len(partes) > 1 else "")
        if que not in ("aplicar", "rechazar", "revertir", "quitar"):
            return {"texto": "No conozco ese botón."}
        try:
            r = n.mejora(que, nombre, confirmado=que in ("aplicar", "quitar"))
        except Exception as e:                        # noqa: BLE001
            return {"texto": texto_error_nucleo(e)}
        return {"texto": str(r.get("texto", "Hecho.")), "refrescar": True}

    def _app_red(self):
        botones = [{"texto": "Buscar aparatos", "accion": "hacer:inventario"},
                   {"texto": "Avisos de la guardiana", "accion": "hacer:alertas"},
                   {"texto": "Mapa de ataques", "accion": "app:mapa"}]
        if self.cli is None:
            return {"titulo": "Mi red", "texto": "No encuentro mi cerebro de casa: sin él no puedo mirar tu red.",
                    "botones": []}
        return {"titulo": "Mi red", "texto": "Miro tu red de casa SOLO para defenderla (nunca fuera de ella). "
                                             "Pulsa «Buscar aparatos» para ver quién está conectado.",
                "botones": botones}

    def _app_cuaderno(self):
        """v3.08: el cuaderno ORDENADO en pestañas: Pensamiento, Conocimiento, Mejoras (portátil/móvil; se puede o se
        debe) y Tareas (activas, en espera, terminadas)."""
        import json as _json
        import pensador_kira as pn
        import cuaderno_clases_kira as cc
        est = pn.cargar(os.path.join(DATOS_NUCLEO, "pensamientos.json"))

        def leer(nombre, defecto):
            try:
                with open(os.path.join(DATOS_NUCLEO, nombre), encoding="utf-8") as f:
                    return _json.load(f)
            except (OSError, ValueError):
                return defecto
        sistema, trabajo = {"permisos": leer("permisos_pendientes.json", {})}, {}
        try:
            import sincronia_kira as sc
            sistema["para_movil"] = sc.mejoras_para_movil(DATOS_NUCLEO)
        except Exception:
            pass
        n = self._nucleo()
        if n is not None:
            try:
                trabajo = n.estado() or {}
            except Exception:
                trabajo = {}
            try:
                m = n.mejoras()
                sistema["kiraos_pendiente"] = m.get("pendiente")
                sistema["kiraos_instaladas"] = m.get("instaladas") or []
            except Exception:
                pass
        encargos = leer("preguntas_mias.json", [])
        pest = cc.pestanas(est, sistema, trabajo, encargos if isinstance(encargos, list) else [],
                           leer("foco.json", {}))
        for p in pest:                                # v3.09: desde la pestaña Mejoras se instalan (ya no hay icono)
            if p["id"] == "tareas":                   # v3.10: cada tarea con Parar / Borrar / Empezar
                p["filas"] = cc.filas_tareas(trabajo, encargos if isinstance(encargos, list) else [],
                                             leer("foco.json", {}))
                p["botones"] = []
            if p["id"] == "mejoras":
                hay = bool(sistema.get("kiraos_pendiente"))
                p["botones"] = [{"texto": "Instalar o deshacer mis mejoras" + (" (1 esperando)" if hay else ""),
                                 "accion": "app:mejoras"}]
        return {"titulo": "Cuaderno", "texto": pest[0]["texto"], "pestanas": pest,
                "botones": [{"texto": "Piensa una ahora", "accion": "decir:piensa una"},
                            {"texto": "Ponte a pensar", "accion": "decir:piensa"},
                            {"texto": "Deja de pensar", "accion": "decir:deja de pensar"}]}

    def _app_maquina(self):
        """v3.14: la ventana de la máquina EN VIVO: qué hace ahora Kira, lo último que ha ejecutado dentro (comandos y
        lo que salió, de maquina.log) y las páginas que ha visitado (puerta.log). Se refresca sola cada 3 s."""
        import maquina_kira as mq
        try:
            m = mq.Maquina()
            texto = m.estado()
        except Exception as e:                        # noqa: BLE001
            m, texto = None, f"[x] {e}"
        ahora = ""
        n = self._nucleo()
        if n is not None and hasattr(n, "estado"):
            try:
                e = n.estado() or {}
                if e.get("ocupada"):
                    ahora = "AHORA: " + str(e.get("haciendo") or "una tarea") + \
                            (("\n  · " + str(e.get("avance"))) if e.get("avance") else "")
            except Exception:
                pass
        vivo = registro_maquina(getattr(m, "base", mq.BASE)) if m is not None else []
        visitas = m.visitas(8) if m is not None else []
        partes = [texto]
        if ahora:
            partes.append(ahora)
        partes.append("LO QUE HAGO DENTRO (en vivo):\n" + ("\n".join(vivo) if vivo else
                      "  (todavía nada: cuando ejecute, estudie o pruebe algo dentro, lo verás aquí)"))
        if visitas:
            partes.append("PÁGINAS QUE HE VISITADO DESDE DENTRO:\n" + "\n".join("  " + v for v in visitas))
        partes.append("Es un Linux ligero y aislado, sin tus archivos. Desde aquí investigo, busco y experimento: sale "
                      "a internet SOLO por mi puerta, que nunca deja ir a tu casa (ni a este portátil ni a tu router), y "
                      "mis experimentos corren con un usuario sin permisos. Si algo va raro, vuelve sola a su foto "
                      "limpia. «Enséñamela» abre su pantalla de verdad.")
        return {"titulo": "Máquina virtual", "texto": "\n\n".join(partes), "refrescar_cada": 3,
                "botones": [{"texto": "Enciéndela", "accion": "decir:enciende tu máquina"},
                            {"texto": "Enséñamela", "accion": "decir:enséñame tu máquina"},
                            {"texto": "Últimas visitas", "accion": "hacer:visitas"},
                            {"texto": "Que la estudie", "accion": "decir:estudia tu máquina"},
                            {"texto": "Apágala", "accion": "decir:apaga tu máquina"}]}

    def _app_movil(self):
        import sincronia_kira as sc
        e = sc.estado_kiraos(DATOS_NUCLEO)
        if e.get("ultima"):
            mins = int((time.time() - e["ultima"]) // 60)
            t = (f"El móvil se sincronizó conmigo hace {mins} min" if mins < 120 else
                 f"El móvil se sincronizó conmigo hace {mins // 60} h") + \
                f". En total me ha pasado {e.get('recibidos_total', 0)} cosa(s) (se suman, no se borra nada)."
        else:
            t = "El móvil todavía no se ha sincronizado conmigo."
        t += ("\n\nCuando Kira app llega a casa me pasa sola lo que ha aprendido y yo le paso lo mío. Si aún no está "
              "emparejado: en el móvil di «Kira, conéctate al portátil» y dale el código de abajo.")
        try:                                          # v3.00: ¿también fuera de casa (Tailscale)?
            import fuera_kira
            t += "\n\n" + fuera_kira.texto_estado()
        except Exception:
            pass
        return {"titulo": "Móvil", "texto": t, "botones": [{"texto": "Ver el código para emparejar",
                                                             "accion": "hacer:codigo"}]}

    def _app_ajustes(self):
        cual = "grande" if getattr(self.cli, "grande", False) else "rápido"
        partida = ""
        try:
            import nacimiento_kira as nk
            partida = nk.texto_partida(nk.cargar(getattr(self, "ruta_nac", None)))
        except Exception:
            pass
        try:
            import version_kira
            ver = version_kira.VERSION
        except Exception:
            ver = "?"
        sis = ""
        try:                                          # v3.21: lo que le has cambiado a su sistema
            import sistema_kira
            sis = sistema_kira.texto_estado(getattr(self, "ruta_sistema", None))
        except Exception:
            pass
        texto = (f"KiraOS versión {ver}.\nCerebro: {cual}.\nVoz: {'puesta' if self.voz_activa else 'quitada'}."
                 + (f"\n\nMI SISTEMA (cámbialo pidiéndomelo):\n{sis}" if sis else "")
                 + (f"\n\n{partida}" if partida else ""))
        return {"titulo": "Ajustes", "texto": texto,
                "botones": [{"texto": "Cerebro rápido", "accion": "hacer:rapido"},
                            {"texto": "Cerebro grande", "accion": "hacer:grande"},
                            {"texto": "Con voz", "accion": "hacer:voz_si"},
                            {"texto": "Sin voz", "accion": "hacer:voz_no"},
                            {"texto": "Estudia solo lo mío", "accion": "decir:estudia solo lo que yo te mande"},
                            {"texto": "Piensa también libre", "accion": "decir:piensa libre"},
                            {"texto": "Tema noche", "accion": "decir:cambia el tema a noche"},
                            {"texto": "Tema bosque", "accion": "decir:cambia el tema a bosque"},
                            {"texto": "Tema océano", "accion": "decir:cambia el tema a oceano"},
                            {"texto": "Tema fuego", "accion": "decir:cambia el tema a fuego"},
                            {"texto": "Tema violeta", "accion": "decir:cambia el tema a violeta"},
                            {"texto": "Tema claro", "accion": "decir:cambia el tema a claro"},
                            {"texto": "Ver salvapantallas", "accion": "decir:enséñame el salvapantallas"},
                            {"texto": "Más brillo", "accion": "decir:sube el brillo"},
                            {"texto": "Menos brillo", "accion": "decir:baja el brillo"},
                            {"texto": "Más volumen", "accion": "decir:sube el volumen"},
                            {"texto": "Menos volumen", "accion": "decir:baja el volumen"},
                            {"texto": "Bluetooth: aparatos", "accion": "decir:busca aparatos bluetooth"},
                            {"texto": "Deshacer último cambio", "accion": "decir:deshaz el último cambio"}]}

    # ---------- apagar / reiniciar ----------
    # v2.98: apagar/reiniciar prueban varias formas, por orden, hasta que una funcione (antes solo `systemctl` y sin
    # mirar si había funcionado). En Xubuntu, la de la propia sesión (xfce4-session-logout) casi siempre vale.
    ORDENES_SISTEMA = {
        "apagar": (["systemctl", "poweroff"], ["xfce4-session-logout", "--halt", "--fast"],
                   ["dbus-send", "--system", "--print-reply", "--dest=org.freedesktop.login1", "/org/freedesktop/login1",
                    "org.freedesktop.login1.Manager.PowerOff", "boolean:true"]),
        "reiniciar": (["systemctl", "reboot"], ["xfce4-session-logout", "--reboot", "--fast"],
                      ["dbus-send", "--system", "--print-reply", "--dest=org.freedesktop.login1", "/org/freedesktop/login1",
                       "org.freedesktop.login1.Manager.Reboot", "boolean:true"]),
    }

    @staticmethod
    def _correr_sistema(orden):
        """Devuelve (código, error). Si la herramienta no existe, (127, …)."""
        try:
            p = subprocess.run(orden, capture_output=True, text=True, timeout=15)
            return p.returncode, (p.stderr or "").strip()
        except FileNotFoundError:
            return 127, f"no está «{orden[0]}»"
        except subprocess.TimeoutExpired:
            return 0, ""                              # si tarda, es que ya se está apagando

    def sistema(self, accion, correr=None):
        if accion == "salir":
            return self.salir_a_linux()
        ordenes = self.ORDENES_SISTEMA.get(accion)
        if ordenes is None:
            return {"ok": False, "texto": "No conozco esa orden."}
        correr = correr or self._correr_sistema
        try:                                          # v3.21: «al apagar di: …» (se dice antes de apagar)
            import sistema_kira
            adios = sistema_kira.despedida(getattr(self, "ruta_sistema", None))
        except Exception:
            adios = ""
        if adios and getattr(self, "voz_activa", True):
            try:
                self._hablar(adios)
                time.sleep(getattr(self, "pausa_despedida", 3.0))
            except Exception:
                pass
        motivos = []
        for orden in ordenes:
            try:
                r = correr(orden)
            except Exception as e:                    # noqa: BLE001
                motivos.append(str(e))
                continue
            cod, err = (0, "") if r is None else r    # correr de las pruebas: None = fue bien
            if cod == 0:
                return {"ok": True, "texto": (adios or "Hasta luego.") if accion == "apagar" else "Vuelvo enseguida."}
            if err:
                motivos.append(err.splitlines()[-1][:160])
        que = "apagar" if accion == "apagar" else "reiniciar"
        return {"ok": False, "texto": f"No he podido {que} el portátil ({'; '.join(motivos[:2]) or 'sin motivo'}). "
                                      "Hazlo desde Xubuntu: menú K ▸ «Ir a Xubuntu», luego el menú de arriba "
                                      "a la izquierda ▸ Salir."}

    def salir_a_linux(self, cerrar=None):
        """v2.98: botón «Ir a Xubuntu». Cierra la ventana de KiraOS (como Alt+F4) y queda el escritorio de Xubuntu
        debajo. Lo de Kira en segundo plano (cerebro, núcleo, vigilancia, WiFi) sigue funcionando. Para volver: el
        menú de Xubuntu ▸ «Kira», o reiniciar."""
        ventana = getattr(self, "_ventana", None)
        if cerrar is None:
            if ventana is None:
                return {"ok": False, "texto": "Aquí no hay ventana de KiraOS que cerrar. Pulsa Alt + F4."}
            cerrar = ventana.destroy
        try:                       # v3.05: la sesión propia de Kira (kiraos-sesion) abre entonces el escritorio
            marca = os.path.join(os.path.expanduser("~"), ".kira_ir_a_xubuntu")
            with open(marca, "w", encoding="utf-8") as f:
                f.write("1")
        except OSError:
            pass
        # un momento de espera para que la pantalla reciba la respuesta antes de que se cierre la ventana
        threading.Timer(0.6, cerrar).start()
        return {"ok": True, "texto": "Te dejo en Xubuntu. Para volver, busca «Kira» en su menú (o reinicia)."}


# ---------- v3.09: lo que enseña el ORBE (qué hace Kira y cuánto le queda) ----------
_PROGRAMA = re.compile(r"\b(?:programa|c[oó]digo|app|aplicaci[oó]n|apk|juego|experimenta|implementa|algoritmo|script|"
                       r"funci[oó]n|calculadora|mej[oó]rate|mejora|escr[ií]be(?:me)?\s+un)", re.I)
_ESTUDIA = re.compile(r"\b(?:estudia|aprende|investiga|lee|leer|resume|busca|pregúntate|averigua|curso|v[ií]deo|pdf)",
                      re.I)


def texto_error_nucleo(e):
    """v3.11: un 404 = mi núcleo aún lleva el código de antes (le falta ese botón): se arregla reiniciando."""
    if getattr(e, "code", None) == 404:
        return ("Mi núcleo todavía va con la versión anterior y no conoce este botón. Reinicia el portátil "
                "(menú K ▸ Reiniciar) y ya funcionará.")
    if getattr(e, "code", None) == 403:
        return "Por seguridad, eso solo se hace desde el propio portátil."
    return f"[x] No he podido: {e}"


def texto_eta(seg):
    """«menos de 1 min» / «unos 5 min» / «1 h 20 min»."""
    seg = int(max(0, seg))
    if seg < 60:
        return "menos de 1 min"
    m = int(round(seg / 60.0))
    if m < 60:
        return f"unos {m} min"
    return f"{m // 60} h {m % 60:02d} min"


def codigo_de_pizarra(texto):
    """v3.14 (puro): de lo que el cerebro lleva escrito saca el CÓDIGO (el último bloque ```python, aunque aún no
    esté cerrado). Si no hay bloque pero el texto ya es código (empieza por def/import/class…), lo devuelve. Si es
    charla normal, ''."""
    t = str(texto or "")
    trozos = re.split(r"```[ \t]*(?:python|py|python3)?[ \t]*\n?", t, flags=re.I)
    if len(trozos) >= 2:
        # trozos impares = dentro de un bloque; me quedo con el último que tenga algo
        dentro = [trozos[i] for i in range(1, len(trozos), 2) if trozos[i].strip()]
        return dentro[-1].rstrip() if dentro else ""
    if re.match(r"\s*(?:#|def |class |import |from \S+ import |async def |@)", t):
        return t.rstrip()
    return ""


def fase_cerebro(piz, inicio_tarea=None, ahora=None):
    """v3.16 (puro): qué está haciendo el cerebro por dentro, para que la espera se entienda:
    - aún no ha escrito nada → «leyendo las instrucciones» (en el Packard Bell, unos minutos antes de la 1.ª palabra);
    - ya escribe → cuántas palabras lleva y a qué ritmo, y lo último que va diciendo (si aún no es código)."""
    ahora = time.time() if ahora is None else ahora
    piz = piz or {}
    ini = piz.get("inicio") or inicio_tarea
    lleva = max(0, int(ahora - float(ini))) if ini else 0
    texto = str(piz.get("texto") or "")
    if not texto.strip():
        return {"paso": "leyendo", "lleva": lleva, "palabras": 0, "por_minuto": 0, "dice": "",
                "texto": "Mi cerebro está leyendo las instrucciones y lo que sé del tema (en este portátil tarda unos "
                         "minutos antes de escribir la primera palabra)" + (f" · lleva {texto_eta(lleva)}" if lleva else "")}
    pal = len(texto.split())
    prim = piz.get("primera") or ini
    escribiendo = max(1.0, ahora - float(prim)) if prim else 0
    pm = int(round(pal * 60 / escribiendo)) if escribiendo else 0
    dice = "" if "```" in texto else re.sub(r"\s+", " ", texto[-300:]).strip()
    return {"paso": "escribiendo", "lleva": lleva, "palabras": pal, "por_minuto": pm, "dice": dice,
            "texto": f"Escribiendo: {pal} palabras" + (f", unas {pm} por minuto" if pm else "") +
                     (f" · lleva {texto_eta(lleva)}" if lleva else "")}


def _explicado(codigo, pedido, estado, avance="", nombre=None):
    try:
        import explicacion_codigo_kira as ex
        r = ex.explicar(codigo)
        lineas, resumen = r.get("lineas", []), r.get("resumen", "")
    except Exception:
        lineas = [{"n": i + 1, "codigo": l, "nota": ""} for i, l in enumerate(str(codigo).splitlines())]
        resumen = ""
    return {"pedido": pedido, "archivo": (nombre or "programa") + ".py", "lineas": lineas, "resumen": resumen,
            "estado": estado, "avance": avance, "codigo": codigo}


def registro_maquina(base, n=40, tope=200000):
    """v3.14: las últimas `n` líneas de maquina.log (lo que Kira ejecuta dentro y lo que sale), sin leer el archivo
    entero y sin líneas larguísimas. Sin claves (por si acaso)."""
    try:
        with open(os.path.join(base, "maquina.log"), "rb") as f:
            f.seek(0, 2)
            tam = f.tell()
            f.seek(max(0, tam - tope))
            datos = f.read().decode("utf-8", "replace")
    except OSError:
        return []
    lineas = [l.rstrip() for l in datos.splitlines() if l.strip()]
    if tam > tope and lineas:
        lineas = lineas[1:]                       # la primera puede venir cortada
    out = []
    for l in lineas[-n:]:
        l = l if len(l) <= 220 else l[:217] + "…"
        try:
            import ordenes_kira
            l = ordenes_kira.ocultar_claves(l)
        except Exception:
            pass
        out.append("  " + l)
    return out


def destino_orbe(d):
    """v3.14 (puro): al PULSAR el orbe, a qué ventana ir según lo que hace Kira: programando → «programando»;
    trabajando con su máquina (estudiar/buscar/experimentar dentro) → «maquina»; pensando → cuaderno ▸ Pensamiento;
    lo demás (estudiar sin máquina, en espera, sin tareas) → cuaderno ▸ Tareas."""
    d = d or {}
    act = d.get("actividad") or {}
    modo = d.get("modo") or ""
    if modo == "Programando":
        return {"app": "programando"}
    if act.get("maquina") and (modo in ("Estudiando", "Trabajando") or re.search(r"m[aá]quina", str(d.get("haciendo")), re.I)):
        return {"app": "maquina"}
    if modo == "Pensando":
        return {"app": "cuaderno", "pestana": "pensamiento"}
    return {"app": "cuaderno", "pestana": "tareas"}


def estado_orbe(e, ahora=None):
    """{'modo': Estudiando|Pensando|Programando|Trabajando|En pausa|Sin tareas, 'eta': texto o ''} desde el estado del
    núcleo. El tiempo se ESTIMA con lo que lleva y la fracción hecha (sin fracción aún: «calculando…»)."""
    ahora = time.time() if ahora is None else ahora
    act = e.get("actividad") or {}
    modo, eta = "Sin tareas", ""
    if e.get("ocupada"):
        orden = str(e.get("haciendo") or "")
        modo = ("Estudiando" if _ESTUDIA.search(orden) else "Programando" if _PROGRAMA.search(orden)
                else "Trabajando")
        fr, ini = float(e.get("fraccion") or 0), e.get("inicio")
        if ini and 0.05 <= fr < 1:
            eta = "termina en " + texto_eta((ahora - float(ini)) * (1 - fr) / fr)
        elif fr >= 1:
            eta = "terminando…"
        else:
            eta = "calculando el tiempo…"
    elif e.get("pausada"):
        modo = "En pausa"
    elif act.get("estudiando"):
        modo = "Estudiando"
    elif act.get("pensando") or act.get("foco"):
        modo = "Pensando"
    n = int(e.get("en_cola") or 0)
    if n:
        eta = (eta + " · " if eta else "") + f"{n} en espera"
    return {"modo": modo, "eta": eta}


def codigo_movil(correr=None):
    """El código de 6 cifras para emparejar el móvil (lo que enseña `kira-codigo`)."""
    correr = correr or (lambda: subprocess.run(["journalctl", "-u", "kira-laboratorio", "--no-pager", "-n", "300"],
                                               capture_output=True, text=True, timeout=10).stdout)
    try:
        salida = correr()
    except Exception:
        salida = ""
    lineas = (salida or "").splitlines()
    for i in range(len(lineas) - 1, -1, -1):
        if "CÓDIGO PARA CONECTAR" in lineas[i]:
            m = re.search(r"CONECTAR[^:]*:\s*(\d{3}\s?\d{3})\b", lineas[i])
            if m:
                return f"Código para emparejar el móvil: {m.group(1)}. Díselo a Kira app cuando te lo pida."
    return ("No veo un código ahora. En el móvil di «Kira, conéctate al portátil»: en ese momento sale uno nuevo "
            "(pulsa otra vez este botón).")
