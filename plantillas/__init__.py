"""Plantillas: datos de un formulario + marca -> proyecto.json listo para editar.

Cada plantilla expone INFO (nombre, descripción y campos del formulario),
guion(datos, marca) -> str y crear(datos, marca) -> dict.

Tipos de campo (los pinta el panel): texto, area, foto, url, precio, numero,
lista (con "campos" internos)."""
import importlib
import re

IDS = ["promo_productos", "oferta", "resenas", "identidad_digital", "libre"]


def modulo(pid):
    if pid not in IDS:
        raise ValueError(f"Plantilla desconocida: {pid}")
    return importlib.import_module(f".{pid}", __name__)


def catalogo():
    return [modulo(p).INFO for p in IDS]


def frase(texto, n=2):
    """Primeras n palabras de un texto, para cortar escenas con "@frase"."""
    palabras = re.sub(r"[¿¡]", "", texto).split()
    return "@" + " ".join(palabras[:n])


def oracion(texto):
    """Asegura que el texto termine en puntuación (para que la voz haga pausa)."""
    texto = texto.strip()
    return texto if not texto or texto[-1] in ".!?…" else texto + "."


def foto_defecto(marca, i=0):
    fotos = marca.datos.get("fotos") or []
    return f"marca:{fotos[i % len(fotos)]}" if fotos else None
