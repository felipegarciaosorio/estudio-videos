"""Crear, listar y duplicar proyectos (carpetas en proyectos/<id>/).

CLI: python -m motor.proyectos nuevo <plantilla> <marca> '<datos json>'"""
import json
import re
import shutil
import sys
import time
import unicodedata

from .base import RAIZ
from .marca import Marca

CARPETA = RAIZ / "proyectos"


def _slug(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "video"


def nuevo(plantilla, marca_slug, datos):
    from plantillas import modulo

    marca = Marca(marca_slug)
    proyecto = modulo(plantilla).crear(datos, marca)
    if datos.get("motor") == "higgsfield":
        from .ia import VOZ_DEFECTO

        proyecto["ia"] = {"motor": "higgsfield", "via": "claude", "voz": dict(VOZ_DEFECTO)}
    pid = f"{time.strftime('%Y%m%d-%H%M%S')}-{_slug(proyecto['nombre'])}"
    carpeta = CARPETA / pid
    carpeta.mkdir(parents=True)
    (carpeta / "proyecto.json").write_text(json.dumps(proyecto, ensure_ascii=False, indent=2))
    return pid


def cargar(pid):
    return json.loads((CARPETA / pid / "proyecto.json").read_text())


def guardar(pid, proyecto):
    (CARPETA / pid / "proyecto.json").write_text(json.dumps(proyecto, ensure_ascii=False, indent=2))


def estado(pid):
    f = CARPETA / pid / "estado.json"
    return json.loads(f.read_text()) if f.exists() else {"etapa": "nuevo", "pct": 0}


def listar():
    salida = []
    for d in sorted(CARPETA.iterdir(), reverse=True):
        if (d / "proyecto.json").exists():
            p = json.loads((d / "proyecto.json").read_text())
            video = RAIZ / "salidas" / f"{d.name}.mp4"
            salida.append({
                "id": d.name, "nombre": p.get("nombre", d.name), "marca": p.get("marca"),
                "plantilla": p.get("plantilla", "libre"), "formato": p.get("formato", "9:16"),
                "estado": estado(d.name), "video": f"/salidas/{d.name}.mp4" if video.exists() else None,
                "motor": (p.get("ia") or {}).get("motor", "gratis"),
            })
    return salida


def duplicar(pid):
    p = cargar(pid)
    p["nombre"] = f"{p.get('nombre', pid)} (copia)"
    nuevo_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{_slug(p['nombre'])}"
    destino = CARPETA / nuevo_id
    destino.mkdir(parents=True)
    for sub in ("clips", "capturas", "fotos", "audio", "ia"):
        if (CARPETA / pid / sub).exists():
            shutil.copytree(CARPETA / pid / sub, destino / sub)
    guardar(nuevo_id, p)
    return nuevo_id


if __name__ == "__main__":
    if sys.argv[1] == "nuevo":
        print(nuevo(sys.argv[2], sys.argv[3], json.loads(sys.argv[4])))
