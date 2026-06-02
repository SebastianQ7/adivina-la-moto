# Adivina Quién — Motos 🏍️

Implementación cliente-servidor del clásico juego de mesa **Adivina Quién**, donde
en lugar de personajes con caras, el tablero usa **24 motos icónicas reales**.

Proyecto para la materia **Programación Distribuida y Paralela** del
**Politécnico Colombiano Jaime Isaza Cadavid**.

---

## 📋 Descripción

Dos jugadores se conectan a un servidor. A cada uno se le asigna en secreto una
moto del tablero. Por turnos, hacen **preguntas de sí/no** sobre los atributos de
las motos (origen, estilo, cilindrada, etc.) para ir descartando candidatas. Gana
quien **adivine primero** la moto secreta del rival. Ojo: **fallar una adivinanza
hace perder de inmediato** (regla clásica).

El proyecto cumple el requisito obligatorio de la materia de usar **hilos
(`threading`)** y **sockets (`socket`)** de la biblioteca estándar de Python.

---

## 🏗️ Arquitectura

```
                       ┌────────────────────────────────────────────┐
                       │                 SERVER.PY                    │
                       │                                              │
   ┌────────────┐ TCP  │   ┌────────────────────────────────────┐   │
   │ CLIENT.PY  │◄────►│   │  Hilo principal (accept loop)       │   │
   │ Jugador 1  │      │   │  socket.accept() ──► nuevo hilo     │   │
   │ ┌────────┐ │      │   └────────────────────────────────────┘   │
   │ │hilo RX │ │      │            │                  │             │
   │ │(red)   │ │      │            ▼                  ▼             │
   │ ├────────┤ │      │   ┌──────────────┐   ┌──────────────┐      │
   │ │hilo    │ │      │   │ hilo handshake│  │ hilo handshake│     │
   │ │teclado │ │      │   │  (espera JOIN)│  │  (espera JOIN)│     │
   │ └────────┘ │      │   └──────┬───────┘   └──────┬───────┘      │
   └────────────┘      │          │                  │              │
                       │          ▼                  ▼              │
   ┌────────────┐ TCP  │   ┌────────────────────────────────────┐  │
   │ CLIENT.PY  │◄────►│   │   WaitingRoom (cola + threading.Lock)│ │
   │ Jugador 2  │      │   └────────────────┬───────────────────┘  │
   │ ┌────────┐ │      │                    │ empareja             │
   │ │hilo RX │ │      │                    ▼                       │
   │ │hilo TX │ │      │   ┌────────────────────────────────────┐  │
   │ └────────┘ │      │   │ GameSession (threading.Thread)      │  │
   └────────────┘      │   │  · una partida = un hilo            │  │
                       │   │  · tablero + motos secretas + turno │  │
   ┌────────────┐ TCP  │   └────────────────────────────────────┘  │
   │ CLIENT.PY  │◄────►│              ▲                              │
   │ Jugador 3  │      │              │ usa los datos               │
   │ (en espera)│      │      ┌───────────────┐                     │
   └────────────┘      │      │   MOTOS.PY    │ (24 motos, sin red) │
                       │      └───────────────┘                     │
                       │      ┌───────────────┐                     │
                       │      │  PROTOCOLO.PY │ (mensajes JSON)      │
                       │      └───────────────┘                     │
                       └────────────────────────────────────────────┘

Protocolo: mensajes JSON UTF-8 delimitados por '\n' sobre TCP.
```

**Modelo de concurrencia (lo que valora el profesor):**

- El **hilo principal** del servidor solo hace `accept()` (operación bloqueante).
- Cada **conexión** entrante se atiende en **su propio hilo de handshake**, para que
  un cliente lento no congele la aceptación de los demás.
- Cada **partida** corre en **su propio hilo** (`GameSession`), de modo que varias
  partidas avanzan en paralelo sin estorbarse. El estado de cada partida es privado
  del hilo, así que no requiere sincronización.
