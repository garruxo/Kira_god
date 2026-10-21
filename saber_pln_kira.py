# -*- coding: utf-8 -*-
"""
saber_pln_kira.py - LENGUAJE NATURAL, RAG, APRENDIZAJE AUTOMÁTICO y AJUSTE FINO para Kira, en Python puro.

  RECETAS   : tokenizar y sacar raíces en español, TF-IDF + coseno, buscador BM25, clasificador de sentimiento (Naive
              Bayes), modelo de lenguaje de n-gramas, extracción de entidades, RAG en pequeño (recuperar + responder
              citando), regresión logística, árbol de decisión (ID3) y LoRA en pequeño (ajuste fino con pocas
              variables). Cada una con su "prueba" (tests/test_saber_avanzado.py: dos laboratorios y el editor).
  CONCEPTOS : fichas de PLN, RAG, ajuste fino (LoRA, QLoRA, DPO), aprendizaje automático clásico, frameworks de deep
              learning y modelos en el móvil.
saber_avanzado_kira las suma: «estudia lenguaje natural», «estudia machine learning», «recetas de lenguaje natural».
"""

_ES_VACIAS = ("de la que el en y a los del se las por un para con no una su al lo como más pero sus le ya o este sí "
              "porque esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante todos "
              "uno les ni contra otros ese eso ante ellos e esto mí antes algunos qué unos yo otro otras otra él tanto "
              "esa estos mucho quienes nada muchos cual poco ella estar estas algunas algo nosotros es son fue era")

