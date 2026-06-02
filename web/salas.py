# -*- coding: utf-8 -*-
"""
Gestion de salas y partidas del modo WEB de "Adivina la Moto".

Replica el modelo de concurrencia del modo clasico (server.py) pero para el
canal WebSocket:

  - GestorSalas: estado COMPARTIDO entre conexiones (cola publica, cola rapida y
    salas privadas por codigo). Se protege con un threading.Lock.
  - GameRoom (threading.Thread): UNA partida = UN hilo. El estado del juego es
    privado del hilo, asi varias partidas corren en paralelo sin estorbarse.
  - Cada jugador HUMANO tiene un hilo lector (en servidor_web.py) que vuelca sus
    mensajes en la cola de eventos de la sala. El bot no necesita lector: juega
    cuando es su turno.

Reutiliza logica.py (reglas puras) y motos.py (datos), igual que el servidor
clasico, para no duplicar las reglas del juego.
"""

import json
import time
import queue
import random
import threading

import motos
import logica
import protocolo

import bot


# Duracion (segundos) del reloj por turno en los modos "rapida".
RELOJ = 30

# Tipo de mensaje extra del modo web (los demas se reutilizan de protocolo.py).
EMOJI = "EMOJI"

crear = protocolo.crear  # alias: construye dicts {tipo, ...}


# --------------------------------------------------------------------------
# Jugador web: envuelve una conexion WebSocket (o un bot, sin conexion)
# --------------------------------------------------------------------------
class JugadorWeb:
    """Representa a un jugador conectado por WebSocket, o a un bot local."""

    def __init__(self, ws, nombre, es_bot=False):
        """Guarda el WebSocket (None si es bot), el nombre y el estado del jugador."""
        self.ws = ws                       # web.ws.WebSocket  (None si es bot)
        self.nombre = nombre
        self.es_bot = es_bot
        self.bot = bot.Bot(nombre) if es_bot else None
        self.moto_secreta = None
        # Para los jugadores que esperan rival: la sala se asigna al emparejar y
        # el Event despierta al hilo que estaba bloqueado esperando.
        self.sala = None
        self.evento_sala = threading.Event()
        self.cancelado = False

    def enviar(self, data: dict) -> bool:
        """Envia un dict (JSON) al jugador. Para el bot es un no-op que devuelve True."""
        if self.es_bot or self.ws is None:
            return True
        try:
            return self.ws.enviar(json.dumps(data, ensure_ascii=False))
        except Exception:
            return False


