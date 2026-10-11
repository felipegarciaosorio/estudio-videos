"""Asistente: de una idea en una frase a un proyecto con prompts optimizados.

El mismo "brief" sirve para ChatGPT (copiar y pegar) y para Claude. Explica cómo
está hecho nuestro sistema (escenas, cortes por frase, qué pone el motor y qué
pone la IA, costos) y pide una respuesta JSON exacta. Esa respuesta se valida
antes de crear el proyecto, y el revisor avisa de prompts que gastarían créditos.

CLI (para Claude):
  python -m motor.asistente ideas                       ideas pendientes
  python -m motor.asistente brief <idea_id>             imprime el brief de una idea
  python -m motor.asistente crear <idea_id> <resp.json> valida y crea el proyecto
"""
import json
import re
import sys
import time
from pathlib import Path

from .base import RAIZ
from .escenas.esquema import ESCENAS
from .marca import Marca
from . import ia

IDEAS = RAIZ / "ia" / "ideas"
PALABRAS_POR_S = 2.6
CAMARA = re.compile(r"push[- ]?in|pull[- ]?(back|out)|dolly|pan(s|ning)?\b|orbit|tilt|zoom|tracking|crane|static|handheld|"
                    r"close[- ]?up|aerial|truck|arc shot|slow motion", re.I)
TEXTO = re.compile(r"\b(text|logo|logos|words?|letters?|sign|signage|caption|title|price|texto|letrero|precio|título)\b", re.I)
ESPANOL = re.compile(r"\b(el|la|los|las|con|una|del|que|sobre|mesa|plato|cámara)\b", re.I)
VARIAS = re.compile(r"\b(then|after that|and finally|luego|después)\b", re.I)


# ------------------------------------------------------------------ revisor
def revisar(e):
    """Avisos de una escena IA (sin costo, antes de pagar)."""
    t, pr = e.get("tipo"), e.get("params") or {}
    avisos = []
    if t not in ("clip_ia", "imagen_ia"):
        return avisos
    prompt = (pr.get("prompt") or "").strip()
    if not prompt:
        return ["Falta el prompt."]
    n = len(prompt.split())
    if t == "clip_ia":
        if n > 60:
            avisos.append(f"Prompt largo ({n} palabras): con menos de 60 el modelo lo sigue mejor.")
        if VARIAS.search(prompt):
            avisos.append("Pide varias acciones seguidas: en 5 s solo cabe una acción y un movimiento de cámara.")
        if not CAMARA.search(prompt):
            avisos.append("No dice el movimiento de cámara (p. ej. slow push-in, dolly, pan, orbit).")
        if not pr.get("imagen") and not pr.get("imagen_prompt"):
            avisos.append("Sin foto de inicio: la IA inventará el producto. Elige una foto real.")
    elif n > 120:
        avisos.append(f"Prompt largo ({n} palabras).")
    if t == "imagen_ia" and not pr.get("referencias"):
        avisos.append("Sin fotos de referencia: el resultado no se parecerá al negocio.")
    if TEXTO.search(prompt):
        avisos.append("Pide texto, precios o logos: la IA los dibuja mal. Los pone nuestro motor encima.")
    if ESPANOL.search(prompt) and len(ESPANOL.findall(prompt)) >= 3:
        avisos.append("Escríbelo en inglés: los modelos de video lo siguen mejor.")
    return avisos


def revisar_proyecto(p, presupuesto=None, dir_proyecto=None):
    salida = [{"escena": i, "avisos": a} for i, e in enumerate(p.get("escenas", [])) if (a := revisar(e))]
    if presupuesto and dir_proyecto:
        costo = ia.estimar(ia.tareas(dir_proyecto, p))
        if costo > float(presupuesto):
            salida.append({"escena": None, "avisos": [f"Cuesta {costo} créditos y el presupuesto es {presupuesto}."]})
    return salida


