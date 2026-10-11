"""Piezas hechas con IA (Higgsfield): voz premium, imágenes y clips de video.

El motor no llama a la IA directamente. Cada proyecto declara lo que quiere
(sección "ia" + escenas clip_ia / imagen_ia), este módulo lo convierte en
TAREAS con un id estable (hash de lo que se pide) y un archivo destino dentro de
proyectos/<id>/ia/. Quien ejecute la tarea (Claude con el MCP de Higgsfield,
ChatGPT con su conector, la API o una subida manual) solo tiene que dejar el
archivo en su destino. Si cambias el prompt o el guion, cambia el hash y se
pide una pieza nueva; lo ya hecho nunca se paga dos veces.

proyecto.json:
  "ia": {"motor": "higgsfield",              "gratis" (defecto) | "higgsfield"
         "via": "claude",                    "claude" | "chatgpt" | "api"
         "voz": {"activa": true, "voice_id": "...", "nombre": "Marisol", "tempo": 1.1}}

CLI (puente con Claude):
  python -m motor.ia pendientes                       tareas por hacer de todos los pedidos (JSON)
  python -m motor.ia proceso <pid> <tarea> <job_id>   marca en proceso
  python -m motor.ia marcar <pid> <tarea> <url|ruta>  descarga/copia el resultado y lo marca listo
  python -m motor.ia error <pid> <tarea> <mensaje>
  python -m motor.ia pedido <pid>                     crea/actualiza el pedido de un proyecto
"""
import hashlib
import json
import math
import shutil
import sys
import time
import urllib.request
from pathlib import Path

from .base import FFMPEG, FFPROBE, RAIZ, run

CARPETA_IA = RAIZ / "ia"
PEDIDOS = CARPETA_IA / "pedidos"
FORMATO_DE = {(1080, 1920): "9:16", (1080, 1080): "1:1", (1920, 1080): "16:9"}
VOZ_DEFECTO = {"activa": True, "voice_id": "75e72cd5-011b-4130-a474-e8b1ab341f04", "nombre": "Marisol", "tempo": 1.1}


def catalogo():
    return json.loads((CARPETA_IA / "catalogo.json").read_text())


def _modelo(tipo, clave):
    cat = catalogo()
    lista = cat["video"] if tipo == "video" else cat["imagen"]
    for m in lista:
        if m["id"] == clave:
            return m
    return next((m for m in lista if m.get("recomendado")), lista[0])