RECETAS = [
{
"id": "raices_es",
"titulo": "Tokenizar y sacar raíces de palabras en español (stemming)",
"area": "IA: lenguaje natural y RAG",
"temas": "tokenizar tokenizacion raices stemming lematizar palabras vacias stopwords normalizar tildes texto "
         "procesamiento lenguaje natural pln nlp espanol",
"idea": "Lo primero en PLN es partir el texto en palabras (tokens), pasarlas a minúsculas, quitar tildes y palabras "
        "vacías («de», «la», «que»…) y reducir cada palabra a su RAÍZ quitando terminaciones (plurales, género, "
        "«-mente», «-ción», tiempos verbales): «jugaban», «jugando» y «juegos» quedan casi iguales. Así un buscador "
        "encuentra lo mismo dicho de formas distintas. Lematizar es más fino: usa un diccionario para llegar a la "
        "palabra base («fueron» -> «ir»).",
"complejidad": "O(longitud del texto)",
"codigo": r'''
import re
import unicodedata

VACIAS = set("''' + _ES_VACIAS + r'''".split())
SUFIJOS = sorted(["amientos", "imientos", "amiento", "imiento", "aciones", "uciones", "adoras", "adores", "ancias",
                  "mente", "acion", "ucion", "adora", "ador", "ancia", "ables", "ibles", "istas", "able", "ible",
                  "ista", "osos", "osas", "oso", "osa", "ando", "iendo", "aban", "aron", "ieron", "aba", "ado", "ada",
                  "idos", "idas", "ido", "ida", "ar", "er", "ir", "es", "os", "as", "a", "o", "e", "s"], key=len, reverse=True)


def sin_tildes(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def tokens(texto):
    return re.findall(r"[a-zñ0-9]+", sin_tildes(texto))


def raiz(palabra):
    for s in SUFIJOS:
        if palabra.endswith(s) and len(palabra) - len(s) >= 3:
            return palabra[:-len(s)]
    return palabra


def registrar():
    def analiza(texto):
        # «raices: Los niños jugaban felizmente con sus juegos»
        ts = tokens(texto)
        utiles = [t for t in ts if t not in VACIAS]
        return (f"Tokens ({len(ts)}): {' '.join(ts)}\nSin palabras vacías ({len(utiles)}): {' '.join(utiles)}\n"
                f"Raíces: {' '.join(raiz(t) for t in utiles)}")
    return {"raices": analiza}
''',
"prueba": [("raices", "Los niños jugaban felizmente con sus juegos", "Raíces: nin jug feliz jueg"),
           ("raices", "La canción", "Tokens (2): la cancion")],
},
{
"id": "tfidf_coseno",
"titulo": "TF-IDF y similitud del coseno: qué textos se parecen",
"area": "IA: lenguaje natural y RAG",
"temas": "tfidf tf idf similitud coseno vectores documentos parecidos frecuencia palabras buscar textos parecidos "
         "pln nlp clasificar agrupar",
"idea": "Cada texto se convierte en un vector: una casilla por palabra con su peso TF-IDF = (cuántas veces sale en "
        "ESE texto) × log(nº de textos / nº de textos que la tienen). Así pesan las palabras que distinguen y casi "
        "nada las que salen en todos. La similitud del coseno (producto escalar entre longitudes) dice cuánto se "
        "parecen dos textos, de 0 a 1, sin que importe su largo.",
"complejidad": "O(palabras) por texto; comparar dos vectores dispersos O(palabras en común)",
"codigo": r'''
import math
import re


def palabras(t):
    return [w for w in re.findall(r"\w+", t.lower()) if len(w) > 2]


def tfidf(textos):
    docs = [palabras(t) for t in textos]
    df = {}
    for d in docs:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    n = len(docs)
    vectores = []
    for d in docs:
        v = {}
        for w in d:
            v[w] = v.get(w, 0) + 1
        vectores.append({w: (c / len(d)) * math.log((1 + n) / (1 + df[w])) + 1e-9 for w, c in v.items()})
    return vectores


def coseno(a, b):
    num = sum(a[w] * b[w] for w in set(a) & set(b))
    den = math.sqrt(sum(x * x for x in a.values())) * math.sqrt(sum(x * x for x in b.values()))
    return num / den if den else 0.0


def registrar():
    def compara(texto):
        # «parecidos: el gato come pescado | el perro come carne | la bolsa sube hoy»
        textos = [t.strip() for t in texto.split("|") if t.strip()]
        if len(textos) < 2:
            raise ValueError("Uso: parecidos: texto 1 | texto 2 | texto 3")
        v = tfidf(textos)
        pares = sorted(((coseno(v[i], v[j]), i, j) for i in range(len(v)) for j in range(i + 1, len(v))), reverse=True)
        lineas = [f"{s:.2f}  «{textos[i]}» ~ «{textos[j]}»" for s, i, j in pares]
        return "\n".join(lineas) + f"\nLos más parecidos: «{textos[pares[0][1]]}» y «{textos[pares[0][2]]}»"
    return {"parecidos": compara}
''',
"prueba": [("parecidos", "el gato come pescado fresco | el perro come carne fresca | la bolsa sube hoy en Madrid",
            "Los más parecidos: «el gato come pescado fresco» y «el perro come carne fresca»")],
},
{
"id": "bm25",
"titulo": "Buscador BM25 (el que usan los buscadores y los RAG)",
"area": "IA: lenguaje natural y RAG",
"temas": "bm25 buscador busqueda ranking relevancia documentos consulta indice invertido rag recuperar okapi "
         "lucene elasticsearch pln",
"idea": "BM25 puntúa cada documento para una consulta: por cada palabra buscada suma su IDF (lo rara que es) × una "
        "frecuencia «saturada» (que salga 10 veces no vale 10 veces más que una) y penaliza los documentos largos. "
        "Parámetros típicos k1 = 1,5 y b = 0,75. Con un índice invertido (palabra -> documentos) no hace falta mirar "
        "todos. Es la base de Lucene/Elasticsearch y una gran primera etapa de un RAG.",
"complejidad": "consulta O(documentos que tienen las palabras); índice O(palabras totales)",
"codigo": r'''
import math
import re

DOCS = ["La fotosíntesis transforma la luz del sol en energía química en las hojas.",
        "Las mitocondrias producen la energía de la célula mediante la respiración.",
        "El agua sube por el xilema desde las raíces hasta las hojas.",
        "La clorofila es el pigmento verde que capta la luz.",
        "Los volcanes expulsan lava cuando sube el magma."]


def palabras(t):
    return [w[:6] for w in re.findall(r"\w+", t.lower()) if len(w) > 2]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [palabras(d) for d in docs]
        self.k1, self.b = k1, b
        self.media = sum(len(d) for d in self.docs) / len(self.docs)
        self.indice = {}
        for i, d in enumerate(self.docs):
            for w in set(d):
                self.indice.setdefault(w, set()).add(i)

    def puntos(self, consulta):
        n, res = len(self.docs), {}
        for w in set(palabras(consulta)):
            con = self.indice.get(w, ())
            idf = math.log(1 + (n - len(con) + 0.5) / (len(con) + 0.5))
            for i in con:
                f = self.docs[i].count(w)
                largo = len(self.docs[i])
                res[i] = res.get(i, 0.0) + idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * largo / self.media))
        return sorted(res.items(), key=lambda x: -x[1])


def registrar():
    def busca(texto):
        # «bm25: ¿qué capta la luz en las plantas?»
        res = BM25(DOCS).puntos(texto)
        if not res:
            return "Ningún documento tiene esas palabras."
        return "\n".join(f"{p:.2f}  {DOCS[i]}" for i, p in res[:3]) + f"\nEl mejor: documento {res[0][0] + 1}"
    return {"bm25": busca}
''',
"prueba": [("bm25", "¿qué pigmento capta la luz?", "El mejor: documento 4"), ("bm25", "cómo sube el agua", "El mejor: documento 3")],
},
{
"id": "sentimiento_bayes",
"titulo": "Clasificar textos: sentimiento con Naive Bayes",
"area": "IA: lenguaje natural y RAG",
"temas": "clasificar textos sentimiento opinion positivo negativo naive bayes bayes probabilidad spam filtro "
         "aprendizaje automatico supervisado pln reseñas",
"idea": "Naive Bayes aprende de ejemplos etiquetados cuántas veces sale cada palabra en cada clase. Para un texto "
        "nuevo suma log P(clase) + Σ log P(palabra | clase) y gana la clase con más puntos. Es «ingenuo» porque "
        "supone las palabras independientes, pero funciona sorprendentemente bien (filtros de spam). El suavizado de "
        "Laplace (+1) evita que una palabra nunca vista dé probabilidad cero.",
"complejidad": "entrenar O(palabras de los ejemplos); clasificar O(palabras del texto × clases)",
"codigo": r'''
import math
import re

EJEMPLOS = [("me encanta, es genial y muy bonito", "positivo"), ("qué maravilla, funciona perfecto", "positivo"),
            ("estoy muy contento con el resultado", "positivo"), ("excelente servicio, lo recomiendo", "positivo"),
            ("me gusta mucho, es fantástico", "positivo"), ("una experiencia increíble y divertida", "positivo"),
            ("es horrible, no funciona nada", "negativo"), ("qué desastre, muy malo", "negativo"),
            ("estoy enfadado, es una estafa", "negativo"), ("pésimo servicio, no lo recomiendo", "negativo"),
            ("me aburre, es feo y lento", "negativo"), ("una experiencia terrible y triste", "negativo")]


def palabras(t):
    return re.findall(r"\w+", t.lower())


def entrenar(ejemplos):
    cuentas, totales, docs, vocab = {}, {}, {}, set()
    for texto, c in ejemplos:
        docs[c] = docs.get(c, 0) + 1
        for w in palabras(texto):
            cuentas.setdefault(c, {})[w] = cuentas.setdefault(c, {}).get(w, 0) + 1
            totales[c] = totales.get(c, 0) + 1
            vocab.add(w)
    return cuentas, totales, docs, vocab


def clasificar(modelo, texto):
    cuentas, totales, docs, vocab = modelo
    n = sum(docs.values())
    puntos = {}
    for c in docs:
        p = math.log(docs[c] / n)
        for w in palabras(texto):
            p += math.log((cuentas[c].get(w, 0) + 1) / (totales[c] + len(vocab)))
        puntos[c] = p
    mejor = max(puntos, key=puntos.get)
    m = max(puntos.values())
    seguridad = math.exp(puntos[mejor] - m) / sum(math.exp(v - m) for v in puntos.values())
    return mejor, seguridad


def registrar():
    modelo = entrenar(EJEMPLOS)

    def sentimiento(texto):
        # «sentimiento: me encanta este móvil, funciona genial»
        c, s = clasificar(modelo, texto)
        return f"Sentimiento: {c} (seguro al {s:.0%})"
    return {"sentimiento": sentimiento}
''',
"prueba": [("sentimiento", "me encanta este móvil, funciona genial", "Sentimiento: positivo"),
           ("sentimiento", "es un desastre horrible y lento", "Sentimiento: negativo")],
},
{
"id": "ngramas",
"titulo": "Modelo de lenguaje de n-gramas: predecir la siguiente palabra",
"area": "IA: lenguaje natural y RAG",
"temas": "ngramas bigramas trigramas modelo lenguaje predecir siguiente palabra perplejidad suavizado markov "
         "autocompletar teclado pln",
"idea": "Antes de las redes neuronales, un modelo de lenguaje contaba: P(palabra | las anteriores) ≈ veces que salió "
        "ese par entre veces que salió la anterior. Con eso se autocompleta (teclados) y se mide la PERPLEJIDAD: lo "
        "«sorprendido» que está el modelo ante un texto (más baja, mejor). El suavizado reparte algo de probabilidad a "
        "lo no visto. Los LLM hacen lo mismo, predecir la siguiente ficha, pero con una red y todo el contexto.",
"complejidad": "entrenar O(palabras); predecir O(1) con un diccionario",
"codigo": r'''
import math
import re

CORPUS = ("kira es mi asistente . kira me ayuda a programar . kira me ayuda a estudiar . "
          "mi asistente programa juegos . el asistente estudia mucho .")


def entrenar(texto):
    w = texto.split()
    uni, bi = {}, {}
    for a, b in zip(w, w[1:]):
        uni[a] = uni.get(a, 0) + 1
        bi.setdefault(a, {})[b] = bi.setdefault(a, {}).get(b, 0) + 1
    return uni, bi, set(w)


def prob(m, a, b):
    uni, bi, vocab = m
    return (bi.get(a, {}).get(b, 0) + 0.1) / (uni.get(a, 0) + 0.1 * len(vocab))   # suavizado aditivo


def perplejidad(m, frase):
    w = frase.split()
    lp = sum(math.log(prob(m, a, b)) for a, b in zip(w, w[1:]))
    return math.exp(-lp / max(1, len(w) - 1))


def registrar():
    m = entrenar(CORPUS)

    def predice(texto):
        # «ngramas: kira me»
        w = re.findall(r"\S+", texto.lower()) or ["kira"]
        frase = list(w)
        for _ in range(5):
            sig = m[1].get(frase[-1])
            if not sig:
                break
            frase.append(max(sig, key=sig.get))
        bien = "kira me ayuda a programar"
        mal = "programar a ayuda me kira"
        return (f"Sigue así: {' '.join(frase)}\nPerplejidad de «{bien}»: {perplejidad(m, bien):.1f}; de «{mal}»: "
                f"{perplejidad(m, mal):.1f} (lo natural sorprende menos)")
    return {"ngramas": predice}
''',
"prueba": [("ngramas", "kira me", "Sigue así: kira me ayuda a programar"), ("ngramas", "", "(lo natural sorprende menos)")],
},
{
"id": "entidades",
"titulo": "Extraer entidades: fechas, horas, correos, cantidades y nombres",
"area": "IA: lenguaje natural y RAG",
"temas": "entidades ner extraer fechas horas correos emails telefonos cantidades dinero nombres propios "
         "informacion texto pln reconocimiento",
"idea": "Reconocer ENTIDADES es sacar del texto lo que importa: quién, cuándo, cuánto, dónde. Con reglas "
        "(expresiones regulares) se cogen bien las que tienen forma fija: fechas, horas, correos, teléfonos, dinero. "
        "Los nombres propios se intuyen por la mayúscula fuera del principio de frase. Los modelos (spaCy, BERT) "
        "aprenden también lugares y organizaciones por el contexto, pero las reglas son rápidas y fiables.",
"complejidad": "O(longitud del texto)",
"codigo": r'''
import re

PATRONES = [
    ("fecha", r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{1,2} de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?: de \d{4})?\b"),
    ("hora", r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b"),
    ("correo", r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),
    ("teléfono", r"\b(?:\+34\s?)?[6789]\d{2}\s?\d{3}\s?\d{3}\b"),
    ("dinero", r"\b\d+(?:[.,]\d+)?\s?(?:€|euros?|dólares?|\$)"),
]


def entidades(texto):
    res = []
    for tipo, p in PATRONES:
        for m in re.finditer(p, texto, re.I):
            res.append((m.start(), tipo, m.group(0)))
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)", texto):
        if not any(s <= m.start() < s + len(v) for s, _t, v in res):
            res.append((m.start(), "nombre", m.group(1)))
    return sorted(res)


def registrar():
    def extrae(texto):
        # «entidades: Quedé con Ana López el 12 de marzo a las 18:30, son 25 euros, escribe a ana@correo.es»
        res = entidades(texto)
        if not res:
            return "No encuentro entidades."
        return "\n".join(f"{t}: {v}" for _s, t, v in res)
    return {"entidades": extrae}
''',
"prueba": [("entidades", "Quedé con Ana López el 12 de marzo a las 18:30, son 25 euros, escribe a ana@correo.es",
            "nombre: Ana López\nfecha: 12 de marzo\nhora: 18:30\ndinero: 25 euros\ncorreo: ana@correo.es")],
},
{
"id": "rag_mini",
"titulo": "RAG en pequeño: recuperar trozos y responder citando",
"area": "IA: lenguaje natural y RAG",
"temas": "rag generacion recuperacion aumentada retrieval augmented generation documentos trozos chunks citar "
         "fuentes responder preguntas apuntes base conocimiento alucinaciones",
"idea": "RAG = Recuperar + Generar: 1) TROCEAR los documentos (párrafos o ~500 palabras, con algo de solape); 2) "
        "RECUPERAR los trozos más parecidos a la pregunta (BM25 o embeddings); 3) darle esos trozos al modelo de "
        "lenguaje con la orden «responde solo con esto y di de dónde sale». Así responde con TUS datos, actualizados, "
        "y se puede comprobar. Aquí la «generación» es extractiva (la frase que mejor responde), sin modelo grande.",
"complejidad": "recuperar O(trozos con palabras en común); responder O(frases de los trozos elegidos)",
"codigo": r'''
import math
import re

APUNTES = {"biologia.pdf": "La fotosíntesis ocurre en los cloroplastos. La clorofila capta la luz roja y azul. "
                           "El oxígeno se libera como producto de la fotosíntesis.",
           "historia.pdf": "La Revolución Francesa empezó en 1789 con la toma de la Bastilla. "
                           "Napoleón se coronó emperador en 1804.",
           "fisica.pdf": "La luz viaja a unos 300.000 kilómetros por segundo. "
                         "El sonido necesita un medio para propagarse."}


def raices(t):
    return [w[:5] for w in re.findall(r"\w+", t.lower()) if len(w) > 3]


def trocear():
    trozos = []
    for doc, texto in APUNTES.items():
        for i, frase in enumerate(re.split(r"(?<=\.)\s+", texto)):
            if frase.strip():
                trozos.append((doc, i + 1, frase.strip()))
    return trozos


def recuperar(pregunta, trozos, n=2):
    q = set(raices(pregunta))
    df = {}
    for _d, _i, t in trozos:
        for w in set(raices(t)):
            df[w] = df.get(w, 0) + 1
    puntos = []
    for d, i, t in trozos:
        p = sum(math.log(1 + len(trozos) / df[w]) for w in q & set(raices(t)))
        if p > 0:
            puntos.append((p, d, i, t))
    return sorted(puntos, reverse=True)[:n]


def registrar():
    def responde(texto):
        # «rag: ¿cuándo empezó la Revolución Francesa?»
        mejores = recuperar(texto, trocear())
        if not mejores:
            return "Mis apuntes no dicen nada de eso (y no me lo invento)."
        _p, d, i, t = mejores[0]
        fuentes = ", ".join(f"{dd} §{ii}" for _pp, dd, ii, _tt in mejores)
        return f"Respuesta: {t}\nFuente: {d}, frase {i}\nTrozos recuperados: {fuentes}"
    return {"rag": responde}
''',
"prueba": [("rag", "¿cuándo empezó la Revolución Francesa?", "Respuesta: La Revolución Francesa empezó en 1789"),
           ("rag", "¿qué capta la clorofila?", "Fuente: biologia.pdf"),
           ("rag", "receta de paella valenciana", "no me lo invento")],
},
{
"id": "regresion_logistica",
"titulo": "Regresión logística: clasificar con probabilidades",
"area": "IA: aprendizaje automático",
"temas": "regresion logistica clasificar probabilidad sigmoide frontera decision aprendizaje automatico machine "
         "learning aprobar suspender descenso gradiente entropia cruzada",
"idea": "Para decidir entre dos clases, la regresión logística calcula z = w·x + b y lo pasa por la sigmoide "
        "1 / (1 + e^-z): da una PROBABILIDAD entre 0 y 1. Se entrena con descenso de gradiente sobre la entropía "
        "cruzada; el gradiente es (p − y)·x, igual que en una neurona (es una red de UNA neurona). La frontera de "
        "decisión es la recta donde p = 0,5.",
"complejidad": "entrenar O(épocas × ejemplos × variables); predecir O(variables)",
"codigo": r'''
import math

# horas de estudio y horas de sueño -> ¿aprueba?
DATOS = [((1, 4), 0), ((2, 5), 0), ((2, 8), 0), ((3, 6), 0), ((4, 4), 0), ((4, 7), 1), ((5, 8), 1),
         ((6, 6), 1), ((6, 8), 1), ((7, 5), 1), ((8, 7), 1), ((3, 3), 0), ((5, 4), 0), ((7, 8), 1)]


def sigmoide(z):
    return 1 / (1 + math.exp(-max(-50, min(50, z))))


def entrenar(datos, epocas=4000, ritmo=0.1):
    w, b = [0.0, 0.0], 0.0
    for _ in range(epocas):
        gw, gb = [0.0, 0.0], 0.0
        for x, y in datos:
            p = sigmoide(w[0] * x[0] + w[1] * x[1] + b)
            gw[0] += (p - y) * x[0]
            gw[1] += (p - y) * x[1]
            gb += p - y
        w = [w[0] - ritmo * gw[0] / len(datos), w[1] - ritmo * gw[1] / len(datos)]
        b -= ritmo * gb / len(datos)
    return w, b


def registrar():
    w, b = entrenar(DATOS)

    def predice(texto):
        # «aprobare: 6 7» -> horas de estudio y de sueño
        p = [float(v) for v in texto.replace(",", ".").split()[:2]] or [5.0, 7.0]
        estudio, sueno = (p + [7.0])[:2]
        prob = sigmoide(w[0] * estudio + w[1] * sueno + b)
        aciertos = sum((sigmoide(w[0] * x[0] + w[1] * x[1] + b) >= 0.5) == bool(y) for x, y in DATOS)
        return (f"Con {estudio:g} h de estudio y {sueno:g} h de sueño: {prob:.0%} de aprobar\n"
                f"Acierta {aciertos} de {len(DATOS)} ejemplos de entrenamiento")
    return {"aprobare": predice}
''',
"prueba": [("aprobare", "7 8", "100% de aprobar"), ("aprobare", "1 4", "0% de aprobar\nAcierta 14 de 14")],
},
{
"id": "arbol_decision",
"titulo": "Árbol de decisión (ID3): aprender reglas que se entienden",
"area": "IA: aprendizaje automático",
"temas": "arbol decision id3 entropia ganancia informacion reglas clasificar aprendizaje automatico machine "
         "learning explicable random forest jugar tenis tiempo",
"idea": "Un árbol de decisión pregunta una cosa en cada nodo («¿hace sol?») y baja por la rama de la respuesta hasta "
        "una hoja con la clase. ID3 elige en cada paso la pregunta que más ORDENA los ejemplos: la de mayor ganancia "
        "de información (lo que baja la entropía). Se entiende a simple vista. Muchos árboles al azar votando forman "
        "un «random forest», de lo mejor para datos en tabla.",
"complejidad": "construir O(atributos × ejemplos × profundidad)",
"codigo": r'''
import math

COLUMNAS = ["cielo", "temperatura", "humedad", "viento"]
DATOS = [("sol", "calor", "alta", "no", "no"), ("sol", "calor", "alta", "si", "no"), ("nubes", "calor", "alta", "no", "si"),
         ("lluvia", "templado", "alta", "no", "si"), ("lluvia", "frio", "normal", "no", "si"),
         ("lluvia", "frio", "normal", "si", "no"), ("nubes", "frio", "normal", "si", "si"),
         ("sol", "templado", "alta", "no", "no"), ("sol", "frio", "normal", "no", "si"),
         ("lluvia", "templado", "normal", "no", "si"), ("sol", "templado", "normal", "si", "si"),
         ("nubes", "templado", "alta", "si", "si"), ("nubes", "calor", "normal", "no", "si"),
         ("lluvia", "templado", "alta", "si", "no")]


def entropia(filas):
    total = len(filas)
    cuenta = {}
    for f in filas:
        cuenta[f[-1]] = cuenta.get(f[-1], 0) + 1
    return -sum(c / total * math.log2(c / total) for c in cuenta.values())


def construir(filas, columnas):
    clases = {f[-1] for f in filas}
    if len(clases) == 1 or not columnas:
        return max(clases, key=lambda c: sum(f[-1] == c for f in filas))
    def ganancia(i):
        resto = 0.0
        for v in {f[i] for f in filas}:
            sub = [f for f in filas if f[i] == v]
            resto += len(sub) / len(filas) * entropia(sub)
        return entropia(filas) - resto
    mejor = max(columnas, key=ganancia)
    return (mejor, {v: construir([f for f in filas if f[mejor] == v], [c for c in columnas if c != mejor])
                    for v in sorted({f[mejor] for f in filas})})


def dibujar(arbol, sangria=""):
    if not isinstance(arbol, tuple):
        return [sangria + "-> " + arbol]
    col, ramas = arbol
    lineas = []
    for v, sub in ramas.items():
        lineas.append(f"{sangria}si {COLUMNAS[col]} = {v}:")
        lineas += dibujar(sub, sangria + "   ")
    return lineas


def registrar():
    arbol = construir(DATOS, list(range(len(COLUMNAS))))

    def explica(texto):
        # «arbol decision» -> ¿se juega al tenis según el tiempo?
        return "¿Jugamos al tenis?\n" + "\n".join(dibujar(arbol))
    return {"arbol decision": explica}
''',
"prueba": [("arbol decision", "", "si cielo = nubes:\n   -> si"), ("arbol decision", "", "si humedad = alta:")],
},
{
"id": "lora_mini",
"titulo": "LoRA en pequeño: ajuste fino entrenando muy pocas variables",
"area": "IA: ajuste fino",
"temas": "lora ajuste fino fine tuning qlora adaptador rango bajo matrices pesos congelados parametros entrenar "
         "modelo base adaptar tarea nueva llm",
"idea": "Ajustar un modelo grande entero es carísimo. LoRA deja los pesos W CONGELADOS y aprende solo un cambio de "
        "RANGO BAJO: W' = W + B·A, con A (r×n) y B (m×r) y r pequeño (4-64). Se entrena un 0,1-1 % de los "
        "parámetros, cabe en una tarjeta gráfica normal y el adaptador ocupa megas, no gigas (llama.cpp lo carga "
        "con --lora). QLoRA hace lo mismo con el modelo base cuantizado a 4 bits.",
"complejidad": "parámetros entrenados r·(m + n) en vez de m·n",
"codigo": r'''
import random

N = 6                                              # una capa 6x6 (en un LLM serían 4096x4096)


def matvec(M, x):
    return [sum(a * b for a, b in zip(fila, x)) for fila in M]


def registrar():
    def ajusta(texto):
        # «lora: 1» -> rango del adaptador
        r = max(1, min(4, int(texto.strip() or "1")))
        rnd = random.Random(2)
        W = [[rnd.uniform(-1, 1) for _ in range(N)] for _ in range(N)]            # el modelo «base» (congelado)
        u = [rnd.uniform(-1, 1) for _ in range(N)]
        v = [rnd.uniform(-1, 1) for _ in range(N)]
        objetivo = [[W[i][j] + 0.8 * u[i] * v[j] for j in range(N)] for i in range(N)]   # la tarea nueva
        datos = [[rnd.uniform(-1, 1) for _ in range(N)] for _ in range(16)]
        A = [[rnd.uniform(-0.1, 0.1) for _ in range(N)] for _ in range(r)]
        B = [[0.0] * r for _ in range(N)]                                        # B empieza en cero: W' = W
        def error():
            e = 0.0
            for x in datos:
                y, t = matvec(W, x), matvec(objetivo, x)
                ax = matvec(A, x)
                y = [yi + sum(B[i][k] * ax[k] for k in range(r)) for i, yi in enumerate(y)]
                e += sum((a - b) ** 2 for a, b in zip(y, t))
            return e / len(datos)
        antes = error()
        for _ in range(120):
            for x in datos:
                ax = matvec(A, x)
                y = [sum(W[i][j] * x[j] for j in range(N)) + sum(B[i][k] * ax[k] for k in range(r)) for i in range(N)]
                t = matvec(objetivo, x)
                d = [2 * (a - b) for a, b in zip(y, t)]
                gB = [[d[i] * ax[k] for k in range(r)] for i in range(N)]
                dax = [sum(B[i][k] * d[i] for i in range(N)) for k in range(r)]
                for k in range(r):
                    for j in range(N):
                        A[k][j] -= 0.03 * dax[k] * x[j]
                for i in range(N):
                    for k in range(r):
                        B[i][k] -= 0.03 * gB[i][k]
        despues = error()
        total = N * N
        entrenados = r * 2 * N
        return (f"Error en la tarea nueva: antes {antes:.3f}, después {despues:.4f}\n"
                f"Parámetros entrenados: {entrenados} de {total} ({entrenados / total:.0%}); el modelo base, intacto")
    return {"lora": ajusta}
''',
"prueba": [("lora", "1", "Parámetros entrenados: 12 de 36 (33%); el modelo base, intacto"), ("lora", "1", "después 0.00")],
},
]


