# -*- coding: utf-8 -*-
"""
Servidor WEB de "Adivina la Moto"  (HTTP + WebSocket con hilos y sockets).

Un solo proceso, solo biblioteca estandar:

  - Hilo principal: crea un socket TCP, hace bind/listen y acepta conexiones
    (accept() es bloqueante). Por cada conexion lanza UN hilo (igual que el
    servidor clasico server.py).
  - Cada conexion empieza como una peticion HTTP normal:
      * Si es un "upgrade" a WebSocket (lo pide el navegador), se hace el
        handshake (ws.py) y la conexion pasa a ser el canal de juego en tiempo
        real. Ese mismo hilo se convierte en el LECTOR del jugador.
      * Si es una peticion HTTP corriente, se sirve un archivo estatico
        (la pagina, el CSS/JS, las imagenes) o la API /api/motos.

Asi cumplimos el requisito de hilos + sockets y, ademas, lo dejamos desplegable
en internet (Render) porque todo viaja por un unico puerto HTTP.
"""

import os
import re
import sys
import json
import socket
import threading

# Permite importar los modulos del proyecto (motos, logica, protocolo) que viven
# en la carpeta padre, y los del modo web (ws, bot, salas) que viven aqui.
_WEB_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_WEB_DIR)
for _p in (_ROOT_DIR, _WEB_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import motos
import protocolo

import ws as ws_mod
import salas as salas_mod


# --------------------------------------------------------------------------
# Configuracion de red y rutas
# --------------------------------------------------------------------------
HOST = "0.0.0.0"
# Render (y otros hosts) inyectan el puerto por la variable de entorno PORT.
PORT = int(os.environ.get("PORT", "8000"))

STATIC_DIR = os.path.join(_WEB_DIR, "static")
IMG_DIR = os.path.join(_ROOT_DIR, "imagenes")

GESTOR = salas_mod.GestorSalas()

# Tipos MIME por extension, para servir los archivos estaticos correctamente.
_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".woff2": "font/woff2",
}


def _slug(nombre: str) -> str:
    """Convierte 'Honda CBR 600RR' -> 'honda_cbr_600rr' (nombre de archivo PNG)."""
    return re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_")


# --------------------------------------------------------------------------
# Lectura de la cabecera HTTP
# --------------------------------------------------------------------------
def _leer_cabecera_http(conn):
    """Lee la cabecera HTTP (hasta la linea en blanco). Devuelve
    (metodo, ruta, headers_dict, bytes_sobrantes) o (None, ...) si falla."""
    datos = b""
    while b"\r\n\r\n" not in datos:
        try:
            trozo = conn.recv(4096)
        except OSError:
            return None, None, None, b""
        if not trozo:
            return None, None, None, b""
        datos += trozo
        if len(datos) > 65536:   # cabecera absurdamente grande: corta
            break

    cabecera, _, resto = datos.partition(b"\r\n\r\n")
    lineas = cabecera.decode("latin-1").split("\r\n")
    partes = (lineas[0].split(" ") + ["", ""])[:3]
    metodo, ruta = partes[0], partes[1]

    headers = {}
    for linea in lineas[1:]:
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            headers[clave.strip().lower()] = valor.strip()
    return metodo, ruta, headers, resto


# --------------------------------------------------------------------------
# Manejo de una conexion (corre en su propio hilo)
# --------------------------------------------------------------------------
def manejar_conexion(conn, addr):
    """Atiende una conexion: o la asciende a WebSocket (juego) o sirve HTTP."""
    metodo, ruta, headers, resto = _leer_cabecera_http(conn)
    if metodo is None:
        conn.close()
        return

    ruta_limpia = ruta.split("?", 1)[0]

    # ¿Peticion de upgrade a WebSocket en /ws?
    if headers.get("upgrade", "").lower() == "websocket" and ruta_limpia == "/ws":
        clave = headers.get("sec-websocket-key")
        if not clave:
            conn.close()
            return
        accept = ws_mod.calcular_accept(clave)
        respuesta = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        )
        try:
            conn.sendall(respuesta.encode("latin-1"))
        except OSError:
            conn.close()
            return
        socket_ws = ws_mod.WebSocket(conn, resto)
        manejar_websocket(socket_ws)
        return

    # Peticion HTTP normal (solo GET).
    if metodo != "GET":
        _responder(conn, 405, "text/plain; charset=utf-8", b"Method Not Allowed")
        conn.close()
        return

    _servir_http(conn, ruta_limpia)
    conn.close()


# --------------------------------------------------------------------------
# Logica del juego sobre el WebSocket
# --------------------------------------------------------------------------
def manejar_websocket(socket_ws):
    """Lee el JOIN, empareja al jugador y luego actua como su hilo lector."""
    primer = socket_ws.recibir()
    if not primer:
        socket_ws.cerrar()
        return
    try:
        datos = json.loads(primer)
    except ValueError:
        socket_ws.cerrar()
        return
    if datos.get("tipo") != protocolo.JOIN:
        socket_ws.enviar(json.dumps(protocolo.crear(
            protocolo.ERROR, msg="Se esperaba un mensaje JOIN.")))
        socket_ws.cerrar()
        return

    nombre = (datos.get("nombre") or "Jugador").strip()[:20] or "Jugador"
    modo = datos.get("modo", "publica")
    codigo = (datos.get("codigo") or "").strip().upper()
    rapida = bool(datos.get("rapida"))

    jugador = salas_mod.JugadorWeb(socket_ws, nombre)
    estado, dato = GESTOR.unir(jugador, modo, codigo, rapida)

    if estado == "ERROR":
        jugador.enviar(protocolo.crear(protocolo.ERROR, msg=dato))
        socket_ws.cerrar()
        return

    if estado == "ESPERA":
        # dato = codigo de sala privada (para mostrar QR) o None (publica).
        jugador.enviar(protocolo.crear(
            protocolo.ESPERANDO,
            msg="Esperando a otro jugador...",
            codigo=dato))
        jugador.evento_sala.wait()       # se despierta al emparejar
        if jugador.cancelado or jugador.sala is None:
            socket_ws.cerrar()
            return
        sala = jugador.sala
    else:  # INICIAR: este hilo es el iniciador; arranca la partida.
        sala = dato
        sala.start()

    # A partir de aqui, este hilo es el LECTOR del jugador: vuelca sus mensajes
    # en la cola de eventos de la sala (igual que el lector del modo clasico).
    _bucle_lector(jugador, sala)


