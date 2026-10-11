"""Cierre de marca: logo, nombre, subtítulo, precio y contacto.

params (todo opcional; por defecto sale de marca.json -> "cierre"):
  subtitulo, precio, url, whatsapp, mostrar_nombre (true)
"""
from PIL import Image, ImageDraw, ImageFilter

from ..base import FPS, EscritorVideo, ease_out, fuente


def _centrado(d, w, y, texto, f, fill):
    b = d.textbbox((0, 0), texto, font=f)
    d.text(((w - (b[2] - b[0])) / 2 - b[0], y), texto, font=f, fill=fill)
    return b[3] - b[1]


def render(params, ctx, salida):
    w, h, s = ctx.w, ctx.h, min(ctx.w, ctx.h * 0.5625) / 1080 if ctx.w > ctx.h else ctx.w / 1080
    m = ctx.marca
    cfg = {**m.cierre, **params}
    oscuro, tinta, prim = m.color("oscuro"), m.color("tinta"), m.color("primario")
    acento = m.color("acento")

    fondo = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(fondo)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(oscuro[i] + (tinta[i] - oscuro[i]) * k) for i in range(3)) + (255,))
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse([w / 2 - 420 * s, h * 0.24, w / 2 + 420 * s, h * 0.24 + 720 * s], fill=120)
    fondo.paste(prim + (255,), (0, 0), glow.filter(ImageFilter.GaussianBlur(140 * s)))

    contenido = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(contenido)
    y = h * (0.26 if h > w else 0.12)
    if m.logo:
        alto = int(340 * s)
        ancho = int(m.logo.width * alto / m.logo.height)
        if ancho > w * 0.8:
            ancho, alto = int(w * 0.8), int(m.logo.height * w * 0.8 / m.logo.width)
        contenido.alpha_composite(m.logo.resize((ancho, alto), Image.LANCZOS), ((w - ancho) // 2, int(y)))
        y += alto + 40 * s
    if cfg.get("mostrar_nombre", True):
        y += _centrado(d, w, y, m.datos.get("nombre_corto", m.nombre), fuente(m.fuente_titulos, 120 * s), (255, 255, 255)) + 50 * s
    if cfg.get("subtitulo"):
        y += _centrado(d, w, y, cfg["subtitulo"], fuente("din", 64 * s), acento) + 40 * s
    if cfg.get("precio"):
        _centrado(d, w, y, cfg["precio"], fuente("din", 96 * s), (255, 255, 255))
    contacto = [x for x in (cfg.get("whatsapp"), cfg.get("url")) if x]
    fc = fuente("avenir-medium", 40 * s)
    for i, c in enumerate(contacto):
        _centrado(d, w, h - (170 - 60 * i) * s - (0 if h > w else 20 * s), c, fc, (220, 240, 232))

    with EscritorVideo(salida, w, h) as ev:
        for fr in range(round(ctx.dur * FPS)):
            t = fr / FPS
            k = ease_out(t / 0.4)
            img = fondo.copy()
            capa = contenido
            if k < 1:
                capa = contenido.copy()
                capa.putalpha(capa.getchannel("A").point(lambda a: int(a * k)))
                capa = capa.transform(capa.size, Image.AFFINE, (1, 0, 0, 0, 1, -int(30 * s * (1 - k))))
            img.alpha_composite(capa)
            ev.escribir(img)
    return []
