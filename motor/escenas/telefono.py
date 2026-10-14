"""Capturas reales animadas dentro de un teléfono: cambios de estado con fundido,
toques visibles, resaltados, zoom y estrellas. Las capturas son de 390x844 css a 3x
(como las saca captura.mjs); taps/rings/zoom van en px css.

params:
  estados  [{"t": 0, "img": "capturas/a.png", "fundido": 0.12}, ...]
  toques   [{"t": 1.2 | "@frase", "x": 195, "y": 362}]
  resaltes [{"t0": .., "t1": .., "x": .., "y": .., "w": .., "h": ..}]
  zoom     [{"t": 0, "s": 1.0, "cx": 195, "cy": 422}, ...]
  estrellas {"t0": .., "t1": ..}   5 estrellas genéricas que entran una a una
  paso     {"n": 2, "titulo": "Tu contacto", "lista": [...]}  chip de tutorial arriba (ver _paso.py)
  estados también acepta {"t", "hasta", "imgs": [...]}: tipeo repartido (ver expandir_estados)
  fondo    imagen de fondo (se desenfoca y oscurece); por defecto degradado de la marca
"""
import math

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ..base import FPS, EscritorVideo, cubrir, ease
from . import _paso, expandir_estados, t_de

CSS_W, CSS_H = 390, 844
ORO = (247, 181, 0)


def _interp(claves, t, campos):
    if t <= claves[0]["t"]:
        return [claves[0][c] for c in campos]
    for a, b in zip(claves, claves[1:]):
        if a["t"] <= t <= b["t"]:
            k = ease((t - a["t"]) / (b["t"] - a["t"])) if b["t"] > a["t"] else 1
            return [a[c] + (b[c] - a[c]) * k for c in campos]
    return [claves[-1][c] for c in campos]


def _mascara(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=255)
    return m


def _estrella(cx, cy, r_out, r_in):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _fondo(ctx, ruta):
    w, h = ctx.w, ctx.h
    if ruta and ruta.exists():
        img = cubrir(Image.open(ruta).convert("RGB"), w, h).filter(ImageFilter.GaussianBlur(28 * w / 1080))
        return ImageEnhance.Brightness(img).enhance(0.45)
    a, b = ctx.marca.color("oscuro"), ctx.marca.color("tinta")
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        k = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3)))
    return img