# --------------------------------------------------------------------------
# GameRoom: una partida (un hilo). Adaptacion de GameSession al canal WebSocket.
# --------------------------------------------------------------------------
class GameRoom(threading.Thread):
    """Maneja UNA partida entre dos jugadores (humano/humano o humano/bot)."""

    _contador = 0
    _contador_lock = threading.Lock()

    def __init__(self, jugadores, reloj=None):
        """Inicializa el estado de la partida. `reloj`=segundos por turno o None."""
        super().__init__(daemon=True)
        with GameRoom._contador_lock:
            GameRoom._contador += 1
            self.id = GameRoom._contador

        self.jugadores = list(jugadores)
        if self.jugadores[0].nombre == self.jugadores[1].nombre:
            self.jugadores[0].nombre += " (1)"
            self.jugadores[1].nombre += " (2)"

        self.reloj = reloj
        self.tablero = []
        self.turno = 0
        self.ganador = None
        self.terminar = False
        self.marcador = {j: 0 for j in self.jugadores}
        self.revancha = set()
        self.eventos = queue.Queue()
        self._turno_inicio = None

    # ---------------- utilidades ----------------
    def _otro(self, jugador):
        """Devuelve el rival de un jugador."""
        return self.jugadores[1 - self.jugadores.index(jugador)]

    def _marcador_dict(self):
        """Marcador {nombre: rondas} para enviarlo a los clientes."""
        return {j.nombre: self.marcador[j] for j in self.jugadores}

    def _broadcast(self, data):
        """Envia el mismo mensaje a ambos jugadores."""
        for jugador in self.jugadores:
            jugador.enviar(data)

    # ---------------- preparacion de ronda ----------------
    def _setup(self):
        """Prepara una ronda: tablero aleatorio (igual para ambos), motos secretas
        distintas y envio del estado inicial. Devuelve True si todo ok."""
        self.turno = 0
        self.ganador = None
        self.revancha = set()
        self.tablero = list(motos.motos.keys())
        random.shuffle(self.tablero)

        secreta_0, secreta_1 = random.sample(self.tablero, 2)
        self.jugadores[0].moto_secreta = secreta_0
        self.jugadores[1].moto_secreta = secreta_1

        # Reinicia el razonamiento del bot para la nueva ronda.
        for j in self.jugadores:
            if j.es_bot:
                j.bot = bot.Bot(j.nombre)

        print(f"[WEB #{self.id}] Secretas -> {self.jugadores[0].nombre}: {secreta_0} | "
              f"{self.jugadores[1].nombre}: {secreta_1}")

        for i, jugador in enumerate(self.jugadores):
            ok = jugador.enviar(crear(
                protocolo.INICIO,
                tu_id=i,
                tu_moto=jugador.moto_secreta,
                tablero=self.tablero,
                tu_turno=(i == self.turno),
                rival=self._otro(jugador).nombre,
                marcador=self._marcador_dict(),
                reloj=self.reloj,
            ))
            if not ok and not jugador.es_bot:
                return False
        self._turno_inicio = time.monotonic()
        return True

    # ---------------- bucle principal ----------------
    def run(self):
        """Juega rondas sucesivas hasta que alguien gana sin revancha o se corta."""
        if not self._setup():
            self._cerrar()
            return
        try:
            while not self.terminar:
                self._jugar_ronda()
                if self.terminar:
                    break
                if not self._fase_revancha():
                    break
                if not self._setup():
                    break
        finally:
            self._cerrar()

    def _jugar_ronda(self):
        """Procesa eventos de una ronda hasta que haya ganador o se corte."""
        while self.ganador is None and not self.terminar:
            actual = self.jugadores[self.turno]

            # Turno del bot: juega solo (no espera eventos).
            if actual.es_bot:
                self._jugar_bot(actual)
                continue

            # Turno de un humano: espera su jugada (con reloj si aplica).
            if self.reloj:
                restante = self.reloj - (time.monotonic() - self._turno_inicio)
                if restante <= 0:
                    self._timeout_turno()
                    continue
                try:
                    jugador, mensaje = self.eventos.get(timeout=restante)
                except queue.Empty:
                    self._timeout_turno()
                    continue
            else:
                jugador, mensaje = self.eventos.get()

            if mensaje is None:
                self._fin_por_corte(self._otro(jugador), "el rival se desconecto")
                return
            self._procesar(jugador, mensaje)

    def _timeout_turno(self):
        """Se acabo el tiempo del turno: el jugador pierde el turno (no la partida)."""
        actual = self.jugadores[self.turno]
        actual.enviar(crear(protocolo.ERROR, msg="Se acabo tu tiempo: pierdes el turno."))
        print(f"[WEB #{self.id}] Tiempo agotado de {actual.nombre}.")
        self._cambiar_turno()

    def _jugar_bot(self, botj):
        """El bot decide y ejecuta su jugada (con una pausa para que se vea natural)."""
        time.sleep(1.2)
        if self.terminar:
            return
        jugada = botj.bot.decidir_jugada()
        if jugada[0] == "PREGUNTA":
            _, atributo, valor = jugada
            self._procesar_pregunta(atributo, valor, botj)
        else:
            _, moto = jugada
            self._procesar_adivinar(moto, botj)

    # ---------------- procesar acciones ----------------
    def _procesar(self, jugador, mensaje):
        """Valida y aplica una accion recibida de un jugador humano."""
        tipo = mensaje.get("tipo")

        if tipo in (protocolo.PREGUNTA, protocolo.ADIVINAR):
            if jugador is not self.jugadores[self.turno]:
                jugador.enviar(crear(protocolo.ERROR, msg="No es tu turno."))
                return
            if tipo == protocolo.PREGUNTA:
                self._procesar_pregunta(mensaje.get("atributo"), mensaje.get("valor"), jugador)
            else:
                self._procesar_adivinar(mensaje.get("moto"), jugador)

        elif tipo == EMOJI:
            self._otro(jugador).enviar(crear(
                EMOJI, quien=jugador.nombre, emoji=mensaje.get("emoji")))

        elif tipo == protocolo.DESCARTAR:
            pass  # ayuda local del jugador; el cliente la pinta

        elif tipo == protocolo.RENDIRSE:
            self._fin(self._otro(jugador), "el rival se rindio", "te rendiste")

        elif tipo == protocolo.SALIR:
            self._fin_por_corte(self._otro(jugador), "el rival abandono")

        else:
            jugador.enviar(crear(protocolo.ERROR, msg=f"Tipo desconocido: {tipo}"))

    def _procesar_pregunta(self, atributo, valor, quien):
        """Responde SI/NO comparando con la moto secreta del rival y pasa el turno."""
        if not logica.atributo_valido(atributo):
            quien.enviar(crear(protocolo.ERROR, msg=f"Atributo invalido: {atributo}"))
            return
        oponente = self._otro(quien)
        respuesta = logica.evaluar_pregunta(
            motos.motos[oponente.moto_secreta], atributo, valor)
        self._broadcast(crear(
            protocolo.RESPUESTA,
            quien=quien.nombre,
            quien_id=self.jugadores.index(quien),
            atributo=atributo,
            valor=valor,
            pregunta=f"¿{atributo} = {valor}?",
            respuesta=respuesta,
        ))
        if quien.es_bot:
            quien.bot.registrar_respuesta(atributo, valor, respuesta)
        self._cambiar_turno()

    def _procesar_adivinar(self, nombre_moto, quien):
        """Intento de adivinar: acertar gana, fallar pierde de inmediato."""
        if not logica.personaje_existe(nombre_moto):
            quien.enviar(crear(protocolo.ERROR,
                               msg=f"Esa moto no existe: {nombre_moto}"))
            return
        oponente = self._otro(quien)
        if nombre_moto == oponente.moto_secreta:
            self._fin(quien, "adivinaste la moto secreta del rival",
                      "el rival adivino tu moto")
        else:
            self._fin(oponente, "el rival fallo al adivinar", "fallaste al adivinar")

    # ---------------- turnos y fin ----------------
    def _cambiar_turno(self):
        """Alterna el turno, reinicia el reloj y avisa a ambos jugadores."""
        self.turno = 1 - self.turno
        self._turno_inicio = time.monotonic()
        for i, jugador in enumerate(self.jugadores):
            jugador.enviar(crear(protocolo.TURNO,
                                 tu_turno=(i == self.turno), reloj=self.reloj))

    def _enviar_fin(self, ganador, motivo_g, motivo_p, revancha):
        """Fija ganador, suma marcador y envia FIN a cada jugador (segun perspectiva)."""
        self.ganador = ganador
        if ganador is not None:
            self.marcador[ganador] += 1
        for jugador in self.jugadores:
            gano = (jugador is ganador)
            msg = ("¡Ganaste! " + motivo_g) if gano else ("Perdiste. " + motivo_p)
            jugador.enviar(crear(
                protocolo.FIN,
                ganaste=gano,
                moto_rival=self._otro(jugador).moto_secreta,
                msg=msg,
                marcador=self._marcador_dict(),
                revancha=revancha,
            ))
        print(f"[WEB #{self.id}] Fin. Ganador: "
              f"{ganador.nombre if ganador else 'nadie'} | {self._marcador_dict()}")

    def _fin(self, ganador, motivo_g, motivo_p=""):
        """Fin de ronda normal: ofrece revancha."""
        self._enviar_fin(ganador, motivo_g, motivo_p, revancha=True)

    def _fin_por_corte(self, ganador, motivo_g, motivo_p=""):
        """Fin por desconexion/abandono: cierra la sesion sin revancha."""
        self._enviar_fin(ganador, motivo_g, motivo_p, revancha=False)
        self.terminar = True

    def _fase_revancha(self):
        """Espera REVANCHA de AMBOS. El bot acepta siempre. True si se juega otra."""
        self.revancha = set()
        for j in self.jugadores:
            if j.es_bot:
                self.revancha.add(j)

        while len(self.revancha) < 2 and not self.terminar:
            jugador, mensaje = self.eventos.get()
            if mensaje is None:
                self.terminar = True
                return False
            tipo = mensaje.get("tipo")
            if tipo == protocolo.REVANCHA:
                self.revancha.add(jugador)
                otro = self._otro(jugador)
                if otro not in self.revancha and not otro.es_bot:
                    otro.enviar(crear(protocolo.ESPERANDO,
                                      msg=f"{jugador.nombre} quiere la revancha."))
                jugador.enviar(crear(protocolo.ESPERANDO,
                                     msg="Esperando que el rival acepte..."))
            elif tipo == protocolo.SALIR:
                self._otro(jugador).enviar(crear(
                    protocolo.ESPERANDO, msg="El rival no quiso revancha."))
                self.terminar = True
                return False
            elif tipo == EMOJI:
                self._otro(jugador).enviar(crear(
                    EMOJI, quien=jugador.nombre, emoji=mensaje.get("emoji")))
            # otros mensajes se ignoran entre rondas
        return not self.terminar

    def _cerrar(self):
        """Cierra los WebSocket de los jugadores humanos."""
        for jugador in self.jugadores:
            if jugador.ws is not None:
                jugador.ws.cerrar()
        print(f"[WEB #{self.id}] Sesion finalizada.")


