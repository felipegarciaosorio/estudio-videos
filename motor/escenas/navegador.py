"""Capturas reales de escritorio dentro de una ventana de navegador (tutoriales
de una web en 16:9). Mismo contrato que telefono, en px css de la captura.

params:
  estados  [{"t": 0, "img": "capturas/a.png", "fundido": 0.12}, ...]
           o {"t": "@frase", "hasta": "@otra", "imgs": [...]} (tipeo repartido)
  toques   [{"t": 1.2 | "@frase", "x": 800, "y": 300}]
  resaltes [{"t0": .., "t1": .., "x": .., "y": .., "w": .., "h": ..}]
  zoom     [{"t": 0, "s": 1.0, "cx": 800, "cy": 450}, ...]   s > 1 acerca hacia (cx, cy)
  css      [1600, 900]   tamaño css de las capturas
  url      texto de la barra de direcciones ("aurelasoluciones.com/nfc")
  paso     {"n": 2, "titulo": "Tu contacto", "lista": [...]}  columna de tutorial (ver _paso.py)
  fondo    imagen de fondo (se desenfoca y oscurece); por defecto degradado de la marca
"""
from PIL import Image, ImageDraw, ImageFilter

from ..base import FPS, EscritorVideo, ease, fuente
from . import _paso, expandir_estados, t_de
from .telefono import _fondo, _interp, _mascara


