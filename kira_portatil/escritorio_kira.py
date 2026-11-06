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
    {"id": "ajustes", "titulo": "Ajustes", "sub": "cerebro, voz, nacimiento"},
]


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
        return {"llamar": p.get("llamar", ""), "wifi": w, "voz": self.voz_activa, "iconos": ICONOS}

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
            if self.cli is None:
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
                                     "lineas": r["lineas"], "resumen": r["resumen"]}
                except Exception:
                    pass

    def hay_programa(self):
        return bool(getattr(self, "programa", None))

    def tarea_hablar(self, cid):
        t = getattr(self, "_charlas", {}).get(str(cid))
        if not t:
            return {"estado": "no existe"}
        return {k: t[k] for k in ("estado", "respuesta", "lineas", "pedir_clave")}

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
        """¿Lo que dijiste/escribiste en la barra es «busca …»? Entonces se abre el buscador: {consulta, tipo}."""
        import internet_kira as ik
        t = re.sub(r"^\s*(?:oye\s+|hola\s+)?kira\b[\s,:;.!¡]*", "", str(texto or ""), flags=re.I).strip()
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
        return {"ok": True, "titulo": pag.get("titulo", ""), "url": pag.get("url", url), "dominio": ik.dominio(url),
                "texto": str(pag.get("texto", ""))[:30000], "codigos": len(pag.get("codigos") or []),
                "tipo": pag.get("tipo", "web"), "via": self._via()}

    # ---------- las demás ventanas (texto + botones) ----------
    def app(self, nombre):
        """Lo que enseña una ventana: {"titulo", "texto", "botones": [{"texto", "accion"}]}.
        accion: «decir:frase» (se la dice a Kira), «app:otra» (abre otra ventana) o «hacer:x» (app_hacer)."""
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
        if nombre == "movil" and accion == "codigo":
            return {"texto": codigo_movil()}
        if nombre == "maquina" and accion == "visitas":
            import maquina_kira as mq
            v = mq.Maquina().visitas(15)
            return {"texto": ("Lo último que ha pasado por la puerta de mi máquina (solo el sitio, nunca el contenido):\n"
                              + "\n".join(v)) if v else "Mi máquina aún no ha salido a internet."}
        return {"texto": "No conozco ese botón."}

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
        import pensador_kira as pn
        est = pn.cargar(os.path.join(DATOS_NUCLEO, "pensamientos.json"))
        texto = pn.texto_cuaderno(est)
        try:
            texto = pn.texto_soluciones(est) + "\n\n" + texto
        except Exception:
            pass
        return {"titulo": "Cuaderno", "texto": texto,
                "botones": [{"texto": "Piensa una ahora", "accion": "decir:piensa una"},
                            {"texto": "Ponte a pensar", "accion": "decir:piensa"},
                            {"texto": "Deja de pensar", "accion": "decir:deja de pensar"}]}

    def _app_maquina(self):
        import maquina_kira as mq
        try:
            texto = mq.Maquina().estado()
        except Exception as e:                        # noqa: BLE001
            texto = f"[x] {e}"
        return {"titulo": "Máquina virtual", "texto": texto + "\n\nEs un Linux ligero y aislado, sin tus archivos. "
                "Desde aquí investigo, busco y experimento: sale a internet SOLO por mi puerta, que nunca deja ir a tu "
                "casa (ni a este portátil ni a tu router), y mis experimentos corren con un usuario sin permisos. Si "
                "algo va raro, vuelve sola a su foto limpia.",
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
        texto = (f"KiraOS versión {ver}.\nCerebro: {cual}.\nVoz: {'puesta' if self.voz_activa else 'quitada'}."
                 + (f"\n\n{partida}" if partida else ""))
        return {"titulo": "Ajustes", "texto": texto,
                "botones": [{"texto": "Cerebro rápido", "accion": "hacer:rapido"},
                            {"texto": "Cerebro grande", "accion": "hacer:grande"},
                            {"texto": "Con voz", "accion": "hacer:voz_si"},
                            {"texto": "Sin voz", "accion": "hacer:voz_no"}]}

    # ---------- apagar / reiniciar ----------
    def sistema(self, accion, correr=None):
        orden = {"apagar": ["systemctl", "poweroff"], "reiniciar": ["systemctl", "reboot"]}.get(accion)
        if orden is None:
            return {"ok": False, "texto": "No conozco esa orden."}
        correr = correr or (lambda o: subprocess.Popen(o, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        try:
            correr(orden)
            return {"ok": True, "texto": "Hasta luego." if accion == "apagar" else "Vuelvo enseguida."}
        except Exception as e:                        # noqa: BLE001
            return {"ok": False, "texto": f"[x] {e}"}


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
