"""Tarjeta / identidad digital: el patrón de los reels de Aurela, para cualquier
negocio que tenga diseño de tarjeta y perfil publicado."""
from . import foto_defecto, frase, oracion
from .promo_productos import _partir, _ultima

INFO = {
    "id": "identidad_digital",
    "nombre": "Tarjeta / identidad digital",
    "descripcion": "Gancho, la tarjeta en 3D, el perfil real capturado de su URL, precio y cierre. Necesita el diseño de la tarjeta en la marca.",
    "campos": [
        {"id": "gancho", "etiqueta": "Gancho", "tipo": "texto", "defecto": "¿Todavía compartes tu número en papel?"},
        {"id": "url_perfil", "etiqueta": "URL del perfil o página", "tipo": "url", "defecto": "https://www.aurelasoluciones.com/p/aurela-soluciones"},
        {"id": "tocar", "etiqueta": "Botón a tocar en el perfil (texto visible)", "tipo": "texto", "defecto": "WhatsApp"},
        {"id": "precio", "etiqueta": "Precio", "tipo": "precio", "defecto": "$99.900"},
        {"id": "cta", "etiqueta": "Llamado a la acción", "tipo": "texto", "defecto": "¡Pídela hoy!"},
    ],
}


def guion(datos, marca):
    return " ".join(x for x in [
        oracion(datos.get("gancho", "")),
        f"Con {marca.nombre}, tu negocio tiene identidad digital: una tarjeta que, con solo acercarla al celular, abre tu perfil.",
        "WhatsApp, redes, servicios y ubicación, en segundos.",
        f"Tarjeta personalizada, {datos.get('precio', '')}, pago único." if datos.get("precio") else "",
        oracion(datos.get("cta", "")),
    ] if x)


def crear(datos, marca):
    texto = datos.get("guion") or guion(datos, marca)
    gancho = datos.get("gancho", "")
    escenas = [
        {"tipo": "texto", "hasta": f"@Con {marca.nombre.split()[0]}",
         "params": {"lineas": _partir(gancho.upper()), "fondo": foto_defecto(marca), "resaltar": [_ultima(gancho).upper()]}},
        {"tipo": "producto_3d", "hasta": "@abre tu perfil", "params": {"modo": "tarjeta_gira"}},
        {"tipo": "captura", "hasta": "@Tarjeta personalizada" if datos.get("precio") else frase(datos.get("cta", "Pídela")),
         "params": {"url": datos.get("url_perfil"), "fondo": foto_defecto(marca),
                    "tocar": [{"t": "@WhatsApp, redes", "texto": datos.get("tocar") or "WhatsApp"}]}},
    ]
    capas = {"subtitulos": True, "logo": True}
    if datos.get("precio"):
        escenas.append({"tipo": "producto_3d", "hasta": frase(datos.get("cta", "Pídela")), "params": {"modo": "tarjeta_mesa"}})
        capas["etiqueta"] = {"desde": "@" + datos["precio"], "dur": 1.6, "grande": datos["precio"], "pequeno": "PAGO ÚNICO"}
    escenas.append({"tipo": "cierre", "hasta": "fin_voz", "extra": 1.0,
                    "params": {"precio": f"{datos['precio']} · PAGO ÚNICO"} if datos.get("precio") else {}})
    return {
        "nombre": f"Identidad digital {marca.nombre}",
        "marca": marca.slug,
        "plantilla": "identidad_digital",
        "datos": datos,
        "formato": datos.get("formato", "9:16"),
        "guion": {"texto": texto},
        "escenas": escenas,
        "capas": capas,
        "audio": {"musica": "sintetica", "sfx_cortes": True},
    }