# ------------------------------------------------------------------ brief
def _fotos(marca):
    fotos = list(marca.datos.get("fotos") or [])
    if (marca.dir / "fotos").exists():
        fotos += [f"fotos/{f.name}" for f in sorted((marca.dir / "fotos").iterdir()) if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    return sorted(set(fotos))


def _escenas_texto(motor):
    lineas = []
    for tipo, d in ESCENAS.items():
        if d.get("ia") and motor != "higgsfield":
            continue
        campos = ", ".join(f'{c["id"]} ({c["etiqueta"]})' for c in d["campos"])
        lineas.append(f'- `{tipo}`: {d["nombre"]}{" [GASTA CRÉDITOS]" if d.get("ia") else ""}. params: {campos}')
    return "\n".join(lineas)


def _catalogo_texto():
    cat = ia.catalogo()
    v = "\n".join(f'  - `{m["id"]}`: {m["nombre"]}, {m["costo_5s"]} créditos por 5 s. {m.get("nota", "")}' for m in cat["video"])
    im = "\n".join(f'  - `{m["id"]}`: {m["nombre"]}, {m["costo"]} créditos. {m.get("nota", "")}' for m in cat["imagen"])
    return f"- Video (`modelo` en clip_ia):\n{v}\n- Imagen (`modelo` en imagen_ia o `modelo_imagen` del keyframe):\n{im}\n- Voz premium: unos {cat['voz_modelo']['costo']} créditos por video."


def brief(idea, marca_slug, formato="9:16", duracion=20, presupuesto=0, motor="gratis"):
    marca = Marca(marca_slug)
    d = marca.datos
    fotos = _fotos(marca)
    palabras = round(float(duracion) * PALABRAS_POR_S)
    guia = (RAIZ / "ia" / "guia-prompts.md").read_text()
    ia_txt = (f"Este video SÍ usa IA de Higgsfield. Presupuesto máximo: {presupuesto} créditos (incluye la voz). "
              "Usa escenas IA solo donde aporten, y escenas gratis para todo lo demás.\n\nCatálogo y costos:\n" + _catalogo_texto()
              if motor == "higgsfield" else
              "Este video es GRATIS: NO uses escenas clip_ia ni imagen_ia.")
    return f"""Eres director creativo de videos cortos para redes sociales de negocios locales (Colombia, LATAM).
Vas a diseñar UN video para nuestro estudio, que lo renderiza automáticamente.
Responde SOLO con un bloque JSON válido (sin texto antes ni después), con el formato del final.

# La idea
{idea}

# El negocio
- Marca: {marca.nombre} (slug `{marca_slug}`)
- Colores: {json.dumps(d.get("colores", {}), ensure_ascii=False)}
- Cierre de marca: {json.dumps(d.get("cierre", {}), ensure_ascii=False)}
- Fotos disponibles (úsalas con el prefijo `marca:`, p. ej. `marca:{fotos[0] if fotos else "fotos/x.jpg"}`):
{chr(10).join(f"  - marca:{f}" for f in fotos) or "  (no hay fotos: usa escenas de texto, oferta o cierre)"}
{"- Diseño de tarjeta disponible (escena producto_3d)." if d.get("tarjeta") else ""}

# El video
- Formato: {formato}. Duración objetivo: {duracion} s, que equivale a un guion de unas {palabras} palabras.
- {ia_txt}

# Escenas disponibles (tipo y params)
{_escenas_texto(motor)}

Reglas de duración de cada escena (usa UNA por escena):
- `"hasta": "@primeras palabras de la frase"`: la escena termina cuando la voz dice esas palabras. Las palabras deben estar
  tal cual en el guion, y cada "@" debe aparecer más adelante en el guion que el anterior.
- `"duracion": 2.5`: segundos fijos.
- La última escena debe ser `cierre` con `"hasta": "fin_voz", "extra": 1.0`.

# Guía de nuestro sistema (síguela al pie de la letra)
{guia}

# Formato de respuesta (JSON)
{{
  "nombre": "título corto del video",
  "guion": "texto completo que dice la voz, frases cortas terminadas en punto",
  "escenas": [
    {{"tipo": "texto", "hasta": "@Plato de", "params": {{"lineas": ["¿ANTOJO DE", "ALGO RICO HOY?"], "resaltar": ["HOY?"], "fondo": "marca:fotos/x.jpg"}}}},
    {{"tipo": "imagen", "hasta": "@Pide ya", "params": {{"archivo": "marca:fotos/x.jpg", "zoom": [1.0, 1.1], "rotulo": {{"titulo": "Plato de la casa", "precio": "$34.000"}}}}}},
    {{"tipo": "cierre", "hasta": "fin_voz", "extra": 1.0, "params": {{}}}}
  ],
  "notas": "en 2-3 líneas: por qué este gancho y dónde gastas créditos"
}}
"""


# ------------------------------------------------------------------ validar y crear
def _json(texto):
    if isinstance(texto, dict):
        return texto
    t = texto.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1)
    ini, fin = t.find("{"), t.rfind("}")
    if ini < 0 or fin < 0:
        raise ValueError("No encontré un JSON en la respuesta. Pega solo el bloque { ... }.")
    try:
        return json.loads(t[ini:fin + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"El JSON tiene un error cerca de la línea {exc.lineno}: {exc.msg}")


def validar(respuesta, marca_slug, formato="9:16", motor="gratis", duracion=None):
    """Devuelve (proyecto, errores, avisos)."""
    from .voz import buscar_frase

    errores, avisos = [], []
    r = _json(respuesta)
    marca = Marca(marca_slug)
    guion = (r.get("guion") or "").strip()
    if not guion:
        errores.append("Falta el guion.")
    escenas = r.get("escenas") or []
    if not escenas:
        errores.append("No hay escenas.")
    palabras = [{"text": w, "s": float(i), "e": i + 0.5} for i, w in enumerate(guion.split())]
    ultimo = -1.0
    for i, e in enumerate(escenas):
        n = f"Escena {i + 1}"
        tipo = e.get("tipo")
        if tipo not in ESCENAS:
            errores.append(f"{n}: tipo «{tipo}» no existe.")
            continue
        if ESCENAS[tipo].get("ia") and motor != "higgsfield":
            errores.append(f"{n}: «{tipo}» gasta créditos y el video es gratis.")
        hasta = e.get("hasta")
        if isinstance(hasta, str) and hasta.startswith("@"):
            t = buscar_frase(palabras, hasta[1:])
            if t is None:
                errores.append(f"{n}: la frase «{hasta[1:]}» no está en el guion.")
            elif t <= ultimo:
                errores.append(f"{n}: «{hasta[1:]}» se dice antes que el corte anterior.")
            else:
                ultimo = t
        pr = e.setdefault("params", {})
        for clave in ("archivo", "fondo", "imagen", "foto"):
            v = pr.get(clave)
            if isinstance(v, str) and v.startswith("marca:") and not (marca.dir / v[6:]).exists():
                errores.append(f"{n}: la foto «{v}» no existe en la marca.")
        for v in pr.get("referencias") or []:
            if isinstance(v, str) and v.startswith("marca:") and not (marca.dir / v[6:]).exists():
                errores.append(f"{n}: la referencia «{v}» no existe en la marca.")
        if tipo == "imagen" and not pr.get("archivo"):
            errores.append(f"{n}: la escena imagen necesita params.archivo.")
        if tipo == "texto" and not pr.get("lineas"):
            errores.append(f"{n}: la escena texto necesita params.lineas.")
        avisos += [f"{n}: {a}" for a in revisar(e)]
    if escenas and escenas[-1].get("tipo") != "cierre":
        avisos.append("La última escena no es el cierre de marca.")
    if duracion and guion:
        seg = len(guion.split()) / PALABRAS_POR_S
        if abs(seg - float(duracion)) > max(4, float(duracion) * 0.3):
            avisos.append(f"El guion dura unos {seg:.0f} s y pediste {duracion} s.")
    proyecto = {
        "nombre": r.get("nombre") or "Video del asistente", "marca": marca_slug, "plantilla": "libre", "formato": formato,
        "guion": {"texto": guion}, "escenas": escenas, "capas": {"subtitulos": True, "logo": True},
        "audio": {"musica": "sintetica", "sfx_cortes": True}, "notas_asistente": r.get("notas", ""),
    }
    if motor == "higgsfield":
        proyecto["ia"] = {"motor": "higgsfield", "via": "claude", "voz": dict(ia.VOZ_DEFECTO)}
    return proyecto, errores, avisos


def crear(respuesta, marca_slug, formato="9:16", motor="gratis", duracion=None):
    from .proyectos import _slug

    proyecto, errores, avisos = validar(respuesta, marca_slug, formato, motor, duracion)
    if errores:
        return {"ok": False, "errores": errores, "avisos": avisos}
    pid = f"{time.strftime('%Y%m%d-%H%M%S')}-{_slug(proyecto['nombre'])}"
    carpeta = RAIZ / "proyectos" / pid
    carpeta.mkdir(parents=True)
    (carpeta / "proyecto.json").write_text(json.dumps(proyecto, ensure_ascii=False, indent=2))
    return {"ok": True, "id": pid, "avisos": avisos, "costo": ia.estimar(ia.tareas(carpeta, proyecto))}


# ------------------------------------------------------------------ ideas (para Claude)
def guardar_idea(datos):
    IDEAS.mkdir(parents=True, exist_ok=True)
    iid = time.strftime("%Y%m%d-%H%M%S")
    idea = {"id": iid, "estado": "pendiente", "creada": time.strftime("%Y-%m-%d %H:%M"), **datos}
    (IDEAS / f"{iid}.json").write_text(json.dumps(idea, ensure_ascii=False, indent=2))
    return idea


def ideas():
    if not IDEAS.exists():
        return []
    return [json.loads(f.read_text()) for f in sorted(IDEAS.glob("*.json"), reverse=True)]


def _idea(iid):
    return json.loads((IDEAS / f"{iid}.json").read_text())


def _args(idea):
    return {k: idea.get(k) for k in ("marca", "formato", "duracion", "presupuesto", "motor")}


def _cli():
    accion = sys.argv[1] if len(sys.argv) > 1 else "ideas"
    if accion == "ideas":
        print(json.dumps([i for i in ideas() if i["estado"] == "pendiente"], ensure_ascii=False, indent=2))
    elif accion == "brief":
        i = _idea(sys.argv[2])
        a = _args(i)
        print(brief(i["idea"], a["marca"], a["formato"] or "9:16", a["duracion"] or 20, a["presupuesto"] or 0, a["motor"] or "gratis"))
    elif accion == "crear":
        i = _idea(sys.argv[2])
        a = _args(i)
        res = crear(Path(sys.argv[3]).read_text(), a["marca"], a["formato"] or "9:16", a["motor"] or "gratis", a["duracion"])
        if res["ok"]:
            i.update(estado="hecha", proyecto=res["id"])
            (IDEAS / f"{i['id']}.json").write_text(json.dumps(i, ensure_ascii=False, indent=2))
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    _cli()
