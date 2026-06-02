# -*- coding: utf-8 -*-
"""
Servidor del juego "Adivina Quien - Motos".

Arquitectura (cliente-servidor con hilos y sockets de la biblioteca estandar):

  - Hilo principal: acepta conexiones TCP en 0.0.0.0:5000.
  - Por cada conexion se lanza un hilo de "handshake" que espera el JOIN
    del jugador y lo mete en la sala de espera (WaitingRoom).
  - Cuando hay dos jugadores en la cola, se crea una GameSession (un hilo
    por partida) que maneja toda la logica de ESA partida de forma aislada.

Asi se pueden jugar varias partidas en paralelo sin que se estorben.

Mensajes: JSON UTF-8 terminados en '\\n' (ver protocolo.py).
"""

import socket
import threading
import random
import queue

import motos
import protocolo
import logica


# --------------------------------------------------------------------------
# Configuracion de red
# --------------------------------------------------------------------------
HOST = "0.0.0.0"   # escucha en todas las interfaces
PORT = 5000


# --------------------------------------------------------------------------
# Jugador: envoltorio de una conexion
# --------------------------------------------------------------------------
class Jugador:
    """Representa a un jugador conectado y su canal de comunicacion."""

    def __init__(self, conn, addr, nombre, receptor):
        """Guarda el socket, la direccion, el nombre y el receptor del jugador."""
        self.conn = conn            # socket TCP
        self.addr = addr            # (ip, puerto)
        self.nombre = nombre
        self.receptor = receptor    # protocolo.Receptor (buffer de entrada)
        self.moto_secreta = None    # nombre de su moto secreta
        self.conectado = True

    def __str__(self):
        """Representacion legible del jugador: nombre + direccion."""
        return f"{self.nombre}{self.addr}"


# --------------------------------------------------------------------------
# WaitingRoom: cola de jugadores en espera
# --------------------------------------------------------------------------
class WaitingRoom:
    """
    Gestiona la cola de jugadores que esperan rival. Usa un Lock para
    evitar condiciones de carrera, ya que varios hilos de handshake pueden
    agregar jugadores al mismo tiempo.
    """

    def __init__(self):
        """Crea la cola vacia y el Lock que la protege."""
        self._cola = []
        # POR QUE UN LOCK: la cola es estado COMPARTIDO entre los multiples
        # hilos de handshake (uno por conexion). Sin sincronizacion, dos hilos
        # podrian leer/modificar la lista a la vez y emparejar mal a un jugador
        # (condicion de carrera). El Lock serializa el acceso a la cola.
        self._lock = threading.Lock()

    def agregar(self, jugador):
        """
        Agrega un jugador a la cola. Si con el se completan dos jugadores,
        los saca de la cola y devuelve la pareja (j1, j2). Si no, None.
        """
        # 'with self._lock' garantiza que solo un hilo a la vez toca la cola.
        with self._lock:
            self._cola.append(jugador)
            print(f"[SALA] {jugador} en espera. En cola: {len(self._cola)}")
            if len(self._cola) >= 2:
                j1 = self._cola.pop(0)
                j2 = self._cola.pop(0)
                print(f"[SALA] Emparejados: {j1.nombre} vs {j2.nombre}")
                return (j1, j2)
            return None


