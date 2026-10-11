"""Oferta: foto del producto, precio de antes tachado, precio nuevo y descuento.

params:
  foto       foto del producto o servicio
  producto   "Corte + barba"
  antes      "$40.000"
  ahora      "$30.000"
  descuento  "-25%" (opcional)
  urgencia   "Solo este fin de semana" (opcional)
  fondo      imagen de fondo (por defecto la misma foto, desenfocada)
"""
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ..base import FPS, EscritorVideo, cubrir, ease, ease_out, fuente


def _centrado(d, w, y, texto, f, **kw):
    b = d.textbbox((0, 0), texto, font=f)
    x = (w - (b[2] - b[0])) / 2 - b[0]
    d.text((x, y), texto, font=f, **kw)
    return x + b[0], y + b[1], x + b[2], y + b[3]


def render(params, ctx, salida):
    w, h = ctx.w, ctx.h
    s = min(w / 1080, h / 1080 * 0.85)
    foto = Image.open(ctx.ruta(params["foto"])).convert("RGB")
    ruta_fondo = ctx.ruta(params.get("fondo")) or ctx.ruta(params["foto"])
    fondo = cubrir(Image.open(ruta_fondo).convert("RGB"), w, h).filter(ImageFilter.GaussianBlur(30 * s))
    fondo = ImageEnhance.Brightness(fondo).enhance(0.35)
    prim, acento = ctx.marca.color("primario"), ctx.marca.color("acento")

    # Tarjeta de la foto (fija), con sombra
    vertical = h > w
    fw = int(w * (0.72 if vertical else 0.4))
    fh = int(fw * 0.62) if vertical else int(h * 0.62)
    fx = (w - fw) // 2 if vertical else int(w * 0.06)
    fy = int(h * 0.13) if vertical else int(h * 0.16)
    marco = cubrir(foto, fw, fh)
    mascara = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, fw - 1, fh - 1], int(36 * s), fill=255)
    sombra = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sombra).rounded_rectangle([fx + 10, fy + 30, fx + fw + 10, fy + fh + 30], int(36 * s), fill=160)
    fondo.paste((0, 0, 0), (0, 0), sombra.filter(ImageFilter.GaussianBlur(30 * s)))

    f_prod = fuente("din", 88 * s)
    f_antes = fuente("din", 96 * s)
    f_ahora = fuente("din", 220 * s)
    f_desc = fuente("din", 92 * s)
    f_urg = fuente("avenir-bold", 44 * s)
    cx_txt = w / 2 if vertical else w * 0.68
    y_txt = fy + fh + 40 * s if vertical else h * 0.18

    with EscritorVideo(salida, w, h) as ev:
        for fr in range(round(ctx.dur * FPS)):
            t = fr / FPS
            img = fondo.copy().convert("RGBA")
            k = ease_out(t / 0.45)
            z = 1.0 + 0.06 * ease(t / ctx.dur)
            cuadro = cubrir(foto, fw, fh, zoom=z)
            dy = int((1 - k) * 80 * s)
            img.paste(cuadro, (fx, fy + dy), mascara)

            capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(capa)
            ancho_txt = w if vertical else w * 0.48
            off = 0 if vertical else w * 0.5

            def centrado(y, texto, f, **kw):
                b = d.textbbox((0, 0), texto, font=f)
                x = off + (ancho_txt - (b[2] - b[0])) / 2 - b[0]
                d.text((x, y), texto, font=f, **kw)
                return x + b[0], y + b[1], x + b[2], y + b[3]

            y = y_txt
            if params.get("producto") and t > 0.2:
                a = int(255 * ease_out((t - 0.2) / 0.3))
                caja = centrado(y, params["producto"].upper(), f_prod, fill=(255, 255, 255, a))
                y = caja[3] + 30 * s
            else:
                y += 126 * s
            if params.get("antes") and t > 0.45:
                a = int(255 * ease_out((t - 0.45) / 0.3))
                caja = centrado(y, params["antes"], f_antes, fill=(220, 220, 220, a))
                kt = ease((t - 0.8) / 0.3)
                if kt > 0:  # línea que tacha
                    ym = (caja[1] + caja[3]) / 2
                    d.line([(caja[0] - 10 * s, ym), (caja[0] - 10 * s + (caja[2] - caja[0] + 20 * s) * kt, ym)],
                           fill=(230, 60, 50, 255), width=int(10 * s))
                y = caja[3] + 30 * s
            if params.get("ahora") and t > 1.05:
                k2 = ease_out((t - 1.05) / 0.3)
                tam = 180 * s * (0.6 + 0.4 * k2 + 0.08 * (1 - abs(1 - 2 * min(1, (t - 1.05) / 0.5))))
                f = fuente("din", tam)
                b = d.textbbox((0, 0), params["ahora"], font=f)
                bw, bh = b[2] - b[0], b[3] - b[1]
                x = off + (ancho_txt - bw) / 2
                pad = 26 * s
                d.rounded_rectangle([x - pad, y - pad * 0.6, x + bw + pad, y + bh + pad * 1.4], 26 * s, fill=prim + (int(255 * k2),))
                d.text((x - b[0], y - b[1] + pad * 0.3), params["ahora"], font=f, fill=(255, 255, 255, int(255 * k2)))
                y += bh + 70 * s
            if params.get("descuento") and t > 1.4:
                k3 = ease_out((t - 1.4) / 0.3)
                r = 120 * s * k3
                cxd, cyd = fx + fw - 30 * s, fy + 30 * s + dy
                d.ellipse([cxd - r, cyd - r, cxd + r, cyd + r], fill=acento + (255,))
                if k3 > 0.6:
                    b = d.textbbox((0, 0), params["descuento"], font=f_desc)
                    d.text((cxd - (b[2] - b[0]) / 2 - b[0], cyd - (b[3] - b[1]) / 2 - b[1]), params["descuento"], font=f_desc, fill=(20, 20, 20))
            if params.get("urgencia") and t > 1.9:
                a = int(255 * ease_out((t - 1.9) / 0.3))
                centrado(y, params["urgencia"].upper(), f_urg, fill=acento + (a,))
            img.alpha_composite(capa)
            ev.escribir(img)
    return [{"sfx": "whoosh", "t": 0.8, "vol": 0.3}, {"sfx": "chime", "t": 1.1, "vol": 0.55}]
