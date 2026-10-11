# Estudio de videos

Programa local (Mac M1, 8 GB de RAM) para producir videos cortos de redes para negocios de cualquier nicho. Es el producto de un servicio de creación de videos para clientes. Nació en `WhatsappRV_V1/estudio` y se independizó el 2026-10-11.

## Arranque
- `./iniciar.sh` abre http://localhost:8765. En Claude Code, `preview_start` con el nombre `estudio-videos`.
- Python 3.11 en `.venv` (`pip install -r requirements.txt`). Usa del sistema: ffmpeg, Node 22 (`~/.nvm/versions/node/v22.12.0`), Chrome y Blender (`/Applications/Blender.app`).
- CLI de render: `PYTHONPATH=. .venv/bin/python -m motor.componer proyectos/<id>`.

## Arquitectura
- **Video:** `proyectos/<id>/proyecto.json` (formato documentado en `motor/componer.py`). La salida va a `salidas/<id>.mp4`. Hay caché por escena con la huella del código.
- **Escenas:** `motor/escenas/<tipo>.py` con `render(params, ctx, salida) -> eventos`.
  - Los formularios del editor y del brief salen de `motor/escenas/esquema.py`.
  - Gratis: imagen, video, texto, captura, telefono, producto_3d (Blender), oferta, resenas, cierre.
  - IA: clip_ia, imagen_ia.
- **Plantillas:** `plantillas/<id>.py` exponen `INFO`, `guion()` y `crear()`.
- **Marcas:** `marcas/<slug>/marca.json` con logo, colores, fuentes, voz, cierre, fotos y tarjeta.
- **Voz gratis:** edge-tts, que da el tiempo de cada palabra. Un audio propio o de IA se transcribe con faster-whisper. `voz.alinear` empata el guion con lo dicho y los cortes `"hasta": "@frase"` caen en la palabra exacta.

## Tour virtual y profundidad
- `motor/escenas/tour.py`: recorrido por paradas (fotos). Cada parada elige modo: `plano`, `profundidad` (gratis), `ia` o `ia_paso` (Kling). Cruces con zoom y desenfoque, nombre del espacio y puntos de recorrido.
- `motor/profundidad.py`: mapa de profundidad (Depth Anything V2 Small en ONNX, `modelos/depth-anything-v2-small.onnx`, 99 MB, Apache-2.0; NO está en git: descargarlo con el comando del error) y paralaje con OpenCV. Mapas en `cache/profundidad/`.
- `motor/escenas/profundidad.py`: una sola foto con profundidad real.
- Las paradas con IA entran en `ia.tareas_escena` igual que clip_ia. Kling Omni «de foto a foto» (`kling_o3_flf`) usa `start_image` y `end_image`.

## IA (Higgsfield), ver `motor/ia.py`
- `proyecto.json` lleva `"ia": {"motor": "higgsfield", "via": "claude|chatgpt|api", "voz": {...}}`.
- Cada pieza (voz, imagen o clip) es una **tarea** con hash estable y un destino en `proyectos/<id>/ia/`. Cuando el archivo existe, la pieza está lista. Mientras tanto el render sale como **borrador** gratis (edge-tts y la foto con "IA pendiente").
- **Vía Claude** (créditos del plan, por MCP): skill `.claude/skills/pedidos-ia`. **Confirmar el gasto con el usuario antes de generar.**
- **Vía ChatGPT:** el panel copia las instrucciones exactas por tarea (`ia.texto_chatgpt`) y el usuario sube cada resultado.
- **Vía API** (`motor/higgsfield_api.py`, `HF_KEY` en `.env`): preparada pero **sin probar**. Necesita `api_id` en el catálogo. La API no tiene voces.
- Catálogo con costos en créditos: `ia/catalogo.json`.
  - Kling 3.0 Pro: 8,75 por 5 s.
  - Seedance Mini: 5.
  - GPT Image alta: 2,75.
  - Voz ElevenLabs: ~0,75.

## Asistente (idea → proyecto), ver `motor/asistente.py`
- `brief()` arma el texto que entiende ChatGPT o Claude: escenas, fotos reales, costos y la guía `ia/guia-prompts.md`. Pide un JSON exacto.
- `validar()` y `crear()` lo convierten en proyecto. `revisar()` avisa sobre prompts que gastarían créditos.
- Ideas guardadas para Claude: `ia/ideas/`. Skill `.claude/skills/idea-a-video`.

## Reglas
- Copy de Aurela: decir **"identidad digital"**, nunca "NFC".
- Sin logos ni imágenes de terceros. Refugio del Viento es un cliente real con permiso. Sabor & Tradición es ficticio.
- La IA nunca dibuja texto, precios ni logos: los pone el motor encima.
- No reenviar una generación tras un timeout. Si Kling responde con un preset, reintentar con `declined_preset_id`.
- Con poca RAM, Blender puede volverse muy lento: cerrar apps pesadas.
