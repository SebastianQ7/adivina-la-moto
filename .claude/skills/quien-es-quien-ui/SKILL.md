---
name: quien-es-quien-ui
description: >-
  Convenciones de la parte VISUAL/UI del juego "Quien es Quien" (version motos),
  hecha en Tkinter. Usar al crear o modificar la interfaz: el tablero/cuadricula
  de cartas, seleccionar/descartar (eliminar) personajes, el layout del juego
  (encabezado, tablero con scroll, panel lateral, barra de estado), la paleta de
  colores, la tipografia, el estilo de las cartas y los componentes visuales.
  Cubre el framework usado, como se conecta la UI con la logica vía protocolo, y
  los patrones de interaccion (hover, seleccion, descarte, estados de turno).
---

# Interfaz (UI) de "Quién es Quién — Motos"

Cliente gráfico en **`gui_client.py`**. Esta skill describe **cómo está hecha la
UI** para mantenerla consistente y separada de la lógica. **No agregar librerías
externas** (requisito de la materia: solo biblioteca estándar).

## Framework y librerías de UI

- **Tkinter** (`import tkinter as tk`) — biblioteca estándar, sin dependencias.
- **`tkinter.ttk`** — solo para los `Combobox` (atributo/valor), con el tema
  `"clam"` para poder colorearlos (`ttk.Style`).
- **`tkinter.messagebox`** — diálogos de confirmar adivinanza, fin de partida,
  errores de conexión.
- **`tk.PhotoImage`** — carga de imágenes **PNG** (no usar JPG: Tkinter no lo
  soporta sin Pillow). Reducción por factor entero con `.subsample()`.
- **`queue.Queue` + `threading` + `root.after()`** — puente seguro entre el hilo
  de red y la UI (Tkinter NO es thread-safe).

> La interfaz del juego es **únicamente gráfica** (`gui_client.py`). La lógica de
> juego vive en el servidor y en `logica.py`; la UI solo presenta.

## Estructura de archivos y conexión con la lógica

- **`gui_client.py`** = capa de **presentación**. Una sola clase `GuiClient` que
  arma la ventana y traduce mensajes del protocolo en cambios visuales.
- **No contiene reglas del juego.** El servidor (`server.py`) es la autoridad.
  La UI solo:
  1. envía intenciones (`PREGUNTA`, `ADIVINAR`, `DESCARTAR`, `REVANCHA`,
     `SALIR`) vía `protocolo.py`;
  2. reacciona a los mensajes del servidor;
  3. mantiene un **espejo local** del tablero para el feedback visual
     (`self.descartadas`), pero la verdad la tiene el servidor.
- **Lobby de inicio**: sin argumentos, `main()` muestra el lobby
  (`_mostrar_lobby`) para escribir nombre/host/puerto; al pulsar Conectar
  (`_accion_conectar`) se conecta y recién ahí se monta el juego
  (`_construir_juego`, que maximiza la ventana). Con argumentos
  (`gui_client.py <nombre> [host] [puerto]`) conecta directo sin lobby.
- **Fin de ronda**: con `FIN` muestra resultado + marcador (`_mostrar_marcador`)
  y, si `revancha=True`, los botones "Jugar de nuevo" / "Salir"
  (`_mostrar_revancha`). Un `INICIO` nuevo (revancha) **reconstruye** el tablero
  desde cero (`_construir_tablero` borra las cartas anteriores) y resetea
  `descartadas`/`seleccionada`.
- **Contador de candidatos** (`_actualizar_contador`): se actualiza al filtrar y
  al descartar; resalta cuando queda 1.
- **Datos y valores se derivan de `motos.py`**, nunca se hardcodean: nombres del
  tablero, atributos (`motos.ATRIBUTOS`) y valores posibles
  (`sorted({m[at] for m in motos.motos.values()})`).
- **Imágenes**: `imagenes/<slug>.png`, donde el slug lo calcula
  `nombre_a_archivo()`. Si falta una imagen, hay **respaldo** (bloque de color
  con el nombre); la UI nunca se rompe por una imagen ausente.

### Mapa mensaje del protocolo → método de UI (en `_manejar`)

`ESPERANDO`→texto de espera · `INICIO`→`_construir_tablero` + `_mostrar_mi_moto`
+ `_set_turno` · `TURNO`→`_set_turno` · `RESPUESTA`→`_registrar` (+`_filtrar_tablero`
si la pregunta fue propia) · `FIN`→`messagebox` ganar/perder · `ERROR`→historial
+ barra de estado · `_DESCONECTADO`→aviso de conexión perdida.

## Convenciones de diseño (las que ya existen)

Todos los colores, tamaños y la distribución están en **constantes al inicio de
`gui_client.py`**. Reutilizarlas siempre; **no escribir hex sueltos** en los
widgets.

### Paleta (tema oscuro "racing")

| Constante | Valor | Uso |
|-----------|-------|-----|
| `BG_MAIN` | `#14161f` | Fondo general |
| `BG_PANEL` | `#1f2330` | Paneles |
| `BG_CARD` | `#2a2f3e` | Carta activa |
| `BG_CARD_OFF` | `#191b24` | Carta descartada |
| `ACCENT` / `ACCENT_HOVER` | `#e10600` / `#ff2b25` | Rojo de carreras: botones, hover |
| `GOLD` | `#f4c430` | Carta seleccionada |
| `TXT` / `TXT_DIM` | `#eef0f6` / `#8b91a4` | Texto principal / tenue |
| `OK` / `BAD` | `#33d17a` / `#ff5b6e` | Tu turno-ganar / turno rival-perder |
| `COLOR_ORIGEN` | dict por país | Franja superior de cada carta y respaldo sin imagen |

