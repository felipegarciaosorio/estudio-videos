"""Tipografía animada a pantalla completa (títulos, listas, cifras).

params:
  lineas     ["¿TU CARTA", "SIGUE EN PAPEL?"]
  resaltar   ["PAPEL?"] palabras que van en caja del color de la marca
  estilo     "titulo" (por defecto) | "lista" (aparecen una a una) | "cifra" (número gigante)
  tiempos    para "lista": [0.2, 1.0, "@frase", ...] cuándo entra cada línea
  subtexto   línea pequeña debajo
  fondo      imagen (se oscurece y desenfoca) o null = degradado de la marca
  fuente     "din" (por defecto), "avenir-heavy", "didot", ...
  posicion   0-1, centro vertical del bloque (0.42)
"""
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ..base import FPS, EscritorVideo, cubrir, ease, ease_out, fuente
from . import t_de


def _fondo(ctx, params):
    w, h = ctx.w, ctx.h
    ruta = ctx.ruta(params.get("fondo"))
    if ruta and ruta.exists():
        img = cubrir(Image.open(ruta).convert("RGB"), w, h).filter(ImageFilter.GaussianBlur(14 * w / 1080))
        return ImageEnhance.Brightness(img).enhance(0.38)
    a, b = ctx.marca.color("oscuro"), ctx.marca.color("tinta")
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)))
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse([w * 0.1, h * 0.25, w * 0.9, h * 0.65], fill=90)
    img.paste(ctx.marca.color("primario"), (0, 0), glow.filter(ImageFilter.GaussianBlur(120 * w / 1080)))
    return img


def render(params, ctx, salida):
    w, h, s = ctx.w, ctx.h, ctx.w / 1080
    estilo = params.get("estilo", "titulo")
    lineas = params["lineas"]
    resaltar = {x.upper() for x in params.get("resaltar", [])}
    tam = {"titulo": 150, "lista": 96, "cifra": 330}[estilo] * s
    f = fuente(params.get("fuente", "din"), tam)
    fsub = fuente("avenir-medium", 46 * s)
    prim = ctx.marca.color("primario")
    if estilo == "lista":
        tiempos = [t_de(x, ctx) for x in params.get("tiempos", [])] or [0.15 + 0.5 * i for i in range(len(lineas))]
    else:
        tiempos = [0.1 + 0.12 * i for i in range(len(lineas))]
    base = _fondo(ctx, params)
    medida = ImageDraw.Draw(base)
    alto_linea = (medida.textbbox((0, 0), "ÁGJ", font=f)[3]) * 1.16
    bloque = alto_linea * len(lineas)
    y_ini = h * params.get("posicion", 0.42) - bloque / 2

    with EscritorVideo(salida, w, h) as ev:
        for fr in range(round(ctx.dur * FPS)):
            t = fr / FPS
            img = base.copy()
            if estilo != "lista":  # leve acercamiento del fondo
                k = 1 + 0.05 * ease(t / ctx.dur)
                img = img.resize((w, h), Image.BILINEAR, box=((w - w / k) / 2, (h - h / k) / 2, (w + w / k) / 2, (h + h / k) / 2))
            capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(capa)
            for i, linea in enumerate(lineas):
                k = ease_out((t - tiempos[i]) / 0.35)
                if k <= 0:
                    continue
                y = y_ini + i * alto_linea + (1 - k) * 60 * s
                alpha = int(255 * k)
                palabras = linea.split()
                gap = 24 * s
                cajas = [d.textbbox((0, 0), p, font=f) for p in palabras]
                total = sum(b[2] - b[0] for b in cajas) + gap * (len(palabras) - 1)
                x = (w - total) / 2
                if estilo == "lista":
                    x = w * 0.12
                for p, b in zip(palabras, cajas):
                    an = b[2] - b[0]
                    if p.upper().strip("¿?¡!.,:;") in {x.strip("¿?¡!.,:;") for x in resaltar}:
                        pad = 14 * s
                        d.rounded_rectangle([x - pad, y + b[1] - pad, x + an + pad, y + b[3] + pad], 16 * s, fill=prim + (alpha,))
                        d.text((x - b[0], y), p, font=f, fill=(255, 255, 255, alpha))
                    else:
                        d.text((x - b[0], y), p, font=f, fill=(255, 255, 255, alpha), stroke_width=int(4 * s), stroke_fill=(0, 0, 0, alpha // 2))
                    x += an + gap
            if params.get("subtexto"):
                k = ease_out((t - tiempos[-1] - 0.3) / 0.35)
                if k > 0:
                    sb = d.textbbox((0, 0), params["subtexto"], font=fsub)
                    d.text(((w - (sb[2] - sb[0])) / 2 - sb[0], y_ini + bloque + 40 * s), params["subtexto"], font=fsub,
                           fill=(235, 240, 238, int(255 * k)))
            img = Image.alpha_composite(img.convert("RGBA"), capa)
            ev.escribir(img)
    return [{"sfx": "whoosh", "t": max(0, x - 0.1), "vol": 0.2} for x in tiempos] if estilo == "lista" else []