CONCEPTOS = [
{"id": "pln_basico", "area": "IA: lenguaje natural y RAG", "titulo": "Procesamiento del lenguaje natural (PLN): las piezas",
 "temas": "pln nlp procesamiento lenguaje natural tokenizacion lematizacion etiquetado gramatical analisis sintactico ner",
 "texto": "El PLN enseña a los ordenadores a trabajar con texto. Piezas clásicas: TOKENIZAR (partir en palabras o "
          "subpalabras), normalizar (minúsculas, tildes), quitar palabras vacías, sacar RAÍCES o LEMAS, etiquetar la "
          "gramática (sustantivo, verbo…), analizar la sintaxis (quién hace qué), reconocer ENTIDADES (personas, "
          "lugares, fechas), clasificar textos (temas, spam, sentimiento), resumir y traducir. Hoy muchas se hacen con "
          "un único modelo de lenguaje, pero las clásicas siguen siendo rápidas, baratas y explicables. En Python: "
          "spaCy, NLTK, y en Kira, recetas en Python puro («recetas de lenguaje natural»)."},
{"id": "tokenizacion_llm", "area": "IA: lenguaje natural y RAG", "titulo": "Fichas (tokens) y tokenizadores de los LLM",
 "temas": "tokens fichas tokenizador bpe subpalabras vocabulario sentencepiece contexto contar tokens coste",
 "texto": "Los modelos de lenguaje no leen letras ni palabras sino FICHAS (tokens): trozos frecuentes de palabras "
          "aprendidos con BPE o SentencePiece. En español una palabra son 1-2 fichas de media; el código y los "
          "números, más. El vocabulario tiene decenas de miles de fichas. La memoria de trabajo (contexto) se mide en "
          "fichas, y lo que se le da más lo que escribe tiene que caber: por eso Kira recorta lo que le da a su "
          "cerebro del móvil (2048 fichas). El coste y la velocidad también van por fichas."},
{"id": "rag", "area": "IA: lenguaje natural y RAG", "titulo": "RAG: generación aumentada por recuperación",
 "temas": "rag generacion aumentada recuperacion retrieval documentos trozos embeddings bm25 citar alucinaciones base conocimiento",
 "texto": "Un modelo de lenguaje solo sabe lo que vio al entrenarse y a veces se inventa cosas. RAG le da, en cada "
          "pregunta, los TROZOS de tus documentos que vienen al caso: 1) trocear (párrafos o 300-800 palabras con "
          "solape), 2) indexar (BM25 por palabras y/o EMBEDDINGS por significado), 3) recuperar los mejores (a veces "
          "con un segundo paso que los reordena), 4) pedir al modelo que responda SOLO con ellos y cite de dónde. "
          "Ventajas: datos al día y privados, respuestas comprobables y menos alucinaciones, sin reentrenar. Kira lo "
          "hace con «pregunta a mis documentos: …» sobre tus PDF (BM25, con página)."},
{"id": "rag_calidad", "area": "IA: lenguaje natural y RAG", "titulo": "Cómo hacer un buen RAG",
 "temas": "rag calidad troceado chunking solape reordenar reranking busqueda hibrida evaluar recuperacion fidelidad",
 "texto": "El 80 % de un RAG es la RECUPERACIÓN: si el trozo bueno no llega, el modelo no puede acertar. Trucos: "
          "trozos con sentido (por secciones, no a ciegas) y algo de solape; guardar título y página con cada trozo; "
          "búsqueda HÍBRIDA (palabras exactas con BM25 + significado con embeddings); reordenar los 20-50 primeros con un "
          "modelo «reranker»; no pasarse de trozos (diluyen); y pedir citas. Se evalúa por separado: ¿recupera el "
          "trozo correcto? (recall@k) y ¿la respuesta es fiel a los trozos? Lo que viene de internet son DATOS, no "
          "órdenes (Kira no deja que un documento le dé instrucciones)."},
{"id": "ajuste_fino", "area": "IA: ajuste fino", "titulo": "Ajuste fino (fine-tuning): cuándo y cómo",
 "temas": "ajuste fino fine tuning entrenar modelo datos instrucciones sft lora qlora cuando rag prompt",
 "texto": "Ajustar un modelo es seguir entrenándolo con TUS ejemplos para que aprenda un estilo, un formato o una "
          "tarea. Orden recomendado: primero un buen prompt con ejemplos; si falta conocimiento, RAG; y si lo que "
          "falla es la FORMA (que escriba módulos de Kira bien hechos, con su estilo), ajuste fino. Se hace con pares "
          "pregunta → respuesta buena (SFT), cientos o miles, limpios y variados. Con LoRA o QLoRA basta una tarjeta "
          "gráfica de consumo o un Colab gratuito para modelos de 1-8 mil millones de parámetros; el resultado se "
          "convierte a GGUF y llama.cpp lo carga con --lora. Riesgos: sobreajuste y «olvido» de lo que ya sabía."},
{"id": "lora_qlora", "area": "IA: ajuste fino", "titulo": "LoRA y QLoRA por dentro",
 "temas": "lora qlora rango bajo adaptador peft cuantizado 4 bits nf4 alfa rango parametros gguf convertir",
 "texto": "LoRA congela los pesos del modelo y, en cada capa elegida (normalmente las de atención q, k, v, o), añade "
          "dos matrices pequeñas A y B cuyo producto es el cambio: W + (α/r)·B·A. Con rango r = 8-16 se entrena menos "
          "del 1 % de los parámetros. QLoRA guarda el modelo base en 4 bits (NF4) para que quepa en poca memoria y "
          "entrena el LoRA en 16 bits. Librerías: Hugging Face PEFT + Transformers (o Unsloth, más rápido). El "
          "adaptador se puede fusionar con el modelo o cargarse aparte; llama.cpp lo convierte a GGUF "
          "(convert_lora_to_gguf.py). Receta: «lora»."},
{"id": "preferencias", "area": "IA: ajuste fino", "titulo": "Alinear con preferencias: RLHF y DPO",
 "temas": "rlhf dpo preferencias alinear recompensa humano mejor peor ajuste fino chat asistente",
 "texto": "Tras enseñarle con ejemplos (SFT), se puede afinar con PREFERENCIAS: pares de respuestas a la misma "
          "pregunta, una mejor y otra peor. RLHF entrena un modelo de recompensa con esas preferencias y luego "
          "optimiza el modelo con refuerzo; DPO consigue algo parecido directamente, sin modelo de recompensa ni "
          "refuerzo, y es mucho más sencillo. Las mejoras que apruebas y las que rechazas en Kira son justo eso: "
          "preferencias tuyas (Kira puede exportarlas para entrenar)."},
{"id": "ml_clasico", "area": "IA: aprendizaje automático", "titulo": "Aprendizaje automático clásico: qué usar",
 "temas": "machine learning aprendizaje automatico regresion logistica arboles random forest gradient boosting svm knn scikit learn tabla",
 "texto": "Para datos en TABLA (filas y columnas), el aprendizaje clásico suele ganar al profundo: regresión lineal y "
          "logística (rápidas, interpretables), k vecinos, árboles de decisión, RANDOM FOREST y GRADIENT BOOSTING "
          "(XGBoost, LightGBM: los reyes de las competiciones), SVM. Flujo: separar entrenamiento/prueba, escalar "
          "variables, elegir hiperparámetros con validación cruzada, medir con la métrica adecuada. En Python: "
          "scikit-learn (en el PC; en el móvil no hay versión). Kira tiene recetas en Python puro: «aprobare», «arbol "
          "decision», «agrupa» (k-means), «regresion»."},
{"id": "frameworks_dl", "area": "IA: aprendizaje automático", "titulo": "Frameworks de deep learning y modelos en el móvil",
 "temas": "pytorch tensorflow keras jax gpu cuda onnx tflite gguf llama cpp movil inferencia exportar numpy",
 "texto": "Para entrenar redes de verdad: PyTorch (el más usado en investigación), TensorFlow/Keras y JAX, con "
          "tarjeta gráfica (CUDA) o en la nube. Para USARLAS en el móvil se exportan a formatos ligeros: TensorFlow "
          "Lite, ONNX Runtime, o GGUF para llama.cpp (el cerebro de Kira) y stable-diffusion.cpp (su pintor), "
          "normalmente cuantizadas. En el móvil, Kira lleva numpy para cálculo con matrices; PyTorch no tiene versión "
          "para Python en Android. Por eso: entrenar en el PC/Colab, ejecutar en el móvil."},
{"id": "datos_entrenamiento", "area": "IA: ajuste fino", "titulo": "Datos de entrenamiento: la parte que más importa",
 "temas": "datos entrenamiento dataset calidad limpiar etiquetar jsonl formato chat instrucciones duplicados sesgo",
 "texto": "Un modelo es tan bueno como sus datos. Para ajuste fino: ejemplos REALES de lo que quieres (pedido → "
          "respuesta correcta), revisados a mano, sin duplicados, variados (no 500 veces lo mismo) y en el formato "
          "de chat del modelo (JSONL con mensajes system/user/assistant). Mejor 300 buenos que 5000 regulares. "
          "Separa un 10 % para evaluar. Cuidado con datos privados y con los sesgos. Kira junta los suyos solos: "
          "cada mejora que apruebas (y que pasó el laboratorio) es un ejemplo bueno; «prepara datos de "
          "entrenamiento» los exporta."},
]