def render(params, ctx, salida):
    w, h, dur = ctx.w, ctx.h, ctx.dur
    css_w, css_h = params.get("css", [1600, 900])
    estados = expandir_estados(params["estados"], ctx)
    imgs = {e["img"]: Image.open(ctx.ruta(e["img"])).convert("RGB") for e in estados}
    toques = [{**tp, "t": t_de(tp["t"], ctx)} for tp in params.get("toques", [])]
    resaltes = [{**r, "t0": t_de(r["t0"], ctx), "t1": t_de(r["t1"], ctx, dur)} for r in params.get("resaltes", [])]
    zoom = [{**z, "t": t_de(z["t"], ctx)} for z in params.get("zoom") or [{"t": 0, "s": 1.0, "cx": css_w / 2, "cy": css_h / 2}]]
    zoom.sort(key=lambda z: z["t"])
    paso = params.get("paso")

    # Ventana: a la izquierda si hay columna de paso, centrada si no.
    # Abajo queda una franja libre para los subtítulos.
    s = h / 1080
    barra = round(46 * s)
    alto_max = round(h * 0.80) - barra
    if paso:
        pan_w = min(round(w * 0.755), round(alto_max * css_w / css_h))
        vx = round(48 * s)
    else:
        pan_w = min(round(w * 0.86), round(alto_max * css_w / css_h))
        vx = (w - pan_w) // 2
    pan_h = round(pan_w * css_h / css_w)
    vy = round(40 * s)
    ven_w, ven_h = pan_w, pan_h + barra
    radio = round(18 * s)

    base = _fondo(ctx, ctx.ruta(params.get("fondo")))
    sombra = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sombra).rounded_rectangle([vx + 6, vy + 28, vx + ven_w + 6, vy + ven_h + 28], radio, fill=160)
    base.paste((0, 0, 0), (0, 0), sombra.filter(ImageFilter.GaussianBlur(36 * s)))
    m_ven = _mascara((ven_w, ven_h), radio)

    # Barra del navegador (fija): tres puntos + caja de dirección.
    cromo = Image.new("RGB", (ven_w, barra), (236, 238, 240))
    dc = ImageDraw.Draw(cromo)
    for i, col in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        cx = round(26 * s + i * 22 * s)
        dc.ellipse([cx - 6 * s, barra / 2 - 6 * s, cx + 6 * s, barra / 2 + 6 * s], fill=col)
    caja_x0, caja_x1 = round(110 * s), ven_w - round(110 * s)
    dc.rounded_rectangle([caja_x0, barra * 0.2, caja_x1, barra * 0.8], round(barra * 0.3), fill=(255, 255, 255))
    url = params.get("url", "")
    if url:
        dc.text(((caja_x0 + caja_x1) / 2, barra / 2), url, font=fuente("avenir-medium", 19 * s), fill=(90, 96, 104), anchor="mm")

    prim = ctx.marca.color("primario")
    esc = pan_w / css_w  # px de video por px css a zoom 1

    with EscritorVideo(salida, w, h) as ev:
        for f in range(round(dur * FPS)):
            t = f / FPS
            z, cx, cy = _interp(zoom, t, ["s", "cx", "cy"])
            cw, ch = css_w / z, css_h / z
            x0 = min(max(cx - cw / 2, 0), css_w - cw)
            y0 = min(max(cy - ch / 2, 0), css_h - ch)

            def pintar(img):
                k = img.width / css_w
                return img.resize((pan_w, pan_h), Image.LANCZOS, box=(x0 * k, y0 * k, (x0 + cw) * k, (y0 + ch) * k))

            cur = max((i for i, e in enumerate(estados) if e["t"] <= t), default=0)
            pantalla = pintar(imgs[estados[cur]["img"]])
            fund = estados[cur].get("fundido", 0)
            if cur > 0 and fund and t - estados[cur]["t"] < fund:
                pantalla = Image.blend(pintar(imgs[estados[cur - 1]["img"]]), pantalla, (t - estados[cur]["t"]) / fund)

            def a_pantalla(px, py):
                return (px - x0) / cw * pan_w, (py - y0) / ch * pan_h

            ov = Image.new("RGBA", (pan_w, pan_h), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            k_z = esc * z
            for r in resaltes:
                if r["t0"] <= t < r["t1"]:
                    a = min(1.0, (t - r["t0"]) / 0.2, (r["t1"] - t) / 0.2)
                    (ax, ay), (bx, by) = a_pantalla(r["x"], r["y"]), a_pantalla(r["x"] + r["w"], r["y"] + r["h"])
                    pad = 8 * k_z
                    d.rounded_rectangle([ax - pad, ay - pad, bx + pad, by + pad], 12 * k_z, outline=prim + (int(255 * a),),
                                        width=max(3, round(4 * k_z)))
            for tp in toques:
                edad = t - tp["t"]
                if -0.35 <= edad <= 0.6:
                    px, py = a_pantalla(tp["x"], tp["y"])
                    # cursor que llega y hace clic
                    llegada = ease(min(1.0, (edad + 0.35) / 0.35))
                    cx_, cy_ = px + (1 - llegada) * 60 * s, py + (1 - llegada) * 40 * s
                    if edad >= 0:
                        k = edad / 0.6
                        rad = (14 + 34 * k) * k_z
                        d.ellipse([px - rad, py - rad, px + rad, py + rad], outline=prim + (int(230 * (1 - k)),), width=max(3, round(4 * k_z)))
                    cur_s = 1.4 * s
                    flecha = [(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 18), (21, 18)]
                    pts = [(cx_ + x * cur_s, cy_ + y * cur_s) for x, y in flecha]
                    d.polygon(pts, fill=(20, 20, 20, 255), outline=(255, 255, 255, 255), width=max(1, round(2 * s)))
            pantalla = Image.alpha_composite(pantalla.convert("RGBA"), ov).convert("RGB")

            ven = Image.new("RGB", (ven_w, ven_h), (255, 255, 255))
            ven.paste(cromo, (0, 0))
            ven.paste(pantalla, (0, barra))
            frame = base.copy()
            frame.paste(ven, (vx, vy), m_ven)
            if paso:
                _paso.columna(frame, paso, ctx, vx + ven_w + round(48 * s), w - round(40 * s), vy, vy + ven_h, min(1.0, t / 0.3))
            ev.escribir(frame)

    return [{"sfx": "tap", "t": tp["t"]} for tp in toques]
