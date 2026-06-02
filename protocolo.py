# -*- coding: utf-8 -*-
"""
Protocolo de comunicacion del juego "Adivina Quien - Motos".

Modulo COMPARTIDO por server.py y gui_client.py. Centraliza:
  - Los tipos de mensaje (constantes), para no escribir cadenas sueltas.
  - La serializacion: cada mensaje es un objeto JSON terminado en '\\n'
    (newline-delimited JSON). El '\\n' marca el fin de cada mensaje dentro
    del flujo de bytes de TCP.
  - Funciones de envio (enviar) y recepcion (Receptor) sobre un socket.

Asi server y client hablan el mismo idioma sin duplicar codigo de red.

POR QUE SOCKETS (TCP):
  El juego es cliente-servidor, asi que hace falta un canal de comunicacion
  entre procesos (posiblemente en maquinas distintas). Usamos sockets TCP
  porque garantizan entrega ORDENADA y SIN PERDIDA de los bytes, algo
  imprescindible cuando el orden de preguntas/respuestas importa. La
  contraparte: TCP es un FLUJO de bytes sin fronteras de mensaje, por eso
  definimos un terminador '\\n' y la clase Receptor para reconstruir cada
  mensaje (framing).
"""

import json
import socket


# --------------------------------------------------------------------------
# Tipos de mensaje
# --------------------------------------------------------------------------

# Cliente  ->  Servidor
JOIN = "JOIN"            # {tipo, nombre}                       el jugador entra
PREGUNTA = "PREGUNTA"    # {tipo, atributo, valor}              pregunta por igualdad
ADIVINAR = "ADIVINAR"    # {tipo, moto}                         intento de ganar
RENDIRSE = "RENDIRSE"    # {tipo}                               se rinde: pierde la ronda
DESCARTAR = "DESCARTAR"  # {tipo, moto}                         marca una ficha descartada
REVANCHA = "REVANCHA"    # {tipo}                               pide jugar otra ronda
SALIR = "SALIR"          # {tipo}                               el jugador se va

# Servidor  ->  Cliente
ESPERANDO = "ESPERANDO"  # {tipo, msg}                          esperando rival
INICIO = "INICIO"        # {tipo, tu_moto, tablero, tu_turno, rival}
RESPUESTA = "RESPUESTA"  # {tipo, quien, atributo, valor, pregunta, respuesta}  SI/NO
TURNO = "TURNO"          # {tipo, tu_turno}                     cambio de turno
FIN = "FIN"              # {tipo, ganaste, moto_rival, msg, marcador, revancha}  fin de ronda
ERROR = "ERROR"          # {tipo, msg}                          mensaje invalido / desconexion


# --------------------------------------------------------------------------
# Autodescubrimiento por UDP
# --------------------------------------------------------------------------
# Permite que el cliente encuentre el servidor en la red local SIN escribir la
# IP: el cliente lanza un broadcast UDP y el servidor responde. El cliente
# deduce la IP del servidor a partir del origen de la respuesta.
DISCOVERY_PORT = 5001                            # puerto UDP del descubrimiento
DISCOVERY_MAGIC = b"ADIVINA_QUIEN_DISCOVERY?"    # peticion que envia el cliente
DISCOVERY_RESPONSE = b"ADIVINA_QUIEN_SERVER:"    # prefijo de la respuesta del servidor


# Codificacion usada para pasar de texto a bytes y viceversa.
_ENCODING = "utf-8"
_FIN_MENSAJE = "\n"


def crear(tipo, **campos):
    """Construye un mensaje (dict) con su 'tipo' y campos adicionales."""
    mensaje = {"tipo": tipo}
    mensaje.update(campos)
    return mensaje


def enviar(sock, mensaje):
    """
    Serializa `mensaje` (dict) a JSON, le agrega '\\n' y lo envia entero
    por el socket. Lanza ConnectionError si la conexion esta caida.
    """
    datos = (json.dumps(mensaje, ensure_ascii=False) + _FIN_MENSAJE)
    sock.sendall(datos.encode(_ENCODING))


