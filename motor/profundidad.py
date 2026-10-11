"""Profundidad real a partir de UNA foto: mapa de profundidad (Depth Anything V2 Small,
ONNX, corre en CPU) + paralaje. La cámara avanza o se desplaza y los objetos cercanos
se mueven más que los lejanos, como en un recorrido de verdad.

El mapa se calcula una sola vez por foto y se guarda en cache/profundidad/.
Modelo: modelos/depth-anything-v2-small.onnx (onnx-community/depth-anything-v2-small, Apache-2.0)."""
import hashlib
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .base import RAIZ, cubrir

MODELO = RAIZ / "modelos" / "depth-anything-v2-small.onnx"
CACHE = RAIZ / "cache" / "profundidad"
_sesion = None


def _modelo():
    global _sesion
    if _sesion is None:
        if not MODELO.exists():
            raise RuntimeError(
                "Falta el modelo de profundidad. Descárgalo con:\n"
                "curl -L -o modelos/depth-anything-v2-small.onnx "
                "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx")
        import onnxruntime as ort

        _sesion = ort.InferenceSession(str(MODELO), providers=["CPUExecutionProvider"])
    return _sesion


def mapa(ruta):
    """Profundidad relativa de la foto, 0 = lejos, 1 = cerca (float32, mismo aspecto que la foto)."""
    ruta = Path(ruta)
    clave = hashlib.md5(ruta.read_bytes()).hexdigest()[:16]
    archivo = CACHE / f"{clave}.npy"
    if archivo.exists():
        return np.load(archivo).astype(np.float32)
    img = Image.open(ruta).convert("RGB")
    # lado largo ~700 px, múltiplos de 14 (lo que pide el modelo)
    esc = 700 / max(img.size)
    w, h = max(14, round(img.width * esc / 14) * 14), max(14, round(img.height * esc / 14) * 14)
    x = np.asarray(img.resize((w, h), Image.BICUBIC), dtype=np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    s = _modelo()
    d = s.run(None, {s.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0][0]
    lo, hi = np.percentile(d, 2), np.percentile(d, 98)
    d = np.clip((d - lo) / max(1e-6, hi - lo), 0, 1).astype(np.float32)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(archivo, d.astype(np.float16))
    return d


class Paralaje:
    """Genera fotogramas de la foto con cámara en movimiento.

    trayectoria: "avanzar" (entra hacia el foco), "derecha", "izquierda", "subir", "orbita" (barrido lateral
    con avance suave). intensidad: 1.0 normal, 0.5 sutil, 1.5 fuerte."""

    def __init__(self, img, profundidad, w, h, foco=(0.5, 0.5), trayectoria="avanzar", intensidad=1.0):
        self.w, self.h = w, h
        base = cubrir(img, w, h, (0.5, 0.5), 1.0)
        self.src = np.ascontiguousarray(np.asarray(base))
        d = cv2.resize(profundidad, (w, h), interpolation=cv2.INTER_CUBIC)
        # suaviza los bordes de profundidad: menos "desgarros" al moverse
        d = cv2.GaussianBlur(d, (0, 0), 5 * w / 1080)
        self.d = np.clip(d, 0, 1).astype(np.float32)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.xx, self.yy = xx, yy
        self.c = (foco[0] * w, foco[1] * h)
        self.tray, self.k = trayectoria, float(intensidad)
        self.s = w / 1080

    def frame(self, u, zoom_extra=1.0):
        """u en 0..1 (progreso del movimiento). Devuelve un arreglo RGB uint8."""
        w, h, d, k = self.w, self.h, self.d, self.k
        e = 0.5 - 0.5 * np.cos(np.pi * min(1.0, max(0.0, u)))
        avance, lat_x, lat_y = 0.0, 0.0, 0.0
        if self.tray == "avanzar":
            avance, lat_x = 0.26 * k * e, (e - 0.5) * 14 * self.s * k
        elif self.tray in ("derecha", "izquierda"):
            avance = 0.06 * k * e
            lat_x = (e - 0.5) * 2 * 44 * self.s * k * (1 if self.tray == "derecha" else -1)
        elif self.tray == "subir":
            avance, lat_y = 0.05 * k * e, (0.5 - e) * 2 * 44 * self.s * k
        elif self.tray == "orbita":
            avance, lat_x = 0.10 * k * e, (e - 0.5) * 2 * 50 * self.s * k
        # profundidad en unidades: cerca = 1, lejos = 1 + 3
        Z = 1.0 + (1.0 - d) * 3.0
        escala = 1.06 * zoom_extra * Z / np.maximum(0.2, Z - avance)  # lo cercano crece más
        cx, cy = self.c
        sx = cx + (self.xx - cx) / escala - lat_x * (d - 0.4)
        sy = cy + (self.yy - cy) / escala - lat_y * (d - 0.4)
        return cv2.remap(self.src, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
