"""Estudio de video: servidor local del panel.

Arranque: .venv/bin/uvicorn app:app --port 8765   (o ./iniciar.sh)
Abre http://localhost:8765
"""
import asyncio
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from motor import asistente, ia  # noqa: E402
from motor import higgsfield_api  # noqa: E402
from motor import proyectos as prj  # noqa: E402
from motor.marca import Marca, listar as listar_marcas  # noqa: E402
from plantillas import catalogo, modulo  # noqa: E402

app = FastAPI(title="Estudio de video")
for carpeta in ("salidas", "marcas", "proyectos", "musica"):
    (RAIZ / carpeta).mkdir(exist_ok=True)
app.mount("/panel", StaticFiles(directory=RAIZ / "panel"), name="panel")
app.mount("/salidas", StaticFiles(directory=RAIZ / "salidas"), name="salidas")
app.mount("/archivos/marcas", StaticFiles(directory=RAIZ / "marcas"), name="marcas")
app.mount("/archivos/proyectos", StaticFiles(directory=RAIZ / "proyectos"), name="proyectos")

IMAGENES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEOS = {".mp4", ".mov", ".m4v"}

from motor.escenas.esquema import ESCENAS  # noqa: E402


def _slug(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40]


def _archivos(carpeta, exts):
    if not carpeta.exists():
        return []
    return sorted(str(p.relative_to(carpeta.parent)) for p in carpeta.iterdir() if p.suffix.lower() in exts)


# ------------------------------------------------------------------ cola de render
cola = queue.Queue()


def _trabajador():
    while True:
        pid = cola.get()
        entorno = {**os.environ, "PYTHONPATH": str(RAIZ)}
        subprocess.run([sys.executable, "-m", "motor.componer", str(RAIZ / "proyectos" / pid)], cwd=RAIZ, env=entorno,
                       capture_output=True)
        cola.task_done()


threading.Thread(target=_trabajador, daemon=True).start()

# pedidos IA por la vía API (solo si hay HF_KEY en .env)
cola_api = queue.Queue()


def _trabajador_api():
    while True:
        pid = cola_api.get()
        try:
            higgsfield_api.procesar_pedido(pid)
            if ia.resumen(ia.leer_pedido(pid))["estado"] == "listo":
                cola.put(pid)  # todo llegó: se renderiza solo
        finally:
            cola_api.task_done()


threading.Thread(target=_trabajador_api, daemon=True).start()


# ------------------------------------------------------------------ panel
@app.get("/")
def inicio():
    return FileResponse(RAIZ / "panel" / "index.html")


# ------------------------------------------------------------------ marcas
def _marca_json(slug):
    m = Marca(slug)
    return {"slug": slug, **m.datos, "fotos_disponibles": _archivos(m.dir / "fotos", IMAGENES)}


@app.get("/api/marcas")
def api_marcas():
    return [_marca_json(s) for s in listar_marcas()]


@app.post("/api/marcas")
def api_crear_marca(datos: dict):
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        raise HTTPException(400, "Falta el nombre")
    slug = _slug(nombre)
    carpeta = RAIZ / "marcas" / slug
    if carpeta.exists():
        raise HTTPException(409, "Ya existe una marca con ese nombre")
    (carpeta / "fotos").mkdir(parents=True)
    base = {"nombre": nombre, "logo_con_nombre": True, "colores": {}, "voz": {}, "cierre": {}, "fotos": []}
    (carpeta / "marca.json").write_text(json.dumps({**base, **datos}, ensure_ascii=False, indent=2))
    return _marca_json(slug)


@app.put("/api/marcas/{slug}")
def api_editar_marca(slug: str, datos: dict):
    archivo = RAIZ / "marcas" / slug / "marca.json"
    if not archivo.exists():
        raise HTTPException(404, "Marca no encontrada")
    actual = json.loads(archivo.read_text())
    datos.pop("slug", None)
    datos.pop("fotos_disponibles", None)
    actual.update(datos)
    archivo.write_text(json.dumps(actual, ensure_ascii=False, indent=2))
    return _marca_json(slug)


