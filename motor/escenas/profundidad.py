"""Una foto con profundidad real: mapa de profundidad + paralaje (gratis).

La cámara avanza o se desplaza y lo cercano se mueve más que lo lejano. Sirve para
dar vida a una foto de un espacio, un plato o un paisaje sin gastar créditos de IA.

params:
  archivo      foto (proyecto o "marca:fotos/x.jpg")
  foco         [x, y] hacia dónde entra la cámara (0.5, 0.5)
  trayectoria  "avanzar" (defecto) | "derecha" | "izquierda" | "subir" | "orbita"
  intensidad   1.0 normal, 0.5 sutil, 1.5 fuerte
  rotulo       {"titulo", "precio", "detalle"} como en "imagen"
"""
from PIL import Image

from ..base import FPS, EscritorVideo
from ..profundidad import Paralaje, mapa
from .clip_ia import con_rotulo


def render(params, ctx, salida):
    ruta = ctx.ruta(params["archivo"])
    par = Paralaje(Image.open(ruta).convert("RGB"), mapa(ruta), ctx.w, ctx.h, tuple(params.get("foco") or (0.5, 0.5)),
                   params.get("trayectoria", "avanzar"), params.get("intensidad", 1.0))
    n = round(ctx.dur * FPS)

    def dibujar(destino):
        with EscritorVideo(destino, ctx.w, ctx.h) as ev:
            for i in range(n):
                ev.escribir(Image.fromarray(par.frame(i / max(1, n - 1))))
        return []

    return con_rotulo(params, ctx, salida, dibujar)
