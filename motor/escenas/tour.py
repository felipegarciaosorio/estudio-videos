"""Tour virtual: recorrido por espacios a partir de FOTOS, con sensación de avanzar.

La cámara entra despacio hacia el punto de interés de cada foto (una puerta, una
ventana, el jacuzzi) y, al cambiar de espacio, "atraviesa" ese punto: la foto se
acerca con desenfoque de movimiento y la siguiente emerge desde atrás. Arriba a la
izquierda va el nombre del espacio y un indicador de recorrido (puntos).

params:
  paradas      lista de espacios, en el orden del recorrido:
                 foto      imagen (proyecto o "marca:fotos/x.jpg")
                 etiqueta  nombre del espacio que se muestra ("TERRAZA")
                 foco      [x, y] hacia dónde entra la cámara (0.5, 0.5 = centro)
                 desde     segundo (en la escena) o "@frase" en que empieza ese espacio;
                           la primera parada empieza en 0
  transicion   duración del cruce entre espacios, en segundos (0.8)
  avance       cuánto se acerca la cámara en cada espacio (0.22 = 22 %)
  indicador    true: nombre del espacio y puntos de recorrido (por defecto)
"""
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from ..base import FPS, EscritorVideo, cubrir, ease, ease_out, fuente
from . import t_de


