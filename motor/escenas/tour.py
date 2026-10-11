"""Tour virtual: recorrido por espacios a partir de FOTOS, con sensación de avanzar.

La cámara entra hacia un punto de interés de cada foto (una puerta, una ventana, el
jacuzzi) y, al cambiar de espacio, "atraviesa" ese punto: la foto se acerca con
desenfoque de movimiento y la siguiente emerge desde atrás. Arriba a la izquierda va el
nombre del espacio y un indicador de recorrido (puntos).

Cada espacio elige CÓMO se mueve (se pueden combinar gratis e IA en el mismo tour):
  "plano"        gratis: la foto se acerca suavemente hacia el foco
  "profundidad"  gratis: profundidad real (mapa de profundidad + paralaje); lo cercano se
                 mueve más que lo lejano, como si la cámara caminara
  "ia"           IA (Kling): anima la foto con un clip de video
  "ia_paso"      IA (Kling Omni, de foto a foto): viaja de esta foto a la de la siguiente parada
Mientras el clip de IA no existe, ese espacio se ve en "profundidad" con el aviso "IA pendiente".

params:
  paradas      lista de espacios, en el orden del recorrido:
                 foto, etiqueta ("TERRAZA"), foco [x, y] (hacia dónde entra la cámara),
                 desde (segundo o "@frase" en que empieza; la primera parada empieza en 0),
                 modo ("plano"), trayectoria ("avanzar" | "derecha" | "izquierda" | "subir" | "orbita"),
                 intensidad (1.0), prompt y modelo (para "ia" / "ia_paso"; ver ia/catalogo.json)
  modo         modo por defecto de las paradas que no lo indican ("plano")
  transicion   duración del cruce entre espacios, en segundos (0.8)
  avance       cuánto se acerca la cámara en el modo "plano" (0.22 = 22 %)
  indicador    true: nombre del espacio y puntos de recorrido (por defecto)
"""
import shutil

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .. import ia
from ..base import FFMPEG, FPS, EscritorVideo, cubrir, duracion, ease, ease_out, fuente, run
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
        yp = y0 + th + 2 * pad + 26 * s
        x = x0 + 4 * s
        for j in range(len(etiquetas)):
            activo = j == i
            ancho = 70 * s if activo else 20 * s
            d.rounded_rectangle([x, yp, x + ancho, yp + 20 * s], 10 * s, fill=prim + (255,) if activo else (255, 255, 255, 120))
            x += ancho + 14 * s
        capas.append(capa)
    return capas


def _aviso_ia(ctx, s, texto):
    capa = Image.new("RGBA", (ctx.w, ctx.h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    f = fuente("avenir-bold", 34 * s)
    b = d.textbbox((0, 0), texto, font=f)
    x, y, pad = 48 * s, ctx.h * (0.64 if ctx.h > ctx.w else 0.7), 18 * s
    d.rounded_rectangle([x, y, x + b[2] - b[0] + 2 * pad, y + b[3] - b[1] + 2 * pad], 14 * s, fill=(20, 20, 20, 205))
    d.text((x + pad - b[0], y + pad - b[1]), texto, font=f, fill=(255, 214, 102))
    return capa


def _extraer_clip(clip, destino, w, h, span):
    """Fotogramas del clip de IA como JPG (acceso aleatorio), ajustados al tiempo del espacio."""
    if destino.exists() and any(destino.iterdir()):
        return sorted(destino.glob("*.jpg"))
    destino.mkdir(parents=True, exist_ok=True)
    vel = min(2.0, max(0.5, duracion(clip) / max(0.5, span)))
    run([FFMPEG, "-loglevel", "error", "-y", "-i", str(clip), "-an",
         "-vf", f"setpts=PTS/{vel},fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
         "-q:v", "3", str(destino / "%04d.jpg")])
    return sorted(destino.glob("*.jpg"))


def render(params, ctx, salida):
    from ..profundidad import Paralaje, mapa

    w, h = ctx.w, ctx.h
    s = min(w / 1080, h / 1080 * 0.85)
    paradas = params["paradas"]
    n = len(paradas)
    d = float(params.get("transicion", 0.8))
    avance = float(params.get("avance", 0.22))
    modo_def = params.get("modo", "plano")
    formato = ia.FORMATO_DE.get((w, h), "9:16")
    imgs = [Image.open(ctx.ruta(p["foto"])).convert("RGB") for p in paradas]
    fondos = [_fondo(im, w, h) for im in imgs]
    focos = [tuple(p.get("foco") or (0.5, 0.5)) for p in paradas]
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

    # ---- cómo se mueve cada espacio
    modos, paralaje, clips, avisos, en_uso = [], {}, {}, {}, set()
    prefijo = f"tour-{round(ctx.t0 * 10)}-"
    for i, p in enumerate(paradas):
        modo = p.get("modo") or modo_def
        modos.append(modo)
        if modo in ("ia", "ia_paso"):
            lista = ia.tareas_clip(ia.params_parada([{**q, "modo": q.get("modo") or modo_def} for q in paradas], i),
                                   formato, ctx.proyecto, ctx.marca.dir)
            clip = ia.resultado(ctx.proyecto, lista[-1]["destino"])
            if clip:
                carpeta = ctx.trabajo / f"{prefijo}{i}-{clip.stem}-{round((fines[i] - inicios[i]) * 10)}"
                clips[i] = _extraer_clip(clip, carpeta, w, h, fines[i] - inicios[i] + d * 0.5)
                en_uso.add(carpeta.name)
            else:
                avisos[i] = _aviso_ia(ctx, s, f"IA PENDIENTE · {lista[-1]['nombre'].split(' · ')[-1]}")
                modos[i] = "profundidad"
        if modos[i] == "profundidad":
            paralaje[i] = Paralaje(imgs[i], mapa(ctx.ruta(p["foto"])), w, h, focos[i],
                                   p.get("trayectoria", "avanzar"), p.get("intensidad", 1.0))

    def vista(i, t, zoom_extra=1.0, escala=1.0, k_centro=None):
        """Espacio i en el instante t (+ zoom extra al cruzar; escala<1 al emerger)."""
        u = ease(min(1.0, max(0.0, (t - inicios[i]) / max(0.1, fines[i] - inicios[i]))))
        fx, fy = focos[i]
        if i in clips:
            cuadros = clips[i]
            k = min(len(cuadros) - 1, max(0, round((t - inicios[i]) * FPS)))
            marco = cubrir(Image.open(cuadros[k]).convert("RGB"), w, h, (fx, fy) if zoom_extra > 1 else (0.5, 0.5), zoom_extra)
        elif modos[i] == "profundidad":
            marco = Image.fromarray(paralaje[i].frame(u, zoom_extra))
        else:
            kc = u if k_centro is None else k_centro
            marco = cubrir(imgs[i], w, h, (0.5 + (fx - 0.5) * kc, 0.5 + (fy - 0.5) * kc), (1.0 + avance * u) * zoom_extra)
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
            if actual in avisos:
                frame = Image.alpha_composite(frame.convert("RGBA"), avisos[actual])
            ev.escribir(frame)
    # borra fotogramas de clips de versiones anteriores (ocupan disco y se regeneran si hace falta)
    for carpeta in ctx.trabajo.glob(prefijo + "*"):
        if carpeta.is_dir() and carpeta.name not in en_uso:
            shutil.rmtree(carpeta, ignore_errors=True)
    return eventos
