# -*- coding: utf-8 -*-
"""Voz rápida (v2.16): la voz propia (VozKira, un solo motor en español) dice la respuesta FRASE A FRASE mientras el
cerebro la escribe; el cerebro del móvil reutiliza lo ya leído (recuerdos fuera de las instrucciones fijas)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = tempfile.mkdtemp(); os.environ["KIRA_DATA_DIR"] = T
os.environ.pop("KIRA_API_KEY", None)
import inicio_kira as ik
n = 0
def ok(c, m):
    global n; n += 1; assert c, "FALLA: " + m

# ---------- trocear en frases ----------
t = "Hola. Soy Kira y te ayudo con lo que necesites. ¿Quieres que abra la sala hacker? Dime"
partes, d = [], 0
while True:
    f, d2 = ik.frases_listas(t, d)
    if not f:
        break
    partes.append(f); d = d2
ok(partes == ["Hola. Soy Kira y te ayudo con lo que necesites.", "¿Quieres que abra la sala hacker?"],
   "junta frases cortas y corta en el final de frase: " + repr(partes))
ok(t[d:].strip() == "Dime", "lo que aún no acabó espera")
ok(ik.frases_listas("Vale, son las 3.", 0) == ("", 0), "un punto al final del todo puede ser un decimal: espera")
largo = "palabra " * 40
f, d = ik.frases_listas(largo, 0)
ok(f and len(f) <= 180 and largo[d - 1] == " ", "una frase larguísima se corta en un espacio")
ok(ik.limpiar_para_voz("[OK] **Hecho**: abro # la `sala`") == "Hecho: abro la sala", "no lee marcas ni asteriscos")

# ---------- voz propia (falsa) ----------
class JavaFalsa:
    def __init__(s, lista=True):
        s.dichas, s.esta_lista, s.hablando_ = [], lista, False
    def lista(s): return s.esta_lista
    def hablar(s, texto, encolar): s.dichas.append((texto, encolar)); s.hablando_ = True; return True
    def hablando(s): return s.hablando_
    def callar(s): s.hablando_ = False

j = JavaFalsa()
v = ik.Voz(java=j)
ok(v.puede_hablar(), "con voz propia puede hablar aunque no haya plyer")
ok(v.hablar("[OK] Hola") and j.dichas[-1] == ("Hola", False), "hablar corta lo anterior (QUEUE_FLUSH) y limpia marcas")
ok(v.hablando(), "sabe de verdad si está hablando (lo dice Android, no un cálculo)")
v.callar(); ok(not v.hablando(), "callar")
ok(v.encolar("Primera frase.", primero=True) and j.dichas[-1] == ("Primera frase.", False), "la primera frase corta lo que hubiera")
ok(v.encolar("Segunda.") and j.dichas[-1] == ("Segunda.", True), "las demás van a la cola, detrás")
ok(not ik.Voz(java=None, plyer_modulo=object()).encolar("x"), "sin voz propia no encola (se dice al final, como antes)")

ok(v.aviso() == "", "sin problemas, sin aviso")
j.aviso = lambda: "no hay voz en español instalada (Ajustes > Texto a voz)"
ok("español" in v.aviso(), "cuenta si falta la voz en español")
import time
j2 = JavaFalsa(lista=False)
v2 = ik.Voz(java=j2)
ok(v2.hablar("Hola") and j2.dichas == [], "si el motor aún arranca, no se pierde la frase…")
j2.esta_lista = True
fin = time.monotonic() + 2
while not j2.dichas and time.monotonic() < fin:
    time.sleep(0.05)
ok(j2.dichas == [("Hola", False)], "…la dice en cuanto está listo")
ok(ik.Voz().java is None, "en el PC no hay voz de Android (y no falla)")

# ---------- hablar mientras llega la respuesta ----------
j3 = JavaFalsa(); v3 = ik.Voz(java=j3)
h = ik.HablaEnVivo(v3)
resp = "Claro que sí, te lo explico. Un grafo son puntos unidos por líneas. Sirve para mapas y redes sociales"
for i in range(1, len(resp) + 1):
    h.trozo(resp[:i])
dichas = [x for x, _ in j3.dichas]
ok(dichas == ["Claro que sí, te lo explico.", "Un grafo son puntos unidos por líneas."], "dice cada frase al completarse: " + repr(dichas))
ok(j3.dichas[0][1] is False and j3.dichas[1][1] is True, "la primera corta, las siguientes se encolan")
ok(h.final(resp) and j3.dichas[-1] == ("Sirve para mapas y redes sociales", True), "al acabar dice solo lo que faltaba")
ok(len(j3.dichas) == 3, "no repite nada")
h2 = ik.HablaEnVivo(v3)
ok(h2.final("Hola") is False, "si no llegó a decir nada, se lee entera como siempre")
ok(not ik.HablaEnVivo(v3, activa=False).activa, "con la voz apagada en ajustes no habla")
ok(not ik.HablaEnVivo(object()).activa, "voz sin 'encolar' (antigua): no rompe nada")
j4 = JavaFalsa(); h4 = ik.HablaEnVivo(ik.Voz(java=j4))
h4.trozo("Hola, esto es una frase completa.  Y otra\nmás")
ok(h4.final("Hola, esto es una frase completa. Y otra más") and j4.dichas[-1][0] == "Y otra más",
   "la respuesta final con espacios arreglados no hace repetir")

# ---------- texto que se escribe: nunca más de 2 s ----------
m = ik.Maquina("x" * 300, cps=45)
m.paso(2.0); ok(m.terminada, "300 letras se escriben en 2 s (antes casi 7)")
m = ik.Maquina("hola mundo", cps=10)
m.paso(0.5); ok(m.visible() == "hola ", "lo corto sigue a su velocidad")

# ---------- cerebro del móvil: reutiliza lo ya leído ----------
import cerebro_ia_kira as ci, kira_god
core = kira_god.KiraGodCore()
core.procesar_orden("guarda recuerdo: mi planta se llama Rita")
vistos = []
core._leer_clave = lambda *a: ci.LOCAL
core._llamar_api = lambda clave, system, usuario, max_tokens=4000, mensajes=None, al_trozo=None: (
    vistos.append((system, json.loads(json.dumps(mensajes)), max_tokens)), "Riégala poco.")[1]
core.conversar("cómo cuido a mi planta Rita")
core.conversar("y en verano qué hago", historial=[("tu", "cómo cuido a mi planta Rita"), ("kira", "Riégala poco.")])
(s1, m1, t1), (s2, m2, _t2) = vistos
ok(s1 == s2 and "Rita" not in s1, "las instrucciones fijas no cambian (el modelo no relee todo cada vez)")
ok("Rita" in m1[-1]["content"] and "Pregunta: cómo cuido" in m1[-1]["content"], "los recuerdos van con la pregunta")
ok(t1 <= 220, "respuestas cortas en el móvil")
ok(m2[0]["content"] == "cómo cuido a mi planta Rita", "la charla anterior se manda tal cual (se reutiliza)")
largo = [("tu" if i % 2 == 0 else "kira", f"turno {i} " + "x" * 500) for i in range(20)]
ok(len(core.armar_mensajes(largo, "hola", turnos=6)) <= 7 and
   all(len(x["content"]) <= 300 + 10 for x in core.armar_mensajes(largo, "hola", turnos=6, largo=300)[:-1]),
   "menos historial y más corto con el modelo del móvil")

class Resp:
    status = 200
    def __init__(s, b): s.b = b
    def read(s, *a): return s.b
    def __enter__(s): return s
    def __exit__(s, *a): return False
enviado = []
def abrir(req, timeout=0):
    enviado.append(json.loads(req.data))
    return Resp(json.dumps({"choices": [{"message": {"content": "Hola"}}]}).encode())
ci.Cerebro(T, abrir=abrir).chat_local("s", [{"role": "user", "content": "x"}])
ok(enviado[-1].get("cache_prompt") is True, "pide reutilizar lo ya leído")
ok(enviado[-1].get("chat_template_kwargs") == {"enable_thinking": False}, "sin razonamiento oculto (Qwen)")

import cerebro_propio_kira as cp
P = cp.CerebroPropio(T) if hasattr(cp, "CerebroPropio") else None
if P is not None:
    a = P._argumentos("motor")
    ok("-np" in a and a[a.index("-np") + 1] == "1", "una sola conversación: toda la memoria para ella")
print("VOZ OK", n)