def _bucle_lector(jugador, sala):
    """Lee mensajes del WebSocket del jugador y los pone en la cola de la sala."""
    while True:
        crudo = jugador.ws.recibir()
        if crudo is None:
            sala.eventos.put((jugador, None))   # desconexion
            break
        try:
            mensaje = json.loads(crudo)
        except ValueError:
            continue
        sala.eventos.put((jugador, mensaje))


# --------------------------------------------------------------------------
# Servir archivos estaticos y la API
# --------------------------------------------------------------------------
def _servir_http(conn, ruta):
    """Sirve la pagina, los estaticos, las imagenes y la API /api/motos."""
    if ruta == "/" or ruta == "":
        _enviar_archivo(conn, os.path.join(STATIC_DIR, "index.html"))
        return

    if ruta == "/api/motos":
        _responder(conn, 200, _MIME[".json"], _api_motos())
        return

    if ruta == "/api/avatares":
        _responder(conn, 200, _MIME[".json"], _api_avatares())
        return

    if ruta.startswith("/img/"):
        _enviar_archivo(conn, _ruta_segura(IMG_DIR, ruta[len("/img/"):]))
        return

    # Cualquier otra ruta: archivo dentro de static/.
    _enviar_archivo(conn, _ruta_segura(STATIC_DIR, ruta.lstrip("/")))


def _api_motos():
    """Devuelve (en bytes JSON) los datos de las motos para el cliente."""
    valores = {a: sorted({motos.motos[m][a] for m in motos.motos})
               for a in motos.ATRIBUTOS}
    imagenes = {m: "/img/" + _slug(m) + ".png" for m in motos.motos}
    payload = {
        "motos": motos.motos,
        "atributos": motos.ATRIBUTOS,
        "valores": valores,
        "imagenes": imagenes,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _api_avatares():
    """Lista (JSON) las imagenes disponibles en imagenes/avatares/.

    Asi el lobby muestra automaticamente cualquier imagen que el usuario ponga
    en esa carpeta, sin tocar el codigo.
    """
    carpeta = os.path.join(IMG_DIR, "avatares")
    extensiones = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
    items = []
    try:
        for f in sorted(os.listdir(carpeta)):
            if os.path.splitext(f)[1].lower() in extensiones:
                items.append("/img/avatares/" + f)
    except OSError:
        pass
    return json.dumps(items).encode("utf-8")


def _ruta_segura(base, relativo):
    """Une base + relativo evitando salir de la carpeta base (path traversal)."""
    destino = os.path.normpath(os.path.join(base, relativo))
    if not destino.startswith(os.path.normpath(base)):
        return None
    return destino


def _enviar_archivo(conn, ruta_archivo):
    """Envia un archivo del disco con su MIME, o un 404 si no existe."""
    if not ruta_archivo or not os.path.isfile(ruta_archivo):
        _responder(conn, 404, "text/plain; charset=utf-8", b"404 Not Found")
        return
    ext = os.path.splitext(ruta_archivo)[1].lower()
    ctype = _MIME.get(ext, "application/octet-stream")
    try:
        with open(ruta_archivo, "rb") as f:
            cuerpo = f.read()
    except OSError:
        _responder(conn, 500, "text/plain; charset=utf-8", b"500 Error")
        return
    _responder(conn, 200, ctype, cuerpo)


def _responder(conn, codigo, ctype, cuerpo):
    """Construye y envia una respuesta HTTP simple."""
    if isinstance(cuerpo, str):
        cuerpo = cuerpo.encode("utf-8")
    razon = {200: "OK", 404: "Not Found", 405: "Method Not Allowed",
             500: "Internal Server Error"}.get(codigo, "OK")
    cabecera = (
        f"HTTP/1.1 {codigo} {razon}\r\n"
        f"Content-Type: {ctype}\r\n"
        f"Content-Length: {len(cuerpo)}\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: close\r\n\r\n"
    )
    try:
        conn.sendall(cabecera.encode("latin-1") + cuerpo)
    except OSError:
        pass


# --------------------------------------------------------------------------
# Punto de entrada
# --------------------------------------------------------------------------
def main():
    """Crea el socket servidor, escucha y acepta conexiones en bucle."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen()

    print("=" * 56)
    print("  SERVIDOR WEB  -  'Adivina la Moto'")
    print(f"  Abre en el navegador:  http://localhost:{PORT}")
    print("  (Ctrl+C para detener)")
    print("=" * 56)

    try:
        while True:
            conn, addr = servidor.accept()
            # Un hilo por conexion: el handshake/lectura bloquea, asi que se
            # delega para que el hilo principal siga aceptando a otros.
            threading.Thread(target=manejar_conexion, args=(conn, addr),
                             daemon=True).start()
    except KeyboardInterrupt:
        print("\n[SERVIDOR WEB] Detenido por el usuario.")
    finally:
        servidor.close()


if __name__ == "__main__":
    main()