- La **sala de espera** (`WaitingRoom`) es estado **compartido** entre los hilos de
  handshake, por eso se protege con un **`threading.Lock`** (evita condiciones de
  carrera al emparejar).
- El **cliente gráfico** usa un **hilo de red** que recibe los mensajes (`recv`,
  bloqueante) y los deja en una `queue.Queue`; la ventana (Tkinter) los consume con
  `root.after()`. Así la interfaz nunca se congela y se actualiza de forma segura
  (Tkinter **no** es seguro entre hilos).
- El **servidor** además lanza un **hilo de autodescubrimiento UDP** que responde a
  los *broadcast* de los clientes para que estos encuentren su IP sin configurarla.

---

## ⚙️ Requisitos técnicos

- **Python 3.7+** (se usa `socket.sendall`, f-strings y `dict` ordenado).
- **Solo biblioteca estándar**: `socket`, `threading`, `json`, `random`, `sys`.
- No requiere instalar dependencias externas.

---

## ▶️ Instrucciones de ejecución (paso a paso)

El juego es **gráfico** (Tkinter). La forma más fácil:

**Opción A — un solo clic:** ejecuta **`iniciar_juego_grafico.bat`**. Abre el
servidor y las dos ventanas de los jugadores automáticamente.

**Opción B — manual** (una terminal por proceso, en la carpeta del proyecto):
```bash
python server.py     # 1) servidor (TCP 0.0.0.0:5000 + autodescubrimiento UDP)
python gui_client.py # 2) ventana del jugador 1
python gui_client.py # 3) ventana del jugador 2
```
En cada ventana aparece el **lobby**: escribe tu **nombre**, elige un **avatar** y
pulsa **JUGAR**. El cliente **encuentra el servidor solo** (no se escribe IP ni
puerto). En cuanto los dos pulsan JUGAR, **la partida arranca automáticamente**.

**Jugar en dos computadores distintos (red local):** no hay que configurar nada.
Levanta `server.py` en un equipo y abre `gui_client.py` en cada PC: el
**autodescubrimiento por UDP** localiza el servidor en la red. Solo deben estar en
la **misma red local** (si el firewall pregunta, permite el acceso a Python).

> **Modo directo (opcional, para pruebas):**
> `python gui_client.py <nombre> [host] [puerto]` se salta el lobby y conecta a esa
> dirección. Sin argumentos, usa el lobby con autodescubrimiento.

**Cómo se juega (en la ventana):**

| Acción | Cómo |
|--------|------|
| Preguntar | Elige **atributo** y **valor** en los menús y pulsa **Preguntar** |
| Adivinar | Selecciona una carta (clic) y pulsa **Adivinar la seleccionada** |
| Descartar / recuperar una carta | **Doble clic** sobre la carta |
| Ver de quién es el turno | Indicador de color en el panel derecho |

---

## 📁 Descripción de cada archivo

| Archivo | Responsabilidad |
|---------|-----------------|
| **`motos.py`** | Base de datos de las 24 motos (diccionario `motos`) con sus 7 atributos, la lista `ATRIBUTOS` y `tabla_balanceo()`. Sin red ni hilos. |
| **`logica.py`** | Reglas **puras** del juego (sin red ni hilos): validar atributo/personaje, responder SI/NO y eliminar candidatos. Reutilizada por servidor y cliente. |
| **`protocolo.py`** | Capa de comunicación **compartida**: tipos de mensaje, `crear()`, `enviar()` (JSON + `\n`) y la clase `Receptor` (reconstruye mensajes del flujo TCP). |
| **`server.py`** | Servidor multihilo. Clases `Jugador`, `WaitingRoom` (cola con `Lock`) y `GameSession` (`threading.Thread`, una partida por hilo, con un hilo lector por jugador). |
| **`gui_client.py`** | Cliente **gráfico** (Tkinter): lobby (nombre + avatar), tablero de cartas, controles e historial. Hilo de red + `queue.Queue` para actualizar la UI con seguridad. |
| **`generar_avatares.py`** | Utilidad que genera los avatares PNG del lobby en `imagenes/avatares/` (solo biblioteca estándar). |
| **`imagenes/`** | Las 24 imágenes PNG de las motos (con respaldo si falta alguna) y la subcarpeta `avatares/` con los avatares del lobby. |
| **`iniciar_juego_grafico.bat`** | Lanzador: abre servidor + 2 ventanas de un clic. |
| **`tests/`** | Pruebas con `unittest` (datos, lógica y protocolo). |
| **`README.md` / `CLAUDE.md`** | Documentación y contexto del proyecto. |

