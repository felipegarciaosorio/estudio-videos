"""Reseñas de clientes: tarjetas con estrellas que entran una tras otra.

params:
  resenas  [{"nombre": "Laura M.", "texto": "La mejor bandeja...", "estrellas": 5}]
  titulo   "Lo que dicen nuestros clientes" (opcional)
  fondo    foto del lugar (se desenfoca); por defecto degradado de la marca
  tiempos  [0.2, "@frase", ...] cuándo entra cada reseña (por defecto se reparten)
"""
import math

from PIL import Image, ImageDraw, ImageFilter

from ..base import FPS, EscritorVideo, ease_out, fuente
from . import t_de
from .texto import _fondo

ORO = (247, 181, 0)


def _estrella(cx, cy, r_out, r_in):
    return [(cx + (r_out if i % 2 == 0 else r_in) * math.cos(-math.pi / 2 + i * math.pi / 5),
             cy + (r_out if i % 2 == 0 else r_in) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]


def _envolver(d, texto, f, ancho):
    lineas, actual = [], ""
    for p in texto.split():
        prueba = f"{actual} {p}".strip()
        if d.textlength(prueba, font=f) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def _tarjeta(r, ancho, s, prim):
    f_txt = fuente("avenir-medium", 54 * s)
    f_nom = fuente("avenir-bold", 46 * s)
    medida = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lineas = _envolver(medida, f"“{r['texto']}”", f_txt, ancho - 100 * s)[:6]
    alto = int(110 * s + 80 * s + len(lineas) * 72 * s + 100 * s)
    img = Image.new("RGBA", (int(ancho), alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, ancho - 1, alto - 1], int(40 * s), fill=(255, 255, 255, 250))
    for i in range(int(r.get("estrellas", 5))):
        d.polygon(_estrella(74 * s + i * 76 * s, 88 * s, 34 * s, 14 * s), fill=ORO)
    y = 160 * s
    for ln in lineas:
        d.text((50 * s, y), ln, font=f_txt, fill=(30, 30, 30))
        y += 72 * s
    d.text((50 * s, y + 20 * s), f"— {r['nombre']}", font=f_nom, fill=prim)
    return img


def render(params, ctx, salida):
    w, h = ctx.w, ctx.h
    s = w / 1080 if h > w else h / 1920 * 1.4
    resenas = params["resenas"]
    n = len(resenas)
    if params.get("tiempos"):
        tiempos = [t_de(x, ctx) for x in params["tiempos"]]
    else:
        tiempos = [0.15 + i * (ctx.dur - 0.4) / n for i in range(n)]
    base = _fondo(ctx, params).convert("RGBA")
    if params.get("titulo"):
        d = ImageDraw.Draw(base)
        f = fuente("din", 86 * s)
        b = d.textbbox((0, 0), params["titulo"].upper(), font=f)
        d.text(((w - (b[2] - b[0])) / 2 - b[0], h * 0.12), params["titulo"].upper(), font=f, fill=(255, 255, 255))
    ancho = w * (0.88 if h > w else 0.5)
    prim = ctx.marca.color("primario")
    tarjetas = [_tarjeta(r, ancho, s, prim) for r in resenas]
    y_centro = h * 0.42

    with EscritorVideo(salida, w, h) as ev:
        for fr in range(round(ctx.dur * FPS)):
            t = fr / FPS
            img = base.copy()
            actual = max((i for i, t0 in enumerate(tiempos) if t0 <= t), default=-1)
            for i in (actual - 1, actual):
                if i < 0:
                    continue
                tar = tarjetas[i]
                if i == actual:
                    k = ease_out((t - tiempos[i]) / 0.4)
                    x = (w - tar.width) / 2 + (1 - k) * w * 0.6
                    y = y_centro - tar.height / 2
                    alpha = k
                else:  # la anterior se va hacia arriba
                    k = ease_out((t - tiempos[actual]) / 0.4)
                    x = (w - tar.width) / 2
                    y = y_centro - tar.height / 2 - k * h * 0.5
                    alpha = 1 - k
                if alpha <= 0.01:
                    continue
                sombra = Image.new("RGBA", (tar.width + 80, tar.height + 80), (0, 0, 0, 0))
                ImageDraw.Draw(sombra).rounded_rectangle([40, 60, 40 + tar.width, 60 + tar.height], int(40 * s), fill=(0, 0, 0, int(120 * alpha)))
                img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(20)), (int(x - 40), int(y - 40)))
                capa = tar if alpha >= 0.99 else tar.copy()
                if alpha < 0.99:
                    capa.putalpha(capa.getchannel("A").point(lambda a: int(a * alpha)))
                img.alpha_composite(capa, (int(x), int(y)))
            ev.escribir(img)
    return [{"sfx": "whoosh", "t": t0, "vol": 0.3} for t0 in tiempos] + [{"sfx": "chime", "t": tiempos[0] + 0.3, "vol": 0.4}]
