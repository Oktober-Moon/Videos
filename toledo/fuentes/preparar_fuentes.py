"""Genera las fuentes estáticas que usa el render a partir de las variables de Google Fonts.

Las fuentes originales (Inter, Cinzel y EB Garamond, licencia OFL) viven en `fuentes/originales/`.
Este script crea:

- `Inter-Regular.ttf` (400), `Inter-SemiBold.ttf` (600), `Inter-Bold.ttf` (700) e `Inter-Light.ttf`
  (300): textos en pantalla del video de forense digital. Las de títulos usan el tamaño óptico
  grande (opsz 32), con letras más ceñidas; la regular, el de texto (opsz 14).
- `Cinzel-Regular.ttf` y `Cinzel-Bold.ttf`: instancias estáticas de peso 400 y 700.
- `EBGaramond-Regular.ttf`: instancia de peso 400 (letras griegas de la carta, títulos de libro).
- `EBGaramond-Versalitas.ttf`: instancia de peso 500 con la función OpenType `smcp`
  «congelada»: las minúsculas quedan mapeadas a sus versalitas. Hace falta porque Pillow sin
  libraqm no aplica funciones OpenType al dibujar texto.

Uso:  python fuentes/preparar_fuentes.py
"""

from pathlib import Path
import subprocess
import sys

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

CARPETA = Path(__file__).resolve().parent
ORIGINALES = CARPETA / "originales"


def instancia(origen: str, peso: int, destino: str, **ejes) -> Path:
    fuente = TTFont(ORIGINALES / origen)
    try:
        estatica = instancer.instantiateVariableFont(fuente, {"wght": peso, **ejes}, updateFontNames=True)
    except ValueError:  # la tabla STAT no nombra ese tamaño óptico: se deja el nombre original
        fuente = TTFont(ORIGINALES / origen)
        estatica = instancer.instantiateVariableFont(fuente, {"wght": peso, **ejes})
    ruta = CARPETA / destino
    estatica.save(ruta)
    return ruta


def congelar_versalitas(origen: Path, destino: str) -> Path:
    ruta = CARPETA / destino
    congelador = Path(sys.executable).with_name("pyftfeatfreeze.exe")
    if not congelador.exists():
        congelador = Path(sys.executable).with_name("pyftfeatfreeze")
    subprocess.run(
        [str(congelador), "-f", "smcp", "-S", "-U", "Versalitas", str(origen), str(ruta)],
        check=True,
    )
    return ruta


def main() -> None:
    instancia("Inter[opsz,wght].ttf", 400, "Inter-Regular.ttf", opsz=14)
    instancia("Inter[opsz,wght].ttf", 300, "Inter-Light.ttf", opsz=32)
    instancia("Inter[opsz,wght].ttf", 600, "Inter-SemiBold.ttf", opsz=32)
    instancia("Inter[opsz,wght].ttf", 700, "Inter-Bold.ttf", opsz=32)
    instancia("Cinzel[wght].ttf", 400, "Cinzel-Regular.ttf")
    instancia("Cinzel[wght].ttf", 700, "Cinzel-Bold.ttf")
    instancia("EBGaramond[wght].ttf", 400, "EBGaramond-Regular.ttf")
    medio = instancia("EBGaramond[wght].ttf", 500, "_EBGaramond-Medium.tmp.ttf")
    congelar_versalitas(medio, "EBGaramond-Versalitas.ttf")
    medio.unlink()
    print("Fuentes listas en", CARPETA)


if __name__ == "__main__":
    main()