# --------------------------------------------------------------------------
# GameSession: una partida entre dos jugadores (un hilo por partida)
# --------------------------------------------------------------------------
class GameSession(threading.Thread):
    """
    Maneja UNA partida completa entre dos jugadores. Contiene todo el estado
    del juego y su bucle principal en run(). Cada partida vive en su propio
    hilo, por lo que varias pueden correr en paralelo sin estorbarse.

    POR QUE UN HILO POR PARTIDA:
      El bucle de una partida es BLOQUEANTE: pasa la mayor parte del tiempo
      esperando (recv) la jugada del jugador en turno. Si todo corriera en un
      solo hilo, una partida bloqueada congelaria a todas las demas. Al darle
      a cada partida su propio hilo (heredando de threading.Thread), el
      servidor atiende multiples partidas de forma concurrente y cada una
      avanza a su ritmo. Como el estado del juego es privado de cada
      GameSession, no se comparte entre hilos y no hace falta sincronizarlo.
    """

    _contador = 0
    _contador_lock = threading.Lock()

    def __init__(self, jugadores):
        """Asigna un id de partida e inicializa el estado del juego (vacio)."""
        super().__init__(daemon=True)

        # Id unico de partida (protegido porque varias sesiones nacen a la vez).
        with GameSession._contador_lock:
            GameSession._contador += 1
            self.id = GameSession._contador

        self.jugadores = list(jugadores)   # [jugador_0, jugador_1]

        # Si ambos eligieron el mismo nombre, los desambiguamos para que el
        # historial y el marcador no los confundan.
        if self.jugadores[0].nombre == self.jugadores[1].nombre:
            self.jugadores[0].nombre += " (1)"
            self.jugadores[1].nombre += " (2)"

        # --- Estado del juego (se completa en _setup_game) ---
        self.tablero = []                                       # 24 motos barajadas
        self.turno = 0                                          # indice del jugador en turno
        self.descartadas = {j: set() for j in self.jugadores}   # fichas descartadas por c/u
        self.ganador = None
        self.activa = True
        self.terminar = False                                   # True = cerrar toda la sesion
        self.marcador = {j: 0 for j in self.jugadores}          # rondas ganadas por c/u
        self.revancha = set()                                   # jugadores que pidieron revancha
        self._receptores = {}                                   # conn -> protocolo.Receptor
        # Cola interna: los hilos lectores (uno por jugador) dejan aqui los
        # eventos (jugador, mensaje) y el bucle de la partida los procesa.
        self.eventos = queue.Queue()

    def _marcador_dict(self):
        """Marcador como dict {nombre: rondas_ganadas} para enviarlo a los clientes."""
        return {j.nombre: self.marcador[j] for j in self.jugadores}

    # ----------------------------------------------------------------------
    # Primitivas de comunicacion (se apoyan en protocolo.py para no duplicar
    # la serializacion JSON + '\n').
    # ----------------------------------------------------------------------
    def _send(self, conn, data):
        """
        Serializa el dict `data` a JSON, le agrega salto de linea y lo envia
        por `conn`. Devuelve True si se envio, False si la conexion fallo.
        """
        try:
            protocolo.enviar(conn, data)
            return True
        except (ConnectionError, OSError) as e:
            print(f"[PARTIDA #{self.id}] Fallo al enviar: {e}")
            return False

    def _recv(self, conn):
        """
        Recibe del socket `conn` hasta encontrar el salto de linea, decodifica
        el JSON y devuelve el dict. Devuelve None si el jugador se desconecto.
        El buffer por conexion lo maneja protocolo.Receptor (framing de TCP).
        """
        receptor = self._receptores.get(conn)
        if receptor is None:
            return None
        return receptor.recibir()

    def _broadcast(self, data):
        """Envia el MISMO mensaje a ambos jugadores."""
        for jugador in self.jugadores:
            self._send(jugador.conn, data)

    def _otro(self, jugador):
        """Devuelve el rival de un jugador."""
        return self.jugadores[1 - self.jugadores.index(jugador)]

    # ----------------------------------------------------------------------
    # 1) Preparacion de la partida
    # ----------------------------------------------------------------------
    def _setup_game(self):
        """
        Prepara una RONDA: reinicia el estado, genera el tablero de 24 motos en
        orden aleatorio (IGUAL para ambos), asigna a cada jugador una moto
        secreta DIFERENTE y envia el estado inicial (INICIO) a los dos. Sirve
        tanto para la primera ronda como para cada revancha. Devuelve True si
        ambos recibieron el INICIO.
        """
        # Reinicio de estado de ronda (importante para las revanchas).
        self.turno = 0
        self.ganador = None
        self.revancha = set()
        self.descartadas = {j: set() for j in self.jugadores}

        # Tablero: las 24 motos barajadas, mismas posiciones para los dos.
        self.tablero = list(motos.motos.keys())
        random.shuffle(self.tablero)

        # Motos secretas: dos distintas, una por jugador.
        secreta_0, secreta_1 = random.sample(self.tablero, 2)
        self.jugadores[0].moto_secreta = secreta_0
        self.jugadores[1].moto_secreta = secreta_1

        # Mapa conn -> receptor, para que _recv sepa de donde leer.
        self._receptores = {j.conn: j.receptor for j in self.jugadores}

        print(f"[PARTIDA #{self.id}] Secretas -> "
              f"{self.jugadores[0].nombre}: {secreta_0} | "
              f"{self.jugadores[1].nombre}: {secreta_1}")

        # Estado inicial a cada jugador (su moto, el tablero y de quien es el turno).
        for i, jugador in enumerate(self.jugadores):
            ok = self._send(jugador.conn, protocolo.crear(
                protocolo.INICIO,
                tu_id=i,                       # id estable del jugador (0/1)
                tu_moto=jugador.moto_secreta,
                tablero=self.tablero,
                tu_turno=(i == self.turno),
                rival=self._otro(jugador).nombre,
                marcador=self._marcador_dict(),
            ))
            if not ok:
                return False
        return True

    # ----------------------------------------------------------------------
    # 5) Procesar una pregunta
    # ----------------------------------------------------------------------
    def _process_question(self, atributo, valor, asking_player):
        """
        Consulta la moto secreta del OPONENTE: responde SI si su `atributo`
        coincide con `valor`, NO si no. Envia la pregunta y la respuesta a
        AMBOS jugadores y pasa el turno. Una pregunta invalida no gasta turno.
        """
        oponente = self._otro(asking_player)

        # Validacion: el atributo debe existir entre los de las motos.
        if not logica.atributo_valido(atributo):
            self._send(asking_player.conn, protocolo.crear(
                protocolo.ERROR, msg=f"Atributo invalido: {atributo}"))
            return  # no cambia el turno

        # Comparacion (regla pura, testeable) contra la moto secreta del oponente.
        atributos_oponente = motos.motos[oponente.moto_secreta]
        respuesta = logica.evaluar_pregunta(atributos_oponente, atributo, valor)
        texto = f"¿{atributo} = {valor}?"

        print(f"[PARTIDA #{self.id}] {asking_player.nombre} pregunta "
              f"'{texto}' (sobre {oponente.nombre}) -> {respuesta}")

        # Ambos jugadores ven la pregunta y la respuesta. Se incluyen
        # 'atributo' y 'valor' (estructurados) para que el cliente pueda
        # actualizar su tablero de forma determinista; 'pregunta' es el
        # texto legible para mostrar.
        self._broadcast(protocolo.crear(
            protocolo.RESPUESTA,
            quien=asking_player.nombre,
            quien_id=self.jugadores.index(asking_player),   # id estable del que pregunto
            atributo=atributo,
            valor=valor,
            pregunta=texto,
            respuesta=respuesta,
        ))

        self._change_turn()

    # ----------------------------------------------------------------------
    # 6) Procesar un intento de adivinar
    # ----------------------------------------------------------------------
    def _process_guess(self, nombre_moto, guessing_player):
        """
        El jugador intenta adivinar la moto secreta del oponente. Si acierta,
        gana; si falla, pierde de inmediato (regla clasica de Adivina Quien).
        Si el nombre no corresponde a ninguna moto, se rechaza con ERROR y no
        termina la partida (asi un error de tipeo no hace perder injustamente).
        """
        # Validacion: el personaje debe existir en el tablero.
        if not logica.personaje_existe(nombre_moto):
            self._send(guessing_player.conn, protocolo.crear(
                protocolo.ERROR, msg=f"Esa moto no existe en el tablero: {nombre_moto}"))
            return  # no consume el turno ni termina la partida

        oponente = self._otro(guessing_player)
        print(f"[PARTIDA #{self.id}] {guessing_player.nombre} intenta adivinar: {nombre_moto}")

        if nombre_moto == oponente.moto_secreta:
            self._end_game(guessing_player,
                           "adivinaste la moto secreta del rival",
                           "el rival adivino tu moto")
        else:
            self._end_game(oponente,
                           "el rival fallo al adivinar",
                           "fallaste al adivinar")

    # ----------------------------------------------------------------------
    # Control de turnos y fin de partida
    # ----------------------------------------------------------------------
    def _change_turn(self):
        """Alterna el turno y avisa a cada jugador si le toca o no."""
        self.turno = 1 - self.turno
        for i, jugador in enumerate(self.jugadores):
            self._send(jugador.conn, protocolo.crear(
                protocolo.TURNO, tu_turno=(i == self.turno)))
        print(f"[PARTIDA #{self.id}] Turno de {self.jugadores[self.turno].nombre}")

    def _enviar_fin(self, ganador, motivo_ganador, motivo_perdedor, ofrecer_revancha):
        """Fija el ganador, suma al marcador y envia el FIN a cada jugador.

        El motivo se manda DISTINTO segun la perspectiva: el ganador recibe
        `motivo_ganador` y el perdedor `motivo_perdedor` (asi el que se rinde no
        lee 'el rival se rindio', por ejemplo).

        `ofrecer_revancha` indica al cliente si puede pedir otra ronda (True al
        ganar/perder normal; False si la sesion se cierra por corte/abandono).
        """
        self.ganador = ganador
        if ganador is not None:
            self.marcador[ganador] += 1
        for jugador in self.jugadores:
            gano = (jugador is ganador)
            msg = ("Ganaste! " + motivo_ganador) if gano else ("Perdiste. " + motivo_perdedor)
            self._send(jugador.conn, protocolo.crear(
                protocolo.FIN,
                ganaste=gano,
                moto_rival=self._otro(jugador).moto_secreta,
                msg=msg,
                marcador=self._marcador_dict(),
                revancha=ofrecer_revancha,
            ))
        print(f"[PARTIDA #{self.id}] Ganador: {ganador.nombre} ({motivo_ganador}) "
              f"| Marcador: {self._marcador_dict()}")

    def _end_game(self, ganador, motivo_ganador, motivo_perdedor=""):
        """Fin de RONDA por victoria normal: ofrece revancha."""
        self._enviar_fin(ganador, motivo_ganador, motivo_perdedor, ofrecer_revancha=True)

    def _fin_por_corte(self, ganador, motivo_ganador, motivo_perdedor=""):
        """Fin de SESION por desconexion/abandono: no ofrece revancha."""
        self._enviar_fin(ganador, motivo_ganador, motivo_perdedor, ofrecer_revancha=False)
        self.terminar = True

    # ----------------------------------------------------------------------
    # 7) Bucle principal de la partida
    # ----------------------------------------------------------------------
    def run(self):
        """
        Prepara la primera ronda, lanza los lectores y juega RONDAS sucesivas:
        cada ronda alterna turnos hasta que hay ganador; al terminar, ofrece
        revancha y, si ambos aceptan, arranca otra ronda. Termina cuando alguien
        se desconecta, abandona o no quiere revancha.
        """
        j0, j1 = self.jugadores
        print(f"[PARTIDA #{self.id}] Inicia: {j0.nombre} vs {j1.nombre}")

        # Preparacion + envio del estado inicial de la primera ronda.
        if not self._setup_game():
            print(f"[PARTIDA #{self.id}] Un jugador cayo antes de iniciar; se cancela.")
            self._cerrar()
            return

        # POR QUE UN HILO LECTOR POR JUGADOR: si el servidor solo leyera al
        # jugador en turno, no podria validar acciones fuera de turno ni notar
        # que el jugador que ESPERA se desconecta. Con un lector por jugador,
        # ambos sockets se escuchan a la vez; los eventos entran a una cola y el
        # bucle los procesa de forma ordenada y validando de quien vienen.
        for jugador in self.jugadores:
            threading.Thread(target=self._lector, args=(jugador,), daemon=True).start()

        try:
            while not self.terminar:
                self._bucle_partida()          # juega una ronda hasta que haya ganador
                if self.terminar:
                    break                      # alguien se fue o se desconecto
                if not self._fase_revancha():  # espera REVANCHA de AMBOS
                    break
                if not self._setup_game():     # arranca la nueva ronda
                    break
        finally:
            self._cerrar()

    def _bucle_partida(self):
        """Procesa eventos de UNA ronda hasta que haya ganador o se corte la sesion."""
        while self.ganador is None and not self.terminar:
            jugador, mensaje = self.eventos.get()
            if mensaje is None:
                print(f"[PARTIDA #{self.id}] {jugador.nombre} se desconecto.")
                self._fin_por_corte(self._otro(jugador), "el rival se desconecto")
                return
            self._procesar_evento(jugador, mensaje)

    def _fase_revancha(self):
        """Tras una ronda, espera a que AMBOS pidan REVANCHA.

        Devuelve True si los dos aceptaron (hay que jugar otra ronda) o False si
        alguien abandono o se desconecto (hay que cerrar la sesion).
        """
        self.revancha = set()
        while len(self.revancha) < 2 and not self.terminar:
            jugador, mensaje = self.eventos.get()
            if mensaje is None:
                self.terminar = True
                return False

            tipo = mensaje.get("tipo")
            if tipo == protocolo.REVANCHA:
                self.revancha.add(jugador)
                otro = self._otro(jugador)
                if otro not in self.revancha:
                    self._send(otro.conn, protocolo.crear(
                        protocolo.ESPERANDO,
                        msg=f"{jugador.nombre} quiere la revancha. ¿Aceptas?"))
                self._send(jugador.conn, protocolo.crear(
                    protocolo.ESPERANDO, msg="Esperando que el rival acepte la revancha..."))
            elif tipo == protocolo.SALIR:
                print(f"[PARTIDA #{self.id}] {jugador.nombre} no quiso revancha.")
                self._send(self._otro(jugador).conn, protocolo.crear(
                    protocolo.ESPERANDO, msg="El rival no quiso revancha. Fin de la sesion."))
                self.terminar = True
                return False
            else:
                # Cualquier otra accion despues de terminar la ronda se ignora.
                self._send(jugador.conn, protocolo.crear(
                    protocolo.ERROR, msg="La ronda termino. Pide revancha o sal."))

        if not self.terminar:
            print(f"[PARTIDA #{self.id}] Ambos aceptaron: nueva ronda.")
        return not self.terminar

    def _lector(self, jugador):
        """Hilo lector de un jugador: vuelca cada mensaje en la cola de eventos."""
        while True:
            mensaje = self._recv(jugador.conn)
            self.eventos.put((jugador, mensaje))
            if mensaje is None:        # se cerro la conexion: termina el lector
                break

    def _es_turno(self, jugador):
        """Indica si es el turno de ese jugador."""
        return jugador is self.jugadores[self.turno]

    def _procesar_evento(self, jugador, mensaje):
        """Valida y aplica una accion recibida de un jugador."""
        tipo = mensaje.get("tipo")

        if tipo in (protocolo.PREGUNTA, protocolo.ADIVINAR):
            # El servidor VALIDA el turno: una jugada fuera de turno se rechaza.
            if not self._es_turno(jugador):
                self._send(jugador.conn, protocolo.crear(
                    protocolo.ERROR, msg="No es tu turno."))
                return
            if tipo == protocolo.PREGUNTA:
                self._process_question(
                    mensaje.get("atributo"), mensaje.get("valor"), jugador)
            else:
                self._process_guess(mensaje.get("moto"), jugador)

        elif tipo == protocolo.DESCARTAR:
            # Descartar es una ayuda local del jugador: se permite siempre.
            moto = mensaje.get("moto")
            self.descartadas[jugador].add(moto)
            print(f"[PARTIDA #{self.id}] {jugador.nombre} descarto: {moto}")

        elif tipo == protocolo.RENDIRSE:
            # Rendirse es valido en cualquier momento (no depende del turno):
            # el que se rinde PIERDE la ronda y el rival gana. Se ofrece revancha.
            print(f"[PARTIDA #{self.id}] {jugador.nombre} se rindio.")
            self._end_game(self._otro(jugador), "el rival se rindio", "te rendiste")

        elif tipo == protocolo.SALIR:
            print(f"[PARTIDA #{self.id}] {jugador.nombre} abandono.")
            self._fin_por_corte(self._otro(jugador), "el rival abandono")

        else:
            self._send(jugador.conn, protocolo.crear(
                protocolo.ERROR, msg=f"Tipo de mensaje desconocido: {tipo}"))

    def _cerrar(self):
        """Cierra los sockets de la partida de forma segura."""
        self.activa = False
        for jugador in self.jugadores:
            try:
                jugador.conn.close()
            except OSError:
                pass
        print(f"[PARTIDA #{self.id}] Sesion finalizada.")


