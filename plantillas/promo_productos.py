"""Promo de productos o menú: gancho, una escena por producto con nombre y precio, CTA."""
from . import foto_defecto, frase, oracion

INFO = {
    "id": "promo_productos",
    "nombre": "Promo de productos o menú",
    "descripcion": "Platos, productos o servicios con foto, nombre y precio, a ritmo rápido. Para restaurantes, tiendas, barberías, spas...",
    "campos": [
        {"id": "gancho", "etiqueta": "Gancho (primera frase)", "tipo": "texto", "defecto": "¿Antojo de algo rico hoy?"},
        {"id": "productos", "etiqueta": "Productos (2 a 5)", "tipo": "lista", "campos": [
            {"id": "nombre", "etiqueta": "Nombre", "tipo": "texto"},
            {"id": "precio", "etiqueta": "Precio", "tipo": "precio"},
            {"id": "detalle", "etiqueta": "Detalle corto (opcional)", "tipo": "texto"},
            {"id": "foto", "etiqueta": "Foto", "tipo": "foto"},
        ]},
        {"id": "cta", "etiqueta": "Llamado a la acción", "tipo": "texto", "defecto": "Pide ya por WhatsApp."},
    ],
}


def guion(datos, marca):
    prods = datos.get("productos") or []
    partes = [oracion(datos.get("gancho", "")), f"En {marca.nombre} te tenemos:"]
    for p in prods:
        partes.append(f"{p['nombre']}, a {p['precio']}." if p.get("precio") else oracion(p["nombre"]))
    partes.append(oracion(datos.get("cta", "")))
    return " ".join(x for x in partes if x)


def crear(datos, marca):
    prods = datos.get("productos") or []
    texto = datos.get("guion") or guion(datos, marca)
    escenas = [{
        "tipo": "texto",
        "hasta": frase(prods[0]["nombre"]) if prods else frase(datos.get("cta", "Pide")),
        "params": {"lineas": _partir(datos.get("gancho", "").upper()), "fondo": prods[0].get("foto") if prods else foto_defecto(marca),
                   "resaltar": [_ultima(datos.get("gancho", "")).upper()]},
    }]
    for i, p in enumerate(prods):
        siguiente = frase(prods[i + 1]["nombre"]) if i + 1 < len(prods) else frase(datos.get("cta", "Pide"))
        escenas.append({
            "tipo": "imagen",
            "hasta": siguiente,
            "params": {"archivo": p.get("foto") or foto_defecto(marca, i), "zoom": [1.0, 1.1],
                       "rotulo": {"titulo": p["nombre"], "precio": p.get("precio"), "detalle": p.get("detalle")}},
        })
    escenas.append({"tipo": "cierre", "hasta": "fin_voz", "extra": 1.0, "params": {}})
    return {
        "nombre": f"Promo {marca.nombre}",
        "marca": marca.slug,
        "plantilla": "promo_productos",
        "datos": datos,
        "formato": datos.get("formato", "9:16"),
        "guion": {"texto": texto},
        "escenas": escenas,
        "capas": {"subtitulos": True, "logo": True},
        "audio": {"musica": "sintetica", "sfx_cortes": True},
    }


def _ultima(texto):
    palabras = texto.replace("¿", "").replace("?", "").replace("¡", "").replace("!", "").split()
    return palabras[-1] if palabras else ""


def _partir(texto, max_chars=14):
    """Corta un título en líneas cortas para que quepa grande."""
    lineas, actual = [], ""
    for p in texto.split():
        if len(f"{actual} {p}".strip()) <= max_chars:
            actual = f"{actual} {p}".strip()
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas[:4]
