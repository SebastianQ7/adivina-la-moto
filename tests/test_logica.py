# -*- coding: utf-8 -*-
"""Tests de las reglas puras del juego (logica.py)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import motos
import logica


class TestEvaluarPregunta(unittest.TestCase):
    """La respuesta SI/NO segun coincidencia del atributo."""

    def setUp(self):
        # Suzuki Hayabusa: japonesa, deportiva, alta, ...
        self.attrs = motos.motos["Suzuki Hayabusa"]

    def test_coincide_responde_si(self):
        self.assertEqual(logica.evaluar_pregunta(self.attrs, "origen", "japonesa"), "SI")

    def test_no_coincide_responde_no(self):
        self.assertEqual(logica.evaluar_pregunta(self.attrs, "origen", "alemana"), "NO")


class TestValidaciones(unittest.TestCase):
    """Validaciones de atributo y de existencia del personaje."""

    def test_atributo_valido(self):
        self.assertTrue(logica.atributo_valido("origen"))
        self.assertFalse(logica.atributo_valido("peso"))

    def test_personaje_existe(self):
        self.assertTrue(logica.personaje_existe("Ducati Monster"))
        self.assertFalse(logica.personaje_existe("Moto Inventada 9000"))


class TestCandidatosADescartar(unittest.TestCase):
    """La eliminacion de candidatos tras una respuesta."""

    def setUp(self):
        self.todos = list(motos.motos)

    def test_si_descarta_las_que_no_coinciden(self):
        # origen=japonesa con respuesta SI: quedan solo las 4 japonesas.
        descartar = logica.candidatos_a_descartar(self.todos, "origen", "japonesa", "SI")
        quedan = [n for n in self.todos if n not in descartar]
        self.assertEqual(len(quedan), 4)
        for nombre in quedan:
            self.assertEqual(motos.motos[nombre]["origen"], "japonesa")

    def test_no_descarta_las_que_coinciden(self):
        # origen=japonesa con respuesta NO: se descartan las 4 japonesas.
        descartar = logica.candidatos_a_descartar(self.todos, "origen", "japonesa", "NO")
        self.assertEqual(len(descartar), 4)
        for nombre in descartar:
            self.assertEqual(motos.motos[nombre]["origen"], "japonesa")

    def test_atributo_invalido_no_descarta_nada(self):
        self.assertEqual(
            logica.candidatos_a_descartar(self.todos, "peso", "alto", "SI"), set())

    def test_no_toca_los_ya_excluidos(self):
        # Si paso solo un subconjunto como candidatos, no inventa otros.
        subconjunto = ["Ducati Monster", "Honda CBR 600RR"]
        descartar = logica.candidatos_a_descartar(subconjunto, "origen", "japonesa", "SI")
        self.assertTrue(descartar.issubset(set(subconjunto)))


if __name__ == "__main__":
    unittest.main()
