# -*- coding: utf-8 -*-
"""Kira se mueve: por sus pantallas («abre la sala hacker», «juega a la serpiente», «atrás») y fuera de la app
(«abre WhatsApp», ajustes del móvil, web, teléfono), también desde otra app con el permiso de segundo plano."""
import os, sys, tempfile, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kivy_falso; kivy_falso.instalar()
from kivy_falso import Clock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import navegar_kira as nk
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- entender la frase ----------
def es(frase, **esperado):
    a = nk.interpretar(frase, juegos_extra=["tetris"])
    ok(a is not None and all(a.get(k) == v for k, v in esperado.items()), f"«{frase}» -> {a}")
es("Kira, abre la sala hacker", tipo="pantalla", destino="sala_hacker")
es("ve a los juegos", tipo="pantalla", destino="juegos")
es("llévame al editor", destino="editor_codigo")
es("llévame al editor de vídeo", destino="editor_video")
es("puedes llevarme a la sala de cine", destino="sala_cine")
es("quiero ir a la mediateca", destino="mediateca")
es("enséñame mis notas", destino="notas")
es("abre el menú por favor", destino="menu")
es("abre la terminal", destino="terminal")
es("abre mejoras", destino="panel:orden")
es("abre la pasarela", destino="pasarela")
es("abre los ajustes", destino="config")
es("muéstrame lo que has aprendido", destino="conocimiento")
es("abre la sala de ciberseguridad", destino="sala_ciber")
es("juega a la serpiente", tipo="juego", id="serpiente")
es("echamos una partida al pong", tipo="juego", id="pong")
es("quiero jugar al rompeladrillos", tipo="juego", id="rompeladrillos")
es("jugamos al tetris", tipo="juego", id="mejora:tetris")
es("atrás", tipo="atras")
es("vuelve", tipo="atras")
es("ven", tipo="kira")
es("abre WhatsApp", tipo="app", nombre="whatsapp", seguro=True)
es("abre la app de YouTube", tipo="app", nombre="youtube", seguro=True)
es("entra en Instagram", tipo="app", nombre="instagram", seguro=False)
es("ve al inicio del móvil", tipo="inicio_movil")
es("minimízate", tipo="inicio_movil")
es("abre los ajustes del wifi", tipo="ajustes", accion="android.settings.WIFI_SETTINGS")
es("abre el bluetooth", tipo="ajustes", accion="android.settings.BLUETOOTH_SETTINGS")
es("abre la configuración del móvil", tipo="ajustes", accion=nk.AJUSTES_GENERAL)
es("busca en internet recetas de paella", tipo="web", url="https://www.google.com/search?q=recetas%20de%20paella")
es("abre youtube.com", tipo="web", url="https://youtube.com")
es("marca el 600 123 456", tipo="marcar", numero="600123456")
es("llama al seis cero cero uno dos tres", tipo="marcar", numero="600123")
es("llama a mamá", tipo="llamar_nombre")
es("permiso para abrir apps", tipo="permiso_fondo")
for f in ("abre la cámara", "abre lo leído en el editor", "abre la receta kmp", "conéctate al ordenador",
          "entra en el laboratorio", "qué tiempo hace", "estudia ingeniería", "recetas de grafos", "hola Kira", ""):
    ok(nk.interpretar(f) is None, f"«{f}» no es moverse (lo hacen otras órdenes o la charla)")

# ---------- fuera de la app: Android simulado ----------
class JavaFalso:
    paquete = "org.kira.kiragod"
    def __init__(s): s.hecho, s.fondo_ok = [], False
    def apps(s):
        return [("WhatsApp", "com.whatsapp"), ("YouTube", "com.google.android.youtube"), ("YouTube Music", "com.google.android.apps.youtube.music"),
                ("Instagram", "com.instagram.android"), ("Ajustes", "com.android.settings"), ("Kira", "org.kira.kiragod"),
                ("Google Maps", "com.google.android.apps.maps"), ("Cámara", "com.sec.android.app.camera")]
    def abrir_paquete(s, p): s.hecho.append(("app", p)); return True
    def inicio(s): s.hecho.append(("inicio",))
    def ajustes(s, a): s.hecho.append(("ajustes", a))
    def ver(s, u): s.hecho.append(("ver", u))
    def marcar(s, num): s.hecho.append(("marcar", num))
    def traer_kira(s): s.hecho.append(("kira",))
    def puede_desde_fondo(s): return s.fondo_ok
    def pedir_permiso_fondo(s): s.hecho.append(("permiso",))
