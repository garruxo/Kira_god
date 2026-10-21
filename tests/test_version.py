# -*- coding: utf-8 -*-
"""La versión que enseña Kira es la misma que la del APK (buildozer.spec)."""
import os, re, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import version_kira
v = re.search(r"^version\s*=\s*(\S+)", open(os.path.join(RAIZ, "buildozer.spec"), encoding="utf-8").read(), re.M).group(1)
assert v == version_kira.VERSION, f"FALLA: buildozer.spec dice {v} y version_kira.py dice {version_kira.VERSION}"
print("VERSIÓN OK", v)
