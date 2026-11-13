# -*- coding: utf-8 -*-
"""v3.35: si Kira NO SABE hacer un código (falla dos veces seguidas), pregunta a OTRAS IA (Claude, Gemini, ChatGPT,
DeepSeek…), PRUEBA lo que le dicen y se queda con lo que funciona. Sin red: las IA son de mentira."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = tempfile.mkdtemp()
os.environ["HOME"] = T
os.environ["KIRA_DATA_DIR"] = T
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "kira_portatil"))
import ayuda_ias_kira as ai   # noqa: E402

fallos = n = 0


def ok(c, m):
    global fallos, n
    n += 1
    print(("  ok  " if c else "FALLA ") + m)
    if not c:
        fallos += 1


D = os.path.join(T, "datos")
os.makedirs(D)

# ---------------- órdenes ----------------
O = ai.orden
ok(O("config gemini AIzaSyA1234567890abcdefghijk") == ("clave", "gemini", "AIzaSyA1234567890abcdefghijk"), "config gemini")
ok(O("Kira, mi clave de chat gpt es sk-abc123abc123abc123abc123") == ("clave", "chatgpt", "sk-abc123abc123abc123abc123"),
   "«mi clave de chat gpt es …»")
ok(O("config Géminis modelo gemini-2.5-pro") == ("modelo", "gemini", "gemini-2.5-pro"), "cambiar el modelo (Géminis)")
ok(O("quita la clave de deepseek") == ("quitar", "deepseek", "") and O("qué IA tengo")[0] == "lista", "quitar / lista")
ok(O("desactiva la ayuda de otras IA")[0] == "desactivar" and O("activa la ayuda de otras ias")[0] == "activar", "interruptor")
ok(O("pregunta a las IA: cómo se hace una GDT") == ("preguntar", "", "cómo se hace una GDT") and
   O("pregúntale a gemini qué es la paginación") == ("preguntar", "gemini", "qué es la paginación"), "preguntar a mano")
for t in ("config github ghp_x", "config clave: x", "qué es gemini", "abre chatgpt"):
    ok(O(t) is None, f"«{t}» no es esto")

# ---------------- claves (0600, nunca se enseñan) ----------------
ok("No tengo ninguna otra IA" in ai.hacer(D, "lista"), "sin claves lo explica")
r = ai.hacer(D, "clave", "gemini", "AIzaSyA1234567890abcdefghijk")
ok("[OK]" in r and "AIza" not in r, "guarda la clave de Gemini y NO la repite")
ok(oct(os.stat(os.path.join(D, ai.ARCHIVO)).st_mode & 0o777) == "0o600", "archivo de claves 0600")
ok("no parece una clave" in ai.hacer(D, "clave", "chatgpt", "hola"), "algo que no es una clave se rechaza")
ai.hacer(D, "clave", "chatgpt", "sk-abc123abc123abc123abc123")
with open(os.path.join(D, "api_key.txt"), "w") as f:
    f.write("sk-ant-falsa-123456789012345")
ok([p for p, _c, _m in ai.configuradas(D)] == ["claude", "gemini", "chatgpt"], "Claude (su clave de siempre) + las nuevas, en orden")
ai.hacer(D, "modelo", "chatgpt", "gpt-5")
ok(dict((p, m) for p, _c, m in ai.configuradas(D))["chatgpt"] == "gpt-5", "modelo cambiado")
ok("Claude" in ai.hacer(D, "lista") and "Gemini" in ai.hacer(D, "lista") and "sk-" not in ai.hacer(D, "lista"),
   "la lista dice cuáles, sin claves")
import ordenes_kira  # noqa: E402
ok("AIza" not in ordenes_kira.ocultar_claves("config gemini AIzaSyA1234567890abcdefghijk") and
   "gpt-5" in ordenes_kira.ocultar_claves("config chatgpt modelo gpt-5"), "el historial tapa las claves (no el modelo)")
import memoria_kira  # noqa: E402
ok(ai.ARCHIVO in memoria_kira.NUNCA, "las claves nunca viajan con la memoria")

# ---------------- cómo se habla con cada una (sin red) ----------------
llamadas = []


def post_falso(url, cuerpo, cab, espera=0):
    llamadas.append((url, cuerpo, cab))
    if "anthropic" in url:
        return {"content": [{"type": "text", "text": "hola claude"}]}
    if "googleapis" in url:
        return {"candidates": [{"content": {"parts": [{"text": "hola gemini"}]}}]}
    return {"choices": [{"message": {"content": "hola openai"}}]}


real_post = ai._post
ai._post = post_falso
ok(ai.pedir_http("claude", "k1", "m1", "s", "u") == "hola claude" and llamadas[-1][2]["x-api-key"] == "k1",
   "Claude: formato de Anthropic")
ok(ai.pedir_http("gemini", "k2", "gemini-x", "s", "u") == "hola gemini" and "gemini-x:generateContent" in llamadas[-1][0]
   and llamadas[-1][2]["x-goog-api-key"] == "k2" and "k2" not in llamadas[-1][0], "Gemini: la clave en cabecera, no en la URL")
ok(ai.pedir_http("deepseek", "k3", "deepseek-chat", "s", "u") == "hola openai" and
   llamadas[-1][2]["Authorization"] == "Bearer k3" and llamadas[-1][1]["messages"][0]["role"] == "system",
   "DeepSeek/ChatGPT/…: formato OpenAI")
res = ai.preguntar_todas(D, "s", "¿qué es la GDT?")
ok([x[0] for x in res] == ["Claude", "Gemini", "ChatGPT"] and all(x[1] for x in res), "pregunta lo mismo a todas")
ai._post = real_post


def http_malo(*a, **k):
    import urllib.error
    raise urllib.error.HTTPError("u", 401, "no", {}, None)


ai._post = http_malo
try:
    ai.pedir_http("gemini", "k", "m", "s", "u")
    ok(False, "debía fallar")
except RuntimeError as e:
    ok("la clave no vale" in str(e) and "k" not in str(e).split(":")[-1].replace("la clave no vale", ""),
       "un 401 se explica sin enseñar la clave")
ai._post = real_post

# ---------------- la ayuda: pregunta, prueba, se queda con lo bueno ----------------
vistas = []


def pedir_falso(respuestas):
    def pedir(p, c, m, s, u):
        vistas.append((p, u))
        r = respuestas.get(p)
        if isinstance(r, Exception):
            raise r
        return r.pop(0) if isinstance(r, list) else r
    return pedir


guardado = []
probar = lambda t: (("BUENO" in t), "funciona" if "BUENO" in t else "sigue fallando: X")
res = ai.ayuda(D, "tarea difícil", "codigo malo", "Error: Y", probar, "sys",
               pedir=pedir_falso({"claude": RuntimeError("Claude: límite de uso"), "gemini": ["malo", "malo otra vez"],
                                  "chatgpt": "esto es BUENO"}),
               guardar=lambda tema, txt: guardado.append((tema, txt)))
ok(res["ok"] and res["ia"] == "ChatGPT", "la primera que FUNCIONA al probarla gana (ChatGPT)")
ok([h[0] for h in res["historial"]] == ["Claude", "Gemini", "Gemini", "ChatGPT"], "Claude no contesta, Gemini falla 2 veces")
ok("tampoco funcionó" in vistas[2][1] and "sigue fallando: X" in vistas[2][1], "a Gemini le vuelve con su error")
ok("codigo malo" in vistas[1][1] and "Error: Y" in vistas[1][1] and "tarea difícil" in vistas[1][1],
   "a cada IA le llega la tarea, el código que falló y el error (nada más)")
ok(any("FUNCIONÓ" in t and "ChatGPT" in tema for tema, t in guardado) and any("NO funcionó" in t for _x, t in guardado),
   "lo recomendado queda en el baúl (funcionara o no)")
res = ai.ayuda(D, "t", "c", "e", probar, "s", pedir=pedir_falso({"claude": "no", "gemini": "no", "chatgpt": "no"}))
ok(not res["ok"] and "ninguna" in res["motivo"], "si ninguna funciona, lo dice")
ai.hacer(D, "desactivar")
res = ai.ayuda(D, "t", "c", "e", probar, "s", pedir=pedir_falso({}))
ok(not res["ok"] and res["sin_ias"] and "desactivada" in res["motivo"], "desactivada: no pregunta a nadie")
ai.hacer(D, "activar")
D2 = os.path.join(T, "vacio")
os.makedirs(D2)
ok(ai.ayuda(D2, "t", "c", "e", probar, "s")["sin_ias"], "sin claves: no pregunta (y no rompe nada)")

# ---------------- en el TALLER DE KERNEL: dos fallos → otras IA → QEMU ----------------
if shutil.which("gcc") and shutil.which("nasm") and shutil.which("ld"):
    import saber_so_kira as so
    import taller_kernel_kira as tk
    FALSO = os.path.join(T, "qemu_falso.py")
    with open(FALSO, "w") as f:
        f.write("import sys,time\nb=open(sys.argv[sys.argv.index('-kernel')+1],'rb').read()\n"
                "for m in ['Hola desde mi SO!','GDT OK','IDT OK','punto de ruptura','Excepciones OK','AYUDA OK',"
                "'KERNEL_LISTO']:\n    m.encode() in b and print(m, flush=True)\ntime.sleep(20)\n")

    def popen(args, **kw):
        if args and args[0] == "qemu-system-i386":
            args = [sys.executable, FALSO] + list(args[1:])
        return subprocess.Popen(args, **kw)

    t = tk.Taller(base=os.path.join(T, "kernel"), popen=popen,
                  which=lambda h: "/x" if h == "qemu-system-i386" else shutil.which(h))
    t.poner_etapa(3, copiar=False)
    malo = "ARCHIVO: kernel.c\n```c\nesto no compila\n```"
    bueno = ("ARCHIVO: kernel.c\n```c\n" + so.etapa(3)["archivos"]["kernel.c"].replace(
        'kprint("KERNEL_LISTO\\n");', 'kprint("AYUDA OK\\n");\n    kprint("KERNEL_LISTO\\n");') + "```")
    cerebro = iter([malo, malo, malo, malo])
    preguntas = []

    def ayuda(**kw):
        preguntas.append(kw)
        return ai.ayuda(D, pedir=pedir_falso({"claude": "nada útil", "gemini": [malo, bueno], "chatgpt": bueno}), **kw)

    r = t.programar("que imprima AYUDA OK", preguntar=lambda s, u: next(cerebro), ayuda=ayuda)
    ok(r["ok"] and r.get("ia") == "Gemini" and "pregunté a otras IA" in r["texto"], "kernel: tras 2 fallos, Gemini lo resuelve")
    ok(len(preguntas) == 1 and "No compila" in preguntas[0]["error"] and preguntas[0]["formato"] == "c",
       "…solo después de DOS fallos, con el error del compilador")
    ok("AYUDA OK" in t.leer("kernel.c") and "AYUDA OK" in r.get("serie", ""), "lo de Gemini queda puesto y arranca")
    antes = t.leer("kernel.c")
    cerebro = iter([malo] * 4)
    r = t.programar("otra cosa imposible", preguntar=lambda s, u: next(cerebro),
                    ayuda=lambda **kw: ai.ayuda(D, pedir=pedir_falso({"claude": malo, "gemini": malo, "chatgpt": malo}),
                                               **kw))
    ok(not r["ok"] and t.leer("kernel.c") == antes and "Otras IA tampoco" in r["texto"] or not r["ok"],
       "si nadie lo logra, el kernel queda como estaba")
    ok(t.leer("kernel.c") == antes, "…intacto")
else:
    print("  (sin gcc/nasm: me salto el taller)")

# ---------------- en los PROGRAMAS: dos fallos → otras IA → se prueba ----------------
import kira_god  # noqa: E402
core = kira_god.KiraGodCore()
ai.hacer(core.dir, "clave", "gemini", "AIzaSyA1234567890abcdefghijk")
real = ai.pedir_http
ai.pedir_http = lambda p, c, m, s, u, max_tokens=4000: ("NOMBRE: saludo\n```python\nprint('hola desde gemini')\n```"
                                                        if p == "gemini" else "no sé")
r = core._programa_con_otras_ias("un programa que salude", {"ok": False, "codigo": "print(", "error": "SyntaxError",
                                                           "intentos": 4}, lambda t: None)
ai.pedir_http = real
ok(r and r["ok"] and r["de_ia"] == "Gemini" and "hola desde gemini" in r["codigo"] and "pregunté a otras IA" in r["texto"],
   "programa: lo de Gemini pasa la prueba y se lo queda")
fuente = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
ok('int(r.get("intentos") or 0) >= 2' in fuente, "solo tras dos intentos fallidos")
nuc = open(os.path.join(RAIZ, "kira_portatil", "nucleo_portatil.py"), encoding="utf-8").read()
ok("ayuda=_ayuda_ias(core)" in nuc, "el núcleo le pasa la ayuda al taller de kernel")
r = core.procesar_orden("qué IA tengo")
ok("Gemini" in r and "AIza" not in r, "«qué IA tengo» desde el núcleo")

print(f"\n{n - fallos}/{n} bien" if fallos else f"\nTODO BIEN ({n})")
sys.exit(1 if fallos else 0)