def render(params, ctx, salida):
    w, h, dur = ctx.w, ctx.h, ctx.dur
    estados = expandir_estados(params["estados"], ctx)
    imgs = {e["img"]: Image.open(ctx.ruta(e["img"])).convert("RGB") for e in estados}
    toques = [{**tp, "t": t_de(tp["t"], ctx)} for tp in params.get("toques", [])]
    resaltes = [{**r, "t0": t_de(r["t0"], ctx), "t1": t_de(r["t1"], ctx, dur)} for r in params.get("resaltes", [])]
    zoom = [{**z, "t": t_de(z["t"], ctx)} for z in params.get("zoom") or [{"t": 0, "s": 1.0, "cx": CSS_W / 2, "cy": CSS_H / 2}]]
    zoom.sort(key=lambda z: z["t"])
    estrellas = params.get("estrellas")
    if estrellas:
        estrellas = {"t0": t_de(estrellas["t0"], ctx), "t1": t_de(estrellas.get("t1"), ctx, dur)}

    # Tamaño del teléfono según el formato (vertical, cuadrado u horizontal)
    bezel = round(20 * w / 1080) if h > w else round(20 * h / 1920 * 1.6)
    pantalla_h = min(round(0.685 * w * CSS_H / CSS_W), round(h * 0.86) - 2 * bezel)
    if params.get("paso") and h > w:  # deja aire arriba para el chip del paso
        pantalla_h = min(pantalla_h, round(h * 0.79) - 2 * bezel)
    pantalla_w = round(pantalla_h * CSS_W / CSS_H)
    tel_w, tel_h = pantalla_w + 2 * bezel, pantalla_h + 2 * bezel
    r_tel, r_pan = round(tel_w * 0.133), round(tel_w * 0.11)
    sx0, sy0 = (w - tel_w) // 2, (h - tel_h) // 2 - round(h * 0.01)
    if params.get("paso") and h > w:
        sy0 = (h - tel_h) // 2 + round(h * 0.03)

    base = _fondo(ctx, ctx.ruta(params.get("fondo")))
    sombra = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sombra).rounded_rectangle([sx0 + 8, sy0 + 36, sx0 + tel_w + 8, sy0 + tel_h + 36], r_tel, fill=170)
    base.paste((0, 0, 0), (0, 0), sombra.filter(ImageFilter.GaussianBlur(40)))
    m_pan, m_tel = _mascara((pantalla_w, pantalla_h), r_pan), _mascara((tel_w, tel_h), r_tel)
    esc = pantalla_w / 740  # escala de los adornos respecto al diseño original

    with EscritorVideo(salida, w, h) as ev:
        for f in range(round(dur * FPS)):
            t = f / FPS
            s, cx, cy = _interp(zoom, t, ["s", "cx", "cy"])
            cw, ch = CSS_W / s, CSS_H / s
            x0 = min(max(cx - cw / 2, 0), CSS_W - cw)
            y0 = min(max(cy - ch / 2, 0), CSS_H - ch)

            def pintar(img):
                k = img.width / CSS_W
                return img.resize((pantalla_w, pantalla_h), Image.LANCZOS, box=(x0 * k, y0 * k, (x0 + cw) * k, (y0 + ch) * k))

            cur = max((i for i, e in enumerate(estados) if e["t"] <= t), default=0)
            pantalla = pintar(imgs[estados[cur]["img"]])
            fund = estados[cur].get("fundido", 0)
            if cur > 0 and fund and t - estados[cur]["t"] < fund:
                pantalla = Image.blend(pintar(imgs[estados[cur - 1]["img"]]), pantalla, (t - estados[cur]["t"]) / fund)

            def a_pantalla(px, py):
                return (px - x0) / cw * pantalla_w, (py - y0) / ch * pantalla_h

            ov = Image.new("RGBA", (pantalla_w, pantalla_h), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            prim = ctx.marca.color("primario")
            for r in resaltes:
                if r["t0"] <= t < r["t1"]:
                    a = min(1.0, (t - r["t0"]) / 0.2)
                    (ax, ay), (bx, by) = a_pantalla(r["x"], r["y"]), a_pantalla(r["x"] + r["w"], r["y"] + r["h"])
                    pad = (14 + 6 * math.sin((t - r["t0"]) * 6)) * esc
                    d.rounded_rectangle([ax - pad, ay - pad, bx + pad, by + pad], 18 * esc, outline=prim + (int(255 * a),), width=max(2, round(7 * esc)))
            for tp in toques:
                edad = t - tp["t"]
                if 0 <= edad <= 0.6:
                    px, py = a_pantalla(tp["x"], tp["y"])
                    k = edad / 0.6
                    rad = (30 + 70 * k) * esc
                    d.ellipse([px - rad, py - rad, px + rad, py + rad], outline=prim + (int(230 * (1 - k)),), width=max(2, round(7 * esc)))
                    if edad < 0.25:
                        d.ellipse([px - 34 * esc, py - 34 * esc, px + 34 * esc, py + 34 * esc], fill=(255, 255, 255, int(170 * (1 - edad / 0.25))))
            pantalla = Image.alpha_composite(pantalla.convert("RGBA"), ov).convert("RGB")

            if estrellas and estrellas["t0"] <= t < estrellas["t1"]:
                k = min(1.0, (t - estrellas["t0"]) / 0.2, (estrellas["t1"] - t) / 0.2)
                capa = Image.new("RGBA", pantalla.size, (0, 0, 0, int(110 * k)))
                dd = ImageDraw.Draw(capa)
                pw, ph = pantalla_w * 0.86, 230 * esc
                px, py = (pantalla_w - pw) / 2, pantalla_h * 0.42
                dd.rounded_rectangle([px, py, px + pw, py + ph], 36 * esc, fill=(255, 255, 255, int(250 * k)))
                for i in range(5):
                    edad = t - (estrellas["t0"] + 0.15 + i * 0.12)
                    if edad < 0:
                        continue
                    sc = min(1.0, edad / 0.18)
                    sc *= 1 + 0.25 * math.sin(math.pi * sc)
                    ccx, ccy = px + pw / 5 * (i + 0.5), py + ph / 2
                    dd.polygon(_estrella(ccx, ccy, 52 * esc * sc, 22 * esc * sc), fill=ORO + (int(255 * k),))
                pantalla = Image.alpha_composite(pantalla.convert("RGBA"), capa).convert("RGB")

            tel = Image.new("RGB", (tel_w, tel_h), (14, 14, 14))
            tel.paste(pantalla, (bezel, bezel), m_pan)
            ImageDraw.Draw(tel).rounded_rectangle(
                [tel_w / 2 - 92 * esc, bezel + 20 * esc, tel_w / 2 + 92 * esc, bezel + 72 * esc], 26 * esc, fill=(0, 0, 0)
            )
            frame = base.copy()
            frame.paste(tel, (sx0, sy0), m_tel)
            if params.get("paso") and h > w:
                _paso.chip(frame, params["paso"], ctx, max(16, sy0 - 108 * w / 1080), min(1.0, t / 0.3))
            sc = 1.0 + 0.04 * ease(t / dur)  # respiración de cámara
            zw, zh = w / sc, h / sc
            ev.escribir(frame.resize((w, h), Image.BILINEAR, box=((w - zw) / 2, (h - zh) / 2, (w + zw) / 2, (h + zh) / 2)))

    eventos = [{"sfx": "tap", "t": tp["t"]} for tp in toques]
    if estrellas:
        eventos += [{"sfx": "tap", "t": estrellas["t0"] + 0.15 + i * 0.12, "vol": 0.35} for i in range(5)]
        eventos.append({"sfx": "chime", "t": estrellas["t0"] + 0.75, "vol": 0.5})
    return eventos
