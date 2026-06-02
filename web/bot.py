# -*- coding: utf-8 -*-
"""
Bot (jugador automatico) para "Adivina la Moto".

El bot juega como un humano mas: en su turno decide entre PREGUNTAR o ADIVINAR.
Reutiliza las reglas puras de `logica.py` y los datos de `motos.py`, asi que su
"inteligencia" se apoya en el mismo motor del juego (sin red ni hilos aqui).

ESTRATEGIA (dificultad "normal", tipo arbol de decision optimo):
  - El bot mantiene el conjunto de motos que TODAVIA pueden ser la moto secreta
    del rival (sus "candidatos").
  - En cada turno elige la pregunta (atributo = valor) que parte el conjunto de
    candidatos lo mas cerca posible de la mitad: asi cada respuesta elimina
    aproximadamente la mitad (busqueda binaria -> ~log2(24) ≈ 5 preguntas).
  - Cuando solo queda UN candidato, lo adivina.
"""

import random

import motos
import logica


class Bot:
    """Estado de razonamiento del bot durante una partida."""

    def __init__(self, nombre="Bot", dificultad="normal"):
        """Arranca con las 24 motos como posibles candidatas del rival."""
        self.nombre = nombre
        self.dificultad = dificultad
        self.candidatos = set(motos.motos.keys())
        # Para no repetir exactamente la misma pregunta si algo sale raro.
        self._preguntas_hechas = set()

    # ------------------------------------------------------------------
    # Aprendizaje: filtrar candidatos tras la respuesta a la propia pregunta
    # ------------------------------------------------------------------
    def registrar_respuesta(self, atributo, valor, respuesta):
        """Descarta candidatos segun la respuesta (SI/NO) a la pregunta del bot.

        Usa exactamente la misma regla pura que el tablero del jugador humano.
        """
        descartar = logica.candidatos_a_descartar(
            self.candidatos, atributo, valor, respuesta)
        self.candidatos -= descartar

    # ------------------------------------------------------------------
    # Decision de jugada
    # ------------------------------------------------------------------
    def decidir_jugada(self):
        """Devuelve la jugada del bot en su turno.

        Retorna una tupla:
          ("ADIVINAR", nombre_moto)        si ya esta seguro (1 candidato), o
          ("PREGUNTA", atributo, valor)    en caso contrario.
        """
        # Si solo queda una opcion (o ninguna por seguridad), adivina.
        if len(self.candidatos) <= 1:
            moto = next(iter(self.candidatos)) if self.candidatos else \
                random.choice(list(motos.motos.keys()))
            return ("ADIVINAR", moto)

        mejor = self._mejor_pregunta()
        if mejor is None:
            # No hay forma de partir mas: adivina al azar entre los candidatos.
            return ("ADIVINAR", random.choice(list(self.candidatos)))
        atributo, valor = mejor
        self._preguntas_hechas.add((atributo, valor))
        return ("PREGUNTA", atributo, valor)

    def _mejor_pregunta(self):
        """Elige (atributo, valor) que parte los candidatos lo mas cerca de la mitad."""
        total = len(self.candidatos)
        objetivo = total / 2.0
        mejor = None
        mejor_dist = None

        for atributo in motos.ATRIBUTOS:
            # Valores posibles de ese atributo ENTRE los candidatos actuales.
            valores = {motos.motos[m][atributo] for m in self.candidatos}
            for valor in valores:
                if (atributo, valor) in self._preguntas_hechas:
                    continue
                # Cuantos candidatos cumplen "atributo == valor".
                cuantos = sum(1 for m in self.candidatos
                              if motos.motos[m][atributo] == valor)
                if cuantos == 0 or cuantos == total:
                    continue  # pregunta inutil: no parte el conjunto
                dist = abs(cuantos - objetivo)
                if mejor_dist is None or dist < mejor_dist:
                    mejor_dist = dist
                    mejor = (atributo, valor)
        return mejor
