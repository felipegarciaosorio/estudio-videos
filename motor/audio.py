"""Base musical, efectos y mezcla final.

- Música: pista propia (carpeta musica/, libre de derechos) o una base sintetizada
  (pad de acordes + pulso suave) a la medida exacta del video.
- SFX: biblioteca en sfx/ (whoosh, tap, chime, tecleo, boligrafo).
- Mezcla: voz al frente, música ~15 dB abajo, limitador y fundido final."""
from pathlib import Path

from .base import FFMPEG, RAIZ, run

SFX = RAIZ / "sfx"
MUSICA = RAIZ / "musica"
VOLUMEN_SFX = {"whoosh": 0.35, "tap": 0.5, "chime": 0.7, "tecleo": 0.45, "boligrafo": 0.55}


def base_sintetica(dur, salida, bpm=110):
    """Pad de 4 acordes con "respiración" + bombo suave, de `dur` segundos."""
    tramo = dur / 4
    acordes = [
        (220, 261.63, 329.63, 392),
        (174.61, 220, 261.63, 329.63),
        (130.81, 164.81, 196, 246.94),
        (196, 246.94, 293.66, 329.63),
    ]
    suma = lambda fs: "+".join(f"sin(2*PI*{f}*t)" for f in fs)
    pad = (
        f"0.18*(if(lt(t,{tramo}),{suma(acordes[0])},if(lt(t,{2*tramo}),{suma(acordes[1])},"
        f"if(lt(t,{3*tramo}),{suma(acordes[2])},{suma(acordes[3])}))))*(0.6+0.4*sin(PI*mod(t,{tramo})/{tramo}))"
    )
    beat = 60 / bpm
    bombo = f"0.9*sin(2*PI*(48+70*exp(-mod(t,{beat})*35))*mod(t,{beat}))*exp(-mod(t,{beat})*10)"
    salida = Path(salida)
    tmp_pad, tmp_bombo = salida.with_suffix(".pad.wav"), salida.with_suffix(".bombo.wav")
    run([FFMPEG, "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"aevalsrc='{pad}':s=44100:d={dur}",
         "-af", f"lowpass=f=1500,aecho=0.8:0.7:120|260:0.35|0.25,afade=t=in:d=0.6,afade=t=out:st={max(0, dur-1.2)}:d=1.2",
         "-ac", "2", str(tmp_pad)])
    run([FFMPEG, "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"aevalsrc='{bombo}':s=44100:d={dur}",
         "-af", f"volume='if(between(t,1.5,{max(1.6, dur-1.0)}),1,0)':eval=frame,lowpass=f=180", "-ac", "2", str(tmp_bombo)])
    run([FFMPEG, "-loglevel", "error", "-y", "-i", str(tmp_pad), "-i", str(tmp_bombo),
         "-filter_complex", "[0:a]volume=0.26[a];[1:a]volume=0.4[b];[a][b]amix=inputs=2:normalize=0", str(salida)])
    tmp_pad.unlink(missing_ok=True)
    tmp_bombo.unlink(missing_ok=True)
    return salida


def mezclar(dur, salida, voz=None, voz_inicio=0.0, musica=None, vol_musica=1.0, eventos=(), ambientes=()):
    """Mezcla final.

    eventos: [{"sfx": "tap", "t": 7.9, "vol": 0.5}] efectos puntuales.
    ambientes: [{"archivo": ruta, "t": 0, "dur": 3, "vol": 1.0}] sonido de clips (p. ej. restaurante)."""
    entradas, filtros, etiquetas = [], [], []

    def entrada(ruta):
        entradas.extend(["-i", str(ruta)])
        return len(entradas) // 2 - 1

    if voz:
        i = entrada(voz)
        ms = int(voz_inicio * 1000)
        filtros.append(f"[{i}:a]adelay={ms}|{ms},aresample=44100,pan=stereo|c0=c0|c1=c0,volume=1.6[voz]")
        etiquetas.append("[voz]")
    if musica:
        i = entrada(musica)
        filtros.append(f"[{i}:a]aresample=44100,atrim=0:{dur},afade=t=out:st={max(0, dur-1.0)}:d=1.0,volume={vol_musica}[mus]")
        etiquetas.append("[mus]")
    for k, amb in enumerate(ambientes):
        i = entrada(amb["archivo"])
        ms = int(amb.get("t", 0) * 1000)
        d = amb.get("dur", 3)
        a0 = amb.get("desde", 0)
        filtros.append(
            f"[{i}:a]atrim={a0}:{a0 + d},asetpts=PTS-STARTPTS,afade=t=out:st={max(0, d-0.5)}:d=0.5,aresample=44100,"
            f"adelay={ms}|{ms},volume={amb.get('vol', 1.0)}[amb{k}]"
        )
        etiquetas.append(f"[amb{k}]")
    for k, ev in enumerate(eventos):
        archivo = SFX / f"{ev['sfx']}.wav"
        if not archivo.exists():
            continue
        i = entrada(archivo)
        ms = max(0, int(ev["t"] * 1000))
        vol = ev.get("vol", VOLUMEN_SFX.get(ev["sfx"], 0.5))
        filtros.append(f"[{i}:a]aresample=44100,adelay={ms}|{ms},volume={vol}[e{k}]")
        etiquetas.append(f"[e{k}]")
    if not etiquetas:
        run([FFMPEG, "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={dur}", str(salida)])
        return salida
    filtros.append(
        f"{''.join(etiquetas)}amix=inputs={len(etiquetas)}:normalize=0:duration=longest,"
        # -14 LUFS: el nivel que usan Instagram/TikTok/YouTube
        f"atrim=0:{dur},loudnorm=I=-14:TP=-1.0:LRA=11,aresample=44100,afade=t=out:st={max(0, dur-0.5)}:d=0.5[out]"
    )
    run([FFMPEG, "-loglevel", "error", "-y", *entradas, "-filter_complex", ";".join(filtros),
         "-map", "[out]", "-c:a", "pcm_s16le", str(salida)])
    return salida


def pista_musica(cfg, dur, carpeta):
    """Resuelve la música del proyecto: None, "sintetica" o un archivo de musica/."""
    if not cfg or cfg == "ninguna":
        return None
    if cfg == "sintetica":
        return base_sintetica(dur, Path(carpeta) / "musica-base.wav")
    ruta = MUSICA / cfg
    return ruta if ruta.exists() else None
