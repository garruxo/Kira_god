"""Kivy de mentira, solo para comprobar el CABLEADO (no dibuja nada)."""
import sys, types, threading, time

class Canvas:
    def __init__(self): self.before = self.after = self
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def clear(self): pass
    def add(self, *a): pass

class Prop:
    def __init__(self, v=0, *a, **k): self.v = v
    def __set_name__(self, o, n): self.n = "_p_" + n
    def __get__(self, i, o=None): return self if i is None else getattr(i, self.n, self.v)
    def __set__(self, i, v): setattr(i, self.n, v)

class Widget:
    def __init__(self, *a, **kw):
        self.children, self._b, self.canvas = [], {}, Canvas()
        self.size, self.pos, self.width, self.height = (100, 100), (0, 0), 100, 100
        self.x = self.y = 0; self.center = (50, 50); self.center_x = 50; self.top = 100
        self.size_hint_y = self.size_hint_x = 1; self.disabled = False; self.opacity = 1; self.text = kw.pop("text", ""); self.texture_size = (10, 10)
        for k, v in kw.items(): setattr(self, k, v)
    def add_widget(self, w, *a): self.children.append(w)
    def remove_widget(self, w):
        if w in self.children: self.children.remove(w)
    def clear_widgets(self): self.children = []
    def bind(self, **kw):
        for k, f in kw.items(): self._b.setdefault(k, []).append(f)
    def setter(self, n): return lambda inst, v: setattr(self, n, v)
    def collide_point(self, x, y): return True
    def walk(self):
        yield self
        for c in self.children:
            if hasattr(c, "walk"): yield from c.walk()
    def fire(self, ev, *a):
        for f in self._b.get(ev, []): f(self, *a)
    def press(self): self.fire("on_release")
    def on_touch_down(self, t): return False
    def refresh(self): pass
    texture = type('Tx', (), {'size': (10, 10), 'width': 10, 'height': 10})()
    @property
    def content_size(self): return (10, 10)
    def get_screen(self, n): return next(s for s in self.children if getattr(s, "name", None) == n)

class ScreenManager(Widget):
    def __init__(self, **kw): super().__init__(**kw); self.current = None
class Screen(Widget): pass

class Evento:
    def __init__(s, f, dt, rep): s.f, s.dt, s.rep, s.t, s.vivo = f, dt, rep, 0.0, True
    def cancel(s): s.vivo = False
class _Clock:
    def __init__(s): s.ev, s.l = [], threading.Lock()
    def schedule_once(s, f, dt=0):
        e = Evento(f, dt, False)
        with s.l: s.ev.append(e)
        return e
    def schedule_interval(s, f, dt):
        e = Evento(f, dt, True)
        with s.l: s.ev.append(e)
        return e
    def correr(s, pasos=1, dt=0.1):
        for _ in range(pasos):
            with s.l: lista = list(s.ev)
            for e in lista:
                if not e.vivo: continue
                e.t += dt
                if e.t >= e.dt:
                    e.t = 0
                    if not e.rep: e.vivo = False
                    e.f(dt)
            with s.l: s.ev = [e for e in s.ev if e.vivo]
Clock = _Clock()

class Animation:
    def __init__(s, **kw): s.kw, s.cb = kw, None
    def bind(s, **kw): s.cb = kw.get("on_complete")
    def start(s, w):
        for k, v in s.kw.items():
            if k not in ("duration", "t"): setattr(w, k, v)
        if s.cb: s.cb(s, w)

class _Win(Widget):
    def __init__(s): super().__init__(); s.clearcolor = None; s.softinput_mode = ""; s.width = 400
Window = _Win()

def _mod(nombre, **attrs):
    m = types.ModuleType(nombre); m.__dict__.update(attrs); sys.modules[nombre] = m; return m
def _gen(nombre, base=Widget):
    def __getattr__(n):
        if n.startswith("__"): raise AttributeError(n)
        c = type(n, (base,), {}); setattr(sys.modules[nombre], n, c); return c
    return __getattr__

def instalar():
    k = _mod("kivy", kivy_data_dir="/nonexistent")
    for nombre in ("kivy.graphics", "kivy.uix.boxlayout", "kivy.uix.button", "kivy.uix.floatlayout", "kivy.uix.label",
                   "kivy.uix.popup", "kivy.uix.scrollview", "kivy.uix.textinput", "kivy.uix.gridlayout",
                   "kivy.uix.widget", "kivy.uix.slider", "kivy.app", "kivy.core.text", "kivy.graphics.texture", "kivy.uix.togglebutton", "kivy.uix.image"):
        m = _mod(nombre); m.__getattr__ = _gen(nombre)
    _mod("kivy.uix"); _mod("kivy.core")
    sys.modules["kivy.uix.screenmanager"] = _mod("kivy.uix.screenmanager", ScreenManager=ScreenManager, Screen=Screen,
        FadeTransition=lambda **k: None, NoTransition=lambda **k: None)
    _mod("kivy.clock", Clock=Clock); _mod("kivy.animation", Animation=Animation)
    _mod("kivy.core.window", Window=Window); _mod("kivy.metrics", dp=lambda v: v, sp=lambda v: v)
    _mod("kivy.utils", platform="linux")
    pr = _mod("kivy.properties"); pr.__getattr__ = lambda n: Prop if not n.startswith("__") else (_ for _ in ()).throw(AttributeError(n))
