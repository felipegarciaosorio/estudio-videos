"""Arma los dos proyectos del tutorial «Completa tu identidad digital» a partir
de las capturas (capturar.mjs) y un solo guion.

Uso (desde la raíz del Estudio):
  .venv/bin/python proyectos/20261012-tutorial-identidad-16x9/tools/armar.py

Escribe proyecto.json en el proyecto 16x9 (escenas «navegador», capturas de
escritorio) y en el 9x16 (escenas «telefono», capturas de celular). Mismo
guion, misma voz y mismos cortes en los dos.
"""
import json
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
RAIZ = AQUI.parent.parent
P169 = AQUI
P916 = AQUI.parent / "20261012-tutorial-identidad-9x16"

GUION = (
    "Tu identidad digital, lista en cinco pasos. Te muestro el camino. "
    "Entra a tu tarjeta en aurelasoluciones.com. Arriba verás la lista de lo que te falta. "
    "Paso uno: quién eres. En Identidad sube tu logo, escribe el nombre de tu negocio, "
    "a qué te dedicas y una presentación corta. "
    "Paso dos: tu contacto. Pon tu número de WhatsApp, el mensaje con el que te van a escribir "
    "y tus redes. Luego guarda los cambios. "
    "Paso tres: tus servicios. Elige tu tipo de negocio, crea una categoría "
    "y agrega cada servicio con su precio. "
    "Paso cuatro: tus fotos. Sube una portada y las fotos de tu negocio. "
    "Si quieres, suma también tus horarios, la ubicación, testimonios y preguntas frecuentes. "
    "Paso cinco: publica. Mientras no publiques, solo tú ves los cambios. "
    "Y listo: tu tarjeta está completa. "
    "¿Dudas? El botón Ayuda te acompaña en cada sección. "
    "Crea tu identidad digital con Aurela."
)
SAY_AS = {"aurelasoluciones.com": "aurela soluciones punto com"}
LISTA = ["Quién eres", "Tu contacto", "Tus servicios", "Tus fotos", "Publica"]
URL = "aurelasoluciones.com/nfc"


def mas(t, d):
    """Corre un tiempo: número o "@frase(+x)"."""
    if isinstance(t, (int, float)):
        return max(0.0, round(t + d, 3))
    m = re.match(r"^(@.*?)\s*([+-]\d+(?:\.\d+)?)?$", t)
    off = round(float(m.group(2) or 0) + d, 3)
    return m.group(1) if off == 0 else f"{m.group(1)}{off:+g}"


class Capturas:
    def __init__(self, carpeta, rel):
        self.m = json.loads((carpeta / "manifest.json").read_text())
        self.rel = rel  # ruta de la carpeta vista desde el proyecto
        self.por_nombre = {c["nombre"]: c for c in self.m["capturas"]}

    def img(self, nombre):
        return f"{self.rel}/{self.por_nombre[nombre]['img']}"

    def tipeo(self, prefijo):
        caps = [c for c in self.m["capturas"] if re.fullmatch(rf"{re.escape(prefijo)}-\d\d", c["nombre"])]
        return [f"{self.rel}/{c['img']}" for c in caps]

    def toque(self, nombre):
        return self.por_nombre[nombre].get("toque")

    def foco(self, nombre):
        c = self.por_nombre.get(nombre) or self.por_nombre.get(f"{nombre}-00")
        return c.get("foco")


def escena(tipo_pantalla, caps, ops, hasta, paso=None, zoom_campo=1.6):
    """ops: lista de
      ("img", t, nombre)                       cambia de captura
      ("tipeo", t, hasta, prefijo)             tipeo repartido
      ("tap", t, nombre)                       toque en el punto guardado en esa captura
      ("zoom", t, nombre | None, s)            acerca al campo de esa captura (None = vista completa)
    """
    css_w, css_h = caps.m["W"], caps.m["H"]
    estados, toques, zoom = [], [], [{"t": 0, "s": 1.0, "cx": css_w / 2, "cy": css_h / 2}]
    for op in ops:
        if op[0] == "img":
            estados.append({"t": op[1], "img": caps.img(op[2])})
        elif op[0] == "tipeo":
            estados.append({"t": op[1], "hasta": op[2], "imgs": caps.tipeo(op[3])})
        elif op[0] == "tap":
            p = caps.toque(op[2])
            if p:
                toques.append({"t": op[1], "x": round(p["x"]), "y": round(p["y"])})
        elif op[0] == "zoom":
            _, t, nombre, s = op
            if nombre:
                r = caps.foco(nombre) or caps.toque(nombre)
                cx, cy = (r["x"] + r.get("w", 0) / 2, r["y"] + r.get("h", 0) / 2)
            else:
                cx, cy, s = css_w / 2, css_h / 2, 1.0
            previo = dict(zoom[-1])
            previo["t"] = mas(t, -0.45)
            zoom += [previo, {"t": t, "s": s, "cx": round(cx), "cy": round(cy)}]
    params = {"estados": estados, "toques": toques}
    if len(zoom) > 1:
        params["zoom"] = zoom
    if tipo_pantalla == "navegador":
        params.update({"css": [css_w, css_h], "url": URL})
    if paso:
        params["paso"] = paso
    return {"tipo": tipo_pantalla, "hasta": hasta, "params": params}


