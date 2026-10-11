"""Kit de marca: lo que hace que un video se vea de ese negocio.

marcas/<slug>/marca.json:
{
  "nombre": "Sabor & Tradición",
  "logo": "logo.png",                    PNG con transparencia
  "colores": {"primario": "#963E26", "oscuro": "#3A1A10", "tinta": "#1E120C",
              "acento": "#D6AA60", "texto": "#FFFFFF"},
  "fuente_subtitulos": "din", "fuente_titulos": "avenir",
  "voz": {"voz": "es-CO-GonzaloNeural", "velocidad": "+12%"},
  "cierre": {"subtitulo": "COCINA DE AUTOR", "url": "...", "whatsapp": "...", "cta": "¡Pídela hoy!"},
  "tarjeta": "tarjeta.png",              diseño plano de la tarjeta (para 3D), opcional
  "fotos": ["fotos/plato.jpg", ...]
}
"""
import json
from functools import cached_property
from pathlib import Path

from PIL import Image

from .base import RAIZ, hex_rgb

DEFECTO_COLORES = {
    "primario": "#0F8F72",
    "oscuro": "#0B3D33",
    "tinta": "#10231F",
    "acento": "#6FD3A8",
    "texto": "#FFFFFF",
}
DEFECTO_VOZ = {"voz": "es-CO-GonzaloNeural", "velocidad": "+12%"}


class Marca:
    def __init__(self, slug):
        self.slug = slug
        self.dir = RAIZ / "marcas" / slug
        self.datos = json.loads((self.dir / "marca.json").read_text())

    @property
    def nombre(self):
        return self.datos.get("nombre", self.slug)

    def color(self, clave):
        colores = {**DEFECTO_COLORES, **self.datos.get("colores", {})}
        return hex_rgb(colores[clave])

    def ruta(self, rel):
        return self.dir / rel if rel else None

    @cached_property
    def logo(self):
        rel = self.datos.get("logo")
        if not rel or not self.ruta(rel).exists():
            return None
        return Image.open(self.ruta(rel)).convert("RGBA")

    @property
    def voz(self):
        return {**DEFECTO_VOZ, **self.datos.get("voz", {})}

    @property
    def cierre(self):
        return self.datos.get("cierre", {})

    @property
    def fuente_subtitulos(self):
        return self.datos.get("fuente_subtitulos", "din")

    @property
    def fuente_titulos(self):
        return self.datos.get("fuente_titulos", "avenir")

    @property
    def tarjeta(self):
        rel = self.datos.get("tarjeta")
        return self.ruta(rel) if rel else None


def listar():
    base = RAIZ / "marcas"
    return sorted(p.name for p in base.iterdir() if (p / "marca.json").exists())
