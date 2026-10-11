"""Oferta / descuento: gancho, antes y después, ahorro, urgencia y CTA."""
import re

from . import foto_defecto, frase, oracion
from .promo_productos import _partir, _ultima

INFO = {
    "id": "oferta",
    "nombre": "Oferta / descuento",
    "descripcion": "Precio de antes tachado, precio nuevo, porcentaje de ahorro, urgencia y llamado a escribir.",
    "campos": [
        {"id": "gancho", "etiqueta": "Gancho", "tipo": "texto", "defecto": "¡Oferta que no vas a creer!"},
        {"id": "producto", "etiqueta": "Producto o servicio", "tipo": "texto"},
        {"id": "foto", "etiqueta": "Foto", "tipo": "foto"},
        {"id": "antes", "etiqueta": "Precio antes", "tipo": "precio"},
        {"id": "ahora", "etiqueta": "Precio ahora", "tipo": "precio"},
        {"id": "urgencia", "etiqueta": "Urgencia", "tipo": "texto", "defecto": "Solo hasta este domingo."},
        {"id": "cta", "etiqueta": "Llamado a la acción", "tipo": "texto", "defecto": "Escríbenos por WhatsApp y apártalo."},
    ],
}


def _valor(precio):
    digitos = re.sub(r"\D", "", precio or "")
    return int(digitos) if digitos else 0


def descuento(datos):
    antes, ahora = _valor(datos.get("antes")), _valor(datos.get("ahora"))
    return round(100 * (antes - ahora) / antes) if antes > ahora > 0 else 0


def guion(datos, marca):
    pct = descuento(datos)
    partes = [
        oracion(datos.get("gancho", "")),
        f"{datos.get('producto', '')}: antes {datos.get('antes', '')}, ahora solo {datos.get('ahora', '')}.",
        f"¡Te ahorras el {pct}%!" if pct else "",
        oracion(datos.get("urgencia", "")),
        oracion(datos.get("cta", "")),
    ]
    return " ".join(x for x in partes if x)


def crear(datos, marca):
    texto = datos.get("guion") or guion(datos, marca)
    pct = descuento(datos)
    foto = datos.get("foto") or foto_defecto(marca)
    escenas = [
        {"tipo": "texto", "hasta": frase(datos.get("producto", "")),
         "params": {"lineas": _partir(datos.get("gancho", "").upper()), "fondo": foto,
                    "resaltar": [_ultima(datos.get("gancho", "")).upper()]}},
        {"tipo": "oferta", "hasta": frase(datos.get("cta", "Escríbenos")),
         "params": {"foto": foto, "producto": datos.get("producto"), "antes": datos.get("antes"), "ahora": datos.get("ahora"),
                    "descuento": f"-{pct}%" if pct else None, "urgencia": datos.get("urgencia", "").rstrip(".")}},
        {"tipo": "cierre", "hasta": "fin_voz", "extra": 1.0, "params": {}},
    ]
    return {
        "nombre": f"Oferta {datos.get('producto', '')}".strip(),
        "marca": marca.slug,
        "plantilla": "oferta",
        "datos": datos,
        "formato": datos.get("formato", "9:16"),
        "guion": {"texto": texto},
        "escenas": escenas,
        "capas": {"subtitulos": True, "logo": True},
        "audio": {"musica": "sintetica", "sfx_cortes": True},
    }
