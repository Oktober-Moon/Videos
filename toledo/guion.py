"""Lee el guion de Word y lo parte en escenas, subescenas, oraciones y pausas.

- "Escena N. Título (m:ss – m:ss)" abre la escena N; lo que sigue hasta "Escena N.1:" es la
  subescena N.0.
- Lo que va entre paréntesis después de un nombre es solo la pronunciación: se quita del texto
  en pantalla y, para la voz generada (`hablado=True`), reemplaza al nombre.
- Un párrafo "(pausa)" marca un silencio después de la oración anterior.

Así, si se corrige el guion en Word, el render toma el texto nuevo sin tocar el código.
"""

from __future__ import annotations

import functools
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

RAIZ = Path(__file__).resolve().parent
RUTA = RAIZ / "Guion Forense digital en moviles e IoT.docx"
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class Subescena:
    id: str                      # "1.0", "1.1", …
    escena: int
    oraciones: list[str] = field(default_factory=list)
    pausas: list[int] = field(default_factory=list)   # índices de oración seguidos de "(pausa)"

    @property
    def palabras(self) -> list[int]:
        return [len(o.split()) for o in self.oraciones]

    @property
    def texto(self) -> str:
        return " ".join(self.oraciones)


@dataclass
class Escena:
    numero: int
    titulo: str
    subescenas: list[Subescena] = field(default_factory=list)


def _parrafos(ruta: Path) -> list[str]:
    raiz = ET.fromstring(zipfile.ZipFile(ruta).read("word/document.xml"))
    salida = []
    for p in raiz.iter(_W + "p"):
        t = "".join(x.text or "" for x in p.iter(_W + "t")).strip()
        if t:
            salida.append(t)
    return salida


_PALABRA = r"[^\s(),:;.¿?¡!]+"


def _como_se_dice(nombres: list[str], pron: str) -> str:
    """«Friburgo», «fri-BÚR-go» -> «fribúrgo». Las siglas (dos mayúsculas o una cifra) se leen
    letra por letra: «UID», «iu-ai-DÍ» -> «iu ai dí»; «AfD» -> «a ef dé»."""
    def sigla(w: str) -> bool:
        return sum(c.isupper() for c in w) >= 2 or any(c.isdigit() for c in w)
    pares = zip(nombres, pron.split()) if len(nombres) == len(pron.split()) else \
        [(" ".join(nombres), p) for p in pron.split()]
    return " ".join((" " if sigla(n) else "").join(p.split("-")).lower() for n, p in pares)


def _pronunciar(m: re.Match) -> str:
    """La pronunciación entre paréntesis reemplaza tantas palabras previas como tiene ella:
    «Syed Rizwan Farook (SÁ-id ris-UÁN fa-RÚK)» cambia las tres; «María Ladenburger
    (LÁ-den-bur-guer)», solo el apellido."""
    palabras, pron = m.group(1).split(), m.group(2)
    n = min(len(pron.split()), len(palabras))
    return " ".join(palabras[:-n] + [_como_se_dice([w.strip("«»\"'") for w in palabras[-n:]], pron)])


def _oraciones(texto: str, hablado: bool = False) -> list[str]:
    if hablado:                                             # para la voz: el nombre como se pronuncia
        texto = re.sub(r"\s*\(\d+:\d+\s*[–-]\s*\d+:\d+\)", "", texto)
        texto = re.sub(rf"((?:{_PALABRA}\s+){{0,3}}{_PALABRA})\s*\(([^)]*)\)", _pronunciar, texto)
    texto = re.sub(r"\s*\([^)]*\)", "", texto).strip()     # pronunciaciones (y lo que quede entre paréntesis)
    partes = re.split(r"(?<=[.!?…])\s+", texto)
    return [p.strip() for p in partes if p.strip()]


@functools.lru_cache(maxsize=2)
def leer(ruta: Path = RUTA, hablado: bool = False) -> dict[int, Escena]:
    escenas: dict[int, Escena] = {}
    actual: Subescena | None = None
    for p in _parrafos(ruta):
        m = re.match(r"Escena (\d+)\.\s+(.+?)\s*\(\d+:\d+\s*[–-]\s*\d+:\d+\)\s*$", p)
        if m:
            n = int(m.group(1))
            escenas[n] = Escena(n, m.group(2).strip())
            actual = Subescena(f"{n}.0", n)
            escenas[n].subescenas.append(actual)
            continue
        m = re.match(r"Escena (\d+)\.(\d+):\s*$", p)
        if m:
            n = int(m.group(1))
            actual = Subescena(f"{n}.{int(m.group(2))}", n)
            escenas[n].subescenas.append(actual)
            continue
        if actual is None:
            continue                                      # título del documento
        if re.fullmatch(r"\(\s*pausa\s*\)", p, re.IGNORECASE):
            if actual.oraciones:
                actual.pausas.append(len(actual.oraciones) - 1)
            continue
        actual.oraciones.extend(_oraciones(p, hablado))
    return escenas


def subescena(id_: str, hablado: bool = False) -> Subescena:
    """`hablado`: el texto para la voz, con cada nombre escrito como se pronuncia."""
    n = int(id_.split(".")[0])
    for s in leer(hablado=hablado)[n].subescenas:
        if s.id == id_:
            return s
    raise KeyError(id_)


if __name__ == "__main__":
    for e in leer().values():
        print(f"Escena {e.numero}: {e.titulo}")
        for s in e.subescenas:
            print(f"  {s.id}: {len(s.oraciones)} oraciones, {sum(s.palabras)} palabras, pausas {s.pausas}")
