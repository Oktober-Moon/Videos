"""Tiempos de una escena: lectura y validación del JSON, y la clase base de cada plano."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

FPS = 30


def a_segundos(valor: str | float | int) -> float:
    """'1:31.5' -> 91.5 ; 12 -> 12.0"""
    if isinstance(valor, (int, float)):
        return float(valor)
    partes = valor.strip().split(":")
    total = 0.0
    for parte in partes:
        total = total * 60 + float(parte)
    return total


def a_cuadro(segundos: float) -> int:
    return int(round(segundos * FPS))


@dataclass
class TiempoPlano:
    numero: int
    inicio: float
    fin: float
    texto: str
    marcas: dict[str, float] = field(default_factory=dict)
    pausa_final: float = 0.0
    subtitulos: list[dict] | None = None

    @property
    def cuadro_inicio(self) -> int:
        return a_cuadro(self.inicio)

    @property
    def cuadro_fin(self) -> int:
        return a_cuadro(self.fin)

    @property
    def cuadros(self) -> int:
        return self.cuadro_fin - self.cuadro_inicio

    @property
    def duracion(self) -> float:
        return self.cuadros / FPS


@dataclass
class TiemposEscena:
    nombre: str
    titulo: str
    palabras_por_minuto: float
    planos: list[TiempoPlano]
    revision: list[dict]

    @property
    def duracion(self) -> float:
        return self.planos[-1].cuadro_fin / FPS

    def plano(self, numero: int) -> TiempoPlano:
        for p in self.planos:
            if p.numero == numero:
                return p
        raise KeyError(f"No existe el plano {numero}")


def cargar_tiempos(ruta: Path) -> TiemposEscena:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    planos = []
    for p in datos["planos"]:
        planos.append(
            TiempoPlano(
                numero=int(p["plano"]),
                inicio=a_segundos(p["inicio"]),
                fin=a_segundos(p["fin"]),
                texto=p.get("texto", "").strip(),
                marcas={k: float(v) for k, v in p.get("marcas", {}).items()},
                pausa_final=float(p.get("pausa_final", 0.0)),
                subtitulos=p.get("subtitulos"),
            )
        )
    _validar(planos)
    return TiemposEscena(
        nombre=datos["escena"],
        titulo=datos.get("titulo", ""),
        palabras_por_minuto=float(datos.get("palabras_por_minuto", 170)),
        planos=planos,
        revision=datos.get("revision", []),
    )


def _validar(planos: list[TiempoPlano]) -> None:
    errores = []
    if planos and planos[0].inicio != 0:
        errores.append(f"El plano {planos[0].numero} debe empezar en 0:00.")
    for anterior, siguiente in zip(planos, planos[1:]):
        if anterior.cuadro_fin != siguiente.cuadro_inicio:
            errores.append(
                f"El plano {anterior.numero} termina en {anterior.fin:.2f} s pero el "
                f"{siguiente.numero} empieza en {siguiente.inicio:.2f} s; deben coincidir."
            )
    for p in planos:
        if p.cuadros <= 0:
            errores.append(f"El plano {p.numero} dura cero o menos.")
        for nombre, t in p.marcas.items():
            if not 0 <= t <= p.duracion:
                errores.append(
                    f"Plano {p.numero}: la marca '{nombre}' ({t} s) cae fuera del plano "
                    f"(dura {p.duracion:.2f} s)."
                )
    if errores:
        raise ValueError("Tiempos inválidos:\n  " + "\n  ".join(errores))


class Plano:
    """Base de un plano: se prepara una vez y luego se pide cuadro por cuadro.

    Cada subclase define `preparar()` (capas fijas, texturas) y `cuadro(t)`, que devuelve la
    imagen float32 (alto, ancho, 3) en 0..1 para el tiempo local `t` (segundos desde el inicio
    del plano). Las transiciones a negro van dentro del propio plano.
    """

    fundido_entrada: float = 0.5
    fundido_salida: float = 0.5

    def __init__(self, tiempo: TiempoPlano):
        self.tiempo = tiempo
        self.duracion = tiempo.duracion

    def m(self, nombre: str, defecto: float | None = None) -> float:
        """Marca de sincronía (segundos desde el inicio del plano)."""
        if nombre in self.tiempo.marcas:
            return self.tiempo.marcas[nombre]
        if defecto is None:
            raise KeyError(f"Plano {self.tiempo.numero}: falta la marca '{nombre}' en el JSON")
        return defecto

    def preparar(self) -> None:  # pragma: no cover - lo define cada plano
        pass

    def cuadro(self, t: float):  # pragma: no cover - lo define cada plano
        raise NotImplementedError

    def opacidad(self, t: float) -> float:
        """Factor de fundido a negro de entrada y salida."""
        f = 1.0
        if self.fundido_entrada > 0:
            f = min(f, max(0.0, t / self.fundido_entrada))
        if self.fundido_salida > 0:
            f = min(f, max(0.0, (self.duracion - t) / self.fundido_salida))
        return f * f * (3 - 2 * f)
