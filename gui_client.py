# -*- coding: utf-8 -*-
"""
Cliente GRAFICO del juego "Adivina Quien - Motos" (Tkinter).

Es una alternativa visual a client.py: en vez de consola, muestra una ventana
con el tablero de 24 motos (cada una con su imagen), controles para preguntar y
para adivinar, el turno, la moto secreta propia y un historial.

NO cambia nada del servidor ni del protocolo: usa el MISMO protocolo JSON sobre
sockets (protocolo.py) y los MISMOS datos (motos.py). Solo cambia la capa visual.

POR QUE HILOS + COLA (queue):
  Tkinter NO es seguro entre hilos: solo el hilo principal (el del mainloop)
  puede tocar los widgets. Pero la red llega por otro hilo bloqueante (recv).
  Solucion estandar: un hilo de recepcion deja los mensajes en una queue.Queue
  y la ventana los consume periodicamente con root.after(). Asi la UI se
  actualiza de forma segura sin condiciones de carrera con el hilo de red.

Tkinter (tk.PhotoImage) soporta PNG y GIF de forma nativa: no hace falta Pillow
ni ninguna libreria externa.
"""

import os
import re
import sys
import queue
import socket
import threading
import unicodedata
import tkinter as tk
from tkinter import ttk

import motos
import protocolo
import logica

# --- Distribucion del tablero ---
CARD_W, CARD_H = 150, 92            # tamano del area de imagen de cada carta (px)
COLS = 6                            # 6 columnas x 4 filas = 24 (mas ancho, menos alto)
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagenes")
AVATAR_DIR = os.path.join(IMG_DIR, "avatares")   # PNG de avatares del perfil
AVATAR_THUMB = 64                                # tamano de miniatura en el lobby

# --- Paleta de color (tema oscuro tipo "racing") ---
BG_MAIN = "#14161f"       # fondo general
BG_PANEL = "#1f2330"      # paneles
BG_CARD = "#2a2f3e"       # carta activa
BG_CARD_OFF = "#191b24"   # carta descartada
ACCENT = "#e10600"        # rojo de carreras (acentos / botones)
ACCENT_HOVER = "#ff2b25"
GOLD = "#f4c430"          # seleccion
TXT = "#eef0f6"           # texto principal
TXT_DIM = "#8b91a4"       # texto tenue
OK = "#33d17a"            # verde (tu turno / ganar)
BAD = "#ff5b6e"           # rojo suave (turno rival / perder)

# Color de acento de los avisos modales segun su tipo.
COLOR_AVISO = {"ok": OK, "bad": BAD, "info": GOLD, "warn": "#e8a13b"}

# Color distintivo por pais (acento de cada carta y respaldo sin imagen).
COLOR_ORIGEN = {
    "japonesa": "#d7263d", "americana": "#1d6fb8", "italiana": "#2a9d4a",
    "inglesa": "#7b5bd6", "alemana": "#c9a227", "austriaca": "#e8743b",
}

HOST_DEFECTO = "127.0.0.1"
PORT_DEFECTO = 5000


def nombre_a_archivo(nombre):
    """Convierte el nombre de una moto en el nombre de archivo PNG esperado.

    Ej: 'Honda CBR 600RR' -> 'honda_cbr_600rr.png'
    """
    s = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s + ".png"


