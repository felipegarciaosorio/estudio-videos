"""Página real (cualquier URL) capturada como celular y animada en el teléfono.
Los toques, resaltes y acercamientos se piden por TEXTO visible; la posición se
calcula sola.

params:
  url            página a capturar (perfil de Aurela, web del negocio, Google Maps...)
  scroll_texto   baja hasta este título antes de capturar ("Nuestra carta")
  ocultar_texto  ["Estás en la demo"] bloques que no deben salir
  js             código opcional antes de capturar
  espera         ms de carga (4000)
  tocar          [{"t": 2.4 | "@frase", "texto": "Déjanos tu reseña"}]
  resaltar       [{"t0": .., "t1": .., "textos": ["$34.000", "$26.000"]}]
  acercar        [{"t": .., "texto": "$34.000", "s": 1.3}, {"t": .., "s": 1.0}]
  estrellas      {"t0": .., "t1": ..}
  fondo          imagen de fondo desenfocada
  refrescar      true para volver a capturar aunque exista caché
"""
import hashlib
import json

from ..base import NODE, RAIZ, run
from . import telefono

CSS_W, CSS_H = 390, 844


def capturar(params, ctx):
    textos = set()
    for x in params.get("tocar", []):
        textos.add(x["texto"])
    for x in params.get("resaltar", []):
        textos.update(x.get("textos", [x.get("texto")]))
    for x in params.get("acercar", []):
        if x.get("texto"):
            textos.add(x["texto"])
    textos.discard(None)
    cfg = {
        "url": params["url"],
        "espera": params.get("espera", 4000),
        "scroll_texto": params.get("scroll_texto"),
        "scroll_extra": params.get("scroll_extra", -40),
        "ocultar_texto": params.get("ocultar_texto", []),
        "js": params.get("js", []),
        "buscar": sorted(textos),
    }
    clave = hashlib.md5(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:10]
    carpeta = ctx.proyecto / "capturas"
    carpeta.mkdir(exist_ok=True)
    png, meta = carpeta / f"cap-{clave}.png", carpeta / f"cap-{clave}.json"
    if params.get("refrescar") or not (png.exists() and meta.exists()):
        cfg["salida"] = str(png)
        out = run([NODE, str(RAIZ / "motor" / "captura.mjs"), json.dumps(cfg)], timeout=120)
        meta.write_text(out)
    return png, json.loads(meta.read_text())["rects"]


def render(params, ctx, salida):
    png, rects = capturar(params, ctx)

    def centro(texto):
        x, y, w, h = rects[texto]
        return x + w / 2, y + h / 2

    toques = []
    for tp in params.get("tocar", []):
        if tp["texto"] in rects:
            cx, cy = centro(tp["texto"])
            toques.append({"t": tp["t"], "x": cx, "y": cy})
    resaltes = []
    for r in params.get("resaltar", []):
        cajas = [rects[t] for t in r.get("textos", [r.get("texto")]) if t in rects]
        if cajas:
            x0 = min(c[0] for c in cajas)
            y0 = min(c[1] for c in cajas)
            x1 = max(c[0] + c[2] for c in cajas)
            y1 = max(c[1] + c[3] for c in cajas)
            resaltes.append({"t0": r["t0"], "t1": r["t1"], "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0})
    zoom = []
    for a in params.get("acercar", []):
        cx, cy = centro(a["texto"]) if a.get("texto") in rects else (CSS_W / 2, CSS_H / 2)
        zoom.append({"t": a["t"], "s": a.get("s", 1.0), "cx": cx, "cy": cy})
    spec = {
        "estados": [{"t": 0, "img": str(png)}],
        "toques": toques,
        "resaltes": resaltes,
        "zoom": zoom or None,
        "estrellas": params.get("estrellas"),
        "fondo": params.get("fondo"),
    }
    return telefono.render(spec, ctx, salida)