def _hash(*partes):
    return hashlib.md5(json.dumps(partes, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]


def cfg(p):
    return p.get("ia") or {}


def activo(p):
    return cfg(p).get("motor") == "higgsfield"


def voz_cfg(p):
    if not activo(p):
        return None
    v = {**VOZ_DEFECTO, **(cfg(p).get("voz") or {})}
    return v if v.get("activa") else None


def resultado(dir_proyecto, destino):
    """Archivo del resultado si ya existe (con cualquier extensión)."""
    base = Path(dir_proyecto) / destino
    for f in sorted(base.parent.glob(base.stem + ".*")) if base.parent.exists() else []:
        if f.suffix.lower() not in (".part", ".json"):
            return f
    return None


# ------------------------------------------------------------------ tareas
def _ref(dir_proyecto, marca_dir, ruta):
    if not ruta:
        return None
    if str(ruta).startswith("marca:"):
        return str(Path(marca_dir) / str(ruta)[6:])
    q = Path(ruta)
    return str(q if q.is_absolute() else Path(dir_proyecto) / q)


def tarea_voz(p, dir_proyecto):
    from .voz import texto_hablado

    v = voz_cfg(p)
    guion = p.get("guion") or {}
    if not v or not guion.get("texto"):
        return None
    from .marca import Marca

    texto = texto_hablado(guion, Marca(p["marca"]))
    m = catalogo()["voz_modelo"]
    h = _hash("voz", texto, v["voice_id"], m["params"])
    return {
        "id": f"voz-{h}", "tipo": "voz", "escena": None, "nombre": f"Voz {v.get('nombre', '')}".strip(),
        "modelo": m["modelo"], "params": {**m["params"], "voice_id": v["voice_id"]},
        "prompt": texto, "referencias": [], "destino": f"ia/voz-{h}.mp3",
        "costo": round(max(m["costo"], m["costo"] * len(texto) / m["por_caracteres"]), 2),
    }


def tarea_imagen(params, formato, dir_proyecto, marca_dir, escena=None):
    """Imagen IA (escena imagen_ia, o keyframe de un clip_ia)."""
    m = _modelo("imagen", params.get("modelo_imagen") or params.get("modelo"))
    refs = [r for r in (_ref(dir_proyecto, marca_dir, x) for x in params.get("referencias") or []) if r]
    h = _hash("img", m["modelo"], m["params"], params.get("imagen_prompt") or params.get("prompt"), refs, formato)
    return {
        "id": f"img-{h}", "tipo": "imagen", "escena": escena, "nombre": m["nombre"], "catalogo": m["id"],
        "modelo": m["modelo"], "params": {**m["params"], "aspect_ratio": formato},
        "prompt": params.get("imagen_prompt") or params.get("prompt", ""),
        "referencias": [{"ruta": r, "rol": "image_references"} for r in refs],
        "destino": f"ia/img-{h}.png", "costo": m["costo"],
    }


def tareas_clip(params, formato, dir_proyecto, marca_dir, escena=None):
    """Clip IA: [keyframe opcional, clip]. Con un modelo "de foto a foto" (frames) y `imagen_final`,
    el clip viaja de la foto de inicio a la foto final (transición entre dos espacios)."""
    salida = []
    inicio = _ref(dir_proyecto, marca_dir, params.get("imagen"))
    if params.get("imagen_prompt"):
        kf = tarea_imagen({**params, "referencias": params.get("referencias") or ([params["imagen"]] if params.get("imagen") else [])},
                          formato, dir_proyecto, marca_dir, escena)
        kf["nombre"] = f"Keyframe · {kf['nombre']}"
        salida.append(kf)
        inicio = str(Path(dir_proyecto) / kf["destino"])
    m = _modelo("video", params.get("modelo"))
    final = _ref(dir_proyecto, marca_dir, params.get("imagen_final")) if m.get("frames") else None
    dur = int(params.get("duracion_clip") or m["duraciones"][0])
    h = _hash("clip", m["modelo"], m["params"], params.get("prompt", ""), inicio, final, dur, formato)
    refs = ([{"ruta": inicio, "rol": "start_image"}] if inicio else []) + ([{"ruta": final, "rol": "end_image"}] if final else [])
    salida.append({
        "id": f"clip-{h}", "tipo": "video", "escena": escena, "nombre": m["nombre"], "catalogo": m["id"],
        "modelo": m["modelo"], "params": {**m["params"], "duration": dur, "aspect_ratio": formato},
        "prompt": params.get("prompt", ""), "referencias": refs,
        "depende": salida[0]["id"] if params.get("imagen_prompt") else None,
        "destino": f"ia/clip-{h}.mp4", "costo": round(m["costo_5s"] * math.ceil(dur / 5), 2),
    })
    return salida


def params_parada(paradas, j):
    """Parámetros de clip_ia equivalentes a una parada de tour con modo "ia" o "ia_paso"
    (None si la parada no usa IA)."""
    p = paradas[j]
    modo = p.get("modo")
    if modo not in ("ia", "ia_paso"):
        return None
    params = {"imagen": p.get("foto"), "prompt": p.get("prompt", ""), "modelo": p.get("modelo") or ("kling_frames" if modo == "ia_paso" else None)}
    if p.get("duracion_clip"):
        params["duracion_clip"] = p["duracion_clip"]
    if modo == "ia_paso" and j + 1 < len(paradas):
        params["imagen_final"] = paradas[j + 1].get("foto")
    return params


def tareas_escena(e, formato, dir_proyecto, marca_dir, escena=None):
    """Tareas IA de una escena (clip_ia, imagen_ia o paradas de un tour)."""
    tipo, pr = e.get("tipo"), e.get("params") or {}
    if tipo == "clip_ia":
        return tareas_clip(pr, formato, dir_proyecto, marca_dir, escena)
    if tipo == "imagen_ia":
        return [tarea_imagen(pr, formato, dir_proyecto, marca_dir, escena)]
    if tipo == "tour":
        salida = []
        paradas = [{**q, "modo": q.get("modo") or pr.get("modo")} for q in pr.get("paradas") or []]
        for j in range(len(paradas)):
            params = params_parada(paradas, j)
            if params:
                for t in tareas_clip(params, formato, dir_proyecto, marca_dir, escena):
                    t["parada"] = j
                    t["nombre"] = f"{paradas[j].get('etiqueta') or 'Parada ' + str(j + 1)} · {t['nombre']}"
                    salida.append(t)
        return salida
    return []


def tareas(dir_proyecto, p=None):
    """Todo lo que el proyecto pide a la IA, con "listo" si el archivo ya está."""
    from .marca import Marca

    dir_proyecto = Path(dir_proyecto)
    p = p or json.loads((dir_proyecto / "proyecto.json").read_text())
    if not activo(p):
        return []
    marca_dir = Marca(p["marca"]).dir
    formato = p.get("formato", "9:16")
    salida = []
    tv = tarea_voz(p, dir_proyecto)
    if tv:
        salida.append(tv)
    for i, e in enumerate(p.get("escenas", [])):
        salida += tareas_escena(e, formato, dir_proyecto, marca_dir, i)
    for t in salida:
        r = resultado(dir_proyecto, t["destino"])
        t["listo"] = bool(r)
        if r:
            t["archivo"] = str(r.relative_to(dir_proyecto))
    return salida


def estimar(lista):
    return round(sum(t["costo"] for t in lista if not t.get("listo")), 2)


def huella(e, dir_proyecto, p):
    """Para la caché de escenas: cambia cuando llega (o cambia) el resultado de la IA."""
    from .marca import Marca

    lista = tareas_escena(e, p.get("formato", "9:16"), dir_proyecto, Marca(p["marca"]).dir)
    partes = []
    for t in lista:
        r = resultado(dir_proyecto, t["destino"])
        partes.append(f"{r.name}:{r.stat().st_mtime}" if r else "pendiente")
    return "|".join(partes)


def voz_lista(dir_proyecto, p, trabajo):
    """MP3 de la voz IA ya acelerada a su tempo, o None si falta."""
    tv = tarea_voz(p, dir_proyecto)
    r = resultado(dir_proyecto, tv["destino"]) if tv else None
    if not r:
        return None
    tempo = float(voz_cfg(p).get("tempo", 1.0))
    if abs(tempo - 1.0) < 0.01:
        return r
    salida = Path(trabajo) / f"{r.stem}-t{round(tempo * 100)}.mp3"
    if not salida.exists():
        run([FFMPEG, "-loglevel", "error", "-y", "-i", str(r), "-filter:a", f"atempo={tempo}", "-b:a", "192k", str(salida)])
    return salida


# ------------------------------------------------------------------ pedidos
def _archivo_pedido(pid):
    return PEDIDOS / f"{pid}.json"


def crear_pedido(pid, via=None):
    """Escribe ia/pedidos/<pid>.json con las tareas pendientes (conserva el estado
    de las que ya estaban en proceso)."""
    dir_proyecto = RAIZ / "proyectos" / pid
    p = json.loads((dir_proyecto / "proyecto.json").read_text())
    lista = tareas(dir_proyecto, p)
    anterior = {t["id"]: t for t in leer_pedido(pid).get("tareas", [])} if _archivo_pedido(pid).exists() else {}
    for t in lista:
        viejo = anterior.get(t["id"], {})
        t["estado"] = "listo" if t["listo"] else viejo.get("estado", "pendiente")
        if t["estado"] == "listo" and not t["listo"]:
            t["estado"] = "pendiente"
        for k in ("job_id", "error", "actualizado"):
            if k in viejo and not t["listo"]:
                t[k] = viejo[k]
    pedido = {
        "pid": pid, "nombre": p.get("nombre", pid), "marca": p.get("marca"),
        "via": via or cfg(p).get("via", "claude"), "creado": time.strftime("%Y-%m-%d %H:%M"),
        "proyecto": str(dir_proyecto), "tareas": lista, "costo": estimar(lista),
    }
    PEDIDOS.mkdir(parents=True, exist_ok=True)
    _archivo_pedido(pid).write_text(json.dumps(pedido, ensure_ascii=False, indent=2))
    return resumen(pedido)


def leer_pedido(pid):
    f = _archivo_pedido(pid)
    return json.loads(f.read_text()) if f.exists() else {}


def resumen(pedido):
    ts = pedido.get("tareas", [])
    n = {e: sum(1 for t in ts if t.get("estado") == e) for e in ("pendiente", "en_proceso", "listo", "error")}
    if not ts:
        estado = "vacio"
    elif n["listo"] == len(ts):
        estado = "listo"
    elif n["error"]:
        estado = "error"
    elif n["en_proceso"] or n["listo"]:
        estado = "en_proceso"
    else:
        estado = "pendiente"
    return {**pedido, "estado": estado, "conteo": n, "total": len(ts)}


def pedidos():
    if not PEDIDOS.exists():
        return []
    return [resumen(json.loads(f.read_text())) for f in sorted(PEDIDOS.glob("*.json"), reverse=True)]


def _actualizar(pid, tarea_id, **cambios):
    pedido = leer_pedido(pid)
    for t in pedido.get("tareas", []):
        if t["id"] == tarea_id:
            t.update(cambios, actualizado=time.strftime("%Y-%m-%d %H:%M:%S"))
            break
    else:
        raise SystemExit(f"No existe la tarea {tarea_id} en el pedido {pid}")
    _archivo_pedido(pid).write_text(json.dumps(pedido, ensure_ascii=False, indent=2))
    return t


def guardar_resultado(dir_proyecto, destino, fuente, nombre_original=""):
    """Descarga (URL) o copia (ruta/bytes) el resultado a su destino y lo valida."""
    base = Path(dir_proyecto) / destino
    base.parent.mkdir(parents=True, exist_ok=True)
    tmp = base.with_suffix(".part")
    if isinstance(fuente, bytes):
        tmp.write_bytes(fuente)
        ext = Path(nombre_original).suffix.lower()
    elif str(fuente).startswith("http"):
        req = urllib.request.Request(str(fuente), headers={"User-Agent": "estudio-videos"})
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        ext = Path(str(fuente).split("?")[0]).suffix.lower()
    else:
        shutil.copy(fuente, tmp)
        ext = Path(str(fuente)).suffix.lower()
    try:
        run([FFPROBE, "-v", "error", "-show_entries", "format=format_name", "-of", "csv=p=0", str(tmp)])
    except RuntimeError:
        tmp.unlink(missing_ok=True)
        raise ValueError("El archivo no es un audio, imagen o video válido")
    for viejo in base.parent.glob(base.stem + ".*"):
        if viejo != tmp:
            viejo.unlink()
    final = base.with_suffix(ext or base.suffix)
    tmp.rename(final)
    return final


def marcar(pid, tarea_id, fuente):
    pedido = leer_pedido(pid)
    t = next((t for t in pedido.get("tareas", []) if t["id"] == tarea_id), None)
    if not t:
        raise SystemExit(f"No existe la tarea {tarea_id} en el pedido {pid}")
    final = guardar_resultado(pedido["proyecto"], t["destino"], fuente)
    _actualizar(pid, tarea_id, estado="listo", archivo=str(Path(final).relative_to(pedido["proyecto"])), error=None)
    return final


def instrucciones(pedido):
    """Pasos exactos por tarea, para Claude (MCP) o para pegar en ChatGPT."""
    pasos = []
    herr = {"voz": "generate_audio", "imagen": "generate_image", "video": "generate_video"}
    for t in pedido.get("tareas", []):
        if t.get("estado") == "listo":
            continue
        params = {"model": t["modelo"], "prompt": t["prompt"], **t["params"]}
        if t["tipo"] == "voz":
            params["voice_type"] = "preset"
        pasos.append({
            "pid": pedido["pid"], "tarea": t["id"], "tipo": t["tipo"], "estado": t.get("estado"),
            "herramienta": herr[t["tipo"]], "params": params,
            "subir": [{"archivo": r["ruta"], "role": r["rol"]} for r in t["referencias"]],
            "depende": t.get("depende"), "costo": t["costo"], "job_id": t.get("job_id"),
        })
    return pasos


def texto_chatgpt(pedido):
    """Instrucciones para pegar en ChatGPT (que también está conectado a Higgsfield)."""
    nombres = {"voz": "voz (texto a voz)", "imagen": "imagen", "video": "clip de video"}
    voces = {v["id"]: v["nombre"] for v in catalogo()["voces"]}
    partes = [
        "Usa tu conexión con Higgsfield para generar estas piezas EXACTAMENTE con estos parámetros (no cambies los "
        "prompts: ya están optimizados). Cuando cada una termine, dame su enlace de descarga con el código de la tarea.",
        "",
    ]
    for i, paso in enumerate(instrucciones(pedido), 1):
        pr = dict(paso["params"])
        modelo, prompt = pr.pop("model"), pr.pop("prompt")
        partes.append(f"TAREA {i} · código {paso['tarea']} · {nombres[paso['tipo']]} · ~{paso['costo']} créditos")
        partes.append(f"- Herramienta: {paso['herramienta']} · modelo: {modelo}")
        if paso["tipo"] == "voz":
            partes.append(f"- Voz: {voces.get(pr.get('voice_id'), '')} (voice_id {pr.get('voice_id')}, voice_type preset, variant {pr.get('variant')})")
            partes.append(f"- Texto exacto: {prompt}")
        else:
            partes.append(f"- Parámetros: {json.dumps(pr, ensure_ascii=False)}")
            partes.append(f"- Prompt exacto: {prompt}")
        for ref in paso["subir"]:
            partes.append(f"- Adjunta la imagen «{Path(ref['archivo']).name}» como {ref['role']} (te la adjunto en este chat)")
        if paso.get("depende"):
            partes.append(f"- Usa como imagen de inicio el resultado de la tarea {paso['depende']}")
        partes.append("")
    return "\n".join(partes)


def _cli():
    accion = sys.argv[1] if len(sys.argv) > 1 else "pendientes"
    if accion == "pendientes":
        salida = []
        for ped in pedidos():
            if ped["estado"] in ("listo", "vacio"):
                continue
            # recalcula por si el proyecto cambió desde que se creó el pedido
            ped = crear_pedido(ped["pid"], ped.get("via"))
            if ped["estado"] != "listo":
                salida.append({"pid": ped["pid"], "nombre": ped["nombre"], "via": ped["via"],
                               "costo_pendiente": ped["costo"], "pasos": instrucciones(ped)})
        print(json.dumps(salida, ensure_ascii=False, indent=2))
    elif accion == "pedido":
        print(json.dumps(crear_pedido(sys.argv[2]), ensure_ascii=False, indent=2))
    elif accion == "proceso":
        _actualizar(sys.argv[2], sys.argv[3], estado="en_proceso", job_id=sys.argv[4])
        print("ok")
    elif accion == "marcar":
        print(marcar(sys.argv[2], sys.argv[3], sys.argv[4]))
    elif accion == "error":
        _actualizar(sys.argv[2], sys.argv[3], estado="error", error=" ".join(sys.argv[4:]))
        print("ok")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    _cli()