def armar(movil):
    if movil:
        caps = Capturas(P169 / "capturas" / "movil", "../20261012-tutorial-identidad-16x9/capturas/movil")
        pantalla, zc = "telefono", 1.25
    else:
        caps = Capturas(P169 / "capturas" / "escritorio", "capturas/escritorio")
        pantalla, zc = "navegador", 1.7
    publico = Capturas(P169 / "capturas" / "movil", ("../20261012-tutorial-identidad-16x9/capturas/movil" if movil else "capturas/movil"))
    paso = lambda n, titulo, **kw: {"n": n, "titulo": titulo, "lista": LISTA, **kw}
    E = lambda ops, hasta, p=None: escena(pantalla, caps, ops, hasta, p, zc)

    escenas = [
        {"tipo": "texto", "hasta": "@Entra a tu tarjeta", "params": {
            "lineas": ["TU IDENTIDAD", "DIGITAL", "EN 5 PASOS"], "resaltar": ["5 PASOS"],
            "fondo": "marca:fotos/tarjeta-mesa.png"}},
        E([("img", 0, "inicio"), ("zoom", "@Arriba verás", "inicio", 1.25 if not movil else 1.0)],
          "@Paso uno", paso(0, "Completa tu tarjeta", etiqueta="EMPIEZA AQUÍ", actual=0)),
        E([("img", 0, "inicio"), ("tap", 0.35, "identidad"), ("img", 0.6, "identidad"),
           ("img", "@sube tu logo-0.3", "logo-antes"), ("zoom", "@sube tu logo-0.3", "logo-antes", zc),
           ("tap", "@sube tu logo+0.3", "logo-antes"), ("img", "@sube tu logo+0.6", "logo-despues"),
           ("zoom", "@escribe el nombre", "nombre", zc), ("tipeo", "@escribe el nombre", "@a qué te dedicas", "nombre"),
           ("zoom", "@a qué te dedicas", "frase", zc), ("tipeo", "@a qué te dedicas", "@y una presentación", "frase"),
           ("zoom", "@y una presentación", "bio", zc), ("tipeo", "@y una presentación", "fin", "bio")],
          "@Paso dos", paso(1, "Quién eres")),
        E([("img", 0, "whatsapp-00"), ("zoom", 0.01, "whatsapp", zc),
           ("tipeo", "@Pon tu número", "@el mensaje con", "whatsapp"),
           ("zoom", "@el mensaje con", "mensaje", zc), ("tipeo", "@el mensaje con", "@y tus redes", "mensaje"),
           ("zoom", "@y tus redes", "instagram", zc), ("tipeo", "@y tus redes", "@Luego guarda", "instagram"),
           ("img", "@Luego guarda", "guardar-identidad-antes"),
           ("zoom", "@Luego guarda", "guardar-identidad-antes", 1.35 if not movil else 1.0),
           ("tap", "@guarda los cambios", "guardar-identidad-antes"), ("img", "@guarda los cambios+0.25", "guardado-identidad")],
          "@Paso tres", paso(2, "Tu contacto")),
        E([("img", 0, "guardado-identidad"), ("tap", 0.35, "servicios"), ("img", 0.6, "servicios"),
           ("img", "@Elige tu tipo-0.4", "tipo-antes"), ("zoom", "@Elige tu tipo-0.2", "tipo-antes", 1.45 if not movil else 1.0),
           ("tap", "@Elige tu tipo", "tipo-antes"), ("img", "@Elige tu tipo+0.25", "tipo-menu"),
           ("tap", "@Elige tu tipo+1.0", "tipo-despues"), ("img", "@Elige tu tipo+1.25", "tipo-despues"),
           ("img", "@crea una categoría-0.4", "categoria-antes"),
           ("tap", "@crea una categoría", "categoria-antes"), ("img", "@crea una categoría+0.25", "categoria"),
           ("zoom", "@agrega cada servicio", "servicio1-nombre", zc),
           ("tipeo", "@agrega cada servicio", "@con su precio", "servicio1-nombre"),
           ("img", "@con su precio", "servicio1-precio-00"),
           ("tipeo", "@con su precio", "@con su precio+0.8", "servicio1-precio"),
           ("img", "@con su precio+0.8", "agregar-antes"),
           ("tap", "@con su precio+0.9", "agregar-antes"), ("img", "@con su precio+1.15", "servicio1-agregado"),
           ("zoom", "@con su precio+1.6", None, 1.0), ("img", "@con su precio+1.7", "servicios-lista")],
          "@Paso cuatro", paso(3, "Tus servicios")),
        E([("img", 0, "guardado-servicios"), ("tap", 0.35, "fotos"), ("img", 0.6, "fotos"),
           ("img", "@Sube una portada+0.4", "fotos-portada"), ("img", "@las fotos de tu negocio+0.4", "fotos-galeria"),
           ("tap", "@suma también-0.3", "horarios"), ("img", "@suma también", "horarios")],
          "@Paso cinco", paso(4, "Tus fotos")),
        E([("img", 0, "horarios"), ("img", "@publica-0.3", "publicar-antes"),
           ("zoom", "@publica", "publicar-antes", 1.5 if not movil else 1.2),
           ("tap", "@publica+0.3", "publicar-antes"), ("img", "@publica+0.55", "publicado"),
           ("zoom", "@Mientras no publiques+0.8", None, 1.0),
           ("tap", "@Y listo-0.3", "lista-completa"), ("img", "@Y listo", "lista-completa")],
          "@Tu tarjeta está", paso(5, "Publica")),
        {"tipo": "telefono", "hasta": "@Dudas", "params": {
            "estados": [{"t": 0, "img": publico.img("publico-arriba")}],
            "zoom": [{"t": 0, "s": 1.0, "cx": 195, "cy": 422}, {"t": "fin", "s": 1.08, "cx": 195, "cy": 360}],
            "fondo": "marca:fotos/tarjeta-mesa.png"}},
        E([("img", 0, "ayuda"), ("zoom", 0.3, "ayuda", 1.9 if not movil else 1.3), ("tap", "@El botón Ayuda+0.2", "ayuda")],
          "@Crea tu identidad"),
        {"tipo": "cierre", "hasta": "fin_voz", "extra": 1.2, "params": {"subtitulo": "IDENTIDAD DIGITAL"}},
    ]
    capas = {"subtitulos": True, "logo": True}
    if not movil:
        capas.update({"altura_subtitulos": 0.885, "escala_subtitulos": 0.8})
    return {
        "nombre": f"Tutorial: completa tu identidad digital ({'9:16' if movil else '16:9'})",
        "marca": "aurela",
        "formato": "9:16" if movil else "16:9",
        "guion": {"texto": GUION, "say_as": SAY_AS},
        # Borrador mientras falta la voz IA de Andre (edge-tts da 403 desde 2026-10-12):
        # voz del Mac, `say -v "Eddy (Spanish (Mexico))"`, ver audio/borrador.txt.
        "voz": {"archivo": "audio/borrador.mp3" if not movil else "../20261012-tutorial-identidad-16x9/audio/borrador.mp3"},
        "escenas": escenas,
        "capas": capas,
        "audio": {"musica": "sintetica", "volumen_musica": 0.6, "sfx_cortes": True},
        "ia": {"motor": "higgsfield", "via": "claude", "voz": {"voice_id": "f1e8226e-2248-4d5f-b43c-0a79e9949dbf", "nombre": "Andre"}},
    }


if __name__ == "__main__":
    P916.mkdir(exist_ok=True)
    for movil, carpeta in [(False, P169), (True, P916)]:
        (carpeta / "proyecto.json").write_text(json.dumps(armar(movil), ensure_ascii=False, indent=1))
        print("escrito", carpeta / "proyecto.json")
