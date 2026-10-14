"""Renderers de escenas. Cada módulo expone:

    render(params, ctx, salida) -> list[dict]

Escribe un MP4 de ctx.dur segundos (ctx.w x ctx.h, 30 fps) y devuelve los efectos
de sonido que la escena pide, con tiempos relativos a su inicio:
[{"sfx": "tap", "t": 1.2}]."""
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Ctx:
    w: int
    h: int
    marca: object
    proyecto: Path
    dur: float
    t0: float = 0.0  # segundo del video en que empieza la escena
    palabras: list = field(default_factory=list)
    trabajo: Path = None  # carpeta para intermedios de esta escena

    def ruta(self, p):
        """Rutas de params: relativas al proyecto, o "marca:<rel>" para el kit de marca."""
        if not p:
            return None
        if str(p).startswith("marca:"):
            return self.marca.dir / str(p)[6:]
        q = Path(p)
        return q if q.is_absolute() else self.proyecto / q

    def frase(self, texto):
        """Segundo (relativo a la escena) en que se dice `texto`."""
        from ..voz import buscar_frase

        t = buscar_frase(self.palabras, texto)
        return None if t is None else t - self.t0


def t_de(valor, ctx, defecto=0.0):
    """Tiempo dentro de la escena: número de segundos, o "@frase del guion"
    (cae en el instante en que la voz dice esa frase). "@frase+0.8" o
    "@frase-0.3" corren ese instante; "fin" es el final de la escena."""
    if valor is None:
        return defecto
    if valor == "fin":
        return max(0.0, ctx.dur - 0.25)
    if isinstance(valor, str) and valor.startswith("@"):
        m = re.match(r"^@(.*?)\s*([+-]\d+(?:\.\d+)?)?$", valor)
        t = ctx.frase(m.group(1))
        return defecto if t is None else max(0.0, t + float(m.group(2) or 0))
    return float(valor)


def expandir_estados(estados, ctx):
    """Estados de una secuencia de capturas con tiempos absolutos de la escena.
    Además de {"t", "img"} acepta {"t", "hasta", "imgs": [...]}: reparte las
    capturas parejo entre t y hasta (un tipeo que dura lo que tarda la voz)."""
    salida = []
    for e in estados:
        t0 = t_de(e.get("t", 0), ctx)
        if "imgs" in e:
            t1 = t_de(e.get("hasta", "fin"), ctx, ctx.dur)
            paso = max(t1 - t0, 0.1) / len(e["imgs"])
            salida += [{"t": t0 + i * paso, "img": img} for i, img in enumerate(e["imgs"])]
        else:
            salida.append({**e, "t": t0})
    return sorted(salida, key=lambda e: e["t"])


def modulo(tipo):
    import importlib

    return importlib.import_module(f".{tipo}", __name__)
