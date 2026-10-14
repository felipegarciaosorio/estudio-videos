"""Rótulo de tutoriales: en qué paso va el recorrido ("Paso 2 de 5 · Contacto").
Lo usan telefono (chip arriba del celular) y navegador (columna a la derecha).

params["paso"] = {"n": 2, "titulo": "Tu contacto", "lista": ["Quién eres", ...]}
  n = 0 deja el rótulo sin número (con "etiqueta", p. ej. "EXTRA").
  actual: qué paso de la lista va en curso (por defecto n; sin n, todos hechos;
          0 = ninguno empezado).
"""
from PIL import ImageDraw

from ..base import fuente


def _texto_corto(paso):
    if paso.get("n"):
        return f"PASO {paso['n']} DE {len(paso.get('lista', [])) or paso['n']}"
    return paso.get("etiqueta", "")


def chip(img, paso, ctx, y, a=1.0):
    """Chip centrado: «PASO 2 DE 5 · TU CONTACTO»."""
    if not paso or a <= 0:
        return
    s = ctx.w / 1080
    d = ImageDraw.Draw(img, "RGBA")
    f1, f2 = fuente("avenir-bold", 40 * s), fuente("avenir", 40 * s)
    t1, t2 = _texto_corto(paso), paso.get("titulo", "").upper()
    sep = "  ·  " if t1 and t2 else ""
    w1 = d.textlength(t1 + sep, font=f1)
    w2 = d.textlength(t2, font=f2)
    pad_x, alto = 34 * s, 78 * s
    x0 = (ctx.w - (w1 + w2 + 2 * pad_x)) / 2
    prim = ctx.marca.color("primario")
    d.rounded_rectangle([x0, y, x0 + w1 + w2 + 2 * pad_x, y + alto], alto / 2, fill=prim + (int(245 * a),))
    ty = y + alto / 2
    d.text((x0 + pad_x, ty), t1 + sep, font=f1, fill=(255, 255, 255, int(255 * a)), anchor="lm")
    d.text((x0 + pad_x + w1, ty), t2, font=f2, fill=(255, 255, 255, int(255 * a)), anchor="lm")


def columna(img, paso, ctx, x0, x1, y0, y1, a=1.0):
    """Columna lateral: número grande, título y la lista de pasos con su avance."""
    if not paso or a <= 0:
        return
    s = ctx.h / 1080
    d = ImageDraw.Draw(img, "RGBA")
    prim, acento = ctx.marca.color("primario"), ctx.marca.color("acento")
    blanco = lambda k=1.0: (255, 255, 255, int(255 * a * k))
    ancho = x1 - x0
    y = y0 + 20 * s
    etiqueta = f"PASO {paso['n']}" if paso.get("n") else paso.get("etiqueta", "")
    d.text((x0, y), etiqueta, font=fuente("avenir-bold", 26 * s), fill=acento + (int(255 * a),))
    y += 44 * s
    if paso.get("n"):
        d.text((x0 - 6 * s, y), str(paso["n"]), font=fuente("avenir-heavy", 150 * s), fill=blanco())
        y += 170 * s
    # título en hasta 3 líneas
    f = fuente("avenir-bold", 46 * s)
    linea, lineas = "", []
    for pal in paso.get("titulo", "").split():
        prueba = (linea + " " + pal).strip()
        if d.textlength(prueba, font=f) > ancho and linea:
            lineas.append(linea)
            linea = pal
        else:
            linea = prueba
    lineas.append(linea)
    for ln in lineas[:3]:
        d.text((x0, y), ln, font=f, fill=blanco())
        y += 58 * s
    y += 36 * s
    d.line([(x0, y), (x1, y)], fill=blanco(0.25), width=max(1, round(2 * s)))
    y += 34 * s
    fl = fuente("avenir-medium", 27 * s)
    actual = paso.get("actual", paso.get("n") or len(paso.get("lista", [])) + 1)
    for i, nombre in enumerate(paso.get("lista", []), start=1):
        r = 17 * s
        cx, cy = x0 + r, y + r
        if i < actual:  # hecho
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=prim + (int(255 * a),))
            d.line([(cx - 8 * s, cy), (cx - 2 * s, cy + 7 * s), (cx + 9 * s, cy - 7 * s)], fill=blanco(), width=max(2, round(4 * s)))
            color = blanco(0.7)
        elif i == actual:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, int(255 * a)))
            d.text((cx, cy), str(i), font=fuente("avenir-bold", 20 * s), fill=prim + (int(255 * a),), anchor="mm")
            color = blanco()
        else:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=blanco(0.45), width=max(1, round(2 * s)))
            d.text((cx, cy), str(i), font=fuente("avenir-bold", 20 * s), fill=blanco(0.45), anchor="mm")
            color = blanco(0.45)
        d.text((x0 + 2 * r + 16 * s, cy), nombre, font=fl, fill=color, anchor="lm")
        y += 56 * s
        if y > y1:
            break
