"""Reseñas / testimonios: foto del lugar, opiniones con estrellas y CTA."""
from . import foto_defecto, frase, oracion
from .promo_productos import _partir

INFO = {
    "id": "resenas",
    "nombre": "Reseñas / testimonios",
    "descripcion": "Opiniones reales de clientes con estrellas sobre la foto del lugar, y llamado a reservar o pedir. Usa reseñas cortas (menos de 15 palabras).",
    "campos": [
        {"id": "gancho", "etiqueta": "Gancho", "tipo": "texto", "defecto": "¿Todavía no nos conoces?"},
        {"id": "foto", "etiqueta": "Foto del lugar", "tipo": "foto"},
        {"id": "resenas", "etiqueta": "Reseñas (2 a 4)", "tipo": "lista", "campos": [
            {"id": "nombre", "etiqueta": "Nombre", "tipo": "texto"},
            {"id": "texto", "etiqueta": "Opinión", "tipo": "texto"},
            {"id": "estrellas", "etiqueta": "Estrellas", "tipo": "numero", "defecto": 5},
        ]},
        {"id": "cta", "etiqueta": "Llamado a la acción", "tipo": "texto", "defecto": "Reserva hoy por WhatsApp."},
    ],
}


def guion(datos, marca):
    partes = [oracion(datos.get("gancho", "")), "Esto dicen nuestros clientes."]
    for r in datos.get("resenas") or []:
        partes.append(f"{r['nombre']}: {oracion(r['texto'])}")
    partes.append(oracion(datos.get("cta", "")))
    return " ".join(x for x in partes if x)


def crear(datos, marca):
    texto = datos.get("guion") or guion(datos, marca)
    resenas = datos.get("resenas") or []
    foto = datos.get("foto") or foto_defecto(marca)
    escenas = [
        {"tipo": "texto", "hasta": "@Esto dicen",
         "params": {"lineas": _partir(datos.get("gancho", "").upper()), "fondo": foto}},
        {"tipo": "resenas", "hasta": frase(datos.get("cta", "Reserva")),
         "params": {"resenas": [{**r, "estrellas": int(r.get("estrellas") or 5)} for r in resenas], "fondo": foto,
                    "titulo": "Lo que dicen nuestros clientes",
                    "tiempos": [0.1] + [frase(r["nombre"], 1) for r in resenas[1:]]}},
        {"tipo": "cierre", "hasta": "fin_voz", "extra": 1.0, "params": {}},
    ]
    return {
        "nombre": f"Reseñas {marca.nombre}",
        "marca": marca.slug,
        "plantilla": "resenas",
        "datos": datos,
        "formato": datos.get("formato", "9:16"),
        "guion": {"texto": texto},
        "escenas": escenas,
        "capas": {"subtitulos": True, "logo": True},
        "audio": {"musica": "sintetica", "sfx_cortes": True},
    }
