"""Revisor de cifras en pantalla: ningún número que no diga el guion se muestra como dato del caso.

Es un documental de casos reales: una hora, un monto o un contador en pantalla se lee como prueba.
Este revisor busca en el código de cada escena (`escenas/escenaNN.py` y sus módulos `*_eNN.py`) los
textos con cifras y comprueba que cada número esté en el guion, escrito con cifras
(«9:23», «1,217») o con letras («doce», «cuatro minutos»). Lo que no está se imprime para revisarlo
a mano. Lo genérico que se lee como ilustración (un volcado, una IP de documentación, el número de
un estándar) va en `PERMITIDAS`, con su razón.

    .venv/Scripts/python revisar_cifras.py          # todas las escenas
    .venv/Scripts/python revisar_cifras.py 6 7      # solo esas

Sale con código 1 si hay cifras sin respaldo.
"""

from __future__ import annotations

import ast
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
import guion  # noqa: E402

# Cifras genéricas aceptadas por escena, con su razón. Una cifra aquí no es dato del caso.
PERMITIDAS: dict[int, dict[str, str]] = {
    2: {"91": "volcado hexadecimal de ejemplo", "62": "volcado hexadecimal de ejemplo",
        "85": "volcado hexadecimal de ejemplo", "17": "volcado hexadecimal de ejemplo",
        "86": "volcado hexadecimal de ejemplo", "0123456789": "alfabeto de una contraseña o de un volcado",
        "2.1": "versión de la herramienta de ejemplo en la laptop del perito",
        "00000000": "dirección de memoria de ejemplo", "256": "nombre del algoritmo SHA-256",
        "0031": "nombre de archivo de ejemplo en la copia"},
    6: {"203.0.113.24": "IP del rango de documentación (RFC 5737), rotulada «número de ejemplo»",
        "8:55": "marca del eje de 6.1 (cada 5 min)", "9:25": "marca del eje de 6.1 (cada 5 min)",
        "10:20": "marca del eje de 6.3", "9:20": "9:18 más «dos minutos después» (6.1)",
        "9:43": "posición de un rótulo dentro de 9:40–9:46; no se muestra",
        "9:44": "posición de un rótulo dentro de 9:40–9:46; no se muestra"},
    7: {"8589934592": "tamaño de una memoria de 8 GB, rotulado como ejemplo",
        "1149.1": "número del estándar JTAG (IEEE 1149.1)", "8": "8 GB del mismo ejemplo",
        "24": "fecha de la nota de Engadget, en el crédito de su titular"},
}

# Textos que son código y no se ven en pantalla: archivos, colores, nombres de plano, nombres con número
# («ventana_1», «mazo2»), formatos («02d») y números sueltos (parámetros). Las marcas redondas de un
# eje de horas («8:30», «9:00») son escala, no dato.
CODIGO = re.compile(r"^[\w\-./\\]+\.(png|jpg|jpeg|wav|mp3|mp4|ttf|otf|json|py|npz|exr|hdr)$|^#|^e\d\d_|^f_"
                    r"|^\d+(\.\d+)?$|^[A-Za-z_]+\d+$|^\d*[dfxX]$|^\d{1,2}:(00|30)$|^[0-9a-f]{8,}$", re.I)
NUMERO = re.compile(r"\d+(?:[.,:]\d+)*(?:[  ]\d{3})*")


def _plano(texto: str) -> str:
    """Minúsculas, sin tildes ni puntuación: «un millón;» -> «un millon»."""
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w:.,]+|(?<!\d)[.,]|[.,](?!\d)", " ", t).split())


def _normal(token: str) -> str:
    """«1,217» y «1 217» -> «1217»; las horas y los decimales se conservan («9:23», «1149.1»)."""
    t = token.replace(" ", "").replace(" ", "")
    if re.fullmatch(r"\d{1,3}(,\d{3})+", t):
        t = t.replace(",", "")
    return t


_UNIDADES = ("cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciseis "
             "diecisiete dieciocho diecinueve veinte veintiuno veintidos veintitres veinticuatro veinticinco "
             "veintiseis veintisiete veintiocho veintinueve").split()
