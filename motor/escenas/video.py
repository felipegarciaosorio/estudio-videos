"""Clip de video propio (tomas de celular, clips de IA, etc.).

params:
  archivo    ruta del clip
  desde      segundo del clip donde empieza (0)
  hasta      segundo donde termina (fin del clip)
  velocidad  1.0 normal; se ajusta sola si "ajustar": true para llenar la escena
  ajustar    true: acelera o frena el tramo para que dure justo lo que la escena
  foco       [x, y] para el recorte a formato (0.5, 0.5 = centro)
  ambiente   volumen del sonido original del clip (0 = mudo)
"""
from ..base import FFMPEG, duracion, run


def render(params, ctx, salida):
    src = ctx.ruta(params["archivo"])
    total = duracion(src)
    desde = float(params.get("desde", 0))
    hasta = float(params.get("hasta", total))
    tramo = max(0.1, hasta - desde)
    vel = tramo / ctx.dur if params.get("ajustar") else float(params.get("velocidad", 1.0))
    fx, fy = params.get("foco", [0.5, 0.5])
    w, h = ctx.w, ctx.h
    vf = (
        f"trim={desde}:{hasta},setpts=(PTS-STARTPTS)/{vel},"
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h}:(iw-{w})*{fx}:(ih-{h})*{fy},setsar=1,fps=30,"
        f"tpad=stop_mode=clone:stop_duration={ctx.dur},format=yuv420p"
    )
    run([FFMPEG, "-loglevel", "error", "-y", "-i", str(src), "-vf", vf, "-an", "-t", f"{ctx.dur:.3f}",
         "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", str(salida)])
    eventos = []
    if params.get("ambiente"):
        eventos.append({"ambiente": str(src), "desde": desde, "dur": min(ctx.dur, tramo), "vol": params["ambiente"]})
    return eventos
