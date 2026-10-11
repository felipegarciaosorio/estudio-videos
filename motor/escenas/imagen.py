"""Foto con movimiento suave (zoom y paneo con easing).

params:
  archivo   ruta de la imagen (proyecto o "marca:fotos/x.jpg")
  zoom      [inicio, fin], p. ej. [1.0, 1.08]
  foco      [x, y] fracción 0-1 del punto que se mantiene al centro al inicio
  foco_fin  [x, y] al final (paneo); por defecto = foco
  oscurecer 0-1 (velo negro, útil si va texto encima)
  rotulo    {"titulo": "Bowl del huerto", "precio": "$26.000", "detalle": "Pollo, aguacate..."}
            nombre y precio que entran animados en la parte de arriba
"""
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ..base import FPS, EscritorVideo, cubrir, ease, ease_out, fuente


def _rotulo(r, ctx):
    """Capa fija con nombre (y precio en caja de la marca)."""
    w, h, s = ctx.w, ctx.h, ctx.w / 1080 if ctx.h > ctx.w else ctx.h / 1920 * 1.4
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    y = h * (0.15 if h > w else 0.1)
    f_t, f_p, f_d = fuente("din", 120 * s), fuente("din", 150 * s), fuente("avenir-medium", 42 * s)
    sombra = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sombra)

    def centrado(texto, f, y, **kw):
        b = d.textbbox((0, 0), texto, font=f)
        x = (w - (b[2] - b[0])) / 2 - b[0]
        ds.text((x, y + 6 * s), texto, font=f, fill=(0, 0, 0, 180))
        d.text((x, y), texto, font=f, **kw)
        return b, x

    b, _ = centrado(r["titulo"].upper(), f_t, y, fill=(255, 255, 255))
    y += b[3] + 24 * s
    if r.get("precio"):
        bp = d.textbbox((0, 0), r["precio"], font=f_p)
        pw, ph = bp[2] - bp[0], bp[3] - bp[1]
        x = (w - pw) / 2
        pad = 24 * s
        d.rounded_rectangle([x - pad, y - pad * 0.5, x + pw + pad, y + ph + pad * 1.2], 22 * s, fill=ctx.marca.color("primario") + (255,))
        d.text((x - bp[0], y - bp[1] + pad * 0.3), r["precio"], font=f_p, fill=(255, 255, 255))
        y += ph + 70 * s
    if r.get("detalle"):
        centrado(r["detalle"], f_d, y, fill=(240, 240, 240))
    capa = Image.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(8 * s)), capa)
    return capa


def render(params, ctx, salida):
    img = Image.open(ctx.ruta(params["archivo"])).convert("RGB")
    z0, z1 = params.get("zoom", [1.0, 1.08])
    f0 = params.get("foco", [0.5, 0.5])
    f1 = params.get("foco_fin", f0)
    velo = params.get("oscurecer", 0.25 if params.get("rotulo") else 0)
    rotulo = _rotulo(params["rotulo"], ctx) if params.get("rotulo") else None
    n = round(ctx.dur * FPS)
    with EscritorVideo(salida, ctx.w, ctx.h) as ev:
        for i in range(n):
            k = ease(i / max(1, n - 1))
            foco = (f0[0] + (f1[0] - f0[0]) * k, f0[1] + (f1[1] - f0[1]) * k)
            frame = cubrir(img, ctx.w, ctx.h, foco, z0 + (z1 - z0) * k)
            if velo:
                frame = ImageEnhance.Brightness(frame).enhance(1 - velo)
            if rotulo:
                kr = ease_out((i / FPS - 0.15) / 0.35)
                if kr > 0:
                    capa = rotulo
                    if kr < 1:
                        capa = rotulo.copy()
                        capa.putalpha(capa.getchannel("A").point(lambda a: int(a * kr)))
                        capa = capa.transform(capa.size, Image.AFFINE, (1, 0, 0, 0, 1, int(50 * (1 - kr))))
                    frame = Image.alpha_composite(frame.convert("RGBA"), capa)
            ev.escribir(frame)
    return [{"sfx": "whoosh", "t": 0.1, "vol": 0.2}] if rotulo else []
