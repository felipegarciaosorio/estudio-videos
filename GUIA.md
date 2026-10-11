# Estudio de videos

Programa local para hacer videos de redes de cualquier negocio: voz neuronal, subtítulos karaoke, fotos con movimiento, clips propios, páginas web reales dentro de un celular, tarjetas y logos en 3D con Blender, ofertas, reseñas y cierre de marca.

## Arrancar

```bash
/Users/pipe/Documents/Codex/estudio-videos/iniciar.sh
```

Se abre http://localhost:8765. Para apagarlo: `Ctrl+C` en la terminal.

## Flujo

1. **Marcas.** Crea el negocio y sube:
   - El logo (PNG con fondo transparente).
   - Las fotos.
   - El diseño plano de su tarjeta, si vas a usar 3D.

   Después elige los colores, la fuente, la voz y los datos del cierre (WhatsApp, web o dirección).
2. **Nuevo video.** Elige la marca, el tipo de video y el formato (9:16, 1:1 o 16:9). Llena el formulario, pulsa **Sugerir guion** y ajústalo a tu gusto.
3. **Editor.** Cambia el guion, la voz, la música y las escenas. Pulsa **Generar video**: tarda de 30 s a 4 min (más si hay 3D) y queda listo para ver y descargar.

## Gratis o con IA (Higgsfield)
En el editor, la tarjeta **Motor** tiene dos modos:

- **Gratis:** todo se hace en tu Mac.
- **Higgsfield (IA):** tú eliges qué partes hace la IA.
  - **Voz premium** (ElevenLabs, unos 0,75 créditos). Hay una lista de voces con ▶ para escuchar una muestra.
  - **Clip de video IA:** en una escena de foto pulsa «✦ Convertir en clip IA» y escribe qué pasa, en inglés. Unos 8,75 créditos con Kling Pro.
  - **Imagen IA:** para cuando no hay buena foto (de 0,5 a 2,75 créditos).

Mientras las piezas no lleguen, «Generar video» saca un **borrador gratis** para revisar ritmo y textos. Cuando estés conforme, pulsa **Enviar pedido IA** y elige quién lo genera:

| Vía | Cómo |
|---|---|
| Claude | Dile a Claude: «procesa los pedidos IA». Usa tus créditos del plan y te muestra el costo antes de gastar. |
| ChatGPT + Higgsfield | El panel copia las instrucciones exactas. Pégalas en ChatGPT, adjunta las fotos que indica y sube cada resultado con «Subir resultado». |
| API directa | Automática cuando pongas `HF_KEY` en `.env`. Es saldo aparte y está sin probar todavía. |

Lo que ya se generó no se vuelve a pagar mientras no cambies el prompt, la foto o el modelo.

## Asistente: de una idea a un video
En la pestaña **Asistente** escribes la idea en una frase y eliges marca, formato, duración, motor y presupuesto de créditos.

- **Copiar para ChatGPT:** copia un brief que explica cómo funciona nuestro sistema. Pegas en el panel la respuesta de ChatGPT y se crea el proyecto, con avisos si algo no cuadra.
- **Enviar a Claude:** guarda la idea. Luego le dices a Claude «procesa las ideas».

La guía de prompts está en `ia/guia-prompts.md`.

## Tipos de video (plantillas)

| Plantilla | Para qué |
|---|---|
| Promo de productos o menú | Platos, productos o servicios con foto, nombre y precio |
| Oferta / descuento | Precio de antes tachado, precio nuevo, % de ahorro y urgencia |
| Reseñas / testimonios | Opiniones de clientes con estrellas sobre la foto del lugar |
| Tarjeta / identidad digital | Tarjeta en 3D, perfil real capturado de su URL, precio y cierre |
| Libre | Cualquier video: tú armas las escenas |

## Escenas disponibles

- **Foto con movimiento:** zoom y paneo. Puede llevar un rótulo con nombre y precio.
- **Clip de video:** tomas grabadas con el celular o clips de IA. Se recortan, se ajustan a la escena y pueden conservar su sonido.
- **Texto animado:** títulos, listas o una cifra grande.
- **Página web en el celular:** captura de cualquier URL. Puede tocar botones y resaltar textos (en "JSON avanzado": `tocar`, `resaltar`, `acercar`, `estrellas`).
- **Tarjeta o logo en 3D (Blender):** `tarjeta_gira`, `tarjeta_mesa` o `logo_flota`.
- **Oferta:** antes y ahora, descuento y urgencia.
- **Reseñas:** tarjetas de opinión con estrellas.
- **Capturas propias en el celular:** capturas tuyas animadas.
- **Cierre de marca:** logo, nombre, subtítulo, precio y contacto.

## Consejos

- **Duración de cada escena:** "Hasta que la voz diga" corta la escena justo cuando la voz pronuncia esa frase. Si cambias el guion, revisa que la frase siga existiendo; si no, el editor te avisa.
- **Precios y porcentajes:** escribe "$26.000" o "25%" y la voz los lee bien solos.
- **Voces:** las voces colombianas son **Gonzalo** (hombre) y **Salomé** (mujer). Usa "▶ Probar voz" antes de generar.
- **Música:** pon pistas libres de derechos (por ejemplo de YouTube Audio Library o Pixabay Music) en la carpeta `musica/`. Aparecen solas en el editor.
- **Tomas reales:** para ver qué grabar con el celular, mira `aurela/assets/grabacion/LISTA-DE-TOMAS.md`.
- **Dónde quedan los videos:** en `salidas/`. Cada proyecto guarda sus archivos en `proyectos/<id>/`.

## Para técnicos

Cada video es un `proyecto.json` (formato documentado en `motor/componer.py`). También se genera desde la terminal:

```bash
cd /Users/pipe/Documents/Codex/estudio-videos && PYTHONPATH=. .venv/bin/python -m motor.componer proyectos/<id>
```
