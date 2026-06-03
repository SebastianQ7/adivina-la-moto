# Adivina el Crack ⚽

Implementación cliente-servidor del clásico juego de mesa **Adivina Quién**, donde
en lugar de personajes con caras, el tablero usa **24 futbolistas icónicos** (en
caricatura).

Proyecto para la materia **Programación Distribuida y Paralela** del
**Politécnico Colombiano Jaime Isaza Cadavid**.

🌐 **En vivo:** https://adivina-la-moto.onrender.com · 📡 **Monitor:** https://adivina-la-moto.onrender.com/monitor

---

## 📋 Descripción

Dos jugadores se conectan a un servidor. A cada uno se le asigna en secreto un
**jugador** del tablero. Por turnos hacen **preguntas de sí/no** sobre los atributos
(posición, confederación, pie hábil, etc.) para ir descartando candidatos. Gana
quien **adivine primero** al jugador secreto del rival. Ojo: **fallar una adivinanza
hace perder de inmediato** (regla clásica).

Hay **dos frontends sobre el mismo motor**:
- **Web** (principal): navegador y móvil, desplegable en internet.
- **Clásico** (respaldo): cliente gráfico de escritorio en Tkinter.

El proyecto cumple el requisito obligatorio de usar **hilos (`threading`)** y
**sockets (`socket`)** de la biblioteca estándar de Python.

---

## 🧵 Modelo de concurrencia (lo que valora el profesor)

Tanto el modo web como el clásico usan el **mismo modelo**:

- El **hilo principal** del servidor solo hace `accept()` (operación bloqueante).
- Cada **conexión** entrante se atiende en **su propio hilo**, para que un cliente
  lento no congele la aceptación de los demás.
- Cada **partida** corre en **su propio hilo** (`GameSession` / `GameRoom`), de modo
  que varias partidas avanzan **en paralelo** sin estorbarse. El estado de cada
  partida es privado del hilo.
- La **cola de emparejamiento** (`WaitingRoom` / `GestorSalas`) es estado
  **compartido** entre hilos, por eso se protege con un **`threading.Lock`** (evita
  condiciones de carrera al emparejar).
- En el modo web, el **WebSocket está hecho a mano** sobre el módulo `socket`
  (handshake + framing), sin librerías: así el uso de sockets queda **a la vista**.
- La página **`/monitor`** transmite por WebSocket, desde un hilo dedicado, cuántas
  partidas (hilos) están activas, cuántos jugadores hay en cola (`Lock`) y cuántas
  conexiones existen: **hace visible la concurrencia** en tiempo real.

---

## 🏗️ Arquitectura (modo web)

```
   Navegador (HTML/CSS/JS)                 ┌──────────────── servidor_web.py ───────────────┐
   · landing, lobby, tablero               │  Hilo principal:  socket.accept()  ──► 1 hilo  │
   · chat · emojis · /monitor              │                                      por conexión│
        │            ▲                      │        │                  │                      │
        │ WebSocket  │ WebSocket            │        ▼                  ▼                      │
        ▼            │                      │   ws.py (WebSocket a mano sobre socket)          │
   ┌─────────┐   ┌─────────┐                │        │                  │                      │
   │Jugador 1│   │Jugador 2│  ───────────►  │   GestorSalas (cola + threading.Lock)            │
   └─────────┘   └─────────┘                │        │ empareja                                 │
                                            │        ▼                                          │
                                            │   GameRoom (threading.Thread) · 1 partida=1 hilo  │
                                            │        │ usa                                      │
                                            │   logica.py + motos.py  (reglas puras)            │
                                            └──────────────────────────────────────────────────┘
```

---

## ⚙️ Requisitos técnicos

- **Python 3.7+** — **solo biblioteca estándar** (`socket`, `threading`, `json`…).
- Sin dependencias externas para correr el juego.
- *(Solo para regenerar las caricaturas se usa Pillow; no hace falta para jugar.)*

---

## ▶️ Cómo ejecutar

