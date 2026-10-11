---
name: idea-a-video
description: Convierte las ideas guardadas en el Asistente del Estudio (o una idea dicha en el chat) en proyectos con guion, escenas y prompts optimizados. Usar cuando digan "procesa las ideas", "hazme un video de..." o /idea-a-video.
---

# Idea → proyecto del Estudio

1. **Ideas pendientes:**
   ```bash
   PYTHONPATH=. .venv/bin/python -m motor.asistente ideas
   ```
   Si el usuario da la idea en el chat, guárdala primero con `POST /api/asistente/ideas` (`idea`, `marca`, `formato`, `duracion`, `motor`, `presupuesto`) o con `asistente.guardar_idea`.
2. **Brief del sistema:**
   ```bash
   PYTHONPATH=. .venv/bin/python -m motor.asistente brief <idea_id>
   ```
   Léelo completo. Trae las escenas, las fotos reales de la marca, los costos, el presupuesto y la guía `ia/guia-prompts.md`.
3. **Escribir la respuesta** como lo haría el director creativo:
   - Un JSON con `nombre`, `guion`, `escenas` y `notas`, en un archivo temporal del scratchpad.
   - El gancho va en los primeros 2 s, a 2,6 palabras por segundo.
   - Escenas IA solo donde aporten y dentro del presupuesto. Los prompts de clip van en inglés: una acción, un movimiento de cámara y siempre una foto de inicio.
   - Para Aurela di "identidad digital", nunca NFC.
4. **Crear y validar:**
   ```bash
   PYTHONPATH=. .venv/bin/python -m motor.asistente crear <idea_id> <respuesta.json>
   ```
   Si devuelve errores, corrige y repite. Revisa también los avisos del revisor.
5. **Borrador gratis:**
   ```bash
   PYTHONPATH=. .venv/bin/python -m motor.componer proyectos/<id>
   ```
   Mira la hoja de contacto y muéstrale al usuario el borrador y el costo IA pendiente. Después ofrece procesar el pedido con el skill `pedidos-ia`.
