"""Plano 3D de producto renderizado con Blender (gratis, fiel al diseño).

params:
  modo        "tarjeta_gira" (por defecto) | "tarjeta_mesa" | "logo_flota"
  textura     diseño plano de la tarjeta (por defecto la "tarjeta" de la marca)
  color_canto [r, g, b] 0-255 del canto/reverso (por defecto el color del borde del diseño)
  fondo       imagen de fondo para los modos con transparencia; por defecto degradado de la marca
  calidad     0.5-1.0 escala del render (0.75); el resto se reescala
  muestras    muestras de EEVEE (24)
"""
import json
import shutil

from PIL import Image

from ..base import BLENDER, FPS, RAIZ, EscritorVideo, run
from .texto import _fondo


def _color_borde(ruta):
    img = Image.open(ruta).convert("RGBA")
    w, h = img.size
    px = img.getpixel((w // 2, int(h * 0.03)))  # franja superior, dentro de la tarjeta
    return [c / 255 for c in px[:3]]


def render(params, ctx, salida):
    modo = params.get("modo", "tarjeta_gira")
    textura = ctx.ruta(params["textura"]) if params.get("textura") else ctx.marca.tarjeta
    logo = ctx.marca.ruta(ctx.marca.datos.get("logo"))
    if modo.startswith("tarjeta") and not (textura and textura.exists()):
        raise ValueError("producto_3d: la marca no tiene diseño de tarjeta (campo \"tarjeta\" en marca.json)")
    calidad = float(params.get("calidad", 0.75))
    rw, rh = int(ctx.w * calidad) // 2 * 2, int(ctx.h * calidad) // 2 * 2
    frames = round(ctx.dur * FPS)
    carpeta = ctx.trabajo / f"blender-{salida.stem}"
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    canto = params.get("color_canto")
    canto = [c / 255 for c in canto] if canto else (_color_borde(textura) if textura else [0.08, 0.08, 0.09])
    cfg = {
        "modo": modo,
        "textura": str(textura) if textura else None,
        "logo": str(logo) if logo else None,
        "color_canto": canto,
        "w": rw,
        "h": rh,
        "frames": frames,
        "fps": FPS,
        "muestras": params.get("muestras", 24),
        "salida": str(carpeta) + "/",
    }
    run([BLENDER, "-b", "--factory-startup", "-P", str(RAIZ / "motor" / "blender" / "escena.py"), "--", json.dumps(cfg)],
        timeout=1800)
    fondo = None if modo == "tarjeta_mesa" else _fondo(ctx, params).convert("RGBA")
    with EscritorVideo(salida, ctx.w, ctx.h) as ev:
        for i in range(1, frames + 1):
            cuadro = Image.open(carpeta / f"f{i:04d}.png").convert("RGBA").resize((ctx.w, ctx.h), Image.LANCZOS)
            if fondo is not None:
                img = fondo.copy()
                img.alpha_composite(cuadro)
                cuadro = img
            ev.escribir(cuadro)
    shutil.rmtree(carpeta, ignore_errors=True)
    return [{"sfx": "whoosh", "t": 0.1, "vol": 0.25}]
