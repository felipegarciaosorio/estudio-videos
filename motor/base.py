"""Utilidades compartidas del motor: rutas, formatos, fuentes, easing y escritura
de frames directo a ffmpeg (sin PNG intermedios)."""
import math
import shutil
import subprocess
from pathlib import Path

from PIL import ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FPS = 30
FORMATOS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
NODE = str(Path.home() / ".nvm/versions/node/v22.12.0/bin/node")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"

_SUP = "/System/Library/Fonts/Supplemental/"
_SYS = "/System/Library/Fonts/"
FUENTES = {
    # nombre: (archivo, índice dentro del .ttc)
    "din": (_SUP + "DIN Condensed Bold.ttf", 0),
    "avenir": (_SYS + "Avenir Next.ttc", 2),  # Demi Bold
    "avenir-bold": (_SYS + "Avenir Next.ttc", 0),
    "avenir-heavy": (_SYS + "Avenir Next.ttc", 8),
    "avenir-medium": (_SYS + "Avenir Next.ttc", 5),
    "didot": (_SUP + "Didot.ttc", 0),
    "optima": (_SUP + "Optima.ttc", 0),
    "impact": (_SUP + "Impact.ttf", 0),
}


def fuente(nombre, tam):
    archivo, idx = FUENTES.get(nombre, FUENTES["avenir"])
    return ImageFont.truetype(archivo, int(tam), index=idx)


def ease(x):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, x)))


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def run(cmd, **kw):
    """Ejecuta un comando y lanza error legible si falla."""
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"Falló: {' '.join(map(str, cmd))[:300]}\n{r.stderr[-2000:]}")
    return r.stdout


def duracion(path):
    out = run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.strip())


class EscritorVideo:
    """Recibe frames PIL y los pasa por tubería a ffmpeg.

    alpha=True guarda un .mov con canal alfa (para capas que van encima)."""

    def __init__(self, salida, w, h, alpha=False):
        self.w, self.h, self.alpha = w, h, alpha
        pix = "rgba" if alpha else "rgb24"
        codec = ["-c:v", "png"] if alpha else ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast"]
        self.proc = subprocess.Popen(
            [FFMPEG, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix, "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-", *codec, str(salida)],
            stdin=subprocess.PIPE,
        )

    def escribir(self, img):
        modo = "RGBA" if self.alpha else "RGB"
        if img.mode != modo:
            img = img.convert(modo)
        self.proc.stdin.write(img.tobytes())

    def cerrar(self):
        self.proc.stdin.close()
        if self.proc.wait() != 0:
            raise RuntimeError("ffmpeg no pudo escribir el video")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cerrar()


def cubrir(img, w, h, foco=(0.5, 0.5), zoom=1.0):
    """Recorta img para cubrir w x h (como object-fit: cover) con zoom y punto focal."""
    escala = max(w / img.width, h / img.height) * zoom
    cw, ch = w / escala, h / escala
    cx = min(max(foco[0] * img.width, cw / 2), img.width - cw / 2)
    cy = min(max(foco[1] * img.height, ch / 2), img.height - ch / 2)
    caja = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return img.resize((w, h), resample=3, box=caja)  # 3 = BICUBIC
