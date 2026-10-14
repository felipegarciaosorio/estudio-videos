"""Formularios de cada tipo de escena para el editor del panel y para el brief del
asistente (lo complejo va en "JSON avanzado"). "ia": True = escena que gasta créditos."""

ESCENAS = {
    "imagen": {"nombre": "Foto con movimiento", "campos": [
        {"id": "archivo", "etiqueta": "Foto", "tipo": "foto"},
        {"id": "zoom", "etiqueta": "Zoom inicio, fin", "tipo": "par", "defecto": [1.0, 1.1]},
        {"id": "foco", "etiqueta": "Punto de interés x, y (0-1)", "tipo": "par", "defecto": [0.5, 0.5]},
        {"id": "rotulo.titulo", "etiqueta": "Rótulo: nombre", "tipo": "texto"},
        {"id": "rotulo.precio", "etiqueta": "Rótulo: precio", "tipo": "texto"},
        {"id": "rotulo.detalle", "etiqueta": "Rótulo: detalle", "tipo": "texto"}]},
    "video": {"nombre": "Clip de video", "campos": [
        {"id": "archivo", "etiqueta": "Clip", "tipo": "video"},
        {"id": "desde", "etiqueta": "Desde (s)", "tipo": "numero"},
        {"id": "hasta", "etiqueta": "Hasta (s)", "tipo": "numero"},
        {"id": "ajustar", "etiqueta": "Ajustar velocidad a la escena", "tipo": "bool"},
        {"id": "ambiente", "etiqueta": "Volumen del sonido original (0-1)", "tipo": "numero"}]},
    "texto": {"nombre": "Texto animado", "campos": [
        {"id": "lineas", "etiqueta": "Líneas (una por renglón)", "tipo": "lineas"},
        {"id": "resaltar", "etiqueta": "Palabras resaltadas (separadas por coma)", "tipo": "lista_texto"},
        {"id": "estilo", "etiqueta": "Estilo", "tipo": "opciones", "opciones": ["titulo", "lista", "cifra"]},
        {"id": "subtexto", "etiqueta": "Subtexto", "tipo": "texto"},
        {"id": "fondo", "etiqueta": "Foto de fondo", "tipo": "foto"}]},
    "captura": {"nombre": "Página web en el celular", "campos": [
        {"id": "url", "etiqueta": "URL", "tipo": "texto"},
        {"id": "scroll_texto", "etiqueta": "Bajar hasta el título", "tipo": "texto"},
        {"id": "fondo", "etiqueta": "Foto de fondo", "tipo": "foto"}]},
    "producto_3d": {"nombre": "Tarjeta / logo en 3D (Blender)", "campos": [
        {"id": "modo", "etiqueta": "Modo", "tipo": "opciones", "opciones": ["tarjeta_gira", "tarjeta_mesa", "logo_flota"]},
        {"id": "fondo", "etiqueta": "Foto de fondo", "tipo": "foto"}]},
    "oferta": {"nombre": "Oferta (antes / ahora)", "campos": [
        {"id": "foto", "etiqueta": "Foto", "tipo": "foto"},
        {"id": "producto", "etiqueta": "Producto", "tipo": "texto"},
        {"id": "antes", "etiqueta": "Antes", "tipo": "texto"},
        {"id": "ahora", "etiqueta": "Ahora", "tipo": "texto"},
        {"id": "descuento", "etiqueta": "Descuento (ej. -25%)", "tipo": "texto"},
        {"id": "urgencia", "etiqueta": "Urgencia", "tipo": "texto"}]},
    "resenas": {"nombre": "Reseñas", "campos": [
        {"id": "titulo", "etiqueta": "Título", "tipo": "texto"},
        {"id": "fondo", "etiqueta": "Foto de fondo", "tipo": "foto"}]},
    "telefono": {"nombre": "Capturas propias en el celular", "campos": [
        {"id": "fondo", "etiqueta": "Foto de fondo", "tipo": "foto"}]},
    "navegador": {"nombre": "Capturas de escritorio en una ventana de navegador", "campos": [
        {"id": "url", "etiqueta": "Dirección que muestra la barra", "tipo": "texto"},
        {"id": "fondo", "etiqueta": "Foto de fondo", "tipo": "foto"}]},
    "clip_ia": {"nombre": "Clip de video IA (Higgsfield)", "ia": True, "campos": [
        {"id": "prompt", "etiqueta": "Qué pasa en el clip (inglés: sujeto, acción, cámara, luz)", "tipo": "area"},
        {"id": "imagen", "etiqueta": "Foto de inicio (da fidelidad al producto)", "tipo": "foto"},
        {"id": "modelo", "etiqueta": "Modelo de video", "tipo": "modelo_video"},
        {"id": "duracion_clip", "etiqueta": "Duración del clip", "tipo": "opciones", "opciones": [5, 10]},
        {"id": "imagen_prompt", "etiqueta": "Opcional: crear primero un keyframe con IA (prompt de imagen)", "tipo": "area"},
        {"id": "modelo_imagen", "etiqueta": "Modelo del keyframe", "tipo": "modelo_imagen"},
        {"id": "rotulo.titulo", "etiqueta": "Rótulo: nombre", "tipo": "texto"},
        {"id": "rotulo.precio", "etiqueta": "Rótulo: precio", "tipo": "texto"},
        {"id": "rotulo.detalle", "etiqueta": "Rótulo: detalle", "tipo": "texto"}]},
    "imagen_ia": {"nombre": "Imagen IA (Higgsfield)", "ia": True, "campos": [
        {"id": "prompt", "etiqueta": "Qué imagen crear", "tipo": "area"},
        {"id": "referencias", "etiqueta": "Fotos de referencia", "tipo": "fotos"},
        {"id": "modelo", "etiqueta": "Modelo de imagen", "tipo": "modelo_imagen"},
        {"id": "zoom", "etiqueta": "Zoom inicio, fin", "tipo": "par", "defecto": [1.0, 1.1]},
        {"id": "rotulo.titulo", "etiqueta": "Rótulo: nombre", "tipo": "texto"},
        {"id": "rotulo.precio", "etiqueta": "Rótulo: precio", "tipo": "texto"},
        {"id": "rotulo.detalle", "etiqueta": "Rótulo: detalle", "tipo": "texto"}]},
    "profundidad": {"nombre": "Foto con profundidad real (gratis)", "campos": [
        {"id": "archivo", "etiqueta": "Foto", "tipo": "foto"},
        {"id": "trayectoria", "etiqueta": "Movimiento de la cámara", "tipo": "opciones", "opciones": ["avanzar", "derecha", "izquierda", "subir", "orbita"]},
        {"id": "intensidad", "etiqueta": "Intensidad (0.5 sutil, 1 normal, 1.5 fuerte)", "tipo": "numero", "defecto": 1},
        {"id": "foco", "etiqueta": "Hacia dónde entra la cámara x, y (0-1)", "tipo": "par", "defecto": [0.5, 0.5]},
        {"id": "rotulo.titulo", "etiqueta": "Rótulo: nombre", "tipo": "texto"},
        {"id": "rotulo.precio", "etiqueta": "Rótulo: precio", "tipo": "texto"},
        {"id": "rotulo.detalle", "etiqueta": "Rótulo: detalle", "tipo": "texto"}]},
    "tour": {"nombre": "Tour virtual (recorrido con fotos)", "campos": [
        {"id": "paradas", "etiqueta": "Espacios del recorrido, en orden", "tipo": "lista", "campos": [
            {"id": "foto", "etiqueta": "Foto", "tipo": "foto"},
            {"id": "etiqueta", "etiqueta": "Nombre del espacio (TERRAZA)", "tipo": "texto"},
            {"id": "modo", "etiqueta": "Cómo se mueve", "tipo": "modo_tour", "defecto": "plano"},
            {"id": "desde", "etiqueta": "Empieza cuando la voz dice (frase) o segundo", "tipo": "texto"},
            {"id": "foco", "etiqueta": "Hacia dónde entra la cámara x, y (0-1)", "tipo": "par", "defecto": [0.5, 0.5]},
            {"id": "trayectoria", "etiqueta": "Movimiento (modo profundidad)", "tipo": "opciones", "opciones": ["avanzar", "derecha", "izquierda", "subir", "orbita"]},
            {"id": "prompt", "etiqueta": "Prompt IA, en inglés (modos IA)", "tipo": "area"},
            {"id": "modelo", "etiqueta": "Modelo IA (modos IA)", "tipo": "modelo_video", "automatico": True}]},
        {"id": "transicion", "etiqueta": "Duración del cruce entre espacios (s)", "tipo": "numero", "defecto": 0.8}]},
    "cierre": {"nombre": "Cierre de marca", "campos": [
        {"id": "subtitulo", "etiqueta": "Subtítulo", "tipo": "texto"},
        {"id": "precio", "etiqueta": "Precio", "tipo": "texto"},
        {"id": "whatsapp", "etiqueta": "WhatsApp", "tipo": "texto"},
        {"id": "url", "etiqueta": "Web / dirección", "tipo": "texto"}]},
}
