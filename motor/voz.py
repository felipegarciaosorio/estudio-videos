"""Voz en off y tiempos por palabra.

- Voz gratis con edge-tts (voces neuronales, p. ej. es-CO-GonzaloNeural): el propio
  servicio entrega el tiempo de cada palabra.
- Audio propio (ElevenLabs, grabación): se transcribe con faster-whisper.
En ambos casos el guion (con su ortografía y "say_as") se alinea con lo dicho para
que los subtítulos y los cortes caigan en la palabra exacta."""
import asyncio
import difflib
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def norm(palabra):
    w = unicodedata.normalize("NFD", palabra.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]", "", w)


def limpiar_token(tok):
    return re.sub(r"^[¿¡\"']+|[.,:;?!\"']+$", "", tok)


def say_as(guion):
    """Precios y porcentajes se leen solos ("$26.000" -> "veintiséis mil pesos");
    "say_as" del guion manda sobre lo automático."""
    from .numeros import say_as_auto

    return {**say_as_auto(guion["texto"]), **guion.get("say_as", {})}


def texto_hablado(guion):
    """El guion tal como se debe leer: aplica say_as ("$99.900" -> palabras)."""
    say_as_ = say_as(guion)
    salida = []
    for tok in guion["texto"].split():
        clave = limpiar_token(tok)
        if clave in say_as_:
            salida.append(tok.replace(clave, say_as_[clave]))
        else:
            salida.append(tok)
    return " ".join(salida)


def _edge(texto, voz, velocidad, mp3):
    import edge_tts

    async def correr():
        c = edge_tts.Communicate(texto, voz, rate=velocidad, boundary="WordBoundary")
        palabras = []
        with open(mp3, "wb") as f:
            async for ch in c.stream():
                if ch["type"] == "audio":
                    f.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    s = ch["offset"] / 1e7
                    palabras.append({"w": ch["text"], "s": round(s, 3), "e": round(s + ch["duration"] / 1e7, 3)})
        return palabras

    return asyncio.run(correr())


def _whisper(mp3):
    from faster_whisper import WhisperModel

    # Sin initial_prompt: si se le pasa el mismo guion, Whisper se salta el comienzo del audio
    modelo = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = modelo.transcribe(str(mp3), language="es", word_timestamps=True)
    return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]


def preparar(guion, cfg_voz, carpeta):
    """Devuelve (ruta_mp3, palabras_crudas). Cachea por texto+voz en carpeta/voz-<hash>.*"""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    if cfg_voz.get("archivo"):
        mp3 = Path(cfg_voz["archivo"])
        cache = carpeta / f"palabras2-{hashlib.md5(str(mp3).encode()).hexdigest()[:10]}.json"
        if cache.exists():
            return mp3, json.loads(cache.read_text())
        palabras = _whisper(mp3)
        cache.write_text(json.dumps(palabras, ensure_ascii=False))
        return mp3, palabras
    texto = texto_hablado(guion)
    clave = hashlib.md5(f"{texto}|{cfg_voz['voz']}|{cfg_voz['velocidad']}".encode()).hexdigest()[:10]
    mp3 = carpeta / f"voz-{clave}.mp3"
    cache = carpeta / f"voz-{clave}.json"
    if mp3.exists() and cache.exists():
        return mp3, json.loads(cache.read_text())
    palabras = _edge(texto, cfg_voz["voz"], cfg_voz["velocidad"], mp3)
    cache.write_text(json.dumps(palabras, ensure_ascii=False))
    return mp3, palabras


def alinear(guion, crudas, offset=0.0, tempo=1.0):
    """Asigna tiempos a cada palabra del guion alineándolo con lo que se dijo.

    Lo que no casa (números escritos distinto, palabras juntas o partidas) se
    interpola entre vecinos."""
    reglas = {k: v.split() for k, v in say_as(guion).items()}
    tokens = guion["texto"].split()
    habladas, dueno = [], []
    for i, tok in enumerate(tokens):
        for s in reglas.get(limpiar_token(tok), [tok]):
            habladas.append(norm(s))
            dueno.append(i)
    oidas = [norm(w["w"]) for w in crudas]
    tiempos = [None] * len(habladas)
    sm = difflib.SequenceMatcher(a=habladas, b=oidas, autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            tiempos[a + k] = (crudas[b + k]["s"], crudas[b + k]["e"])
    conocidos = [i for i, t in enumerate(tiempos) if t]
    fin_total = crudas[-1]["e"] if crudas else 0.0
    for i, t in enumerate(tiempos):
        if t:
            continue
        prev = max((k for k in conocidos if k < i), default=None)
        nxt = min((k for k in conocidos if k > i), default=None)
        s0 = tiempos[prev][1] if prev is not None else 0.0
        s1 = tiempos[nxt][0] if nxt is not None else fin_total
        lo = prev if prev is not None else -1
        hi = nxt if nxt is not None else len(tiempos)
        f0, f1 = (i - lo) / (hi - lo), (i + 1 - lo) / (hi - lo)
        tiempos[i] = (s0 + (s1 - s0) * f0, s0 + (s1 - s0) * f1)
    palabras = []
    for i, tok in enumerate(tokens):
        idx = [k for k, o in enumerate(dueno) if o == i]
        palabras.append(
            {"text": tok, "s": tiempos[idx[0]][0] / tempo + offset, "e": tiempos[idx[-1]][1] / tempo + offset}
        )
    return palabras


def buscar_frase(palabras, frase):
    """Segundo en que empieza `frase` dentro del guion alineado (None si no está)."""
    objetivo = [norm(limpiar_token(t)) for t in frase.split() if norm(limpiar_token(t))]
    texto = [norm(limpiar_token(w["text"])) for w in palabras]
    for i in range(len(texto) - len(objetivo) + 1):
        if texto[i : i + len(objetivo)] == objetivo:
            return palabras[i]["s"]
    return None