---

## 📡 Resumen del protocolo

Cada mensaje es un objeto **JSON UTF-8 terminado en `\n`**, con una clave `tipo`.

### Cliente → Servidor

| `tipo` | Cuándo | Estructura |
|--------|--------|------------|
| `JOIN` | Al conectarse | `{tipo, nombre}` |
| `PREGUNTA` | En su turno | `{tipo, atributo, valor}` |
| `ADIVINAR` | En su turno | `{tipo, moto}` |
| `DESCARTAR` | Al descartar una ficha | `{tipo, moto}` |
| `REVANCHA` | Al terminar una ronda, para pedir otra | `{tipo}` |
| `SALIR` | Al abandonar | `{tipo}` |

### Servidor → Cliente

| `tipo` | Cuándo | Estructura |
|--------|--------|------------|
| `ESPERANDO` | Aún no hay rival | `{tipo, msg}` |
| `INICIO` | Al emparejar / cada ronda | `{tipo, tu_moto, tablero, tu_turno, rival, marcador}` |
| `TURNO` | Al alternar turno | `{tipo, tu_turno}` |
| `RESPUESTA` | Tras una pregunta (a ambos) | `{tipo, quien, atributo, valor, pregunta, respuesta}` |
| `FIN` | Adivinanza / abandono / desconexión | `{tipo, ganaste, moto_rival, msg, marcador, revancha}` |
| `ERROR` | Mensaje inválido | `{tipo, msg}` |

> **Nota sobre TCP:** se usa el terminador `\n` porque TCP entrega un *flujo* de
> bytes sin fronteras de mensaje; la clase `Receptor` acumula en un buffer y corta
> cada mensaje al encontrar el `\n` (framing).

> **Autodescubrimiento (UDP):** aparte del juego (TCP), el servidor escucha un
> *broadcast* UDP en el puerto **5001**. El cliente envía `ADIVINA_QUIEN_DISCOVERY?`,
> el servidor responde con su puerto TCP y el cliente deduce la IP del origen del
> paquete. Así no hace falta escribir la IP del servidor.

---

## 🏍️ Las 24 motos del tablero

Atributos: **origen** (japonesa/americana/italiana/inglesa/alemana/austriaca),
**estilo** (deportiva/naked/cruiser/touring/trail/enduro),
**cilindrada** (baja `<500cc` / media `500-999cc` / alta `≥1000cc`),
**era** (clasica_pre1990 / noventas / moderna_post2000),
**cilindros** (1/2/3/4_o_mas), **refrigeracion** (aire/liquida),
**famosa_en_cine** (si/no).

