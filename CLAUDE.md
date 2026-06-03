# Adivina el Crack — Fútbol

Proyecto para la materia **Programación Distribuida y Paralela** del
**Politécnico Colombiano Jaime Isaza Cadavid**.

## Descripción

Implementación del juego de mesa *Adivina Quién* en modo cliente-servidor.
En lugar de personajes con caras, el tablero usa **24 futbolistas icónicos**
(en caricatura) como fichas. Tiene dos frontends sobre el mismo motor:

- **Web** (principal): jugable en navegador y móvil, desplegable en internet.
- **Clásico** (respaldo): cliente gráfico de escritorio en Tkinter.

Uso explícito de **hilos y sockets** es **requisito obligatorio** de la materia.

## Stack técnico

- **Lenguaje:** Python 3 (solo biblioteca estándar)
- **Concurrencia:** módulo `threading` (un hilo por conexión, un hilo por partida)
- **Red:** módulo `socket` — TCP para el modo clásico; HTTP + **WebSocket hecho a
  mano** (sobre `socket`) para el modo web
- **Frontend web:** HTML/CSS/JS vanilla; **Tkinter** para el cliente clásico

## Arquitectura

### Núcleo compartido (reglas puras, sin red ni hilos)
| Archivo | Descripción |
|---------|-------------|
| `motos.py` | Datos de los 24 jugadores y sus atributos. *(Conserva el nombre `motos.py` y el dict `motos` por compatibilidad; el motor es genérico.)* |
| `logica.py` | Reglas del juego: evaluar preguntas, descartar candidatos, validar |
| `protocolo.py` | Tipos de mensaje y envío/recepción JSON |

### Modo web (principal) — carpeta `web/`
| Archivo | Descripción |
|---------|-------------|
| `web/servidor_web.py` | Servidor HTTP + WebSocket. Hilo principal hace `accept()`; un hilo por conexión. Sirve la página, `/api/motos`, `/api/avatares` y `/monitor` |
| `web/ws.py` | WebSocket **a mano** sobre `socket` crudo (handshake + framing) |
| `web/salas.py` | `GestorSalas` (cola pública/rápida y salas privadas, protegido con `Lock`) y `GameRoom` (una partida = un hilo). Registro de partidas activas para el monitor |
| `web/bot.py` | Bot que usa `logica.py`; dificultad fácil / normal / difícil |
| `web/static/` | `index.html`, `style.css`, `app.js`, `i18n.js` (es/en), `monitor.html`, `sounds/` |
| `web/procesar_cartoon.py`, `web/procesar_lote.py` | Utilidades que recortan el fondo de las caricaturas (transparente) y las normalizan |

### Modo clásico (respaldo)
| Archivo | Descripción |
|---------|-------------|
| `server.py` | Servidor TCP multihilo (`WaitingRoom` + `Lock`, `GameSession` por partida) + autodescubrimiento UDP |
| `gui_client.py` | Cliente gráfico Tkinter |

## Los 24 jugadores del tablero

Atributos (los que se usan para preguntar):

- **posicion** — portero / defensa / mediocampista / delantero
- **confederacion** — uefa / conmebol
- **pie** — derecho / izquierdo
- **era** — leyenda / dosmil / actual
- **gano_mundial** — si / no
- **gano_balon_oro** — si / no
- **liga** (más representativa) — laliga / seriea / bundesliga / premier / ligue1 / otra

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

## Flujo del juego (web)

1. El servidor escucha en `0.0.0.0:$PORT` (HTTP + WebSocket) y sirve la página.
2. En la **landing** el jugador ve cómo se juega, las reglas y la galería; pulsa
   **Jugar**, escribe su **nombre**, elige **avatar** (entrenador) y un **modo**:
   pública, privada (código + QR), partida rápida (reloj 30 s) o **vs Bot**.
3. Al emparejar, el servidor asigna a cada uno un jugador secreto distinto y envía
   el mismo tablero (24 fichas en orden aleatorio).
4. Por turnos se envían preguntas sí/no sobre los atributos; el servidor evalúa
   contra el jugador rival y responde a ambos. El tablero **tacha solo** los
   imposibles. Hay **chat** y **emojis** entre jugadores.
5. Quien adivina al rival gana (fallar hace perder). Al final hay **revancha** y
   se lleva el **marcador** de la sesión.

## Modos de juego y rutas

- **Modos:** pública · privada (código propio + QR) · partida rápida (reloj 30 s,
  al agotarse se pierde el turno) · vs Bot (dificultad fácil/normal/difícil).
- **`/monitor`** — panel en vivo (por WebSocket) que muestra partidas activas
  (hilos `GameRoom`), jugadores en cola (`Lock`) y conexiones. Hace **visible la
  concurrencia**; ideal para la sustentación.

## Despliegue

- Desplegado en **Render** (plan gratis): https://adivina-la-moto.onrender.com
- Repo: https://github.com/SebastianQ7/adivina-la-moto (rama `main`).
- Render está conectado a otra cuenta de GitHub, así que **no hay auto-deploy**:
  tras un `push` hay que hacer **Manual Deploy → Deploy latest commit** en Render.
- El servidor lee el puerto de la variable de entorno `PORT` y escucha en `0.0.0.0`.

## Notas de desarrollo

- Las imágenes de los jugadores son `imagenes/<slug>.png` (caricaturas con fondo
  transparente). Los avatares (entrenadores) están en `imagenes/avatares/`.
- Las caricaturas originales sin procesar van en `imagenes/cartoon_raw/`
  (ignoradas por git). Se procesan con `python web/procesar_lote.py`.
- Para correr en local: `python web/servidor_web.py` → http://localhost:8000
- Mensajes JSON UTF-8; en el modo clásico van delimitados por `\n` sobre TCP.