def _fondo(img, w, h):
    """Versión desenfocada y oscura de la foto: se ve alrededor cuando la foto emerge más chica."""
    chica = cubrir(img, w // 4, h // 4).filter(ImageFilter.GaussianBlur(10))
    return Image.eval(chica.resize((w, h), Image.BILINEAR), lambda v: int(v * 0.55))


def _desenfoque(img_fn, zooms):
    """Promedio de la misma vista a varios zooms: imita el desenfoque radial de moverse rápido."""
    acc = None
    for i, z in enumerate(zooms):
        f = img_fn(z)
        acc = f if acc is None else Image.blend(acc, f, 1 / (i + 1))
    return acc


def _indicador(ctx, s, etiquetas):
    """Una capa RGBA por espacio: etiqueta arriba a la izquierda y puntos de recorrido."""
    w, h = ctx.w, ctx.h
    prim = ctx.marca.color("primario")
    f = fuente("avenir-bold", 62 * s)
    capas = []
    x0, y0 = 48 * s, (290 if h > w else 160) * s
    for i, et in enumerate(etiquetas):
        capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        b = d.textbbox((0, 0), et, font=f)
        tw, th = b[2] - b[0], b[3] - b[1]
        pad = 28 * s
        d.rounded_rectangle([x0, y0, x0 + 52 * s + tw + 2 * pad, y0 + th + 2 * pad], 24 * s, fill=(12, 16, 22, 185))
        d.ellipse([x0 + pad, y0 + pad + th / 2 - 11 * s, x0 + pad + 22 * s, y0 + pad + th / 2 + 11 * s], fill=prim + (255,))
        d.text((x0 + pad + 46 * s - b[0], y0 + pad - b[1]), et, font=f, fill=(255, 255, 255))
        # puntos de recorrido
        yp = y0 + th + 2 * pad + 26 * s
        x = x0 + 4 * s
        for j in range(len(etiquetas)):
            activo = j == i
            ancho = 70 * s if activo else 20 * s
            d.rounded_rectangle([x, yp, x + ancho, yp + 20 * s], 10 * s, fill=prim + (255,) if activo else (255, 255, 255, 120))
            x += ancho + 14 * s
        capas.append(capa)
    return capas


def render(params, ctx, salida):
    w, h = ctx.w, ctx.h
    s = min(w / 1080, h / 1080 * 0.85)
    paradas = params["paradas"]
    n = len(paradas)
    d = float(params.get("transicion", 0.8))
    avance = float(params.get("avance", 0.22))
    imgs = [Image.open(ctx.ruta(p["foto"])).convert("RGB") for p in paradas]
    fondos = [_fondo(im, w, h) for im in imgs]
    focos = [tuple(p.get("foco", (0.5, 0.5))) for p in paradas]
    inicios = [0.0]
    for i, p in enumerate(paradas[1:], 1):
        t = t_de(p.get("desde"), ctx, None)
        inicios.append(t if t is not None else ctx.dur * i / n)
    # a prueba de frases fuera de orden: cada espacio empieza después del anterior
    for i in range(1, n):
        inicios[i] = max(inicios[i], inicios[i - 1] + d * 1.5)
    fines = inicios[1:] + [ctx.dur]
    # el cruce cae un poco antes del instante de la frase: así el nuevo espacio ya se ve cuando lo nombran
    cruce = [None] + [(inicios[i] - d * 0.65, inicios[i] + d * 0.35) for i in range(1, n)]
    etiquetas = [str(p.get("etiqueta", "")).upper() for p in paradas]
    capas = _indicador(ctx, s, etiquetas) if params.get("indicador", True) and any(etiquetas) else None

    def vista(i, t, zoom_extra=1.0, escala=1.0, k_centro=None):
        """Foto i en el instante t: avance suave hacia su foco (+ zoom extra al cruzar)."""
        u = ease(min(1.0, max(0.0, (t - inicios[i]) / max(0.1, fines[i] - inicios[i]))))
        if k_centro is None:
            k_centro = u
        fx, fy = focos[i]
        centro = (0.5 + (fx - 0.5) * k_centro, 0.5 + (fy - 0.5) * k_centro)
        z = (1.0 + avance * u) * zoom_extra
        marco = cubrir(imgs[i], w, h, centro, z)
        if escala < 1.0:
            chico = marco.resize((int(w * escala), int(h * escala)), Image.BILINEAR)
            base = fondos[i].copy()
            base.paste(chico, ((w - chico.width) // 2, (h - chico.height) // 2))
            return base
        return marco

    eventos = [{"sfx": "whoosh", "t": round(max(0.0, cruce[i][0]), 2), "vol": 0.45} for i in range(1, n)]
    total = round(ctx.dur * FPS)
    with EscritorVideo(salida, w, h) as ev:
        for fr in range(total):
            t = fr / FPS
            actual = max(i for i in range(n) if t >= inicios[i] - (d * 0.65 if i else 0))
            frame = None
            if actual > 0 and cruce[actual][0] <= t <= cruce[actual][1]:
                k = (t - cruce[actual][0]) / (cruce[actual][1] - cruce[actual][0])
                ant = actual - 1
                # sale: se acelera hacia el foco, con desenfoque de movimiento y se desvanece
                kz = ease(k) ** 1.6
                zs = [1.0 + 0.9 * kz * (1 + 0.06 * j) for j in range(-2, 3)]
                sale = _desenfoque(lambda z: vista(ant, t, zoom_extra=z, k_centro=1.0), zs if kz > 0.08 else [zs[2]])
                # entra: emerge desde atrás, del tamaño de una "puerta" al cuadro completo
                entra = vista(actual, t, escala=0.82 + 0.18 * ease_out(k))
                a = 1 - min(1.0, max(0.0, (k - 0.35) / 0.45))
                frame = Image.blend(entra, sale, ease(a))
            else:
                frame = vista(actual, t)
            if capas:
                # el nombre del espacio entra al cruzar y sale justo antes del siguiente cruce
                centro = inicios[actual] - d * 0.15 if actual else 0.15
                a_in = ease_out((t - centro) / 0.35)
                sig = cruce[actual + 1][0] if actual + 1 < n else ctx.dur + 1
                a_out = 1 - ease((t - (sig - 0.25)) / 0.25)
                alfa = max(0.0, min(1.0, a_in * a_out))
                if alfa > 0:
                    capa = capas[actual]
                    if alfa < 1:
                        capa = capa.copy()
                        capa.putalpha(capa.getchannel("A").point(lambda v: int(v * alfa)))
                        capa = ImageChops.offset(capa, 0, int(18 * s * (1 - alfa)))
                    frame = Image.alpha_composite(frame.convert("RGBA"), capa)
            ev.escribir(frame)
    return eventos