# --------------------------------------------------------------------------
# GestorSalas: empareja jugadores (estado compartido protegido por Lock)
# --------------------------------------------------------------------------
class GestorSalas:
    """Cola publica, cola rapida y salas privadas por codigo. Protegido con Lock."""

    def __init__(self):
        """Inicializa las colas/registros vacios y el Lock que los protege."""
        self.lock = threading.Lock()
        self.esp_publica = None          # JugadorWeb esperando partida publica
        self.esp_rapida = None           # JugadorWeb esperando partida rapida
        self.privadas = {}               # codigo -> (JugadorWeb, rapida_bool)

    def _vivo(self, jugador):
        """True si la conexion del jugador sigue abierta."""
        return jugador is not None and jugador.ws is not None and not jugador.ws.cerrado

    def unir(self, jugador, modo, codigo, rapida):
        """Empareja al jugador segun el modo. Devuelve una tupla:
          ("INICIAR", sala)  -> hay pareja; el llamante hace sala.start()
          ("ESPERA", dato)   -> sigue esperando (dato = codigo de sala o None)
          ("ERROR", msg)     -> no se pudo (mensaje para el cliente)
        """
        with self.lock:
            if modo == "bot":
                bot_j = JugadorWeb(None, "Bot", es_bot=True)
                sala = GameRoom([jugador, bot_j], reloj=(RELOJ if rapida else None))
                jugador.sala = sala
                return ("INICIAR", sala)

            if modo in ("publica", "rapida"):
                es_rapida = (modo == "rapida")
                attr = "esp_rapida" if es_rapida else "esp_publica"
                esperando = getattr(self, attr)
                if not self._vivo(esperando):
                    setattr(self, attr, jugador)
                    return ("ESPERA", None)
                setattr(self, attr, None)
                sala = GameRoom([esperando, jugador],
                                reloj=(RELOJ if es_rapida else None))
                esperando.sala = sala
                jugador.sala = sala
                esperando.evento_sala.set()
                return ("INICIAR", sala)

            if modo == "privada_crear":
                if not codigo:
                    return ("ERROR", "Debes ingresar un codigo para la sala.")
                if codigo in self.privadas and self._vivo(self.privadas[codigo][0]):
                    return ("ERROR", "Ya existe una sala con ese codigo.")
                self.privadas[codigo] = (jugador, rapida)
                return ("ESPERA", codigo)

            if modo == "privada_unir":
                if not codigo:
                    return ("ERROR", "Ingresa el codigo de la sala.")
                entrada = self.privadas.get(codigo)
                if entrada is None or not self._vivo(entrada[0]):
                    return ("ERROR", "No existe una sala con ese codigo.")
                self.privadas.pop(codigo, None)
                esperando, esp_rapida = entrada
                sala = GameRoom([esperando, jugador],
                                reloj=(RELOJ if esp_rapida else None))
                esperando.sala = sala
                jugador.sala = sala
                esperando.evento_sala.set()
                return ("INICIAR", sala)

            return ("ERROR", f"Modo desconocido: {modo}")
