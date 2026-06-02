# -*- coding: utf-8 -*-
"""
Reglas PURAS del juego "Adivina Quien - Motos".

Funciones sin sockets, sin hilos y sin interfaz: solo deciden, a partir de los
datos de motos.py, las cuestiones de logica del juego (validar una pregunta,
responder SI/NO, que candidatos se descartan, si un personaje existe).

Al estar aisladas de la red y la UI, son faciles de probar con unittest y las
pueden reutilizar tanto el servidor (server.py) como los clientes
(client.py / gui_client.py) sin duplicar las reglas.
"""

from typing import Iterable

import motos


def atributo_valido(atributo: str) -> bool:
    """Indica si un atributo se puede preguntar (existe en motos.ATRIBUTOS)."""
    return atributo in motos.ATRIBUTOS


def personaje_existe(nombre: str) -> bool:
    """Indica si una moto existe en el tablero."""
    return nombre in motos.motos


def evaluar_pregunta(atributos_personaje: dict, atributo: str, valor: str) -> str:
    """Responde 'SI' o 'NO' segun si el atributo del personaje coincide con valor.

    La comparacion es por igualdad de texto (todos los atributos son categoricos).
    """
    return "SI" if str(atributos_personaje.get(atributo)) == str(valor) else "NO"


def candidatos_a_descartar(candidatos: Iterable[str], atributo: str,
                           valor: str, respuesta: str) -> set:
    """Devuelve el conjunto de motos a descartar tras la respuesta a una pregunta.

    - respuesta 'SI': el personaje TIENE ese valor -> se descartan las que NO lo tienen.
    - respuesta 'NO': el personaje NO tiene ese valor -> se descartan las que SI lo tienen.

    Si el atributo no es valido, no descarta nada.
    """
    descartar: set = set()
    if not atributo_valido(atributo):
        return descartar
    for nombre in candidatos:
        coincide = str(motos.motos[nombre].get(atributo)) == str(valor)
        if (respuesta == "SI" and not coincide) or (respuesta == "NO" and coincide):
            descartar.add(nombre)
    return descartar
