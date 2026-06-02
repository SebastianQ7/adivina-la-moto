# -*- coding: utf-8 -*-
"""
WebSocket "a mano" sobre sockets TCP de la biblioteca estandar.

POR QUE ESTE MODULO:
  El navegador NO puede abrir un socket TCP crudo: para hablar en tiempo real
  con el servidor usa el protocolo WebSocket (RFC 6455), que viaja SOBRE una
  conexion TCP normal. Aqui implementamos a mano las dos partes del protocolo
  usando solo el modulo `socket`:

    1. El "handshake": el navegador manda una peticion HTTP de tipo Upgrade y el
       servidor responde con un codigo 101 y una clave calculada (SHA-1 + base64).
    2. El "framing": despues del handshake, los mensajes viajan en TRAMAS
       (frames) con un encabezado de bytes. El cliente SIEMPRE enmascara su
       payload; el servidor responde SIN mascara.

  Hacerlo a mano (sin librerias) mantiene el proyecto en biblioteca estandar y
  deja a la vista el uso real de sockets, que es justo lo que se evalua.
"""

import base64
import hashlib
import struct


# Constante magica definida por el estandar WebSocket (RFC 6455). Se concatena
# a la clave del cliente para calcular la respuesta del handshake.
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# Opcodes de las tramas WebSocket.
_OP_CONT = 0x0      # continuacion (fragmentacion)
_OP_TEXT = 0x1      # texto (UTF-8)  <- el unico que usamos para el juego
_OP_BIN = 0x2       # binario
_OP_CLOSE = 0x8     # cierre de conexion
_OP_PING = 0x9      # ping (keep-alive)
_OP_PONG = 0xA      # pong (respuesta al ping)


def calcular_accept(clave_cliente: str) -> str:
    """Calcula el valor 'Sec-WebSocket-Accept' a partir de la clave del cliente.

    Es SHA-1 de (clave + GUID) codificado en base64. El navegador valida esta
    respuesta para confirmar que hablamos WebSocket de verdad.
    """
    sha1 = hashlib.sha1((clave_cliente + _GUID).encode("utf-8")).digest()
    return base64.b64encode(sha1).decode("ascii")


def es_peticion_websocket(headers: dict) -> bool:
    """Indica si los headers HTTP corresponden a una peticion de upgrade a WebSocket."""
    return (headers.get("upgrade", "").lower() == "websocket"
            and "websocket-key" in [k.replace("sec-", "") for k in headers])


class WebSocket:
    """Envuelve un socket TCP ya "ascendido" a WebSocket y ofrece enviar/recibir
    mensajes de TEXTO (cadenas), ocultando el framing del protocolo.

    Interfaz pensada para parecerse a `protocolo.Receptor` del modo clasico:
      ws.enviar(texto)   -> manda un mensaje de texto
      ws.recibir()       -> devuelve el siguiente mensaje de texto o None si cerro
      ws.cerrar()        -> cierra la conexion
    """

    def __init__(self, conn, buffer_inicial: bytes = b""):
        """Guarda el socket y un buffer con los bytes que ya se hayan leido de mas."""
        self.conn = conn
        self._buffer = buffer_inicial
        self.cerrado = False

    # ------------------------------------------------------------------
    # Lectura de bytes con buffer (TCP es un flujo, puede llegar partido)
    # ------------------------------------------------------------------
    def _leer_exacto(self, n: int):
        """Lee EXACTAMENTE n bytes del socket (acumulando en el buffer).

        Devuelve None si la conexion se cierra antes de completar n bytes.
        """
        while len(self._buffer) < n:
            try:
                trozo = self.conn.recv(4096)
            except OSError:
                return None
            if not trozo:
                return None  # el navegador cerro la conexion
            self._buffer += trozo
        datos, self._buffer = self._buffer[:n], self._buffer[n:]
        return datos

    # ------------------------------------------------------------------
    # Recepcion de un mensaje (puede venir en varias tramas/fragmentos)
    # ------------------------------------------------------------------
    def recibir(self):
        """Devuelve el siguiente mensaje de texto (str) o None si la conexion cerro.

        Gestiona internamente las tramas de control (ping/pong/close) y la
        fragmentacion (un mensaje partido en varias tramas).
        """
        fragmentos = bytearray()
        while True:
            cabecera = self._leer_exacto(2)
            if cabecera is None:
                return None

            b0, b1 = cabecera[0], cabecera[1]
            fin = (b0 & 0x80) != 0
            opcode = b0 & 0x0F
            enmascarado = (b1 & 0x80) != 0
            longitud = b1 & 0x7F

            # Longitud extendida: 126 -> 2 bytes siguientes; 127 -> 8 bytes.
            if longitud == 126:
                ext = self._leer_exacto(2)
                if ext is None:
                    return None
                longitud = struct.unpack(">H", ext)[0]
            elif longitud == 127:
                ext = self._leer_exacto(8)
                if ext is None:
                    return None
                longitud = struct.unpack(">Q", ext)[0]

            # El cliente SIEMPRE enmascara: leemos la mascara de 4 bytes.
            mascara = b""
            if enmascarado:
                mascara = self._leer_exacto(4)
                if mascara is None:
                    return None

            payload = self._leer_exacto(longitud) if longitud else b""
            if payload is None:
                return None

            # Desenmascarado: XOR de cada byte con la mascara ciclica.
            if enmascarado and payload:
                payload = bytes(b ^ mascara[i % 4] for i, b in enumerate(payload))

            # --- Tramas de control ---
            if opcode == _OP_CLOSE:
                self._enviar_trama(_OP_CLOSE, b"")
                self.cerrado = True
                return None
            if opcode == _OP_PING:
                self._enviar_trama(_OP_PONG, payload)  # responder pong y seguir
                continue
            if opcode == _OP_PONG:
                continue  # keep-alive: lo ignoramos

            # --- Tramas de datos ---
            fragmentos += payload
            if fin:
                try:
                    return fragmentos.decode("utf-8")
                except UnicodeDecodeError:
                    return ""  # mensaje corrupto: cadena vacia (no rompe el bucle)
            # Si fin == False, es un fragmento: seguimos leyendo continuaciones.

    # ------------------------------------------------------------------
    # Envio de un mensaje de texto (servidor -> cliente, SIN mascara)
    # ------------------------------------------------------------------
    def enviar(self, texto: str) -> bool:
        """Envia un mensaje de texto al navegador. Devuelve True/False segun exito."""
        return self._enviar_trama(_OP_TEXT, texto.encode("utf-8"))

    def _enviar_trama(self, opcode: int, payload: bytes) -> bool:
        """Construye y envia una trama WebSocket (servidor: sin enmascarar)."""
        if self.cerrado:
            return False
        cabecera = bytearray()
        cabecera.append(0x80 | opcode)  # FIN=1 + opcode

        n = len(payload)
        if n < 126:
            cabecera.append(n)
        elif n < 65536:
            cabecera.append(126)
            cabecera += struct.pack(">H", n)
        else:
            cabecera.append(127)
            cabecera += struct.pack(">Q", n)

        try:
            self.conn.sendall(bytes(cabecera) + payload)
            return True
        except OSError:
            self.cerrado = True
            return False

    def cerrar(self):
        """Envia la trama de cierre y cierra el socket subyacente."""
        try:
            self._enviar_trama(_OP_CLOSE, b"")
        except OSError:
            pass
        try:
            self.conn.close()
        except OSError:
            pass
        self.cerrado = True