### Modo web (principal)
```bash
python web/servidor_web.py        # http://localhost:8000  (y /monitor)
```
Abre **http://localhost:8000** en el navegador. En la **landing** verás cómo se
juega, las reglas y la galería; pulsa **Jugar**, escribe tu nombre, elige avatar y
un modo. Para jugar de a dos: abre la página en dos dispositivos/pestañas, o usa el
modo **vs Bot** para jugar solo.

### Modo clásico (respaldo, escritorio)
```bash
python server.py                  # TCP 0.0.0.0:5000 + autodescubrimiento UDP
python gui_client.py              # ventana del jugador 1
python gui_client.py              # ventana del jugador 2
```

---

## 🌐 Despliegue (Render)

- Desplegado en **Render** (plan gratis): el servidor lee el puerto de la variable
  `PORT` y escucha en `0.0.0.0`; sirve HTTP + WebSocket por ese único puerto.
- Repo: **https://github.com/SebastianQ7/adivina-la-moto** (rama `main`).
- Render está conectado a otra cuenta de GitHub, por lo que **no hay auto-deploy**:
  tras un `push` se hace **Manual Deploy → Deploy latest commit** en Render.
- El plan gratis "duerme" tras ~15 min de inactividad; la primera carga tras dormir
  tarda ~40 s (conviene abrir la URL unos minutos antes de usarla).

---

## 🎮 Modos de juego

| Modo | Descripción |
|------|-------------|
| **Pública** | Te empareja con el siguiente que busque rival. |
| **Privada** | Creas con tu **código** → se genera un **QR**; el otro entra con código o QR. |
| **Rápida** | Con **reloj de 30 s** por turno; si se agota, pierdes el turno (no la partida). |
| **vs Bot** | Juegas solo contra la máquina (dificultad **fácil / normal / difícil**). |

Extras: **chat de texto** y **emojis** entre jugadores, tablero que **tacha solo**
los imposibles, **revancha**, **marcador** de la sesión y **multi-idioma (es/en)**.

---

## 📁 Descripción de los archivos

**Núcleo compartido (sin red ni hilos):**

| Archivo | Responsabilidad |
|---------|-----------------|
| `motos.py` | Datos de los 24 jugadores y sus 7 atributos. *(Conserva el nombre `motos`/`motos.py` por compatibilidad; el motor es genérico.)* |
| `logica.py` | Reglas **puras**: validar, responder SÍ/NO, descartar candidatos. |
| `protocolo.py` | Tipos de mensaje y envío/recepción JSON. |

**Modo web (`web/`):**

| Archivo | Responsabilidad |
|---------|-----------------|
| `web/servidor_web.py` | Servidor HTTP + WebSocket (accept en hilo principal, un hilo por conexión). Sirve la página, `/api/motos`, `/api/avatares` y `/monitor`. |
| `web/ws.py` | WebSocket **a mano** sobre `socket` crudo (handshake + framing). |
| `web/salas.py` | `GestorSalas` (cola con `Lock`, salas privadas) y `GameRoom` (una partida = un hilo); registro de partidas activas. |
| `web/bot.py` | Bot que usa `logica.py`; dificultad fácil/normal/difícil. |
| `web/static/` | `index.html`, `style.css`, `app.js`, `i18n.js`, `monitor.html`, `sounds/`. |
| `web/procesar_cartoon.py`, `web/procesar_lote.py` | Recortan el fondo de las caricaturas (transparente) y las normalizan. |

**Modo clásico:**

| Archivo | Responsabilidad |
|---------|-----------------|
| `server.py` | Servidor TCP multihilo (`WaitingRoom`+`Lock`, `GameSession`) + autodescubrimiento UDP. |
| `gui_client.py` | Cliente gráfico Tkinter (hilo de red + `queue.Queue` para actualizar la UI). |
| `imagenes/` | Caricaturas `<slug>.png` de los jugadores y `avatares/` (entrenadores). |
| `tests/` | Pruebas con `unittest` (datos, lógica y protocolo). |

---

## 📡 Resumen del protocolo (web)

Mensajes JSON con una clave `tipo`, sobre WebSocket.

**Cliente → Servidor:** `JOIN` (nombre, modo, código, rápida, dificultad) ·
`PREGUNTA` (atributo, valor) · `ADIVINAR` (moto) · `DESCARTAR` · `EMOJI` ·
`CHAT` (texto) · `RENDIRSE` · `REVANCHA` · `SALIR` · `MONITOR` (abre el panel).