# --------------------------------------------------------------------------
# Handshake inicial por conexion
# --------------------------------------------------------------------------
def handshake(conn, addr, sala):
    """
    Espera el JOIN del cliente, crea el Jugador y lo mete en la sala.
    Corre en su propio hilo para no bloquear la aceptacion de conexiones.
    """
    receptor = protocolo.Receptor(conn)
    try:
        mensaje = receptor.recibir()
        if not mensaje or mensaje.get("tipo") != protocolo.JOIN:
            protocolo.enviar(conn, protocolo.crear(
                protocolo.ERROR, msg="Se esperaba un mensaje JOIN."))
            conn.close()
            return

        nombre = mensaje.get("nombre") or f"Jugador-{addr[1]}"
        jugador = Jugador(conn, addr, nombre, receptor)
        print(f"[SERVIDOR] {nombre} se unio desde {addr}.")

        pareja = sala.agregar(jugador)
        if pareja:
            # Con este jugador se completo una pareja: arranca la partida.
            GameSession(pareja).start()
        else:
            # Sigue esperando rival.
            protocolo.enviar(conn, protocolo.crear(
                protocolo.ESPERANDO, msg="Esperando a otro jugador..."))

    except (ConnectionError, OSError) as e:
        print(f"[SERVIDOR] Error en handshake con {addr}: {e}")
        try:
            conn.close()
        except OSError:
            pass


