# -*- coding: utf-8 -*-
"""v2.81: «estudia X» estudia DE VERDAD —webs oficiales + CURSOS COMPLETOS de YouTube (gratis)— con BARRA animada, y
cuando no estudia sigue pensando. La búsqueda de YouTube y el reconocedor son puros (probados de verdad); el resto
(web real, YouTube real, barra Kivy, cerebro) se comprueba por AST/texto."""
import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import video_kira as vk
import estudio_kira as est

n = 0


def ok(c, m):
    global n
    n += 1
    assert c, "FALLA: " + m


# ---------- buscar vídeos en YouTube (puro sobre el HTML de resultados) ----------
HTML = (
    'basura {"videoRenderer":{"videoId":"aaaaaaaaaaa","thumbnail":{},'
    '"title":{"runs":[{"text":"Curso COMPLETO de Python gratis"}]}}} '
    '{"videoRenderer":{"videoId":"bbbbbbbbbbb","title":{"runs":[{"text":"Tutorial Python desde cero"}]}}} '
    '{"videoRenderer":{"videoId":"aaaaaaaaaaa","title":{"runs":[{"text":"repetido"}]}}}'
)
vids = vk._videos_de_busqueda(HTML, 3)
ok(len(vids) == 2, "saca 2 vídeos (sin repetir)")
ok(vids[0][0] == "aaaaaaaaaaa" and "Curso" in vids[0][1], "primero el curso completo, con título")
ok(vids[1][0] == "bbbbbbbbbbb", "segundo el tutorial, en orden")
# buscar() con un «bajar» de mentira (sin internet aquí)
got = vk.buscar("python", bajar=lambda u: HTML.encode("utf-8"), maximo=1)
ok(len(got) == 1 and got[0][0] == "aaaaaaaaaaa", "buscar devuelve el primero")
ok(vk.buscar("python", bajar=lambda u: (_ for _ in ()).throw(RuntimeError("sin red"))) == [], "sin red -> lista vacía")

# ---------- reconocer «estudia X» genérico vs especiales ----------
ok(est.es_estudia_general("estudia Python") == "Python", "«estudia Python» -> Python")
ok(est.es_estudia_general("Kira, estudia la fotosíntesis") == "la fotosíntesis", "quita «Kira,»")
ok(est.es_estudia_general("estudia ciberseguridad") is None, "ciberseguridad es ESPECIAL, no genérico")
ok(est.es_estudia_general("estudia ingeniería") is None, "ingeniería es especial")
ok(est.es_estudia_general("estudia redes neuronales") is None, "redes es especial")
ok(est.es_estudia_general("estudia en internet python") is None, "«en internet» va por su sitio")
ok(est.es_estudia_general("hola qué tal") is None, "no es «estudia»")

# ---------- cableado por AST ----------
src_g = open(os.path.join(RAIZ, "kira_god.py"), encoding="utf-8").read()
src_i = open(os.path.join(RAIZ, "interfaz_kira.py"), encoding="utf-8").read()
arb = ast.parse(src_g)
met = {nd.name for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef)}
for m in ("estudiar_a_fondo", "_buscar_cursos_youtube", "es_estudia_general"):
    ok(m in met, f"kira_god define {m}")
eaf = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "estudiar_a_fondo")
cuerpo = ast.get_source_segment(src_g, eaf) or ""
ok("estudiar_en_internet" in cuerpo, "estudia de webs (oficiales/tutoriales/cursos)")
ok("_buscar_cursos_youtube" in cuerpo and "aprender_de_video" in cuerpo, "estudia de CURSOS de YouTube")
ok("_estudiando" in cuerpo, "marca que está estudiando (para no pensar a la vez)")
ok("pensar_sola(True" in cuerpo, "al acabar, sigue pensando")
bc = next(nd for nd in ast.walk(arb) if isinstance(nd, ast.FunctionDef) and nd.name == "_buscar_cursos_youtube")
ok("curso completo" in (ast.get_source_segment(src_g, bc) or ""), "busca CURSOS COMPLETOS")
# el bucle de pensar NO piensa mientras estudia
ok('getattr(self, "_estudiando", False)' in src_g, "el bucle de pensar se pausa mientras estudia")
# la interfaz lanza el estudio con BARRA y lo intercepta
ok("def estudiar_por_voz" in src_i, "la interfaz tiene estudiar_por_voz (con barra)")
ok("tarea_empieza(\"estudio\"" in src_i, "el estudio es una tarea con barra")
ok("core.es_estudia_general(orden)" in src_i, "la interfaz intercepta «estudia X» genérico")
ok("avance(txt, fr)" in src_i, "la barra se mueve con el progreso del estudio")

print(f"\nTODO BIEN {n}")