**Servidor → Cliente:** `ESPERANDO` (msg, código) · `INICIO` (tu_moto, tablero,
tu_turno, rival, marcador, reloj) · `TURNO` · `RESPUESTA` · `EMOJI` · `CHAT` ·
`FIN` (ganaste, moto_rival, marcador, revancha) · `ERROR` · `STATS` (al monitor).

> En el modo clásico (TCP) los mensajes van delimitados por `\n` (framing en
> `protocolo.Receptor`), y hay autodescubrimiento por *broadcast* UDP.

---

## ⚽ Los 24 jugadores del tablero

Atributos: **posicion** (portero/defensa/mediocampista/delantero),
**confederacion** (uefa/conmebol), **pie** (derecho/izquierdo),
**era** (leyenda/dosmil/actual), **gano_mundial** (si/no),
**gano_balon_oro** (si/no), **liga** (laliga/seriea/bundesliga/premier/ligue1/otra).

| # | Jugador | posición | conf. | pie | era | Mundial | B.Oro | liga |
|---|---------|----------|-------|-----|-----|:---:|:---:|------|
| 1 | Gianluigi Buffon | portero | uefa | derecho | dosmil | si | no | seriea |
| 2 | Iker Casillas | portero | uefa | derecho | actual | si | no | laliga |
| 3 | Manuel Neuer | portero | uefa | derecho | actual | si | no | bundesliga |
| 4 | Sergio Ramos | defensa | uefa | derecho | actual | si | no | laliga |
| 5 | Paolo Maldini | defensa | uefa | izquierdo | leyenda | no | no | seriea |
| 6 | Franz Beckenbauer | defensa | uefa | derecho | leyenda | si | si | bundesliga |
| 7 | Roberto Carlos | defensa | conmebol | izquierdo | dosmil | si | no | laliga |
| 8 | Fabio Cannavaro | defensa | uefa | derecho | dosmil | si | si | seriea |
| 9 | Zinedine Zidane | mediocampista | uefa | derecho | dosmil | si | si | laliga |
| 10 | Andrés Iniesta | mediocampista | uefa | derecho | actual | si | no | laliga |
| 11 | Xavi Hernández | mediocampista | uefa | derecho | actual | si | no | laliga |
| 12 | Luka Modrić | mediocampista | uefa | derecho | actual | no | si | laliga |
| 13 | Kevin De Bruyne | mediocampista | uefa | derecho | actual | no | no | premier |
| 14 | Michel Platini | mediocampista | uefa | derecho | leyenda | no | si | seriea |
| 15 | Kaká | mediocampista | conmebol | derecho | dosmil | si | si | seriea |
| 16 | Andrea Pirlo | mediocampista | uefa | derecho | dosmil | si | no | seriea |
| 17 | Lionel Messi | delantero | conmebol | izquierdo | actual | si | si | laliga |
| 18 | Cristiano Ronaldo | delantero | uefa | derecho | actual | no | si | laliga |
| 19 | Pelé | delantero | conmebol | derecho | leyenda | si | no | otra |
| 20 | Diego Maradona | delantero | conmebol | izquierdo | leyenda | si | no | seriea |
| 21 | Ronaldo Nazário | delantero | conmebol | derecho | dosmil | si | si | laliga |
| 22 | Ronaldinho | delantero | conmebol | derecho | dosmil | si | si | laliga |
| 23 | Kylian Mbappé | delantero | uefa | derecho | actual | si | no | ligue1 |
| 24 | Robert Lewandowski | delantero | uefa | derecho | actual | no | no | bundesliga |

> La `liga` es la más representativa de su carrera y la `era` es aproximada.

---

## 🧪 Pruebas realizadas

Probado de extremo a extremo: partida completa con adivinanza correcta y fallida,
emparejamiento de dos jugadores, salas privadas por código, reloj de la partida
rápida, chat, emojis, revancha, varias partidas concurrentes (visibles en
`/monitor`) y manejo de desconexiones (si un jugador se cae, gana el rival).
