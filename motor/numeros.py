"""Números a palabras en español, para que la voz lea bien precios y porcentajes.

    "$26.000" -> "veintiséis mil pesos"     "25%" -> "veinticinco por ciento"
"""
import re

UNIDADES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez",
            "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve",
            "veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis",
            "veintisiete", "veintiocho", "veintinueve"]
DECENAS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
CENTENAS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos",
            6: "seiscientos", 7: "setecientos", 8: "ochocientos", 9: "novecientos"}


def _hasta_999(n):
    if n == 100:
        return "cien"
    c, resto = divmod(n, 100)
    partes = [CENTENAS[c]] if c else []
    if resto < 30:
        if resto or not partes:
            partes.append(UNIDADES[resto])
    else:
        d, u = divmod(resto, 10)
        partes.append(DECENAS[d] + (f" y {UNIDADES[u]}" if u else ""))
    return " ".join(partes)


def _apocope(txt):
    """Delante de "mil", "millones" o "pesos": uno -> un, veintiuno -> veintiún."""
    if txt.endswith("veintiuno"):
        return txt[:-9] + "veintiún"
    if txt.endswith("uno"):
        return txt[:-3] + "un"
    return txt


def palabras(n):
    n = int(n)
    if n < 1000:
        return _hasta_999(n)
    if n < 1_000_000:
        miles, resto = divmod(n, 1000)
        txt = "mil" if miles == 1 else f"{_apocope(_hasta_999(miles))} mil"
        return txt + (f" {_hasta_999(resto)}" if resto else "")
    millones, resto = divmod(n, 1_000_000)
    txt = "un millón" if millones == 1 else f"{_apocope(palabras(millones))} millones"
    return txt + (f" {palabras(resto)}" if resto else "")


def leer(token):
    """Versión hablada de un token con precio o porcentaje (o None si no aplica)."""
    t = re.sub(r"^[¿¡(]+|[.,:;?!)]+$", "", token)
    m = re.fullmatch(r"\$\s?(\d{1,3}(?:\.\d{3})+|\d+)", t)
    if m:
        valor = int(m.group(1).replace(".", ""))
        txt = _apocope(palabras(valor))
        return f"{txt} {'de ' if txt.endswith(('millón', 'millones')) else ''}pesos"
    m = re.fullmatch(r"-?(\d{1,3})%", t)
    if m:
        return f"{palabras(int(m.group(1)))} por ciento"
    return None


def say_as_auto(texto):
    """{token_limpio: hablado} para todos los precios y porcentajes del guion."""
    salida = {"&": "y"} if " & " in f" {texto} " else {}
    for tok in texto.split():
        hablado = leer(tok)
        if hablado:
            salida[re.sub(r"^[¿¡(]+|[.,:;?!)]+$", "", tok)] = hablado
    return salida