J = JavaFalso()
M = nk.Movil(J)
ok(M.buscar_app("whatsapp") == ("WhatsApp", "com.whatsapp"), "busca por el nombre")
ok(M.buscar_app("youtube")[1] == "com.google.android.youtube", "el más parecido (YouTube, no YouTube Music)")
ok(M.buscar_app("maps")[1] == "com.google.android.apps.maps", "por una palabra del nombre")
ok(M.buscar_app("instagran")[1] == "com.instagram.android", "aunque se oiga mal")
ok(M.buscar_app("kira") is None, "a sí misma no se abre")
ok(M.buscar_app("tiktok") is None, "lo que no está, no está")
def hacer(frase, en_fondo=False):
    return M.hacer(nk.interpretar(frase), en_fondo=en_fondo)
ok(hacer("abre WhatsApp") == (True, "Abro WhatsApp.") and J.hecho[-1] == ("app", "com.whatsapp"), "abre WhatsApp")
ok(hacer("abre tiktok")[0] is False and "No encuentro" in hacer("abre tiktok")[1], "app que no hay: lo dice")
ok(hacer("entra en tiktok") == (None, ""), "«entra en…» algo que no es app: que siga la charla")
ok(hacer("ve al inicio del móvil")[0] and J.hecho[-1] == ("inicio",), "inicio del móvil")
ok(hacer("abre los ajustes del wifi")[1] == "Te abro los ajustes del WiFi." and J.hecho[-1] == ("ajustes", "android.settings.WIFI_SETTINGS"), "ajustes del wifi")
ok(hacer("abre youtube.com")[0] and J.hecho[-1] == ("ver", "https://youtube.com"), "una web")
r = hacer("marca el 600 123 456")
ok(r[0] and "Pulsa llamar" in r[1] and J.hecho[-1] == ("marcar", "600123456"), "marcar abre el teléfono, no llama sola")
r = hacer("llama a mamá")
ok(r[0] is False and "contactos" in r[1] and J.hecho[-1] == ("marcar", "600123456"), "por nombre no (no lee contactos)")
antes = len(J.hecho)
r = hacer("abre WhatsApp", en_fondo=True)
ok(r == (False, nk.Movil.SIN_PERMISO_FONDO) and len(J.hecho) == antes, "desde otra app sin permiso: no lo intenta y explica cómo")
ok(hacer("permiso para abrir apps")[0] and J.hecho[-1] == ("permiso",), "pide el permiso «mostrar sobre otras apps»")
J.fondo_ok = True
ok(hacer("abre WhatsApp", en_fondo=True)[0] and J.hecho[-1] == ("app", "com.whatsapp"), "con el permiso, también desde otra app")
ok("Ya tengo ese permiso" in hacer("permiso para abrir apps")[1], "si ya lo tiene, lo dice")
PC = nk.Movil(None)
ok(PC.hacer(nk.interpretar("abre WhatsApp")) == (False, nk.Movil.SOLO_MOVIL), "en el PC lo dice claro")
ok(PC.hacer(nk.interpretar("entra en algo")) == (None, ""), "en el PC, lo dudoso sigue a la charla")
ok(M.hacer({"tipo": "pantalla", "destino": "menu"}) == (None, ""), "las pantallas no son cosa de Movil")

# ---------- el núcleo (consola) ----------
import kira_god
core = kira_god.KiraGodCore()
core.movil = nk.Movil(J)
ok(core.procesar_orden("abre youtube").startswith("[OK] Abro YouTube"), "núcleo: abrir app")
ok(core.procesar_orden("abre los ajustes del bluetooth").startswith("[OK]"), "núcleo: ajustes")
ok(core.procesar_orden("hola que tal").startswith(core.NO_RECONOCIDA), "lo demás sigue igual")
sistemas = []
core._leer_clave = lambda: "clave-de-prueba"
core._llamar_api = lambda clave, sistema, usuario, *a, **k: (sistemas.append(sistema), "Vale.")[1]
core.conversar("¿te puedes mover por la app?")
ok("abre la sala hacker" in sistemas[-1] and "nunca que no puedes" in sistemas[-1], "su cerebro sabe que sí puede moverse")

# ---------- la interfaz: por voz y por texto ----------
import inicio_kira as ik
class VozMuda:
    error = ""
    def __init__(s): s.dichos = []
    def puede_hablar(s): return True
    def puede_escuchar(s): return False
    def hablando(s): return False
    def hablar(s, t): s.dichos.append(t); return True
    def iniciar_escucha(s, idioma="es-ES"): return False, "no"
    def sondear(s): return "error", ""
    def parar_escucha(s): pass
