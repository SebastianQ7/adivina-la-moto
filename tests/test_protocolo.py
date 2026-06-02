# -*- coding: utf-8 -*-
"""Tests del protocolo: serializacion y framing con un socket FALSO (sin red real)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import protocolo


class SocketFalso:
    """Socket de mentira: guarda lo 'enviado' y lo devuelve por trozos en recv().

    El parametro `chunk` permite simular que TCP entrega los bytes partidos
    (para probar el reensamblado de mensajes que hace Receptor).
    """

    def __init__(self, chunk=4096):
        self.enviado = b""
        self._chunk = chunk

    def sendall(self, data):
        self.enviado += data

    def recv(self, n):
        size = min(n, self._chunk)
        trozo, self.enviado = self.enviado[:size], self.enviado[size:]
        return trozo


class TestProtocolo(unittest.TestCase):

    def test_ida_y_vuelta(self):
        """Un mensaje enviado se recibe identico."""
        s = SocketFalso()
        protocolo.enviar(s, protocolo.crear(
            protocolo.PREGUNTA, atributo="origen", valor="japonesa"))
        msg = protocolo.Receptor(s).recibir()
        self.assertEqual(msg["tipo"], protocolo.PREGUNTA)
        self.assertEqual(msg["atributo"], "origen")
        self.assertEqual(msg["valor"], "japonesa")

    def test_dos_mensajes_pegados(self):
        """Dos mensajes en el mismo flujo se separan por el terminador '\\n'."""
        s = SocketFalso()
        protocolo.enviar(s, protocolo.crear(protocolo.TURNO, tu_turno=True))
        protocolo.enviar(s, protocolo.crear(protocolo.TURNO, tu_turno=False))
        receptor = protocolo.Receptor(s)
        self.assertEqual(receptor.recibir()["tu_turno"], True)
        self.assertEqual(receptor.recibir()["tu_turno"], False)

    def test_mensaje_partido_en_varios_recv(self):
        """Un mensaje que llega byte a byte se reensambla correctamente."""
        s = SocketFalso(chunk=1)   # un byte por recv
        protocolo.enviar(s, protocolo.crear(protocolo.JOIN, nombre="Ana"))
        msg = protocolo.Receptor(s).recibir()
        self.assertEqual(msg["tipo"], protocolo.JOIN)
        self.assertEqual(msg["nombre"], "Ana")

    def test_conexion_cerrada_devuelve_none(self):
        """Si no hay datos (recv vacio), recibir() devuelve None."""
        s = SocketFalso()
        self.assertIsNone(protocolo.Receptor(s).recibir())

    def test_json_invalido_devuelve_error(self):
        """Un mensaje corrupto se reporta como ERROR, no rompe el receptor."""
        s = SocketFalso()
        s.enviado = b"{ esto no es json }\n"
        msg = protocolo.Receptor(s).recibir()
        self.assertEqual(msg["tipo"], protocolo.ERROR)

    def test_acentos_utf8(self):
        """Los caracteres no ASCII viajan bien (UTF-8)."""
        s = SocketFalso()
        protocolo.enviar(s, protocolo.crear(protocolo.RESPUESTA, pregunta="¿origen?"))
        self.assertEqual(protocolo.Receptor(s).recibir()["pregunta"], "¿origen?")


if __name__ == "__main__":
    unittest.main()
