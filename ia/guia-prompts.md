# Guía de prompts del Estudio

Reglas para escribir el guion y los prompts de IA de manera que el video salga bien a la primera y no se gasten créditos en pruebas. Estas reglas las lee el asistente (Claude o ChatGPT) y el revisor del panel avisa cuando no se cumplen.

## 1. Cómo arma el video nuestro sistema
- El video es una **voz en off continua** con subtítulos karaoke. Las escenas se cortan cuando la voz dice una frase: `"hasta": "@Plato de"` termina la escena justo cuando suena "Plato de".
- El **logo** va arriba, los **subtítulos** abajo (al 75 % del alto) y el **cierre de marca** (logo, contacto y CTA) al final. Todo eso lo pone el motor. **La IA nunca debe dibujar texto, precios ni logos.**
- Las escenas **gratis** son: foto con movimiento (`imagen`, con rótulo de nombre y precio), texto animado (`texto`), oferta antes/ahora (`oferta`), reseñas (`resenas`), página web en celular (`captura`), tarjeta o logo 3D (`producto_3d`) y cierre (`cierre`).
- Las escenas **pagadas** son: `clip_ia`, un clip de video desde una foto (Kling, de 5 a 10 créditos), e `imagen_ia`, una imagen nueva (de 0,5 a 2,75 créditos). La voz premium cuesta unos 0,75 créditos por video.

## 2. Guion (voz)
- Calcula **2,6 palabras por segundo**: 15 s son unas 40 palabras, 20 s unas 50 y 30 s unas 78.
- El **gancho va en los primeros 2 segundos**: una pregunta o un dolor del cliente ("¿Tu carta sigue en papel?").
- Usa frases cortas, cada una terminada en punto. Cada escena empieza en una frase distinta.
- Escribe los precios con "$" y punto de miles ("$34.000") y los porcentajes con "%". La voz los lee bien sola.
- Cierra con una sola llamada a la acción: "Pide ya por WhatsApp", "Reserva hoy" o similar.
- Para Aurela y sus tarjetas di **"identidad digital"**, nunca "NFC".
- No uses marcas, logos ni nombres de otras empresas.

## 3. Clip IA (`clip_ia`)
- **Úsalo solo donde una foto con zoom no basta**: vapor, gente moviéndose, un brindis, la cámara recorriendo el lugar. Uno o dos clips por video suelen ser suficientes.
- **Parte siempre de una foto real** (`imagen`) del negocio o del producto. Sin foto de inicio, la IA inventa el producto.
- El prompt va **en inglés**, con menos de 60 palabras, en este orden: **sujeto, una sola acción, un movimiento de cámara, luz y estilo**.
  - Bien: "Slow push-in on a grilled steak plate with fresh salad on a rustic wooden table, gentle steam rising, warm restaurant light, shallow depth of field".
  - Mal: "El plato aparece, luego un mesero lo sirve, la cámara gira y aparece el logo con el precio".
- Movimientos de cámara que funcionan: slow push-in, dolly in/out, slow pan left/right, orbit, tilt up, static shot with subtle motion.
- Pide pocas caras y manos. Si tienen que aparecer personas, que estén de espaldas o desenfocadas.
- Duración: 5 s. Si la escena dura más, el motor ralentiza el clip.
- Modelos:
  - `kling_pro` (8,75): es el más fiel al producto.
  - `seedance_mini` (5): es el más barato; sirve para ambiente y fondos.

## 4. Imagen IA (`imagen_ia`) y keyframes
- Úsala cuando el cliente no tiene una buena foto, o para un keyframe del que luego sale un clip (`imagen_prompt` dentro de `clip_ia`).
- Pasa **referencias** (logo, tarjeta, producto, foto del lugar) para que el resultado sea fiel.
- Pide **encuadre vertical** y deja espacio libre arriba (logo) y abajo (subtítulos). Así sale: "vertical 9:16 composition, empty space at top and bottom".
- No pidas texto, letreros ni precios dentro de la imagen.
- Prueba primero con `gpt_borrador` (0,5) y usa `gpt_alta` (2,75) solo para la versión final.

## 5. Ahorro
- Primero arma el video gratis, revísalo en **borrador** (las escenas IA salen como foto con el aviso "IA pendiente") y solo después envía el pedido IA.
- Nada se paga dos veces: si no cambias el prompt, la foto ni el modelo, el resultado queda guardado.
- Respeta el presupuesto de créditos del pedido. Si no alcanza, cambia clips por fotos con movimiento.