_DECENAS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"}
_CENTENAS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos", 6: "seiscientos",
             7: "setecientos", 8: "ochocientos", 9: "novecientos"}


def _letras(n: int) -> str:
    """Un número de 0 a 999 999 en palabras, sin tildes (como queda el guion tras `_plano`)."""
    if n < 30:
        return _UNIDADES[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DECENAS[d * 10] + (f" y {_UNIDADES[u]}" if u else "")
    if n < 1000:
        c, r = divmod(n, 100)
        return "cien" if n == 100 else _CENTENAS[c] + (f" {_letras(r)}" if r else "")
    m, r = divmod(n, 1000)
    return ("mil" if m == 1 else f"{_letras(m)} mil") + (f" {_letras(r)}" if r else "")


def _en_letras(token: str) -> list[str]:
    t = _normal(token)
    hora = re.fullmatch(r"(\d{1,2}):00", t)
    if hora:                                            # «9:00» se dice «las nueve»
        t = hora.group(1)
    if t.isdigit() and int(t) % 1_000_000 == 0 and 0 < int(t) < 1_000_000_000:
        m = int(t) // 1_000_000                         # «un millón», «dos millones»
        return ["un millon"] if m == 1 else [f"{_letras(m)} millones"]
    if not t.isdigit() or int(t) >= 1_000_000:
        return []
    n = int(t)
    formas = {_letras(n)}
    if n == 1:
        formas |= {"un", "una", "la una"}
    if n % 10 == 1 and n > 20:
        formas.add(_letras(n)[:-1])                     # «veintiún», «treinta y un»
    return list(formas)


def textos_con_cifras(n: int) -> list[tuple[str, int, str]]:
    """(archivo, línea, texto) de cada cadena con cifras de los módulos de la escena."""
    archivos = [RAIZ / "escenas" / f"escena{n:02d}.py", *sorted((RAIZ / "escenas").glob(f"*_e{n:02d}.py"))]
    hallados = []
    for ruta in archivos:
        if not ruta.exists():
            continue
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        documentacion = {id(nodo.body[0].value) for nodo in ast.walk(arbol)
                         if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.ClassDef)) and nodo.body
                         and isinstance(nodo.body[0], ast.Expr) and isinstance(nodo.body[0].value, ast.Constant)}
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) and id(nodo) not in documentacion
                    and re.search(r"\d", nodo.value) and not CODIGO.match(nodo.value.strip())):
                hallados.append((ruta.name, nodo.lineno, nodo.value))
    return hallados


def revisar(n: int) -> list[str]:
    # Contra el guion entero: el cierre (escena 8) retoma horas y fechas que se dijeron en la 5 y la 6.
    todo = guion.leer()
    dicho = " ".join(o for e in todo.values() for s in e.subescenas for o in guion.subescena(s.id).oraciones)
    dicho += " " + " ".join(e.titulo for e in todo.values())
    cifras_guion = {_normal(t) for t in NUMERO.findall(dicho)}
    palabras = f" {_plano(dicho)} "
    permitidas = PERMITIDAS.get(n, {})
    avisos = []
    for archivo, linea, texto in textos_con_cifras(n):
        for token in NUMERO.findall(texto):
            t = _normal(token)
            if t in cifras_guion or t in permitidas or any(f" {f} " in palabras for f in _en_letras(token)):
                continue
            avisos.append(f"  escena {n}  {archivo}:{linea}  «{t}» en {texto.strip()[:70]!r}")
    return avisos


def main() -> int:
    escenas = [int(a) for a in sys.argv[1:]] or [n for n in range(1, 9) if (RAIZ / "escenas" / f"escena{n:02d}.py").exists()]
    total = 0
    for n in escenas:
        avisos = revisar(n)
        total += len(avisos)
        print(f"Escena {n}: " + ("sin cifras fuera del guion" if not avisos else f"{len(avisos)} por revisar"))
        print("\n".join(avisos)) if avisos else None
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