@app.post("/api/marcas/{slug}/archivo")
async def api_subir_marca(slug: str, tipo: str = Form(...), archivo: UploadFile = File(...)):
    carpeta = RAIZ / "marcas" / slug
    if not (carpeta / "marca.json").exists():
        raise HTTPException(404, "Marca no encontrada")
    ext = Path(archivo.filename).suffix.lower()
    if ext not in IMAGENES:
        raise HTTPException(400, "Sube una imagen (jpg, png o webp)")
    datos = json.loads((carpeta / "marca.json").read_text())
    if tipo in ("logo", "tarjeta"):
        destino = carpeta / f"{tipo}{ext}"
        datos[tipo] = destino.name
    else:
        (carpeta / "fotos").mkdir(exist_ok=True)
        destino = carpeta / "fotos" / f"{_slug(Path(archivo.filename).stem) or 'foto'}{ext}"
        rel = f"fotos/{destino.name}"
        datos["fotos"] = [*[f for f in datos.get("fotos", []) if f != rel], rel]
    destino.write_bytes(await archivo.read())
    (carpeta / "marca.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2))
    return _marca_json(slug)


# ------------------------------------------------------------------ voces
_voces_cache = []


@app.get("/api/voces")
async def api_voces():
    global _voces_cache
    if not _voces_cache:
        import edge_tts

        voces = await edge_tts.list_voices()
        _voces_cache = sorted(
            ({"id": v["ShortName"], "genero": v["Gender"], "pais": v["Locale"]} for v in voces if v["Locale"].startswith("es-")),
            key=lambda v: (v["pais"] != "es-CO", v["pais"], v["id"]),
        )
    return _voces_cache


@app.post("/api/voz/prueba")
async def api_probar_voz(datos: dict):
    import edge_tts

    texto = datos.get("texto") or "Hola, así suena esta voz para tus videos."
    voz, vel = datos.get("voz", "es-CO-GonzaloNeural"), datos.get("velocidad", "+12%")
    clave = hashlib.md5(f"{texto}|{voz}|{vel}".encode()).hexdigest()[:10]
    carpeta = RAIZ / "proyectos" / "_pruebas"
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / f"voz-{clave}.mp3"
    if not destino.exists():
        await edge_tts.Communicate(texto, voz, rate=vel).save(str(destino))
    return {"url": f"/archivos/proyectos/_pruebas/{destino.name}"}


@app.get("/api/musica")
def api_musica():
    return ["sintetica", "ninguna"] + sorted(p.name for p in (RAIZ / "musica").iterdir() if p.suffix.lower() in {".mp3", ".wav", ".m4a"})


# ------------------------------------------------------------------ plantillas y escenas
@app.get("/api/plantillas")
def api_plantillas():
    return catalogo()


@app.get("/api/escenas")
def api_escenas():
    return ESCENAS


@app.post("/api/plantillas/{pid}/guion")
def api_sugerir_guion(pid: str, datos: dict):
    return {"guion": modulo(pid).guion(datos.get("datos", {}), Marca(datos["marca"]))}


# ------------------------------------------------------------------ proyectos
@app.get("/api/proyectos")
def api_proyectos():
    return [p for p in prj.listar() if not p["id"].startswith("_")]


@app.post("/api/proyectos")
def api_crear_proyecto(datos: dict):
    try:
        pid = prj.nuevo(datos["plantilla"], datos["marca"], datos.get("datos", {}))
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    return {"id": pid}


def _carpeta(pid):
    carpeta = RAIZ / "proyectos" / pid
    if not (carpeta / "proyecto.json").exists() or ".." in pid:
        raise HTTPException(404, "Proyecto no encontrado")
    return carpeta


@app.get("/api/proyectos/{pid}")
def api_proyecto(pid: str):
    carpeta = _carpeta(pid)
    video = RAIZ / "salidas" / f"{pid}.mp4"
    return {
        "id": pid,
        "proyecto": prj.cargar(pid),
        "estado": prj.estado(pid),
        "video": f"/salidas/{pid}.mp4?v={int(video.stat().st_mtime)}" if video.exists() else None,
        "archivos": _archivos(carpeta / "fotos", IMAGENES) + _archivos(carpeta / "clips", VIDEOS | IMAGENES),
    }


@app.put("/api/proyectos/{pid}")
def api_guardar_proyecto(pid: str, proyecto: dict):
    _carpeta(pid)
    prj.guardar(pid, proyecto)
    return {"ok": True}


@app.post("/api/proyectos/{pid}/archivo")
async def api_subir_proyecto(pid: str, archivo: UploadFile = File(...)):
    carpeta = _carpeta(pid)
    ext = Path(archivo.filename).suffix.lower()
    if ext in IMAGENES:
        destino = carpeta / "fotos"
    elif ext in VIDEOS:
        destino = carpeta / "clips"
    else:
        raise HTTPException(400, "Sube una imagen o un video (jpg, png, webp, mp4, mov)")
    destino.mkdir(exist_ok=True)
    nombre = f"{_slug(Path(archivo.filename).stem) or 'archivo'}{ext}"
    (destino / nombre).write_bytes(await archivo.read())
    return {"ruta": f"{destino.name}/{nombre}"}


@app.post("/api/proyectos/{pid}/generar")
def api_generar(pid: str):
    carpeta = _carpeta(pid)
    estado = prj.estado(pid)
    # si quedó "en curso" pero hace más de 20 min que no avanza, se da por caído
    viejo = time.time() - estado.get("ts", 0) > 1200
    if estado.get("etapa") not in ("listo", "error", "nuevo") and not viejo:
        return {"ok": True, "estado": estado}
    (carpeta / "estado.json").write_text(json.dumps({"etapa": "en_cola", "pct": 0, "mensaje": "En cola"}))
    cola.put(pid)
    return {"ok": True}


@app.get("/api/proyectos/{pid}/estado")
def api_estado(pid: str):
    _carpeta(pid)
    return prj.estado(pid)


@app.post("/api/proyectos/{pid}/duplicar")
def api_duplicar(pid: str):
    _carpeta(pid)
    return {"id": prj.duplicar(pid)}


# ------------------------------------------------------------------ IA (Higgsfield)
@app.get("/api/ia/catalogo")
def api_ia_catalogo():
    return {**ia.catalogo(), "api_disponible": higgsfield_api.disponible()}


@app.get("/api/ia/guia")
def api_ia_guia():
    return {"texto": (RAIZ / "ia" / "guia-prompts.md").read_text()}


@app.get("/api/ia/pedidos")
def api_ia_pedidos():
    return ia.pedidos()


@app.get("/api/proyectos/{pid}/ia")
def api_proyecto_ia(pid: str):
    carpeta = _carpeta(pid)
    p = prj.cargar(pid)
    lista = ia.tareas(carpeta, p)
    pedido = ia.leer_pedido(pid)
    return {"tareas": lista, "costo": ia.estimar(lista), "pedido": ia.resumen(pedido) if pedido else None,
            "revision": asistente.revisar_proyecto(p)}


@app.post("/api/proyectos/{pid}/ia/pedido")
def api_crear_pedido(pid: str, datos: dict):
    _carpeta(pid)
    via = datos.get("via", "claude")
    if via == "api" and not higgsfield_api.disponible():
        raise HTTPException(400, "La vía API necesita HF_KEY en el archivo .env")
    pedido = ia.crear_pedido(pid, via)
    if via == "api" and pedido["estado"] != "listo":
        cola_api.put(pid)
    return pedido


@app.get("/api/proyectos/{pid}/ia/chatgpt")
def api_pedido_chatgpt(pid: str):
    _carpeta(pid)
    pedido = ia.leer_pedido(pid) or ia.crear_pedido(pid, "chatgpt")
    return {"texto": ia.texto_chatgpt(pedido), "archivos": sorted({r["archivo"] for p in ia.instrucciones(pedido) for r in p["subir"]})}


@app.post("/api/proyectos/{pid}/ia/resultado")
async def api_subir_resultado(pid: str, tarea: str = Form(...), archivo: UploadFile = File(...)):
    carpeta = _carpeta(pid)
    t = next((t for t in ia.tareas(carpeta) if t["id"] == tarea), None)
    if not t:
        raise HTTPException(404, "Esa pieza ya no está en el proyecto (¿cambiaste el prompt?)")
    try:
        final = ia.guardar_resultado(carpeta, t["destino"], await archivo.read(), archivo.filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if ia.leer_pedido(pid):
        ia.crear_pedido(pid)
    return {"ok": True, "archivo": str(final.relative_to(carpeta))}


@app.get("/api/ia/archivo")
def api_ia_archivo(ruta: str):
    """Sirve una referencia local (fotos de marca/proyecto) para descargarla y adjuntarla en ChatGPT."""
    f = Path(ruta).resolve()
    if not (f.is_file() and (f.is_relative_to(RAIZ / "marcas") or f.is_relative_to(RAIZ / "proyectos"))):
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(f, filename=f.name)


# ------------------------------------------------------------------ asistente (idea -> proyecto)
@app.post("/api/asistente/brief")
def api_brief(datos: dict):
    try:
        texto = asistente.brief(datos["idea"], datos["marca"], datos.get("formato", "9:16"), datos.get("duracion", 20),
                                datos.get("presupuesto", 0), datos.get("motor", "gratis"))
    except KeyError as exc:
        raise HTTPException(400, f"Falta {exc}")
    return {"brief": texto}


@app.post("/api/asistente/crear")
def api_asistente_crear(datos: dict):
    try:
        return asistente.crear(datos["respuesta"], datos["marca"], datos.get("formato", "9:16"), datos.get("motor", "gratis"),
                               datos.get("duracion"))
    except ValueError as exc:
        return {"ok": False, "errores": [str(exc)], "avisos": []}


@app.post("/api/asistente/ideas")
def api_guardar_idea(datos: dict):
    if not (datos.get("idea") and datos.get("marca")):
        raise HTTPException(400, "Escribe la idea y elige la marca")
    return asistente.guardar_idea(datos)


@app.get("/api/asistente/ideas")
def api_ideas():
    return asistente.ideas()


@app.post("/api/proyectos/{pid}/ia/revisar")
def api_revisar_escena(pid: str, datos: dict):
    """Avisos del revisor y costo de UNA escena IA (en vivo, mientras se edita)."""
    carpeta = _carpeta(pid)
    e, formato = datos.get("escena") or {}, datos.get("formato", "9:16")
    marca_dir = Marca(prj.cargar(pid)["marca"]).dir
    lista = ia.tareas_escena(e, formato, carpeta, marca_dir)
    for t in lista:
        t["listo"] = bool(ia.resultado(carpeta, t["destino"]))
    return {"avisos": asistente.revisar(e), "costo": ia.estimar(lista), "listo": bool(lista) and all(t["listo"] for t in lista),
            "tareas": [{"id": t["id"], "tipo": t["tipo"], "listo": t["listo"]} for t in lista]}