`COLOR_ORIGEN`: japonesa `#d7263d`, americana `#1d6fb8`, italiana `#2a9d4a`,
inglesa `#7b5bd6`, alemana `#c9a227`, austriaca `#e8743b`.

### Tipografía

- **`Segoe UI`** para casi todo; **`Segoe UI Black` 20 bold** para el título del
  encabezado; **bold** para nombres de carta (8) y etiquetas importantes.
- **`Consolas` 9** para el historial (`Listbox`).

### Espaciado y layout

- Ventana **maximizada** (`root.state("zoomed")`, fallback `1280x760`),
  `minsize(1000, 600)`, redimensionable.
- **Grid raíz**: fila 0 = encabezado (`columnspan=2`), fila 1 = tablero (col 0) +
  panel (col 1), fila 2 = barra de estado. `rowconfigure(1, weight=1)` y
  `columnconfigure(0, weight=1)` para que el tablero crezca.
- **Tablero**: cuadrícula **6 columnas × 4 filas** (`COLS = 6`,
  `divmod(i, COLS)`), dentro de un `Canvas` con `Scrollbar` vertical + rueda del
  ratón (nunca se corta, aunque la pantalla sea pequeña).
- **Carta**: `CARD_W, CARD_H = 150, 92`; `padx=6, pady=6` entre cartas;
  `padx 12 / 16` en márgenes de zonas y paneles.

### Estilo de carta (componente central)

Cada carta es un `Frame` con `highlightthickness=3` que contiene:
1. una **franja de color** superior (`height=4`) según `COLOR_ORIGEN`;
2. un contenedor de tamaño fijo (`pack_propagate(False)`) con un `Label`
   (`display`) que muestra la **imagen** o el respaldo de color;
3. un `Label` con el **nombre** debajo (bold).

### Botones

Crear siempre con el helper **`_boton(parent, texto, comando, color=ACCENT)`**:
`relief="flat"`, `fg="white"`, `activebackground=ACCENT_HOVER`,
`cursor="hand2"`, `disabledforeground="#6b6f7d"`. No crear `tk.Button` sueltos
con estilo propio.

## Patrones de interacción (estados de la carta)

Toda la apariencia de una carta se centraliza en **`_pintar_carta(nombre)`**, que
decide el aspecto según el estado. Para cambiar el look de un estado, editar ahí
(no esparcir `config()` por el código).

- **Seleccionar** (`_seleccionar`, clic izquierdo): borde **dorado** (`GOLD`).
  Solo puede haber una seleccionada; es la candidata para "Adivinar".
- **Descartar / recuperar** (`_toggle_descarte`, **doble clic**): alterna en
  `self.descartadas`. Descartada → fondo `BG_CARD_OFF`, una **✕** en color `BAD`
  y nombre atenuado. Al descartar manualmente, se envía `DESCARTAR` al servidor.
- **Hover** (`_hover`, `<Enter>`/`<Leave>`): borde `ACCENT` si la carta está
  activa y no seleccionada (feedback al pasar el ratón).
- **Filtrado automático** (`_filtrar_tablero`): al responder una pregunta propia,
  se descartan las cartas incompatibles (SI → quita las que no coinciden; NO →
  quita las que coinciden) y se repinta cada una.

### Estados globales de la partida

- **Turno** (`_set_turno`): etiqueta `● ES TU TURNO` en `OK` o `○ Turno del
  rival` en `BAD`; además **habilita/inhabilita** los botones con
  `_habilitar_controles()` (no se puede preguntar/adivinar fuera de turno).
- **Fin**: `messagebox.showinfo` con ganar/perder + la moto secreta del rival;
  los controles quedan deshabilitados.
- **Barra de estado** (`lbl_estado`): mensajes breves ("Seleccionada: ...",
  "Tu turno: pregunta o adivina", errores). Es el canal de feedback secundario.

## Mejores prácticas para UI consistente y separada de la lógica

1. **Colores/medidas solo por constante.** Cambios de tema = editar las
   constantes del inicio, no los widgets uno por uno.
2. **Apariencia de carta centralizada** en `_pintar_carta`; estados nuevos se
   agregan ahí. La construcción (una sola vez) va en `_construir_tablero`.
3. **Construcción por secciones**: respetar los métodos `_construir_encabezado`,
   `_construir_zona_tablero`, `_construir_panel`, `_construir_barra_estado`. Cada
   zona se arma en su método.
4. **Tkinter no es thread-safe**: la red SIEMPRE llega por `queue` y se procesa
   en `_procesar_cola` (vía `root.after`). Nunca tocar widgets desde el hilo de
   red (`_escuchar`).
5. **Conservar referencias a las imágenes** (`self.imagenes[nombre]`,
   `display.image = img`, `self._mi_img`) o el recolector de basura las borra y
   las cartas salen en blanco.
6. **Respaldo sin imagen**: mantener el camino que dibuja un bloque de color con
   el nombre cuando falta el PNG; la UI no debe asumir que las imágenes existen.
7. **La UI no aplica reglas**: no decidir aquí quién gana, si una jugada es
   válida o de quién es el turno. Solo refleja lo que dice el servidor; este
   revalida todo. El filtrado local es solo ayuda visual.
8. **Valores derivados de `motos.py`**, no listas hardcodeadas de atributos o
   valores en la UI.
9. **Texto y emojis en UTF-8**: el archivo lleva `# -*- coding: utf-8 -*-`;
   los símbolos (`●`, `○`, `✕`) van en literales de cadena.
