# 📱 Guion de sustentación — Adivina el Crack

> Hecho para estudiar en el celular. Lo más importante está arriba: **las 3
> preguntas que el profe SÍ pregunta**. Respuestas listas para decir + el código
> exacto que las respalda.

---

# 🔥 LAS 3 PREGUNTAS CLAVE (apréndetelas bien)

## 1) ¿Qué utilizaste para hacer el juego?

**Respuesta corta para decir:**
> *"Lo hice en **Python 3.10**, usando **solo la biblioteca estándar**, sin
> instalar nada (cero dependencias). Es **cliente-servidor en ambiente web**: el
> servidor HTTP + WebSocket lo escribí **a mano**, no usé frameworks como Flask ni
> librerías de WebSocket. El frontend es **HTML, CSS y JavaScript puro**. Está
> desplegado en internet en **Render**."*

**Módulos que usé (por si pide detalle):**
- `socket` → la red (sockets TCP)
- `threading` → los hilos (concurrencia)
- `queue` → cola segura entre hilos
- `json` → los mensajes entre cliente y servidor
- `random` → barajar el tablero y elegir los secretos
- `select` → vigilar varios sockets a la vez
- `hashlib`, `base64`, `struct` → para implementar el WebSocket a mano
- `logica.py` y `motos.py` → las reglas y los 24 jugadores (sin red)

**Por qué tiene mérito:** no usé librerías que "hagan la magia"; el servidor web,
el WebSocket y la concurrencia están hechos **a mano con la biblioteca estándar**,
así que **los hilos y los sockets están a la vista** (que es lo que evalúa).

---

## 2) ¿Qué TIPO de sockets utilizaste?

**Respuesta corta para decir:**
> *"**Sockets TCP**. En código creo el socket con
> `socket.socket(socket.AF_INET, socket.SOCK_STREAM)`: **AF_INET** es IPv4 y
> **SOCK_STREAM** es **TCP**. Usé TCP porque el juego necesita que los mensajes
> lleguen **completos, en orden y sin perderse** —no puedo perder una pregunta o
> una respuesta—; eso lo garantiza TCP y UDP no."*

**El código exacto (`web/servidor_web.py`, función `main`):**
```python
servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # IPv4 + TCP
servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # reutilizar puerto
servidor.bind((HOST, PORT))   # se "pega" al puerto
servidor.listen()             # queda escuchando
...
conn, addr = servidor.accept()  # acepta un cliente (bloqueante)
```
Operaciones del socket: **`bind` → `listen` → `accept` → `recv` / `sendall`**.

**Sobre el WebSocket (pregunta trampa frecuente):**
> *"El **WebSocket NO es otro tipo de socket**: es un **protocolo que viaja SOBRE
> el mismo socket TCP**. El navegador no puede abrir un socket TCP crudo, entonces
> manda una petición HTTP con la cabecera `Upgrade: websocket`; yo respondo
> `101 Switching Protocols` con una clave calculada con **SHA-1 + Base64**, y de
> ahí en adelante los mensajes van en **'frames'** por ese mismo socket TCP. Todo
> ese handshake y el 'framing' lo programé a mano en `web/ws.py`."*

> Dato extra: en el modo clásico de respaldo también uso **UDP** (`SOCK_DGRAM`)
> para que el cliente **descubra** al servidor en la red local.

---

## 3) ¿Cómo manejaste los hilos?

**Respuesta corta para decir:**
> *"Con el módulo **`threading`**. El **hilo principal** solo hace `accept()`
> esperando conexiones; por **cada cliente que entra lanzo un hilo nuevo**; y
> **cada partida corre en su propio hilo**. Así muchas partidas avanzan **en
> paralelo** sin bloquearse. El estado de cada partida es privado de su hilo, y lo
> único compartido —la cola de espera— lo protejo con un **`Lock`**."*

**Los hilos que hay corriendo:**
1. **Hilo principal** → bucle de `accept()` (acepta conexiones).
2. **1 hilo por conexión** → atiende el handshake y luego **lee** los mensajes de
   ese jugador.
3. **1 hilo por partida** → la clase `GameRoom` **es** un hilo.
4. **1 hilo para el monitor** → transmite las estadísticas en vivo.

**El código exacto:**
```python
# 1 hilo por cada conexión (web/servidor_web.py, en el accept loop):
threading.Thread(target=manejar_conexion, args=(conn, addr), daemon=True).start()

# 1 hilo por partida (web/salas.py):
class GameRoom(threading.Thread):
    def __init__(self, ...):
        super().__init__(daemon=True)   # se arranca con .start() -> ejecuta run()
```

**Sincronización (esto es lo que el profe quiere oír):**
- **`threading.Lock`** en `GestorSalas` (`self.lock = threading.Lock()`): protege la
  **cola de espera** (estado compartido entre hilos) → evita **condiciones de
  carrera** al emparejar dos jugadores a la vez.
- **`threading.Event`** (`evento_sala`): **despierta** al jugador que está en
  espera justo cuando llega un rival.
