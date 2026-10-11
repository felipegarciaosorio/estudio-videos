"""Libre: guion propio y escenas que se arman a mano en el editor."""
from . import foto_defecto

INFO = {
    "id": "libre",
    "nombre": "Libre (cualquier video)",
    "descripcion": "Escribe tu guion y arma las escenas como quieras: fotos, clips propios, textos, páginas web, 3D, oferta, reseñas...",
    "campos": [
        {"id": "guion", "etiqueta": "Guion (lo que dice la voz)", "tipo": "area",
         "defecto": "Escribe aquí lo que dirá la voz. Cada oración puede ser una escena."},
    ],
}


def guion(datos, marca):
    return datos.get("guion", "")


def crear(datos, marca):
    return {
        "nombre": datos.get("nombre") or f"Video {marca.nombre}",
        "marca": marca.slug,
        "plantilla": "libre",
        "datos": datos,
        "formato": datos.get("formato", "9:16"),
        "guion": {"texto": datos.get("guion", "")},
        "escenas": [
            {"tipo": "imagen", "hasta": "fin_voz", "params": {"archivo": foto_defecto(marca), "zoom": [1.0, 1.1]}},
            {"tipo": "cierre", "duracion": 2.5, "params": {}},
        ],
        "capas": {"subtitulos": True, "logo": True},
        "audio": {"musica": "sintetica", "sfx_cortes": True},
    }
