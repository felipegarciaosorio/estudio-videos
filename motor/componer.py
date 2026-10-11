"""Compositor: proyecto.json -> MP4 final.

Uso: python -m motor.componer proyectos/<id>

proyecto.json:
{
  "nombre": "Reseñas Sabor & Tradición",
  "marca": "sabor-y-tradicion",
  "formato": "9:16",                       "9:16" | "1:1" | "16:9"
  "guion": {"texto": "...", "say_as": {"$99.900": "noventa y nueve mil novecientos pesos"}},
  "voz": {"voz": "es-CO-GonzaloNeural", "velocidad": "+12%"}   o {"archivo": "audio/voz.mp3"}
  "inicio_voz": 0.15,
  "escenas": [
    {"tipo": "imagen", "hasta": "@Con Aurela", "params": {...}},     termina cuando la voz dice la frase
    {"tipo": "video", "duracion": 2.5, "params": {...}},
    {"tipo": "cierre", "duracion": 2.8}
  ],
  "capas": {"subtitulos": true, "logo": true,
            "etiqueta": {"desde": "@$99.900", "dur": 1.5, "grande": "$99.900", "pequeno": "PAGO ÚNICO"}},
  "audio": {"musica": "sintetica", "sfx_cortes": true},
  "ia": {"motor": "higgsfield", "voz": {"voice_id": "...", "tempo": 1.1}}   piezas IA, ver motor/ia.py
}
"""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

from . import audio, ia, subtitulos, voz
from .base import FFMPEG, FORMATOS, FPS, RAIZ, duracion, run
from .escenas import Ctx, modulo, t_de
from .marca import Marca

SIN_LOGO = {"telefono", "captura", "cierre"}  # escenas donde el logo de arriba estorba


class Progreso:
    def __init__(self, carpeta):
        self.archivo = Path(carpeta) / "estado.json"

    def __call__(self, etapa, pct, mensaje="", **extra):
        self.archivo.write_text(json.dumps({"etapa": etapa, "pct": round(pct), "mensaje": mensaje, "ts": time.time(), **extra}, ensure_ascii=False))


def _tiempos(escenas, palabras, fin_voz):
    """Inicio y duración de cada escena, alineados a frames."""
    t, salida = 0.0, []
    for i, e in enumerate(escenas):
        if "duracion" in e:
            fin = t + float(e["duracion"])
        elif e.get("hasta") == "fin_voz" or (not e.get("hasta") and i == len(escenas) - 1):
            fin = max(fin_voz + 0.3 + float(e.get("extra", 0)), t + 1.0)
        elif e.get("hasta"):
            frase = e["hasta"].lstrip("@")
            fin = voz.buscar_frase(palabras, frase)
            if fin is None:
                raise ValueError(f"Escena {i + 1}: la frase «{frase}» no está en el guion")
            if fin <= t:
                raise ValueError(f"Escena {i + 1}: «{frase}» se dice antes de que la escena empiece")
        else:
            # sin duración ni frase: hasta donde empiece la siguiente con frase, o 3 s
            fin = t + 3.0
        f0, f1 = round(t * FPS), round(fin * FPS)
        salida.append((f0 / FPS, (f1 - f0) / FPS))
        t = f1 / FPS
    return salida


def _version_codigo():
    """Huella del código de las escenas: si cambia un renderer, la caché se invalida."""
    archivos = sorted((RAIZ / "motor").rglob("*.py")) + [RAIZ / "motor" / "blender" / "escena.py"]
    return hashlib.md5(b"".join(f.read_bytes() for f in archivos)).hexdigest()[:8]


def _hash_escena(e, dur, w, h, marca, extra=""):
    datos = json.dumps({"e": e, "dur": dur, "w": w, "h": h, "m": marca.datos, "v": _version_codigo(), "x": extra},
                       sort_keys=True, ensure_ascii=False)
    return hashlib.md5(datos.encode()).hexdigest()[:12]


