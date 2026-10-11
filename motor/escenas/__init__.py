"""Renderers de escenas. Cada módulo expone:

    render(params, ctx, salida) -> list[dict]

Escribe un MP4 de ctx.dur segundos (ctx.w x ctx.h, 30 fps) y devuelve los efectos
de sonido que la escena pide, con tiempos relativos a su inicio:
[{"sfx": "tap", "t": 1.2}]."""
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
    (cae en el instante en que la voz dice esa frase)."""
    if valor is None:
        return defecto
    if isinstance(valor, str) and valor.startswith("@"):
        t = ctx.frase(valor[1:])
        return defecto if t is None else max(0.0, t)
    return float(valor)


def modulo(tipo):
    import importlib

    return importlib.import_module(f".{tipo}", __name__)