class Receptor:
    """
    Lee mensajes completos de un socket. Como TCP es un flujo continuo de
    bytes (un sendall puede llegar partido o pegado a otro), acumulamos lo
    recibido en un buffer y entregamos un mensaje cada vez que aparece '\\n'.

    Uso tipico:
        receptor = Receptor(sock)
        for mensaje in receptor:      # itera mensaje a mensaje (dicts)
            ...
    o bien:
        mensaje = receptor.recibir()  # None si la conexion se cerro
    """

    def __init__(self, sock):
        """Guarda el socket y arranca un buffer de texto vacio."""
        self.sock = sock
        self._buffer = ""

    def recibir(self):
        """Devuelve el siguiente mensaje (dict) o None si se cerro la conexion."""
        while _FIN_MENSAJE not in self._buffer:
            try:
                trozo = self.sock.recv(4096)
            except OSError:
                return None
            if not trozo:
                return None  # el otro extremo cerro la conexion
            self._buffer += trozo.decode(_ENCODING)

        linea, self._buffer = self._buffer.split(_FIN_MENSAJE, 1)
        linea = linea.strip()
        if not linea:
            return self.recibir()  # linea vacia: intenta el siguiente

        try:
            return json.loads(linea)
        except json.JSONDecodeError:
            # Mensaje corrupto: lo reportamos como ERROR en vez de romper.
            return crear(ERROR, msg="mensaje JSON invalido")

    def __iter__(self):
        """Permite usar el receptor en un bucle 'for mensaje in receptor'."""
        return self

    def __next__(self):
        """Entrega el siguiente mensaje; corta el bucle si la conexion cerro."""
        mensaje = self.recibir()
        if mensaje is None:
            raise StopIteration
        return mensaje


# --------------------------------------------------------------------------
# Funciones de autodescubrimiento (UDP)
# --------------------------------------------------------------------------
def servidor_descubrimiento(tcp_port):
    """Responde a los broadcast de descubrimiento de los clientes (lado servidor).

    Pensado para correr en un hilo daemon dentro del servidor: escucha en el
    puerto UDP de descubrimiento y, por cada peticion valida, responde al
    cliente indicando el puerto TCP del juego. El cliente deduce la IP del
    servidor a partir del origen del paquete.
    """
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # En Windows, si respondemos a un cliente que ya cerro su socket UDP, el SO
    # genera un ICMP "port unreachable" que haria que el siguiente recvfrom lance
    # ConnectionResetError (WSAECONNRESET). SIO_UDP_CONNRESET=False desactiva ese
    # comportamiento para que el hilo no se caiga tras el primer cliente.
    if hasattr(socket, "SIO_UDP_CONNRESET"):
        try:
            udp.ioctl(socket.SIO_UDP_CONNRESET, False)
        except OSError:
            pass
    udp.bind(("", DISCOVERY_PORT))
    print(f"[DESCUBRIMIENTO] Escuchando broadcast UDP en el puerto {DISCOVERY_PORT}")
    while True:
        try:
            datos, origen = udp.recvfrom(1024)
        except ConnectionResetError:
            # Un cliente cerro su socket antes de leer la respuesta: lo ignoramos
            # y seguimos escuchando (NO matamos el hilo).
            continue
        except OSError:
            break  # socket cerrado de verdad: termina el hilo
        try:
            if datos.strip() == DISCOVERY_MAGIC:
                respuesta = DISCOVERY_RESPONSE + str(tcp_port).encode(_ENCODING)
                udp.sendto(respuesta, origen)
                print(f"[DESCUBRIMIENTO] Servidor anunciado a {origen[0]}")
        except OSError:
            # Un fallo al responder a UN cliente no debe tumbar el servicio.
            continue


def descubrir_servidor(timeout=2.0):
    """Busca el servidor en la red local por broadcast UDP (lado cliente).

    Devuelve (host, puerto_tcp) si algun servidor responde dentro de `timeout`
    segundos, o None si no aparece ninguno.
    """
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp.settimeout(timeout)
    try:
        # Se envia al broadcast de la red y tambien a localhost: asi funciona
        # tanto entre PCs distintas como en una sola maquina (donde el broadcast
        # puede no volver por loopback).
        for destino in ("255.255.255.255", "127.0.0.1"):
            try:
                udp.sendto(DISCOVERY_MAGIC, (destino, DISCOVERY_PORT))
            except OSError:
                pass
        datos, origen = udp.recvfrom(1024)
        if datos.startswith(DISCOVERY_RESPONSE):
            puerto = int(datos[len(DISCOVERY_RESPONSE):])
            return (origen[0], puerto)
    except (OSError, ValueError):
        return None
    finally:
        udp.close()
    return None
