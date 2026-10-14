# Estudio de videos

Programa local para producir videos cortos de redes (9:16, 1:1 y 16:9) para negocios de cualquier nicho. Se escribe un guion y el estudio arma el video con:

- voz y subtítulos karaoke sincronizados palabra por palabra;
- fotos con movimiento o con profundidad real, y clips propios;
- páginas web reales dentro de un celular o de un navegador;
- tarjetas y logos en 3D con Blender;
- ofertas, reseñas, tours virtuales y un cierre de marca.

Todo corre en el Mac y es gratis. La IA (Higgsfield: voz ElevenLabs, imágenes GPT Image y clips Kling o Seedance) es opcional y se pide pieza por pieza.

> Guía de uso del panel, paso a paso: [GUIA.md](GUIA.md).

## Requisitos

Probado en un Mac M1 con 8 GB de RAM.

| Herramienta | Para qué |
|---|---|
| Python 3.11 | Motor y panel (FastAPI) |
| ffmpeg | Render y mezcla de audio |
| Node 22 y Google Chrome | Capturas de páginas web |
| Blender (`/Applications/Blender.app`) | Escenas 3D (opcional) |

## Instalación

En un Mac nuevo, con [Homebrew](https://brew.sh):

```bash
brew install python@3.11 ffmpeg node@22
```

```bash
git clone https://github.com/felipegarciaosorio/estudio-videos.git && cd estudio-videos
```

```bash
python3.11 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

Para usar el modo de profundidad (escenas `profundidad` y paradas del tour), descarga el modelo, que no está en git (99 MB, Apache-2.0):

```bash
mkdir -p modelos && curl -L -o modelos/depth-anything-v2-small.onnx https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx
```

Para la vía API de Higgsfield, copia `.env.example` a `.env` y pon tu `HF_KEY`. Es opcional y todavía está sin probar.

## Uso

Para abrir el panel en http://localhost:8765:

```bash
./iniciar.sh
```

Para renderizar un proyecto desde la terminal (el MP4 queda en `salidas/<id>.mp4`):

```bash
PYTHONPATH=. .venv/bin/python -m motor.componer proyectos/<id>
```

## Cómo está armado

```
app.py              API y servidor del panel (FastAPI)
panel/              Interfaz web (HTML, CSS y JS sin build)
motor/
  componer.py       proyecto.json → MP4 (formato documentado al inicio del archivo)
  escenas/          Un módulo por tipo de escena: render(params, ctx, salida) -> eventos
  escenas/esquema.py  Campos de cada escena para el editor y el brief
  voz.py            Voz (edge-tts o audio propio transcrito con faster-whisper) y alineación con el guion
  subtitulos.py     Subtítulos karaoke
  audio.py          Música, efectos y mezcla
  ia.py             Piezas IA como tareas con hash estable; borrador gratis mientras llegan
  asistente.py      De una idea a un proyecto (brief para ChatGPT o Claude, validación)
  profundidad.py    Mapa de profundidad (Depth Anything V2) y paralaje
  blender/          Escena 3D de Blender
plantillas/         Tipos de video: INFO, guion() y crear()
marcas/<slug>/      marca.json, logo, fotos y tarjeta de cada negocio
proyectos/<id>/     proyecto.json y los archivos de cada video (no van en git)
ia/                 Catálogo con costos, guía de prompts, diccionario de pronunciación, ideas y pedidos
sfx/                Efectos de sonido
.claude/skills/     Skills de Claude Code: pedidos-ia e idea-a-video
```

No van en git: `proyectos/` (los videos de los clientes), `salidas/`, `cache/`, `modelos/`, `ia/descargas/` y `.env`.

### Escenas

- **Gratis:** `imagen`, `video`, `texto`, `captura`, `telefono`, `navegador`, `producto_3d`, `oferta`, `resenas`, `tour`, `profundidad` y `cierre`.
- **Con IA:** `clip_ia` e `imagen_ia`. Las paradas del tour también pueden ir en modo `ia` o `ia_paso`.

Cada escena dura un tiempo fijo o va «hasta» que la voz dice una frase (`"hasta": "@frase"`); el corte cae en la palabra exacta. Cada escena se guarda en caché según sus parámetros y la huella del código, así que solo se vuelve a renderizar lo que cambió.

### IA (Higgsfield)

Cada pieza IA (voz, imagen o clip) es una tarea. Mientras su archivo no exista en `proyectos/<id>/ia/`, el video sale como borrador gratis. Hay tres vías:

- **Claude:** con los créditos del plan, vía MCP y la skill `pedidos-ia`. Confirma el costo antes de gastar.
- **ChatGPT:** el panel copia las instrucciones y el usuario sube cada resultado.
- **API directa:** con `HF_KEY` en `.env`.

Los costos en créditos están en [`ia/catalogo.json`](ia/catalogo.json). Lo ya generado no se vuelve a pagar mientras no cambie el prompt, la foto o el modelo.

## Reglas de contenido

- La IA nunca dibuja texto, precios ni logos: los pone el motor encima.
- No se usan logos ni imágenes de terceros.
- En el copy de Aurela se dice «identidad digital», nunca «NFC».

Las notas técnicas para trabajar con Claude Code están en [CLAUDE.md](CLAUDE.md).