# --------------------------------------------------------------------------
# Punto de entrada: bucle de aceptacion de conexiones
# --------------------------------------------------------------------------
def main():
    """Crea el socket servidor, escucha y acepta conexiones en bucle."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite reusar el puerto inmediatamente al reiniciar el servidor.
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen()

    print("=" * 50)
    print("  SERVIDOR 'Adivina Quien - Motos'")
    print(f"  Escuchando en {HOST}:{PORT}")
    print("  (Ctrl+C para detener)")
    print("=" * 50)

    # Hilo de autodescubrimiento UDP: deja que los clientes encuentren este
    # servidor en la red local sin escribir la IP. daemon=True: muere con el
    # servidor.
    threading.Thread(target=protocolo.servidor_descubrimiento, args=(PORT,),
                     daemon=True).start()

    sala = WaitingRoom()
    try:
        while True:
            # accept() es BLOQUEANTE: el hilo principal se dedica solo a aceptar
            # conexiones nuevas.
            conn, addr = servidor.accept()
            print(f"[SERVIDOR] Conexion entrante de {addr}")
            # POR QUE UN HILO POR CONEXION: el handshake hace recv() (espera el
            # JOIN), que bloquea. Si lo hicieramos en el hilo principal, un
            # cliente lento congelaria el accept() y nadie mas podria entrar.
            # Delegando cada handshake a su propio hilo, el servidor sigue
            # aceptando jugadores en paralelo. daemon=True: el hilo no impide
            # que el programa termine al cerrar el servidor.
            threading.Thread(target=handshake, args=(conn, addr, sala),
                             daemon=True).start()
    except KeyboardInterrupt:
        print("\n[SERVIDOR] Detenido por el usuario.")
    finally:
        servidor.close()
        print("[SERVIDOR] Socket cerrado. Adios.")


if __name__ == "__main__":
    main()