def componer(dir_proyecto, progreso=None):
    dir_proyecto = Path(dir_proyecto).resolve()
    progreso = progreso or Progreso(dir_proyecto)
    p = json.loads((dir_proyecto / "proyecto.json").read_text())
    marca = Marca(p["marca"])
    w, h = FORMATOS[p.get("formato", "9:16")]
    trabajo = dir_proyecto / "trabajo"
    trabajo.mkdir(exist_ok=True)

    # 1. Voz y tiempos por palabra
    progreso("voz", 3, "Preparando la voz")
    palabras, mp3, inicio = [], None, float(p.get("inicio_voz", 0.15))
    guion = p.get("guion") or {}
    borrador = [t for t in ia.tareas(dir_proyecto, p) if not t["listo"]]
    if guion.get("texto"):
        cfg_voz = dict(p.get("voz") or {})
        voz_ia = ia.voz_lista(dir_proyecto, p, trabajo) if ia.voz_cfg(p) else None
        if voz_ia:
            cfg_voz = {"archivo": str(voz_ia)}
        elif cfg_voz.get("archivo"):
            cfg_voz["archivo"] = str((dir_proyecto / cfg_voz["archivo"]).resolve())
        else:
            cfg_voz = {**marca.voz, **cfg_voz}
        mp3, crudas = voz.preparar(guion, cfg_voz, trabajo, marca)
        palabras = voz.alinear(guion, crudas, offset=inicio, marca=marca)
    fin_voz = (duracion(mp3) + inicio) if mp3 else 0.0

    # 2. Duración de cada escena
    escenas = p["escenas"]
    tiempos = _tiempos(escenas, palabras, fin_voz)
    total = sum(d for _, d in tiempos)

    # 3. Render de escenas (con caché)
    segmentos, eventos, ambientes = [], [], []
    for i, (e, (t0, dur)) in enumerate(zip(escenas, tiempos)):
        progreso("escenas", 8 + 62 * i / len(escenas), f"Escena {i + 1} de {len(escenas)}: {e['tipo']}")
        seg = trabajo / f"seg-{i:02d}-{_hash_escena(e, dur, w, h, marca, ia.huella(e, dir_proyecto, p))}.mp4"
        meta = seg.with_suffix(".json")
        ctx = Ctx(w=w, h=h, marca=marca, proyecto=dir_proyecto, dur=dur, t0=t0, palabras=palabras, trabajo=trabajo)
        if seg.exists() and meta.exists():
            evs = json.loads(meta.read_text())
        else:
            evs = modulo(e["tipo"]).render(e.get("params", {}), ctx, seg)
            meta.write_text(json.dumps(evs))
        for ev in evs:
            if "ambiente" in ev:
                ambientes.append({"archivo": ev["ambiente"], "desde": ev.get("desde", 0), "t": t0, "dur": ev["dur"], "vol": ev["vol"]})
            else:
                eventos.append({**ev, "t": ev["t"] + t0})
        if i > 0 and (p.get("audio") or {}).get("sfx_cortes", True):
            eventos.append({"sfx": "whoosh", "t": t0 - 0.25})
        segmentos.append(seg)

    # 4. Unir escenas
    progreso("montaje", 72, "Uniendo escenas")
    lista = trabajo / "lista.txt"
    lista.write_text("".join(f"file '{s}'\n" for s in segmentos))
    base = trabajo / "base.mp4"
    run([FFMPEG, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
         "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), str(base)])

    # 5. Capa de subtítulos, logo y etiqueta
    progreso("subtitulos", 78, "Subtítulos y marca")
    capas = dict(p.get("capas") or {})
    ocultar = list(capas.get("ocultar_logo", []))
    for e, (t0, dur) in zip(escenas, tiempos):
        if e["tipo"] in SIN_LOGO or e.get("sin_logo"):
            ocultar.append([t0, t0 + dur])
    capas["ocultar_logo"] = ocultar
    if capas.get("etiqueta"):
        et = dict(capas["etiqueta"])
        ctx_global = Ctx(w=w, h=h, marca=marca, proyecto=dir_proyecto, dur=total, palabras=palabras)
        et["desde"] = t_de(et.get("desde", 0), ctx_global)
        et["hasta"] = et["desde"] + float(et.get("dur", 1.5))
        capas["etiqueta"] = et
    overlay = trabajo / "capa.mov"
    subtitulos.renderizar(marca, w, h, palabras, capas, total, overlay)

    # 6. Audio
    progreso("audio", 90, "Mezclando voz, música y efectos")
    cfg_audio = p.get("audio") or {}
    musica = audio.pista_musica(cfg_audio.get("musica", "sintetica"), total, trabajo)
    mezcla = trabajo / "audio.wav"
    audio.mezclar(total, mezcla, voz=mp3, voz_inicio=inicio, musica=musica, vol_musica=cfg_audio.get("volumen_musica", 1.0),
                  eventos=eventos, ambientes=ambientes)

    # 7. Final
    progreso("final", 95, "Exportando")
    salidas = RAIZ / "salidas"
    salidas.mkdir(exist_ok=True)
    final = salidas / f"{dir_proyecto.name}.mp4"
    run([FFMPEG, "-loglevel", "error", "-y", "-i", str(base), "-i", str(overlay), "-i", str(mezcla),
         "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]", "-map", "[v]", "-map", "2:a",
         "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(final)])
    if borrador:
        faltan = ", ".join(sorted({t["tipo"] for t in borrador}))
        progreso("listo", 100, f"Borrador listo: faltan piezas IA ({faltan})", salida=str(final), duracion=round(total, 2),
                 borrador=len(borrador))
    else:
        progreso("listo", 100, "Video listo", salida=str(final), duracion=round(total, 2))
    return final


if __name__ == "__main__":
    try:
        print(componer(sys.argv[1]))
    except Exception as exc:  # deja el error legible para el panel
        Progreso(Path(sys.argv[1]))("error", 0, str(exc)[:1500])
        raise
