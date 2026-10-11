"""Imagen hecha con IA (GPT Image vía Higgsfield), animada como "imagen".

params:
  prompt       qué imagen generar
  referencias  fotos de referencia (logo, tarjeta, producto, lugar)
  modelo       id del catálogo (ia/catalogo.json → imagen), p. ej. "gpt_alta"
  + los de la escena "imagen": zoom, foco, foco_fin, oscurecer, rotulo

Sin resultado todavía, dibuja un borrador con la primera referencia."""
from .. import ia
from .clip_ia import _formato, borrador, con_rotulo


def render(params, ctx, salida):
    from . import imagen

    t = ia.tarea_imagen(params, _formato(ctx), ctx.proyecto, ctx.marca.dir)
    r = ia.resultado(ctx.proyecto, t["destino"])
    if r:
        return imagen.render({**params, "archivo": str(r)}, ctx, salida)
    refs = params.get("referencias") or []
    return con_rotulo(params, ctx, salida, lambda destino: borrador(ctx, destino, ctx.ruta(refs[0]) if refs else None,
                                                                   t["nombre"], params.get("prompt", "")))