- **`queue.Queue`**: cola **segura entre hilos** por la que el hilo lector le pasa
  las jugadas al hilo de la partida.
- Todos los hilos son **`daemon=True`** → se cierran al apagar el servidor.

**🧠 Pregunta avanzada (el GIL) — si la hace, brillas:**
> *"Sé que Python tiene **GIL** (solo un hilo ejecuta código Python a la vez).
> Pero en operaciones de **red bloqueantes** como `recv` o `accept`, el hilo
> **libera el GIL** mientras espera; por eso, en un servidor de entrada/salida como
> este, los hilos **sí dan concurrencia real**: mientras un hilo espera el mensaje
> de un jugador, otro hilo avanza su partida."*

---

# 🅰️ Lo que pidió el profesor (mapeo rápido)

| Requisito | Cómo lo cumplo | Dónde |
|-----------|----------------|-------|
| **Emparejamiento** (espera → partida independiente) | Cola con `Lock`; al haber par se crea un `GameRoom` (hilo) | `salas.py` `GestorSalas.unir`, `GameRoom` |
| **Tablero aleatorio, igual para ambos, secreto distinto** | `random.shuffle(tablero)` y `random.sample(tablero, 2)` | `salas.py` `_setup()` |
| **Turnos, preguntas SÍ/NO, adivinar, validar, victoria** | Servidor valida turno y datos; decide quién gana | `salas.py` `_procesar*`, `logica.py` |
| **Estado solo en el servidor** | Tablero, secretos, turno y marcador viven en `GameRoom` | `salas.py` |
| **Múltiples partidas sin interferencia** | Un hilo por partida (estado privado) + `Lock` en lo compartido | `GameRoom`, `GestorSalas` |

**Frase resumen:** *"El cliente solo dibuja; **todas las reglas y el estado están
en el servidor**, y la concurrencia se logra con un hilo por partida."*

---

# 🅱️ Lo que agregamos (extras, no exigidos)

- **📡 Monitor en vivo (`/monitor`)** → muestra en tiempo real las **partidas
  activas (= hilos)**, jugadores en cola (**Lock**) y conexiones. *Hace VISIBLE la
  concurrencia* — úsalo para demostrar el requisito.
- **🤖 vs Bot** (fácil/normal/difícil) → reutiliza `logica.py`.
- **🔒 Salas privadas con código + QR.**
- **⏱️ Partida rápida** con reloj por turno.
- **💬 Chat de texto** (viaja por el mismo WebSocket) y **😀 emojis**.
- **🗣️ Multi-idioma es/en**, **🎴 caricaturas** y **avatares de entrenadores**.
- **🌐 Desplegado en internet** (Render).

---

# 🎥 Demo en vivo (orden sugerido)
1. Landing (cómo se juega, reglas, galería).
2. Abre **`/monitor`** en otra pestaña.
3. Crea una **sala privada**, únete con el **QR** desde el celular → muestra:
   emparejamiento, tablero igual, secreto distinto, turnos, pregunta SÍ/NO,
   adivinar, victoria.
4. Lanza **2-3 partidas vs Bot** → el monitor marca **3 activas** → *"cada una es
   un hilo en paralelo"*.

---

# ❓ Banco de preguntas

- **¿Qué es un socket?** → Un extremo de comunicación por red. Aquí, TCP: el
  servidor hace `bind`, `listen`, `accept`.
- **¿TCP o UDP y por qué?** → TCP, porque garantiza entrega **completa y en orden**
  (no puedo perder preguntas/respuestas).
- **¿Qué es un hilo?** → Una línea de ejecución dentro del proceso; comparten
  memoria. Lo uso para atender varias partidas a la vez.
- **¿Por qué un hilo por partida?** → Para **aislar** el estado y que corran en
  **paralelo** sin interferirse.
- **¿Dónde usas el Lock y por qué?** → En la cola de espera (`GestorSalas`), que es
  compartida; evita condiciones de carrera al emparejar.
- **¿Dónde está el estado del juego?** → Solo en el servidor (`GameRoom`).
- **¿Y si un jugador se desconecta?** → El hilo lector lo detecta y el rival gana.
- **¿Por qué WebSocket?** → El navegador no abre TCP crudo; el WebSocket va **sobre**
  TCP y lo implementé a mano (handshake + frames).

---

# ✅ Checklist antes de exponer
- [ ] Hacer el **Manual Deploy** final en Render.
- [ ] Abrir la URL **5 min antes** (para que "despierte").
- [ ] 2 pestañas listas: **el juego** y **`/monitor`**.
- [ ] Celular con cámara para el **QR**.
- [ ] Saber abrir rápido **2-3 vs Bot** para inflar el monitor.
- [ ] Tener abiertos: `servidor_web.py`, `salas.py`, `ws.py`, `logica.py`.

---

**Lo esencial en una frase:**
> *"Python puro, **sockets TCP** (`AF_INET`/`SOCK_STREAM`) con un **WebSocket hecho
> a mano** encima, y **`threading`**: hilo principal que acepta, un hilo por
> conexión y un hilo por partida, con un **`Lock`** protegiendo la cola compartida."*
