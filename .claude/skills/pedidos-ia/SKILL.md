---
name: pedidos-ia
description: Procesa los pedidos IA del Estudio (voz ElevenLabs, imágenes GPT Image y clips Kling) con el MCP de Higgsfield y los créditos del plan del usuario. Usar cuando digan "procesa los pedidos IA", "genera lo de Higgsfield" o /pedidos-ia.
---

# Procesar pedidos IA (vía Claude)

Los pedidos los crea el panel (editor → Motor Higgsfield → «Enviar pedido IA») en `ia/pedidos/<pid>.json`. Cada tarea ya trae el modelo, los parámetros, el prompt optimizado y el destino. **No cambies los prompts** salvo que el usuario lo pida.

## Pasos

1. **Ver qué falta:**
   ```bash
   PYTHONPATH=. .venv/bin/python -m motor.ia pendientes
   ```
   El comando devuelve, por pedido, una lista de `pasos`. Cada paso trae `herramienta`, `params`, `subir` (archivos locales con su `role`), `depende` y `costo`.
2. **Confirmar el gasto antes de generar.** Muestra al usuario una tabla con video, piezas y créditos, y el saldo (`balance`). Espera un sí explícito. Nunca generes sin esa confirmación.
3. **Subir las referencias** de cada paso, una sola vez por archivo:
   1. `media_upload` con el nombre del archivo.
   2. `curl -X PUT --upload-file <archivo> "<upload_url>"` con el content-type que indique.
   3. `media_confirm`.

   Usa el `media_id` como `medias: [{value, role}]`.
4. **Generar en orden:** primero las imágenes (keyframes) y después los clips que `depende`n de ellas. Para esos clips usa como `start_image` el job_id del keyframe.
   - **Voz:** `generate_audio` con `model: text2speech_v2`, `variant: elevenlabs`, `voice_type: preset`, `voice_id` y `prompt` igual al texto exacto.
   - **Imagen:** `generate_image` con `model: gpt_image_2_5`, más `quality`, `resolution`, `aspect_ratio` y `prompt`.
   - **Clip:** `generate_video` con `model` y sus params (`mode`, `sound: off`, `duration`, `aspect_ratio`).

   Justo después de enviar cada uno, marca la tarea en proceso:
   `PYTHONPATH=. .venv/bin/python -m motor.ia proceso <pid> <tarea> <job_id>`.
5. **Esperar y descargar:** usa `jobs_wait` (o `job_display`) hasta que termine. Con la URL del resultado:
   ```bash
   PYTHONPATH=. .venv/bin/python -m motor.ia marcar <pid> <tarea> "<url>"
   ```
   El comando descarga, valida con ffprobe y deja la pieza en `proyectos/<pid>/ia/`. Si un job falla:
   `python -m motor.ia error <pid> <tarea> "<motivo>"`.
6. **Renderizar** cuando el pedido quede completo:
   - Si el panel está abierto: `curl -X POST localhost:8765/api/proyectos/<pid>/generar`.
   - Si no: `PYTHONPATH=. .venv/bin/python -m motor.componer proyectos/<pid>`.

   Revisa el resultado con una hoja de contacto y avisa al usuario.

## Cuidados (aprendidos con los reels)
- Si `generate_video` responde con una recomendación de preset en vez de generar, reintenta con `declined_preset_id`.
- Si hay un timeout de red, **no reenvíes**: el job pudo quedar creado. Revisa con `show_generations` o el `job_id`.
- Kling: `sound: "off"` (el audio lo pone nuestro motor) y una sola acción por clip.
- No uses `use_unlim` salvo que el usuario lo pida.

## Refrescar el catálogo (voces, modelos y costos)
Si el usuario pide más voces o modelos:
- Usa `list_voices`, `models_explore` y `get_cost: true` (sin gastar) para cada configuración.
- Actualiza `ia/catalogo.json` con el mismo formato (`voces[]`, `video[]` con `costo_5s`, `imagen[]` con `costo`).
- Mantén los `id` existentes para no romper proyectos.