| # | Moto | origen | estilo | cilindrada | era | cilindros | refrigeracion | cine |
|---|------|--------|--------|------------|-----|-----------|---------------|------|
| 1 | Honda CBR 600RR | japonesa | deportiva | media | moderna_post2000 | 4_o_mas | liquida | no |
| 2 | Kawasaki Ninja H2 | japonesa | deportiva | media | moderna_post2000 | 4_o_mas | liquida | no |
| 3 | Yamaha YZF-R1 | japonesa | deportiva | media | noventas | 4_o_mas | liquida | si |
| 4 | Suzuki Hayabusa | japonesa | deportiva | alta | noventas | 4_o_mas | liquida | si |
| 5 | Harley-Davidson Fat Boy | americana | cruiser | alta | noventas | 2 | aire | si |
| 6 | Harley-Davidson Sportster | americana | cruiser | media | clasica_pre1990 | 2 | aire | no |
| 7 | Indian Chief | americana | cruiser | alta | clasica_pre1990 | 2 | aire | no |
| 8 | Harley-Davidson Road King | americana | touring | alta | noventas | 2 | aire | no |
| 9 | Ducati Panigale V4 | italiana | deportiva | alta | moderna_post2000 | 4_o_mas | liquida | no |
| 10 | Ducati Monster | italiana | naked | media | moderna_post2000 | 2 | liquida | no |
| 11 | Aprilia RSV4 | italiana | deportiva | alta | moderna_post2000 | 4_o_mas | liquida | no |
| 12 | Ducati Multistrada | italiana | trail | alta | moderna_post2000 | 2 | liquida | no |
| 13 | Triumph Bonneville | inglesa | naked | media | clasica_pre1990 | 2 | aire | si |
| 14 | Triumph Speed Triple | inglesa | naked | alta | noventas | 3 | liquida | si |
| 15 | Triumph Rocket 3 | inglesa | cruiser | alta | moderna_post2000 | 3 | liquida | no |
| 16 | Triumph Tiger | inglesa | trail | media | moderna_post2000 | 3 | liquida | no |
| 17 | BMW R 1250 GS | alemana | trail | alta | moderna_post2000 | 2 | liquida | no |
| 18 | BMW S1000RR | alemana | deportiva | media | moderna_post2000 | 4_o_mas | liquida | no |
| 19 | BMW R nineT | alemana | naked | alta | moderna_post2000 | 2 | aire | no |
| 20 | BMW K 1600 | alemana | touring | alta | moderna_post2000 | 4_o_mas | liquida | no |
| 21 | KTM 1290 Super Duke | austriaca | naked | alta | moderna_post2000 | 2 | liquida | no |
| 22 | KTM 1290 Super Adventure | austriaca | trail | alta | moderna_post2000 | 2 | liquida | no |
| 23 | KTM RC 390 | austriaca | deportiva | baja | moderna_post2000 | 1 | liquida | no |
| 24 | KTM 690 Enduro | austriaca | enduro | media | moderna_post2000 | 1 | liquida | no |

> Son **4 motos por origen** (6 orígenes × 4 = 24). Los valores se basan en datos
> reales del modelo de referencia.

---

## 🎬 Ejemplo de partida

Supongamos que a **Ana** le toca la `Aprilia RSV4` y a **Beto** la `BMW K 1600`.
Ana empieza (su moto la adivina Beto; Ana debe adivinar la de Beto):

```
============================================================
  PARTIDA INICIADA  -  Tu rival: Beto
  TU MOTO SECRETA (la que el rival debe adivinar): Aprilia RSV4
============================================================
>>> ES TU TURNO.

> origen alemana
[RESPUESTA] Preguntaste: ¿origen = alemana?  ->  SI
  TABLERO  (quedan 4/24 posibles)     # solo quedan las 4 alemanas

... Turno del rival. Espera tu turno.
[RESPUESTA] Beto preguntó: ¿refrigeracion = aire?  ->  NO

>>> ES TU TURNO.
> estilo touring
[RESPUESTA] Preguntaste: ¿estilo = touring?  ->  SI
  TABLERO  (quedan 1/24 posibles)     # alemana + touring = BMW K 1600

... (Beto pregunta de nuevo y cede el turno) ...

>>> ES TU TURNO.
> adivinar BMW K 1600
============================================================
  FIN DE LA PARTIDA: Ganaste! adivino la moto secreta del rival
  La moto secreta del rival era: BMW K 1600
============================================================
```

Cada pregunta **filtra automáticamente** el tablero local del jugador que la hizo:
- respuesta **SI** → se descartan las motos que **no** tienen ese valor;
- respuesta **NO** → se descartan las motos que **sí** lo tienen.

---

## 🧪 Pruebas realizadas

El proyecto fue probado de extremo a extremo: partida completa con adivinanza
correcta, adivinanza fallida (derrota inmediata), tercer cliente en espera, varias
partidas concurrentes y manejo de desconexiones (si un jugador se cae, gana el rival).