class GuiClient:
    """Ventana del juego: gestiona conexion, estado local y todos los widgets."""

    def __init__(self, nombre, host, port):
        """Crea la ventana base y deja el estado del juego inicializado."""
        self.nombre = nombre
        self.host = host
        self.port = port

        # Red
        self.sock = None
        self.receptor = None
        self.cola = queue.Queue()      # puente hilo-red -> hilo-UI

        # Estado del juego
        self.tablero = []
        self.mi_id = None              # id estable que asigna el servidor (0/1)
        self.mi_moto = None
        self.rival = None
        self.mi_turno = False
        self.iniciado = False
        self.descartadas = set()
        self.seleccionada = None

        # Recursos visuales
        self.imagenes = {}             # nombre -> PhotoImage (evita que se borren)
        self.cartas = {}               # nombre -> {frame, display, nombre_lbl}

        # Avatar (perfil local: el rival ve tu nombre, no tu avatar)
        self.avatar = None             # ruta del avatar elegido
        self.avatar_img = None         # PhotoImage del avatar en el encabezado
        self._thumbs = {}              # ruta -> PhotoImage de la miniatura (lobby)
        self._tiles = {}               # ruta -> widget de la miniatura (para resaltar)

        self._construir_ventana_base()

    # ------------------------------------------------------------------
    # Construccion de la interfaz
    # ------------------------------------------------------------------
    def _construir_ventana_base(self):
        """Crea la ventana raiz y el estilo. El lobby o el juego se montan luego."""
        self.root = tk.Tk()
        self.root.title("Adivina Quien - Motos")
        self.root.configure(bg=BG_MAIN)
        self.root.protocol("WM_DELETE_WINDOW", self._al_cerrar)
        self.root.geometry("440x460")   # tamano del lobby; el juego maximiza luego

        # Estilo de los Combobox (tema 'clam' permite colorearlos).
        estilo = ttk.Style(self.root)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("TCombobox", fieldbackground=BG_CARD, background=BG_CARD,
                         foreground=TXT, arrowcolor=TXT, bordercolor=BG_PANEL)
        # En estado 'readonly', ttk pinta el texto con los colores de SELECCION,
        # que por defecto quedan oscuro-sobre-oscuro (no se ve el valor elegido).
        # Mapeamos esos colores por estado para que el valor siempre sea legible.
        estilo.map(
            "TCombobox",
            fieldbackground=[("readonly", BG_CARD)],
            background=[("readonly", BG_CARD)],
            foreground=[("readonly", TXT)],
            selectbackground=[("readonly", BG_CARD)],
            selectforeground=[("readonly", TXT)],
            arrowcolor=[("readonly", TXT)],
        )
        # Colores de la lista que se despliega (popdown): fondo, texto y resaltado.
        self.root.option_add("*TCombobox*Listbox.background", BG_CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", TXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")

    # ------------------------------------------------------------------
    # Pantalla de inicio (lobby)
    # ------------------------------------------------------------------
    def _mostrar_lobby(self):
        """Pantalla inicial: el jugador solo elige nombre y avatar.

        Ya NO se pide host ni puerto: al pulsar JUGAR, el cliente busca el
        servidor en la red local por UDP (autodescubrimiento).
        """
        self.root.geometry("460x600")
        self._lobby = tk.Frame(self.root, bg=BG_PANEL, padx=34, pady=24)
        self._lobby.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(self._lobby, text="ADIVINA QUIEN", bg=BG_PANEL, fg=ACCENT,
                 font=("Segoe UI Black", 22, "bold")).pack()
        tk.Label(self._lobby, text="· MOTOS ·", bg=BG_PANEL, fg=GOLD,
                 font=("Segoe UI", 13, "bold")).pack(pady=(0, 16))

        self._e_nombre = self._campo_lobby("Tu nombre", self.nombre)

        tk.Label(self._lobby, text="Elige tu avatar", bg=BG_PANEL, fg=TXT_DIM,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(14, 4))
        self._construir_galeria_avatares(self._lobby)

        self._lobby_error = tk.Label(self._lobby, text="", bg=BG_PANEL, fg=BAD,
                                     font=("Segoe UI", 9), wraplength=340)
        self._lobby_error.pack(pady=(10, 4))

        self._boton(self._lobby, "JUGAR", self._accion_jugar).pack(fill="x", pady=(4, 0))
        self.root.bind("<Return>", lambda e: self._accion_jugar())

    def _campo_lobby(self, etiqueta, valor):
        """Crea una etiqueta + Entry en el lobby y devuelve el Entry."""
        tk.Label(self._lobby, text=etiqueta, bg=BG_PANEL, fg=TXT_DIM,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(8, 0))
        entry = tk.Entry(self._lobby, bg=BG_CARD, fg=TXT, insertbackground=TXT,
                         relief="flat", font=("Segoe UI", 11), width=26)
        entry.insert(0, valor)
        entry.pack(fill="x", ipady=4)
        return entry

    # ------------------------------------------------------------------
    # Avatares (perfil local)
    # ------------------------------------------------------------------
    def _listar_avatares(self):
        """Devuelve las rutas de los PNG disponibles en imagenes/avatares/."""
        if not os.path.isdir(AVATAR_DIR):
            return []
        archivos = sorted(f for f in os.listdir(AVATAR_DIR)
                          if f.lower().endswith(".png"))
        return [os.path.join(AVATAR_DIR, f) for f in archivos]

    def _cargar_avatar(self, ruta, lado):
        """Carga un avatar PNG escalado a ~`lado` px (o None si falla)."""
        try:
            img = tk.PhotoImage(file=ruta)
        except tk.TclError:
            return None
        factor = max(1, img.width() // lado, img.height() // lado)
        if factor > 1:
            img = img.subsample(factor, factor)
        return img

    def _construir_galeria_avatares(self, parent):
        """Muestra los avatares como una cuadricula seleccionable."""
        rutas = self._listar_avatares()
        if not rutas:
            tk.Label(parent, text="(no hay avatares en imagenes/avatares)",
                     bg=BG_PANEL, fg=TXT_DIM, font=("Segoe UI", 8)).pack()
            return
        grid = tk.Frame(parent, bg=BG_PANEL)
        grid.pack()
        cols = 4
        for i, ruta in enumerate(rutas):
            thumb = self._cargar_avatar(ruta, AVATAR_THUMB)
            self._thumbs[ruta] = thumb          # mantener referencia (evita GC)
            tile = tk.Label(grid, image=thumb, bg=BG_CARD, cursor="hand2",
                            bd=0, highlightthickness=3, highlightbackground=BG_PANEL)
            tile.grid(row=i // cols, column=i % cols, padx=4, pady=4)
            tile.bind("<Button-1>", lambda e, r=ruta: self._elegir_avatar(r))
            self._tiles[ruta] = tile
        self._elegir_avatar(rutas[0])           # uno seleccionado por defecto

    def _elegir_avatar(self, ruta):
        """Marca el avatar elegido y resalta su miniatura."""
        self.avatar = ruta
        for r, tile in self._tiles.items():
            sel = (r == ruta)
            tile.config(highlightbackground=(GOLD if sel else BG_PANEL),
                        highlightcolor=(GOLD if sel else BG_PANEL))

    def _accion_jugar(self):
        """Busca el servidor por UDP, conecta y, si funciona, monta el juego."""
        self.nombre = self._e_nombre.get().strip() or "Jugador"
        self._lobby_error.config(text="Buscando servidor en la red...", fg=TXT_DIM)
        self.root.update_idletasks()

        encontrado = protocolo.descubrir_servidor(timeout=2.5)
        if not encontrado:
            self._lobby_error.config(
                text="No se encontro ningun servidor en la red. ¿Esta corriendo server.py?",
                fg=BAD)
            return

        self.host, self.port = encontrado
        if not self.conectar():
            self._lobby_error.config(
                text=f"Servidor hallado en {self.host}, pero no se pudo conectar.", fg=BAD)
            return

        self.root.unbind("<Return>")
        self._lobby.destroy()
        self._construir_juego()
        self._arrancar_red()

    # ------------------------------------------------------------------
    # Construccion del juego (tras conectar)
    # ------------------------------------------------------------------
    def _construir_juego(self):
        """Monta la ventana de juego: encabezado, tablero, panel y barra de estado."""
        self.root.title(f"Adivina Quien - Motos   ·   {self.nombre}")
        self.root.minsize(1000, 600)
        try:
            self.root.state("zoomed")       # maximiza para que entre el tablero
        except tk.TclError:
            self.root.geometry("1280x760")
        # La fila 1 (tablero) y la columna 0 se estiran al redimensionar.
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        self._construir_encabezado()
        self._construir_zona_tablero()
        self._construir_panel()
        self._construir_barra_estado()

    def _construir_encabezado(self):
        """Barra superior con el titulo del juego y los jugadores."""
        cab = tk.Frame(self.root, bg=ACCENT)
        cab.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(cab, text="ADIVINA QUIEN", bg=ACCENT, fg="white",
                 font=("Segoe UI Black", 20, "bold")).pack(side="left", padx=(18, 6), pady=8)
        tk.Label(cab, text="·  MOTOS  ·", bg=ACCENT, fg="#ffd9d8",
                 font=("Segoe UI", 14, "bold")).pack(side="left", pady=8)
        self.lbl_vs = tk.Label(cab, text=f"Jugador: {self.nombre}", bg=ACCENT,
                               fg="white", font=("Segoe UI", 11, "bold"))
        self.lbl_vs.pack(side="right", padx=(6, 18))
        # Avatar propio (perfil local) a la izquierda del nombre.
        if self.avatar:
            self.avatar_img = self._cargar_avatar(self.avatar, 40)
            if self.avatar_img:
                tk.Label(cab, image=self.avatar_img, bg=ACCENT).pack(side="right")

    def _construir_zona_tablero(self):
        """Crea el area del tablero dentro de un Canvas con scroll vertical."""
        contenedor = tk.Frame(self.root, bg=BG_MAIN)
        contenedor.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=12)
        contenedor.rowconfigure(0, weight=1)
        contenedor.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(contenedor, bg=BG_MAIN, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll = tk.Scrollbar(contenedor, orient="vertical", command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scroll.set)

        # Frame interno (dentro del canvas) donde van las cartas.
        self.frame_tablero = tk.Frame(self.canvas, bg=BG_MAIN)
        self._ventana_canvas = self.canvas.create_window((0, 0), window=self.frame_tablero,
                                                          anchor="nw")
        self.frame_tablero.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        # Rueda del raton: desplaza el area sobre la que esta el cursor (tablero
        # o panel), no siempre el tablero.
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

        self.lbl_placeholder = tk.Label(self.frame_tablero, text="Conectando...",
                                        bg=BG_MAIN, fg=TXT_DIM, font=("Segoe UI", 14))
        self.lbl_placeholder.pack(padx=40, pady=40)

    def _construir_panel(self):
        """Panel derecho: moto secreta, turno, controles e historial.

        El contenido puede superar el alto de la ventana (sobre todo al aparecer
        los botones de fin de ronda), asi que va DENTRO de un Canvas con scroll
        vertical. 'panel' sigue siendo el frame donde se empaqueta todo.
        """
        cont_panel = tk.Frame(self.root, bg=BG_PANEL)
        cont_panel.grid(row=1, column=1, sticky="ns", padx=(6, 12), pady=12)
        cont_panel.rowconfigure(0, weight=1)

        self.panel_canvas = tk.Canvas(cont_panel, bg=BG_PANEL, highlightthickness=0,
                                      width=300)
        self.panel_canvas.grid(row=0, column=0, sticky="ns")
        sb_panel = tk.Scrollbar(cont_panel, orient="vertical",
                                command=self.panel_canvas.yview)
        sb_panel.grid(row=0, column=1, sticky="ns")
        self.panel_canvas.configure(yscrollcommand=sb_panel.set)

        panel = tk.Frame(self.panel_canvas, bg=BG_PANEL)
        self._win_panel = self.panel_canvas.create_window((0, 0), window=panel,
                                                          anchor="nw")
        # El alto del frame interno define la region scrolleable...
        panel.bind("<Configure>",
                   lambda e: self.panel_canvas.configure(
                       scrollregion=self.panel_canvas.bbox("all")))
        # ...y el frame interno toma el ancho del canvas (para que los botones
        # con fill="x" se vean bien).
        self.panel_canvas.bind("<Configure>",
                               lambda e: self.panel_canvas.itemconfigure(
                                   self._win_panel, width=e.width))

        # Indicador de turno (arriba, bien visible).
        self.lbl_turno = tk.Label(panel, text="Conectando...", bg=BG_PANEL, fg=TXT_DIM,
                                  font=("Segoe UI", 14, "bold"))
        self.lbl_turno.pack(pady=(14, 2), padx=16)

        # Moto secreta propia.
        caja_moto = tk.Frame(panel, bg=BG_CARD, padx=10, pady=10)
        caja_moto.pack(padx=16, fill="x")
        tk.Label(caja_moto, text="TU MOTO SECRETA", bg=BG_CARD, fg=GOLD,
                 font=("Segoe UI", 9, "bold")).pack()
        self.lbl_mi_moto_img = tk.Label(caja_moto, bg=BG_CARD)
        self.lbl_mi_moto_img.pack(pady=4)
        self.lbl_mi_moto = tk.Label(caja_moto, text="(esperando...)", bg=BG_CARD, fg=TXT,
                                    font=("Segoe UI", 10, "bold"), wraplength=220)
        self.lbl_mi_moto.pack()

        # Contador de candidatos restantes.
        self.lbl_candidatos = tk.Label(panel, text="", bg=BG_PANEL, fg=TXT,
                                       font=("Segoe UI", 10, "bold"))
        self.lbl_candidatos.pack(pady=(8, 0), padx=16)

        # Controles de pregunta.
        caja_preg = tk.LabelFrame(panel, text=" Preguntar ", bg=BG_PANEL, fg=TXT,
                                  font=("Segoe UI", 10, "bold"), padx=10, pady=10,
                                  labelanchor="n")
        caja_preg.pack(padx=16, pady=14, fill="x")

        self.var_atributo = tk.StringVar(value=motos.ATRIBUTOS[0])
        self.var_valor = tk.StringVar()

        tk.Label(caja_preg, text="Atributo", bg=BG_PANEL, fg=TXT_DIM).grid(row=0, column=0, sticky="w")
        self.cb_atributo = ttk.Combobox(caja_preg, textvariable=self.var_atributo,
                                        values=motos.ATRIBUTOS, state="readonly", width=18)
        self.cb_atributo.grid(row=1, column=0, pady=(0, 6))
        self.cb_atributo.bind("<<ComboboxSelected>>", self._actualizar_valores)

        tk.Label(caja_preg, text="Valor", bg=BG_PANEL, fg=TXT_DIM).grid(row=2, column=0, sticky="w")
        self.cb_valor = ttk.Combobox(caja_preg, textvariable=self.var_valor,
                                     state="readonly", width=18)
        self.cb_valor.grid(row=3, column=0, pady=(0, 8))
        self._actualizar_valores()

        self.btn_preguntar = self._boton(caja_preg, "PREGUNTAR", self._accion_preguntar)
        self.btn_preguntar.grid(row=4, column=0, sticky="ew")

        # Boton de adivinar.
        self.btn_adivinar = self._boton(panel, "ADIVINAR SELECCIONADA",
                                        self._accion_adivinar, color="#b8860b")
        self.btn_adivinar.pack(padx=16, fill="x")
        tk.Label(panel, text="clic = seleccionar   ·   doble clic = descartar",
                 bg=BG_PANEL, fg=TXT_DIM, font=("Segoe UI", 8)).pack(pady=(4, 8))

        # Boton de rendirse: habilitado SOLO durante la partida (entre INICIO y
        # FIN); rendirse cuenta como perder la ronda. No depende del turno.
        self.btn_rendirse = self._boton(panel, "RENDIRSE", self._accion_rendirse,
                                        color="#8a3b3b")
        self.btn_rendirse.pack(padx=16, fill="x", pady=(0, 8))
        self.btn_rendirse.config(state="disabled")

        # Botones de fin de ronda (ocultos durante el juego).
        self.frame_revancha = tk.Frame(panel, bg=BG_PANEL)
        self.btn_revancha = self._boton(self.frame_revancha, "JUGAR DE NUEVO",
                                        self._accion_revancha, color=OK)
        self.btn_revancha.pack(fill="x", pady=(0, 4))
        self.btn_salir = self._boton(self.frame_revancha, "SALIR",
                                     self._accion_salir, color="#555a6b")
        self.btn_salir.pack(fill="x")
        # No se empaqueta self.frame_revancha aun: aparece solo al terminar la ronda.

        # Historial.
        self.lbl_historial = tk.Label(panel, text="HISTORIAL", bg=BG_PANEL, fg=GOLD,
                                      font=("Segoe UI", 9, "bold"))
        self.lbl_historial.pack()
        cont_log = tk.Frame(panel, bg=BG_PANEL)
        cont_log.pack(padx=16, pady=(2, 14), fill="both", expand=True)
        sb = tk.Scrollbar(cont_log)
        sb.pack(side="right", fill="y")
        self.log = tk.Listbox(cont_log, width=32, height=12, yscrollcommand=sb.set,
                              bg=BG_CARD, fg=TXT, borderwidth=0, highlightthickness=0,
                              selectbackground=ACCENT, font=("Consolas", 9))
        self.log.pack(side="left", fill="both", expand=True)
        sb.config(command=self.log.yview)

        self._habilitar_controles(False)

    def _on_wheel(self, event):
        """Desplaza con la rueda el area (tablero o panel) bajo el cursor."""
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        destino = self._canvas_de(widget)
        if destino is not None:
            destino.yview_scroll(int(-event.delta / 120), "units")

    def _canvas_de(self, widget):
        """Sube por la jerarquia hasta el canvas scrolleable que contiene al widget."""
        canvases = (getattr(self, "panel_canvas", None), getattr(self, "canvas", None))
        while widget is not None:
            if widget in canvases:
                return widget
            widget = getattr(widget, "master", None)
        return None

    def _construir_barra_estado(self):
        """Barra inferior con mensajes de estado."""
        self.lbl_estado = tk.Label(self.root, text="Listo.", bg="#0d0e14", fg=TXT_DIM,
                                   anchor="w", font=("Segoe UI", 9), padx=12)
        self.lbl_estado.grid(row=2, column=0, columnspan=2, sticky="ew")

    def _boton(self, parent, texto, comando, color=ACCENT):
        """Crea un boton con el estilo del juego (plano, con color de acento)."""
        return tk.Button(parent, text=texto, command=comando, bg=color, fg="white",
                         activebackground=ACCENT_HOVER, activeforeground="white",
                         relief="flat", font=("Segoe UI", 10, "bold"), cursor="hand2",
                         disabledforeground="#6b6f7d", padx=10, pady=7, bd=0)

    # ------------------------------------------------------------------
    # Avisos modales con el estilo del juego (reemplazan a messagebox)
    # ------------------------------------------------------------------
    def _modal(self, titulo, mensaje, tipo="info", icono="", botones=None):
        """Muestra un dialogo modal oscuro y devuelve el valor del boton pulsado.

        botones: lista de (texto, valor, color). Si es None, un unico boton 'OK'.
        Bloquea hasta que el usuario responde (wait_window). El primer boton es
        el valor por defecto al cerrar con la X o con Escape.
        """
        color = COLOR_AVISO.get(tipo, GOLD)
        if botones is None:
            botones = [("OK", True, ACCENT)]
        cerrar_valor = botones[0][1]

        win = tk.Toplevel(self.root)
        win.withdraw()                     # se muestra ya centrado (evita parpadeo)
        win.title(titulo)
        win.configure(bg=BG_PANEL)
        win.resizable(False, False)
        win.transient(self.root)

        resultado = {"valor": cerrar_valor}

        def elegir(valor):
            resultado["valor"] = valor
            win.destroy()

        # Barra de color superior con el titulo.
        barra = tk.Frame(win, bg=color)
        barra.pack(fill="x")
        tk.Label(barra, text=titulo.upper(), bg=color, fg=BG_MAIN,
                 font=("Segoe UI Black", 14, "bold"), pady=8).pack()

        # Cuerpo: icono + mensaje + botones.
        cuerpo = tk.Frame(win, bg=BG_PANEL, padx=30, pady=18)
        cuerpo.pack(fill="both", expand=True)
        if icono:
            tk.Label(cuerpo, text=icono, bg=BG_PANEL, fg=color,
                     font=("Segoe UI", 32, "bold")).pack(pady=(0, 8))
        tk.Label(cuerpo, text=mensaje, bg=BG_PANEL, fg=TXT, justify="center",
                 font=("Segoe UI", 11), wraplength=340).pack()

        fila = tk.Frame(cuerpo, bg=BG_PANEL)
        fila.pack(pady=(18, 0))
        for texto, valor, bcolor in botones:
            self._boton(fila, texto, lambda v=valor: elegir(v),
                        color=bcolor).pack(side="left", padx=6, ipadx=8)

        # Teclado: Enter = ultimo boton; Escape o X = cerrar_valor.
        win.bind("<Return>", lambda e: elegir(botones[-1][1]))
        win.bind("<Escape>", lambda e: elegir(cerrar_valor))
        win.protocol("WM_DELETE_WINDOW", lambda: elegir(cerrar_valor))

        self._centrar(win)
        win.deiconify()
        win.grab_set()                     # modal: bloquea la ventana principal
        win.focus_set()
        self.root.wait_window(win)
        return resultado["valor"]

    def _centrar(self, win):
        """Centra una ventana modal sobre la ventana principal."""
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        x = rx + (rw - w) // 2
        y = ry + (rh - h) // 3
        win.geometry(f"+{max(rx, x)}+{max(ry, y)}")

    def _aviso(self, titulo, mensaje, tipo="info", icono=""):
        """Aviso informativo con un unico boton OK."""
        self._modal(titulo, mensaje, tipo=tipo, icono=icono)

    def _confirmar(self, titulo, mensaje, texto_si, color_si, tipo="info", icono="?"):
        """Confirmacion con dos botones (CANCELAR / accion). Devuelve True/False."""
        return self._modal(
            titulo, mensaje, tipo=tipo, icono=icono,
            botones=[("CANCELAR", False, "#555a6b"), (texto_si, True, color_si)])

    def _actualizar_valores(self, *_):
        """Rellena el combo de valores segun el atributo elegido."""
        atributo = self.var_atributo.get()
        valores = sorted({str(m[atributo]) for m in motos.motos.values()})
        self.cb_valor.config(values=valores)
        if valores:
            self.var_valor.set(valores[0])

    def _habilitar_controles(self, activo):
        """Activa/desactiva los botones de jugar (segun el turno)."""
        estado = "normal" if activo else "disabled"
        self.btn_preguntar.config(state=estado)
        self.btn_adivinar.config(state=estado)

    # ------------------------------------------------------------------
    # Tablero e imagenes
    # ------------------------------------------------------------------
    def _cargar_imagen(self, nombre):
        """Carga el PNG de una moto (o None si no existe). Reduce si es grande."""
        ruta = os.path.join(IMG_DIR, nombre_a_archivo(nombre))
        if not os.path.exists(ruta):
            return None
        try:
            img = tk.PhotoImage(file=ruta)
            factor = max(1, img.width() // CARD_W, img.height() // CARD_H)
            if factor > 1:
                img = img.subsample(factor, factor)
            return img
        except tk.TclError:
            return None  # formato no soportado (p. ej. JPG): cae al respaldo

    def _construir_tablero(self):
        """Crea las 24 cartas en una cuadricula a partir del tablero recibido.

        Limpia primero cualquier carta anterior (asi sirve tambien al empezar
        una revancha con un tablero nuevo).
        """
        for w in self.frame_tablero.winfo_children():
            w.destroy()
        self.cartas = {}
        for nombre in self.tablero:
            self.imagenes[nombre] = self._cargar_imagen(nombre)

        for col in range(COLS):
            self.frame_tablero.columnconfigure(col, weight=1)

        for i, nombre in enumerate(self.tablero):
            fila, col = divmod(i, COLS)
            origen = motos.motos[nombre]["origen"]

            # Marco exterior: borde de color por pais + borde de seleccion.
            frame = tk.Frame(self.frame_tablero, bg=BG_CARD, bd=0,
                             highlightthickness=3, highlightbackground=BG_CARD)
            barra = tk.Frame(frame, bg=COLOR_ORIGEN.get(origen, "#666"), height=4)
            barra.pack(fill="x")
            cont = tk.Frame(frame, width=CARD_W, height=CARD_H, bg=BG_CARD)
            cont.pack_propagate(False)
            cont.pack()
            display = tk.Label(cont, bg=BG_CARD)
            display.pack(fill="both", expand=True)
            nom = tk.Label(frame, text=nombre, bg=BG_CARD, fg=TXT, wraplength=CARD_W,
                           font=("Segoe UI", 8, "bold"), pady=3)
            nom.pack(fill="x")

            for w in (frame, barra, cont, display, nom):
                w.bind("<Button-1>", lambda e, n=nombre: self._seleccionar(n))
                w.bind("<Double-Button-1>", lambda e, n=nombre: self._toggle_descarte(n))
                w.bind("<Enter>", lambda e, n=nombre: self._hover(n, True))
                w.bind("<Leave>", lambda e, n=nombre: self._hover(n, False))

            frame.grid(row=fila, column=col, padx=6, pady=6, sticky="n")
            self.cartas[nombre] = {"frame": frame, "display": display, "nombre_lbl": nom}
            self._pintar_carta(nombre)

    def _pintar_carta(self, nombre):
        """Dibuja una carta segun su estado (activa con imagen/respaldo, o descartada)."""
        info = self.cartas.get(nombre)
        if not info:
            return
        display, frame, nom = info["display"], info["frame"], info["nombre_lbl"]
        seleccionada = (nombre == self.seleccionada)
        frame.config(highlightbackground=(GOLD if seleccionada else BG_CARD),
                     highlightcolor=(GOLD if seleccionada else BG_CARD))

        if nombre in self.descartadas:
            display.config(image="", text="✕", bg=BG_CARD_OFF, fg=BAD,
                           font=("Segoe UI", 26, "bold"))
            display.image = None
            frame.config(bg=BG_CARD_OFF)
            nom.config(bg=BG_CARD_OFF, fg=TXT_DIM)
            return

        frame.config(bg=BG_CARD)
        nom.config(bg=BG_CARD, fg=TXT)
        img = self.imagenes.get(nombre)
        if img is not None:
            display.config(image=img, text="", bg=BG_CARD)
            display.image = img            # mantener referencia (evita GC)
        else:
            color = COLOR_ORIGEN.get(motos.motos[nombre]["origen"], "#666666")
            display.config(image="", text=nombre, bg=color, fg="white",
                           font=("Segoe UI", 9, "bold"), wraplength=CARD_W - 12)
            display.image = None

    def _hover(self, nombre, encima):
        """Resalta sutilmente la carta al pasar el raton por encima."""
        if nombre in self.descartadas or nombre == self.seleccionada:
            return
        info = self.cartas.get(nombre)
        if info:
            info["frame"].config(highlightbackground=(ACCENT if encima else BG_CARD))

    # ------------------------------------------------------------------
    # Interaccion del usuario
    # ------------------------------------------------------------------
    def _seleccionar(self, nombre):
        """Marca una carta como seleccionada (para adivinarla)."""
        anterior = self.seleccionada
        self.seleccionada = nombre
        if anterior:
            self._pintar_carta(anterior)
        self._pintar_carta(nombre)
        self.lbl_estado.config(text=f"Seleccionada: {nombre}")

    def _toggle_descarte(self, nombre):
        """Descarta o recupera una carta manualmente (doble clic)."""
        if nombre in self.descartadas:
            self.descartadas.discard(nombre)
        else:
            self.descartadas.add(nombre)
            self._enviar(protocolo.crear(protocolo.DESCARTAR, moto=nombre))
        self._pintar_carta(nombre)
        self._actualizar_contador()

    def _accion_preguntar(self):
        """Envia la pregunta (atributo + valor) si es el turno propio."""
        if not (self.iniciado and self.mi_turno):
            return
        atributo = self.var_atributo.get()
        valor = self.var_valor.get()
        self._enviar(protocolo.crear(protocolo.PREGUNTA, atributo=atributo, valor=valor))

    def _accion_adivinar(self):
        """Pide confirmacion y envia el intento de adivinar la moto seleccionada."""
        if not (self.iniciado and self.mi_turno):
            return
        if not self.seleccionada:
            self._aviso("Adivinar", "Primero selecciona una moto (clic en una carta).",
                        tipo="info", icono="!")
            return
        if self._confirmar(
                "Adivinar",
                f"Vas a adivinar:\n{self.seleccionada}\n\nSi fallas, PIERDES de inmediato.",
                "ADIVINAR", "#b8860b", icono="?"):
            self._enviar(protocolo.crear(protocolo.ADIVINAR, moto=self.seleccionada))

    # ------------------------------------------------------------------
    # Red: conexion, recepcion (hilo) y procesamiento (UI)
    # ------------------------------------------------------------------
    def conectar(self):
        """Abre el socket y envia el JOIN. Devuelve True si conecto, False si no.

        No muestra dialogos: quien llama decide como reportar el error (el lobby
        lo muestra inline; el modo directo usa un messagebox).
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.receptor = protocolo.Receptor(self.sock)
            protocolo.enviar(self.sock, protocolo.crear(protocolo.JOIN, nombre=self.nombre))
            return True
        except (ConnectionError, OSError):
            return False

    def _escuchar(self):
        """Hilo de recepcion: deja cada mensaje del servidor en la cola."""
        try:
            while True:
                mensaje = self.receptor.recibir()
                if mensaje is None:
                    self.cola.put({"tipo": "_DESCONECTADO"})
                    break
                self.cola.put(mensaje)
        except (ConnectionError, OSError):
            self.cola.put({"tipo": "_DESCONECTADO"})

    def _procesar_cola(self):
        """Consume la cola en el hilo de la UI (seguro para Tkinter)."""
        try:
            while True:
                self._manejar(self.cola.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._procesar_cola)

    def _manejar(self, msg):
        """Traduce cada mensaje del protocolo en cambios visibles en la ventana."""
        tipo = msg.get("tipo")

        if tipo == protocolo.ESPERANDO:
            self.lbl_turno.config(text="Esperando rival...", fg=TXT_DIM)
            self.lbl_estado.config(text="Esperando a que se conecte otro jugador.")

        elif tipo == protocolo.INICIO:
            self.tablero = msg["tablero"]
            self.mi_id = msg.get("tu_id")
            self.mi_moto = msg["tu_moto"]
            self.rival = msg.get("rival")
            self.mi_turno = msg["tu_turno"]
            self.iniciado = True
            self.descartadas = set()       # tablero limpio (sirve para revanchas)
            self.seleccionada = None
            self.lbl_vs.config(text=f"{self.nombre}   VS   {self.rival}")
            self._mostrar_revancha(False)  # esconde los botones de fin de ronda
            self._mostrar_marcador(msg.get("marcador"))
            self._construir_tablero()
            self._mostrar_mi_moto()
            self._actualizar_contador()
            self.log.delete(0, "end")      # historial limpio para la nueva ronda
            self.btn_rendirse.config(state="normal")   # solo activo en partida
            self._set_turno(self.mi_turno)

        elif tipo == protocolo.TURNO:
            self._set_turno(msg["tu_turno"])

        elif tipo == protocolo.RESPUESTA:
            quien = msg.get("quien")
            quien_id = msg.get("quien_id")
            atributo, valor = msg.get("atributo"), msg.get("valor")
            respuesta = msg.get("respuesta")
            # "Mio" se decide por ID estable, NO por nombre (dos jugadores pueden
            # llamarse igual). El historial muestra el nombre real de quien pregunto.
            mio = (quien_id == self.mi_id)
            self._registrar(f"{quien}: {atributo}={valor}? -> {respuesta}")
            # Feedback resaltado de la ultima pregunta en la barra de estado.
            color = OK if respuesta == "SI" else BAD
            etiqueta = "Tú" if mio else quien
            self.lbl_estado.config(text=f"{etiqueta}: ¿{atributo} = {valor}?  →  {respuesta}", fg=color)
            if mio:
                self._filtrar_tablero(atributo, valor, respuesta)

        elif tipo == protocolo.FIN:
            self._habilitar_controles(False)
            self.btn_rendirse.config(state="disabled")   # ya no hay partida activa
            ganaste = msg.get("ganaste")
            self.lbl_turno.config(text=("GANASTE!" if ganaste else "PERDISTE"),
                                  fg=(OK if ganaste else BAD))
            self._mostrar_marcador(msg.get("marcador"))
            # Si el servidor ofrece revancha, mostramos los botones de fin de ronda.
            if msg.get("revancha"):
                self._mostrar_revancha(True)
            # Forzar el repintado del marcador ANTES del aviso modal, para que el
            # encabezado ya muestre el resultado actualizado al instante.
            self.root.update_idletasks()
            self._aviso(
                "Ganaste!" if ganaste else "Perdiste",
                f"{msg.get('msg', '')}\n\n"
                f"La moto secreta del rival era:\n{msg.get('moto_rival')}",
                tipo=("ok" if ganaste else "bad"),
                icono=("★" if ganaste else "✖"))

        elif tipo == protocolo.ERROR:
            # Error bien visible: barra de estado en rojo (no va al historial,
            # que queda reservado solo para preguntas y respuestas).
            self.lbl_estado.config(text=f"⚠ {msg.get('msg')}", fg=BAD)

        elif tipo == "_DESCONECTADO":
            self._habilitar_controles(False)
            self.btn_rendirse.config(state="disabled")
            self.lbl_turno.config(text="Conexion perdida", fg=BAD)
            self._aviso("Conexión", "Se cerró la conexión con el servidor.",
                        tipo="warn", icono="⚠")

    def _set_turno(self, mi_turno):
        """Actualiza el indicador de turno y habilita/inhabilita los controles."""
        self.mi_turno = mi_turno
        if mi_turno:
            self.lbl_turno.config(text="● ES TU TURNO", fg=OK)
            self.lbl_estado.config(text="Tu turno: pregunta o adivina.", fg=TXT_DIM)
        else:
            self.lbl_turno.config(text="○ Turno del rival", fg=BAD)
            self.lbl_estado.config(text="Espera tu turno...", fg=TXT_DIM)
        self._habilitar_controles(mi_turno)

    def _mostrar_mi_moto(self):
        """Muestra la moto secreta propia (imagen si hay, o el nombre)."""
        img = self._cargar_imagen(self.mi_moto)
        if img is not None:
            self._mi_img = img             # referencia persistente
            self.lbl_mi_moto_img.config(image=img)
        self.lbl_mi_moto.config(text=self.mi_moto)

    def _mostrar_marcador(self, marcador):
        """Actualiza el encabezado con los nombres y las partidas ganadas.

        Formato: 'Ana  2  -  1  Beto' (numero = rondas ganadas por cada uno).
        El marcador vive arriba, junto al VS, no en el panel lateral.
        """
        if not marcador:
            return
        mio = marcador.get(self.nombre, 0)
        suyo = marcador.get(self.rival, 0) if self.rival else 0
        self.lbl_vs.config(text=f"{self.nombre}  {mio}   -   {suyo}  {self.rival}")

    def _actualizar_contador(self):
        """Actualiza el contador de candidatos restantes; resalta cuando queda 1."""
        total = len(self.tablero)
        restantes = total - len(self.descartadas)
        self.lbl_candidatos.config(text=f"Candidatos: {restantes}/{total}")
        if restantes == 1 and self.iniciado:
            queda = next(n for n in self.tablero if n not in self.descartadas)
            self.lbl_candidatos.config(fg=GOLD)
            self.lbl_estado.config(text=f"Solo queda 1: ¿adivinar {queda}?", fg=GOLD)
        else:
            self.lbl_candidatos.config(fg=TXT)

    def _mostrar_revancha(self, visible):
        """Muestra u oculta los botones de fin de ronda (revancha / salir).

        Se ancla JUSTO ENCIMA del historial (before=self.lbl_historial) para
        que quede en un lugar fijo y visible; antes se empaquetaba al final,
        debajo del historial expansible, y quedaba fuera de la ventana.
        """
        if visible:
            self.frame_revancha.pack(padx=16, pady=(8, 8), fill="x",
                                     before=self.lbl_historial)
        else:
            self.frame_revancha.pack_forget()

    def _accion_revancha(self):
        """Pide otra ronda al servidor y queda a la espera del rival."""
        self._enviar(protocolo.crear(protocolo.REVANCHA))
        self._mostrar_revancha(False)
        self.lbl_turno.config(text="Esperando al rival...", fg=TXT_DIM)
        self.lbl_estado.config(text="Pediste revancha. Esperando al rival.", fg=TXT_DIM)

    def _accion_rendirse(self):
        """Se rinde tras confirmar: pierde la ronda y el rival gana."""
        if not self.iniciado:
            return
        if self._confirmar(
                "Rendirse",
                "¿Seguro que quieres rendirte?\nPerderás esta ronda.",
                "RENDIRSE", "#8a3b3b", tipo="warn", icono="!"):
            self._enviar(protocolo.crear(protocolo.RENDIRSE))

    def _accion_salir(self):
        """Sale de la sesion y cierra la ventana."""
        self._al_cerrar()

    def _filtrar_tablero(self, atributo, valor, respuesta):
        """Descarta automaticamente las cartas incompatibles con la respuesta.

        Usa la regla compartida de logica.candidatos_a_descartar (la misma del
        servidor y el cliente de consola) y repinta las cartas afectadas.
        """
        candidatos = [n for n in self.tablero if n not in self.descartadas]
        nuevas = logica.candidatos_a_descartar(candidatos, atributo, valor, respuesta)
        self.descartadas |= nuevas
        for nombre in nuevas:
            self._pintar_carta(nombre)
        self._actualizar_contador()

    def _registrar(self, texto):
        """Agrega una linea al historial y baja el scroll."""
        self.log.insert("end", texto)
        self.log.see("end")

    # ------------------------------------------------------------------
    # Envio y cierre
    # ------------------------------------------------------------------
    def _enviar(self, mensaje):
        """Envia un mensaje al servidor manejando posibles fallos de red."""
        try:
            protocolo.enviar(self.sock, mensaje)
        except (ConnectionError, OSError):
            self.lbl_estado.config(text="Error de envio (conexion caida).")

    def _al_cerrar(self):
        """Maneja el cierre de la ventana: avisa SALIR y cierra el socket."""
        try:
            if self.sock:
                self._enviar(protocolo.crear(protocolo.SALIR))
                self.sock.close()
        except OSError:
            pass
        self.root.destroy()

    def _arrancar_red(self):
        """Lanza el hilo de recepcion y el sondeo de la cola en la UI."""
        # POR QUE UN HILO DE RED: recv() bloquea; si lo hicieramos en el hilo de
        # la UI, la ventana se congelaria. El hilo deja mensajes en la cola y la
        # UI los procesa con after(). daemon=True: muere al cerrar la ventana.
        threading.Thread(target=self._escuchar, daemon=True).start()
        self.root.after(100, self._procesar_cola)

    def _iniciar_partida(self):
        """Modo directo (con argumentos): conecta y monta el juego sin lobby."""
        if self.avatar is None:                 # sin lobby no se eligio avatar
            avatares = self._listar_avatares()
            self.avatar = avatares[0] if avatares else None
        if self.conectar():
            self._construir_juego()
            self._arrancar_red()
        else:
            self._aviso(
                "Sin conexión",
                f"No se pudo conectar a {self.host}:{self.port}.\nInicia primero server.py.",
                tipo="bad", icono="✖")
            self.root.destroy()

    def run(self, con_lobby=True):
        """Arranca la app: muestra el lobby o conecta directo, y corre el mainloop."""
        if con_lobby:
            self._mostrar_lobby()
        else:
            self._iniciar_partida()
        self.root.mainloop()


def main():
    """Arranca el cliente grafico.

    - Con argumentos (p. ej. desde el .bat): `gui_client.py <nombre> [host] [puerto]`
      conecta directo, sin lobby.
    - Sin argumentos (doble clic): muestra el lobby para escribir los datos.
    """
    if len(sys.argv) > 1:
        nombre = sys.argv[1]
        host = sys.argv[2] if len(sys.argv) > 2 else HOST_DEFECTO
        port = int(sys.argv[3]) if len(sys.argv) > 3 else PORT_DEFECTO
        GuiClient(nombre, host, port).run(con_lobby=False)
    else:
        GuiClient("Jugador", HOST_DEFECTO, PORT_DEFECTO).run(con_lobby=True)


if __name__ == "__main__":
    main()
