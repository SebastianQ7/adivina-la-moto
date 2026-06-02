# -*- coding: utf-8 -*-
"""Tests de integridad de los datos de motos.py."""

import os
import sys
import unittest

# Permite ejecutar los tests desde cualquier sitio (raiz del proyecto al path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import motos


class TestMotos(unittest.TestCase):
    """Verifica que el tablero de datos sea consistente."""

    def test_hay_24_motos(self):
        """El tablero debe tener exactamente 24 motos."""
        self.assertEqual(len(motos.motos), 24)

    def test_todas_tienen_los_7_atributos(self):
        """Cada moto debe tener exactamente los atributos de ATRIBUTOS."""
        for nombre, attrs in motos.motos.items():
            self.assertEqual(set(attrs), set(motos.ATRIBUTOS), msg=nombre)

    def test_hay_4_motos_por_origen(self):
        """El enunciado pide 4 motos por cada uno de los 6 origenes."""
        conteo = motos.tabla_balanceo()["origen"]
        self.assertEqual(len(conteo), 6)
        for origen, cantidad in conteo.items():
            self.assertEqual(cantidad, 4, msg=origen)

    def test_balanceo_suma_24(self):
        """El conteo de cada atributo debe sumar 24 (sin motos sin valor)."""
        for atributo, conteo in motos.tabla_balanceo().items():
            self.assertEqual(sum(conteo.values()), 24, msg=atributo)


if __name__ == "__main__":
    unittest.main()
