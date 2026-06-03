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
        """Devuelve la jugada del bot segun su dificultad.

        Retorna una tupla:
          ("ADIVINAR", nombre)             si decide arriesgar, o
          ("PREGUNTA", atributo, valor)    en caso contrario.

        Diferencias por dificultad:
          - dificil: siempre la mejor pregunta (parte a la mitad) y solo adivina
            cuando esta SEGURO (1 candidato). Rapido y certero.
          - normal: la mejor pregunta el 70% de las veces (a veces una al azar);
            adivina con 1 candidato.
          - facil: preguntas al azar (no optimas) y se arriesga a adivinar con
            2 candidatos -> falla mas seguido (mas facil ganarle).
        """
        n = len(self.candidatos)

        # ¿Cuando adivinar? El facil se arriesga antes (con 2), los demas con 1.
        if self.dificultad == "facil":
            if n <= 2:
                return ("ADIVINAR", self._un_candidato())
        else:
            if n <= 1:
                return ("ADIVINAR", self._un_candidato())

        # ¿Que pregunta hacer?
        if self.dificultad == "dificil":
            mejor = self._mejor_pregunta()
        elif self.dificultad == "facil":
            mejor = self._pregunta_aleatoria()
        else:  # normal
            mejor = self._mejor_pregunta() if random.random() < 0.7 else self._pregunta_aleatoria()

        if mejor is None:
            return ("ADIVINAR", self._un_candidato())
        atributo, valor = mejor
        self._preguntas_hechas.add((atributo, valor))
        return ("PREGUNTA", atributo, valor)

    def _un_candidato(self):
        """Un candidato al azar (o cualquier moto si el conjunto quedo vacio)."""
        if self.candidatos:
            return random.choice(list(self.candidatos))
        return random.choice(list(motos.motos.keys()))

    def _pregunta_aleatoria(self):
        """Una pregunta VALIDA al azar que parta el conjunto (no necesariamente la mejor)."""
        total = len(self.candidatos)
        opciones = []
        for atributo in motos.ATRIBUTOS:
            valores = {motos.motos[m][atributo] for m in self.candidatos}
            for valor in valores:
                if (atributo, valor) in self._preguntas_hechas:
                    continue
                cuantos = sum(1 for m in self.candidatos
                              if motos.motos[m][atributo] == valor)
                if 0 < cuantos < total:
                    opciones.append((atributo, valor))
        return random.choice(opciones) if opciones else None

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
