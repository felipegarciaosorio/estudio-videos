"""Clip de video hecho con IA (Higgsfield: Kling, Seedance...).

params:
  prompt         qué pasa en el clip (inglés, una acción + un movimiento de cámara)
  imagen         foto de inicio (proyecto o "marca:fotos/x.jpg"); da fidelidad al producto
  imagen_prompt  opcional: generar primero un keyframe con IA (usa "imagen"/"referencias" como referencia)
  referencias    fotos de referencia para el keyframe
  modelo         id del catálogo (ia/catalogo.json → video), p. ej. "kling_pro"
  modelo_imagen  id del catálogo para el keyframe, p. ej. "gpt_alta"
  duracion_clip  5 o 10 s
  desde          segundo del clip donde empieza (0)
  foco           [x, y] para el recorte a formato
  rotulo         {"titulo", "precio", "detalle"} como en "imagen" (nombre y precio encima del clip)

Mientras el clip no exista (pedido IA pendiente) se dibuja un BORRADOR gratis:
la foto de inicio (o el keyframe, o el fondo de la marca) con zoom y el aviso
"IA pendiente", para poder revisar ritmo y textos antes de pagar."""
from pathlib import Path

from PIL import Image, ImageDraw

from .. import ia
from ..base import FFMPEG, FPS, EscritorVideo, cubrir, duracion, ease, fuente, run


def _formato(ctx):
    return ia.FORMATO_DE.get((ctx.w, ctx.h), "9:16")


def con_rotulo(params, ctx, salida, render_base):
    """Renderiza la escena y le pone encima el rótulo (nombre/precio) que entra animado."""
    if not params.get("rotulo"):
        return render_base(salida)
    from .imagen import _rotulo

    base = salida.with_name(salida.stem + "-base.mp4")
    eventos = render_base(base)
    png = salida.with_name(salida.stem + "-rotulo.png")
    _rotulo(params["rotulo"], ctx).save(png)
    run([FFMPEG, "-loglevel", "error", "-y", "-i", str(base), "-loop", "1", "-i", str(png), "-filter_complex",
         f"[0:v]eq=brightness=-0.06[b];[1:v]format=rgba,fade=in:st=0.15:d=0.35:alpha=1[r];[b][r]overlay=0:0:shortest=1,format=yuv420p",
         "-t", f"{ctx.dur:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", str(salida)])
    base.unlink(missing_ok=True)
    png.unlink(missing_ok=True)
    return eventos + [{"sfx": "whoosh", "t": 0.1, "vol": 0.2}]


def borrador(ctx, salida, foto, etiqueta, texto=""):
    from .texto import _fondo

    base = Image.open(foto).convert("RGB") if foto and Path(foto).exists() else _fondo(ctx, {})
    s = min(ctx.w, ctx.h) / 1080
    capa = Image.new("RGBA", (ctx.w, ctx.h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f, fp = fuente("avenir-bold", 34 * s), fuente("avenir-medium", 30 * s)
    rot = f"IA PENDIENTE · {etiqueta}"
    b = d.textbbox((0, 0), rot, font=f)
    x, y, pad = 40 * s, ctx.h * (0.56 if ctx.h > ctx.w else 0.5), 18 * s
    d.rounded_rectangle([x, y, x + b[2] - b[0] + 2 * pad, y + b[3] - b[1] + 2 * pad], 14 * s, fill=(20, 20, 20, 200))
    d.text((x + pad - b[0], y + pad - b[1]), rot, font=f, fill=(255, 214, 102))
    if texto:
        lineas, linea = [], ""
        for palabra in texto.split():
            if d.textlength(linea + " " + palabra, font=fp) > ctx.w - 120 * s:
                lineas.append(linea)
                linea = palabra
            else:
                linea = (linea + " " + palabra).strip()
        lineas.append(linea)
        ty = y + b[3] - b[1] + 2 * pad + 16 * s
        for l in lineas[:4]:
            d.text((x + 4 * s, ty), l, font=fp, fill=(255, 255, 255, 230), stroke_width=int(3 * s), stroke_fill=(0, 0, 0))
            ty += 40 * s
    n = round(ctx.dur * FPS)
    with EscritorVideo(salida, ctx.w, ctx.h) as ev:
        for i in range(n):
            frame = cubrir(base, ctx.w, ctx.h, (0.5, 0.5), 1.0 + 0.12 * ease(i / max(1, n - 1))).convert("RGBA")
            ev.escribir(Image.alpha_composite(frame, capa))
    return []


def render(params, ctx, salida):
    return con_rotulo(params, ctx, salida, lambda destino: _render(params, ctx, destino))


def _render(params, ctx, salida):
    from . import video

    lista = ia.tareas_clip(params, _formato(ctx), ctx.proyecto, ctx.marca.dir)
    clip = ia.resultado(ctx.proyecto, lista[-1]["destino"])
    if clip:
        total = duracion(clip)
        desde = float(params.get("desde", 0))
        tramo = total - desde
        # si el clip es más corto que la escena, se ralentiza (cámara lenta) en vez de congelarse
        vel = min(1.0, tramo / ctx.dur)
        return video.render({"archivo": str(clip), "desde": desde, "velocidad": vel, "foco": params.get("foco", [0.5, 0.5])},
                            ctx, salida)
    foto = None
    if params.get("imagen_prompt"):
        foto = ia.resultado(ctx.proyecto, lista[0]["destino"])
    foto = foto or ctx.ruta(params.get("imagen"))
    return borrador(ctx, salida, foto, lista[-1]["nombre"], params.get("prompt", ""))
