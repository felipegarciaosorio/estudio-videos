"""Capa superior del video (con transparencia): subtítulos karaoke, logo de la
marca arriba y etiqueta de precio. Va encima de todas las escenas."""
import re

from PIL import Image, ImageDraw, ImageFilter

from .base import FPS, EscritorVideo, ease_out, fuente


def _display(tok):
    # el punto dentro de un dominio ("aurelasoluciones.com") se queda
    return re.sub(r"(?<=\D)[.,:](?![^\W\d_])|[,:;]$|\.$", "", tok).upper()


def _chunks(palabras, max_palabras=3):
    """Frases de 1 a 3 palabras, cortando en la puntuación."""
    out, cur = [], []
    for w in palabras:
        cur.append(w)
        if len(cur) == max_palabras or re.search(r"[.,:;?!]$", w["text"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


class Capa:
    def __init__(self, marca, w, h, palabras, cfg, dur):
        self.marca, self.w, self.h, self.dur = marca, w, h, dur
        # escala: 1.0 en vertical; en cuadrado/horizontal se toma del alto
        self.s = min(w / 1080, h / 1080 * 0.85)
        self.cfg = cfg
        self.palabras = palabras
        self.chunks = _chunks(palabras) if cfg.get("subtitulos", True) else []
        self.f_sub = fuente(marca.fuente_subtitulos, 112 * self.s * cfg.get("escala_subtitulos", 1.0))
        self.y_sub = h * cfg.get("altura_subtitulos", 0.745 if h > w else 0.78)
        self.resalte = marca.color("primario")
        self.logo_capa = self._logo() if cfg.get("logo", True) else None
        self.ocultar_logo = cfg.get("ocultar_logo", [])
        self.etiqueta = cfg.get("etiqueta")
        self.etiqueta_capa = self._etiqueta() if self.etiqueta else None

    # ---------------- capas fijas (se calculan una vez)
    def _logo(self):
        capa = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        alto = int(92 * self.s)
        logo = self.marca.logo
        nombre = self.marca.datos.get("nombre_corto", self.marca.nombre)
        f = fuente(self.marca.fuente_titulos, 64 * self.s)
        tb = d.textbbox((0, 0), nombre, font=f)
        lw = 0
        if logo:
            lw = int(logo.width * alto / logo.height)
            logo = logo.resize((lw, alto), Image.LANCZOS)
        mostrar_nombre = self.marca.datos.get("logo_con_nombre", True)
        total = lw + ((18 * self.s + tb[2] - tb[0]) if mostrar_nombre else 0)
        vertical = self.h > self.w
        x0 = (self.w - total) / 2 if vertical else 48 * self.s
        y0 = int(110 * self.s if vertical else 44 * self.s)
        ty = y0 + (alto - (tb[3] - tb[1])) / 2 - tb[1]
        tx = x0 + lw + 18 * self.s - tb[0]
        sombra = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sombra)
        if logo:
            sombra.paste((0, 0, 0, 140), (int(x0), int(y0 + 4)), logo.getchannel("A"))
        if mostrar_nombre:
            sd.text((tx, ty + 4), nombre, font=f, fill=(0, 0, 0, 160))
        capa.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(8 * self.s)))
        if logo:
            capa.alpha_composite(logo, (int(x0), int(y0)))
        if mostrar_nombre:
            d.text((tx, ty), nombre, font=f, fill=(255, 255, 255))
        return capa

    def _etiqueta(self):
        e = self.etiqueta
        capa = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        fb, fs = fuente("din", 210 * self.s), fuente("din", 72 * self.s)
        y = int(self.h * 0.17)
        bb, sb = d.textbbox((0, 0), e["grande"], font=fb), d.textbbox((0, 0), e.get("pequeno", ""), font=fs)
        bw, sw = bb[2] - bb[0], sb[2] - sb[0]
        sombra = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        ImageDraw.Draw(sombra).text(((self.w - bw) / 2 - bb[0], y + 6), e["grande"], font=fb, fill=(0, 0, 0, 170))
        capa.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(10)))
        d.text(((self.w - bw) / 2 - bb[0], y), e["grande"], font=fb, fill=(255, 255, 255))
        if e.get("pequeno"):
            py = y + bb[3] + 30 * self.s
            pad = 26 * self.s
            d.rounded_rectangle([(self.w - sw) / 2 - pad, py - 12 * self.s, (self.w + sw) / 2 + pad, py + sb[3] + 16 * self.s],
                                16 * self.s, fill=self.resalte + (255,))
            d.text(((self.w - sw) / 2 - sb[0], py), e["pequeno"], font=fs, fill=(255, 255, 255))
        return capa

    # ---------------- por frame
    def _subtitulo(self, img, t):
        actual = None
        for i, c in enumerate(self.chunks):
            sig = self.chunks[i + 1][0]["s"] if i + 1 < len(self.chunks) else self.dur
            if c[0]["s"] - 0.05 <= t < sig - 0.05:
                actual = c
        if not actual:
            return
        d = ImageDraw.Draw(img)
        gap = 26 * self.s
        textos = [_display(w["text"]) for w in actual]
        cajas = [d.textbbox((0, 0), tx, font=self.f_sub) for tx in textos]
        anchos = [b[2] - b[0] for b in cajas]
        # si no cabe en una línea (formatos anchos o palabras largas), reduce
        f = self.f_sub
        total = sum(anchos) + gap * (len(actual) - 1)
        if total > self.w * 0.92:
            f = fuente(self.marca.fuente_subtitulos, self.f_sub.size * self.w * 0.92 / total)
            cajas = [d.textbbox((0, 0), tx, font=f) for tx in textos]
            anchos = [b[2] - b[0] for b in cajas]
            total = sum(anchos) + gap * (len(actual) - 1)
        x, y = (self.w - total) / 2, self.y_sub
        dichas = [w for w in actual if w["s"] <= t]
        activa = dichas[-1] if dichas else None
        for w, tx, b, an in zip(actual, textos, cajas, anchos):
            if w is activa:
                px, py = 16 * self.s, 10 * self.s
                d.rounded_rectangle([x - px, y + b[1] - py, x + an + px, y + b[3] + py], 14 * self.s, fill=self.resalte + (255,))
                d.text((x - b[0], y), tx, font=f, fill=(255, 255, 255))
            else:
                d.text((x - b[0], y), tx, font=f, fill=(255, 255, 255), stroke_width=int(7 * self.s), stroke_fill=(0, 0, 0))
            x += an + gap

    def frame(self, t):
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        if self.logo_capa and not any(a <= t < b for a, b in self.ocultar_logo):
            img.alpha_composite(self.logo_capa)
        e = self.etiqueta
        if self.etiqueta_capa and e["desde"] <= t < e["hasta"]:
            k = ease_out((t - e["desde"]) / 0.25)
            capa = self.etiqueta_capa
            if k < 1:
                capa = capa.copy()
                capa.putalpha(capa.getchannel("A").point(lambda a: int(a * k)))
                capa = capa.transform(capa.size, Image.AFFINE, (1, 0, 0, 0, 1, -int(40 * self.s * (1 - k))))
            img.alpha_composite(capa)
        self._subtitulo(img, t)
        return img


def renderizar(marca, w, h, palabras, cfg, dur, salida):
    capa = Capa(marca, w, h, palabras, cfg, dur)
    with EscritorVideo(salida, w, h, alpha=True) as ev:
        for f in range(round(dur * FPS)):
            ev.escribir(capa.frame(f / FPS))
    return salida
