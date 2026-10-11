"""Vía API directa de Higgsfield (open.higgsfield.ai): automática, saldo en USD aparte.

ESTADO: preparada pero SIN PROBAR (no hay llave todavía). Para activarla:
1. Crear la llave en open.higgsfield.ai y ponerla en .env:  HF_KEY=llave:secreto
2. En ia/catalogo.json, a cada modelo que se quiera usar ponerle:
     "api_id": "<id del modelo en la API>",            p. ej. "bytedance/seedream/v4/text-to-image"
     "api_args": {"start_image": "image_url", "image_references": "image_urls"},  cómo se llaman los campos de imagen
     "api_params": {...}                                parámetros fijos del modelo en la API
3. En el editor elegir la vía "API".

La API no tiene voces: las tareas de voz se quedan para la vía Claude (o subida manual).
"""
import os

from .base import RAIZ


def cargar_env():
    f = RAIZ / ".env"
    if f.exists():
        for linea in f.read_text().splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def disponible():
    cargar_env()
    return bool(os.getenv("HF_KEY") or (os.getenv("HF_API_KEY") and os.getenv("HF_API_SECRET")))


def _modelo_catalogo(t):
    from .ia import catalogo

    cat = catalogo()
    for m in cat["video"] + cat["imagen"]:
        if m["id"] == t.get("catalogo"):
            return m
    return None


def _primera_url(obj, exts):
    """Busca la URL del resultado dentro de la respuesta (el formato varía por modelo)."""
    if isinstance(obj, str):
        return obj if obj.startswith("http") and (not exts or obj.split("?")[0].lower().endswith(exts)) else None
    if isinstance(obj, dict):
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            u = _primera_url(v, exts)
            if u:
                return u
    return None


def ejecutar(t):
    """Corre una tarea de imagen o video y devuelve la URL del resultado."""
    import higgsfield_client as hf

    if t["tipo"] == "voz":
        raise RuntimeError("La API de Higgsfield no tiene voces: usa la vía Claude o sube el audio.")
    m = _modelo_catalogo(t)
    if not m or not m.get("api_id"):
        raise RuntimeError(f"El modelo «{t.get('catalogo')}» no tiene api_id en ia/catalogo.json.")
    args = {"prompt": t["prompt"], "aspect_ratio": t["params"].get("aspect_ratio"), **(m.get("api_params") or {})}
    if t["tipo"] == "video":
        args.setdefault("duration", t["params"].get("duration", 5))
    nombres = m.get("api_args") or {"start_image": "image_url", "image_references": "image_urls"}
    for r in t["referencias"]:
        url = hf.upload_file(r["ruta"])
        campo = nombres.get(r["rol"], "image_url")
        if campo.endswith("s"):
            args.setdefault(campo, []).append(url)
        else:
            args[campo] = url
    resultado = hf.subscribe(m["api_id"], arguments={k: v for k, v in args.items() if v is not None})
    exts = (".mp4", ".mov", ".webm") if t["tipo"] == "video" else (".png", ".jpg", ".jpeg", ".webp")
    url = _primera_url(resultado, exts) or _primera_url(resultado, ())
    if not url:
        raise RuntimeError(f"La API no devolvió una URL: {str(resultado)[:300]}")
    return url


def procesar_pedido(pid, avisar=print):
    """Ejecuta todas las tareas pendientes de imagen/video de un pedido (en orden de dependencias)."""
    from . import ia

    pedido = ia.leer_pedido(pid)
    hechas = {t["id"] for t in pedido["tareas"] if t.get("estado") == "listo"}
    for t in pedido["tareas"]:
        if t.get("estado") == "listo" or t["tipo"] == "voz":
            continue
        if t.get("depende") and t["depende"] not in hechas:
            # la referencia del clip es el keyframe que acaba de llegar
            continue
        try:
            ia._actualizar(pid, t["id"], estado="en_proceso", job_id="api")
            avisar(f"{pid}: {t['id']} en la API")
            ia.marcar(pid, t["id"], ejecutar(t))
            hechas.add(t["id"])
        except Exception as exc:  # se registra y sigue con las demás
            ia._actualizar(pid, t["id"], estado="error", error=str(exc)[:500])