VOZ = VozMuda(); ik.Voz = lambda *a, **k: VOZ
class OidoFalso:
    def __init__(s): s.cb, s.pausas, s.estado, s.mensaje = None, [], "apagado", ""
    def disponible(s): return True
    def modelo_instalado(s): return True
    def libreria_disponible(s): return True
    def encender(s, al_frase, al_estado=None): s.cb, s.estado = al_frase, "escuchando"; return True, "ok"
    def pausar(s, si): s.pausas.append(si)
    def apagar(s): s.estado = "apagado"
    def oye(s, texto): threading.Thread(target=s.cb, args=(texto,)).start()
OIDO = OidoFalso(); core.oido = OIDO
charlas = []
core.conversar = lambda t, h=(), al_trozo=None: (charlas.append(t), "Te contesto charlando.")[1]
from interfaz_kira import construir_interfaz
sm = construir_interfaz(core)
def correr(seg=2.0, cond=None):
    t = time.time()
    while time.time() - t < seg:
        Clock.correr(1, 0.05)
        if cond and cond():
            return True
        time.sleep(0.01)
    return bool(cond and cond())
correr(1.5)
ok(OIDO.cb is not None, "el oído propio está escuchando")
entrada = next(w for w in sm.walk() if type(w).__name__ == "TextInput" and "Escríbele" in getattr(w, "hint_text", ""))
enviar = next(w for w in sm.walk() if type(w).__name__ == "Button" and w.text == "Enviar")
def escribe(texto):
    sm.ir("inicio"); entrada.text = texto; enviar.press(); correr(0.4)
escribe("abre la sala hacker")
ok(sm.current == "sala_hacker", "por texto: «abre la sala hacker»")
escribe("Kira, llévame a los juegos")
ok(sm.current == "juegos" and not charlas, "«llévame a los juegos» sin preguntar a la IA")
escribe("abre mejoras")
ok(sm.current == "panel", "«abre mejoras» va al panel de mejoras")
escribe("juega a la serpiente")
ok(sm.current == "jugar", "«juega a la serpiente» empieza el juego")
sm.ir("menu"); sm.ir("notas")
entrada.text = ""
# por voz desde OTRA pantalla: va directo, sin volver antes al botón
VOZ.dichos.clear()
OIDO.oye("Kira, abre el editor de código")
ok(correr(3, lambda: sm.current == "editor_codigo"), "por voz desde las notas: al editor")
ok(any("editor de código" in d for d in VOZ.dichos), "y lo dice en voz alta")
OIDO.oye("Kira, atrás")
ok(correr(3, lambda: sm.current == "menu"), "«Kira, atrás» desde el editor vuelve al menú")
OIDO.oye("Kira, abre WhatsApp")
ok(correr(3, lambda: J.hecho[-1] == ("app", "com.whatsapp")), "por voz: abre WhatsApp")
OIDO.oye("Kira, ve a dormir")
ok(correr(4, lambda: "ve a dormir" in charlas), "lo que no es una app ni una pantalla: lo contesta charlando")
# desde OTRA app (Kira en segundo plano)
core.en_segundo_plano = True
J.fondo_ok = False; VOZ.dichos.clear(); antes = len(J.hecho)
OIDO.oye("Kira, abre YouTube")
ok(correr(3, lambda: any("Mostrar sobre otras apps" in d for d in VOZ.dichos)) and len(J.hecho) == antes,
   "en segundo plano sin permiso: no lo intenta y explica cómo")
J.fondo_ok = True; VOZ.dichos.clear()
OIDO.oye("Kira, abre YouTube")
ok(correr(3, lambda: J.hecho[-1] == ("app", "com.google.android.youtube")), "con el permiso, abre YouTube aunque estés en otra app")
OIDO.oye("Kira, abre la sala de cine")
ok(correr(3, lambda: ("kira",) in J.hecho), "algo de Kira desde otra app: primero vuelve a primer plano")
core.en_segundo_plano = False
ok(correr(3, lambda: sm.current == "sala_cine"), "y luego va a la sala de cine")
# configuración: botón del permiso
sm.ir("config")
J.fondo_ok = False
next(w for w in sm.get_screen("config").walk() if type(w).__name__ == "Button" and "segundo plano" in w.text).press()
ok(J.hecho[-1] == ("permiso",), "Configuración: botón para el permiso de segundo plano")
print("NAVEGAR OK", n)
