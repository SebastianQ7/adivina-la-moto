---
name: quien-es-quien-logic
description: >-
  Convenciones y patrones para la LOGICA en Python del juego "Quien es Quien"
  (version motos). Usar al crear, editar o depurar la logica del juego: el
  modelo de personajes/motos y sus atributos (motos.py), el sistema de
  preguntas y filtrado por atributo, la eliminacion de candidatos, y la gestion
  de turnos y estado de la partida (server.py / GameSession). Cubre la
  estructura del proyecto, las convenciones de codigo reales (naming,
  docstrings, separacion logica/presentacion, type hints en codigo nuevo) y
  como escribir y correr tests con unittest.
---

# Lógica del juego "Quién es Quién — Motos"

Juego cliente-servidor en Python (solo biblioteca estándar: `socket`,
`threading`, `json`). Esta skill describe **cómo está hecho el proyecto** para
mantener consistencia al tocar la lógica del juego. **No introducir librerías
externas** (es requisito de la materia).

## Estructura del proyecto

| Archivo | Responsabilidad | Regla |
|---------|-----------------|-------|
| `motos.py` | Datos puros: `dict` anidado `motos` (nombre → atributos), lista `ATRIBUTOS`, función `tabla_balanceo()`. | **Sin red, sin hilos, sin presentación.** Solo datos y helpers de datos. |
| `logica.py` | **Reglas puras** (sin sockets/hilos/UI): `atributo_valido()`, `personaje_existe()`, `evaluar_pregunta()`, `candidatos_a_descartar()`. Con type hints. | Aquí va la regla que decide algo. Reutilizada por servidor y clientes; **no duplicar reglas en otro archivo**. |
| `protocolo.py` | Capa de comunicación compartida: constantes de tipos de mensaje, `crear()`, `enviar()`, clase `Receptor`. | Todo lo que sea serialización/red compartida vive aquí. |
| `server.py` | **Orquestación del juego**: clases `Jugador`, `WaitingRoom` (cola + `threading.Lock`), `GameSession(threading.Thread)`. Un **hilo lector por jugador** vuelca eventos a `self.eventos` (`queue.Queue`); el bucle valida turno y aplica las reglas de `logica.py`. | Maneja turnos, estado y red. Las decisiones puras las delega a `logica.py`. No mete presentación. |
| `gui_client.py` | Cliente **gráfico** (Tkinter, hilo de red + `queue.Queue` + `root.after`). Es la única interfaz del juego. | Presentación. Para filtrar usa `logica.candidatos_a_descartar`. |
| `tests/` | Tests con `unittest`: `test_motos.py`, `test_logica.py`, `test_protocolo.py`. | Probar reglas puras y datos, sin red real. |

La **orquestación** (turnos, estado, red) está en `GameSession` (`server.py`); las
**reglas puras** en `logica.py`; los **datos** en `motos.py`. Nunca mezclar capas.

### Modelo de personajes/atributos (`motos.py`)

- Cada moto es una entrada de `motos`: `nombre (str) -> dict de atributos`.
- Atributos actuales (todos `str` categóricos): `origen`, `estilo`, `cilindrada`,
  `era`, `cilindros`, `refrigeracion`, `famosa_en_cine`.
- **`ATRIBUTOS`** es la **única fuente de verdad** de qué atributos son
  preguntables. Toda validación se hace contra `motos.ATRIBUTOS`.
- Al **agregar/cambiar un atributo**: actualizarlo en las **24** motos y en
  `ATRIBUTOS`, y revisar el balance con `tabla_balanceo()`.

### Estado de la partida (`GameSession`)

Estado que mantiene cada partida (un hilo por partida):
`self.tablero` (24 nombres barajados, igual para ambos), `self.turno` (índice
0/1), `self.descartadas` (`{jugador: set()}`), `self.ganador`, `self.activa`, y
`jugador.moto_secreta` por jugador.

## Convenciones de código (las que ya existen)

- **Idioma**: vocabulario del dominio en **español** (`moto`, `jugador`,
  `tablero`, `turno`, `pregunta`, `adivinar`, `descartar`, `secreta`,
  `descartadas`). Conviven nombres de método en inglés heredados
  (`run`, `_setup_game`, `_send`, `_recv`, `_broadcast`, `_process_question`,
  `_process_guess`, `_change_turn`, `_end_game`) con otros en español
  (`conectar`, `_escuchar`, `_manejar`, `_enviar`, `_cerrar`). **Regla:**
  imitar el estilo del archivo/clase que estás tocando; no renombrar lo
  existente solo por uniformar.
- **Naming**: `snake_case` para funciones, métodos y variables; `CamelCase`
  para clases (`GameSession`, `WaitingRoom`, `GuiClient`, `Jugador`,
  `Receptor`); `MAYUSCULAS` para constantes (`HOST`, `PORT`, `ATRIBUTOS`,
  `JOIN`, `PREGUNTA`, ...).
- **Métodos privados** con prefijo `_` (`_setup_game`, `_filtrar_tablero`).
- **Docstrings obligatorios**: módulo + cada clase + cada método (en español,
  triple comilla). Es el estándar del proyecto; mantenerlo.
- **Comentarios "POR QUE"**: donde se usa concurrencia o sockets, explicar
  *por qué* esa técnica (ej. "POR QUE UN HILO POR PARTIDA", "POR QUE UN LOCK").
  El profesor lo valora; conservar y replicar este patrón.
- **Type hints (híbrido)**: el código actual **no** tiene type hints. **En
  código NUEVO sí añadirlos** (parámetros y retorno), p. ej.
  `def evaluar(atributos: dict, atributo: str, valor: str) -> str:`. **No
  retrofitear** masivamente lo existente.
- **dataclasses**: **opcionales**. Solo si aportan claridad real a una
  estructura nueva. `Jugador` hoy es una clase normal y así se queda; los
  datos de motos siguen siendo `dict`.
- **Codificación**: archivos con `# -*- coding: utf-8 -*-`. Los clientes hacen
  `sys.stdout.reconfigure(encoding="utf-8")` para Windows.

## Mejores prácticas y patrones a seguir

1. **Fuente de verdad única para datos.** Validar atributos contra
   `motos.ATRIBUTOS` y nombres contra `motos.motos`. No hardcodear listas de
   atributos/valores en la lógica ni en la UI; derivarlas de `motos.py`
   (ej. valores posibles: `sorted({m[at] for m in motos.motos.values()})`).
2. **Preguntas por igualdad.** El sistema de preguntas compara el atributo de
   la moto secreta del **oponente** con un valor y responde `"SI"`/`"NO"`
   (`_process_question`). Los atributos son categóricos (strings); no asumir
   comparaciones numéricas.
3. **Filtrado / eliminación de candidatos.** La regla canónica:
   - respuesta `"SI"` → descartar las motos cuyo atributo **≠** valor;
   - respuesta `"NO"` → descartar las motos cuyo atributo **=** valor.
   Ver `_filtrar_tablero` (GUI) y `_aplicar_respuesta` (consola). Si cambias
   esta regla, cámbiala en ambos clientes.
4. **El servidor manda; no confiar en el cliente.** `GameSession` valida cada
   acción: jugada **fuera de turno** → `ERROR "No es tu turno."`; atributo
   inexistente → `ERROR`; adivinar un personaje que no existe → `ERROR` (sin
   terminar la partida). Una jugada inválida **no** consume turno.
5. **Turnos.** `self.turno` es índice 0/1; `_change_turn()` alterna y notifica
   a ambos con `TURNO`. Preguntar cede el turno; adivinar termina la partida.
6. **Fin de ronda y revancha.** Adivinar bien → gana; adivinar mal → **pierde
   de inmediato** (regla clásica). El fin **normal** pasa por `_end_game()` →
   `_enviar_fin(..., ofrecer_revancha=True)`: suma al `self.marcador` y manda
   `FIN` con `marcador` y `revancha=True`. Luego `_fase_revancha()` espera que
   AMBOS envíen `REVANCHA` para llamar de nuevo a `_setup_game()` (otra ronda,
   mismo par). Desconexión o `SALIR` → `_fin_por_corte()` (`revancha=False`,
   `self.terminar=True`) y se cierra la sesión.
7. **Mensajería siempre vía `protocolo.py`.** Usar `protocolo.crear()`,
   `protocolo.enviar()` y `protocolo.Receptor`; nunca construir JSON a mano ni
   tocar el socket crudo desde la lógica. **Mensaje nuevo = constante nueva en
   `protocolo.py`** (y documentarla en README + `protocolo.py`).
8. **Concurrencia.** Una `GameSession` por partida (su estado es privado del
   hilo → no necesita lock). Dentro de la partida hay **un hilo lector por
   jugador** (`_lector`) que vuelca eventos `(jugador, mensaje)` a
   `self.eventos` (`queue.Queue`); el bucle de `run()` los procesa de a uno (así
   se escucha a ambos jugadores a la vez y se detecta una desconexión en
   cualquier momento). El estado **compartido** entre hilos (`WaitingRoom._cola`)
   se protege con `threading.Lock`. En la GUI, la red va en un hilo que deja
   mensajes en `queue.Queue` y la UI los consume con `root.after()` (Tkinter NO
   es thread-safe).
9. **Manejo de excepciones de red.** Envolver operaciones de socket en
   `try/except (ConnectionError, OSError)`. En recepción, `recibir()`/`_recv()`
   devolviendo `None` significa desconexión → gana el rival.

## Tests (unittest — biblioteca estándar)

El proyecto **ya tiene** tests en `tests/` con **`unittest`** (stdlib, sin
dependencias): `test_motos.py` (integridad de datos), `test_logica.py` (reglas
puras) y `test_protocolo.py` (serialización y framing con un socket falso).
Cada archivo agrega `sys.path.insert` de la raíz para ser ejecutable solo.

Convención al ampliarlos:

- Archivos `test_<modulo>.py`, clases `Test...`, métodos `test_...`.
- Probar **lógica pura sin red**. Si una regla nueva vive dentro de un método
  acoplado a sockets, **extraerla a `logica.py`** como función pura y testear
  esa (es lo que ya se hizo con `evaluar_pregunta` y `candidatos_a_descartar`).
- Para probar el protocolo sin red, usar un **socket falso** (clase con
  `sendall`/`recv` sobre un buffer en memoria), como en `test_protocolo.py`.

Ejemplos típicos a cubrir:

```python
# tests/test_motos.py
import unittest
import motos

class TestMotos(unittest.TestCase):
    def test_hay_24_motos(self):
        self.assertEqual(len(motos.motos), 24)

    def test_todas_tienen_los_atributos(self):
        for nombre, attrs in motos.motos.items():
            self.assertEqual(set(attrs), set(motos.ATRIBUTOS), nombre)

    def test_balanceo_suma_24(self):
        for conteo in motos.tabla_balanceo().values():
            self.assertEqual(sum(conteo.values()), 24)
```

```python
# tests/test_protocolo.py  -> prueba el framing con un socket FALSO (sin red real)
import unittest
import protocolo

class SocketFalso:
    """Socket de mentira: guarda lo enviado y lo devuelve por trozos en recv."""
    def __init__(self): self.buffer = b""
    def sendall(self, data): self.buffer += data
    def recv(self, n):
        trozo, self.buffer = self.buffer[:n], self.buffer[n:]
        return trozo

class TestProtocolo(unittest.TestCase):
    def test_ida_y_vuelta(self):
        s = SocketFalso()
        protocolo.enviar(s, protocolo.crear(protocolo.PREGUNTA,
                                            atributo="origen", valor="japonesa"))
        msg = protocolo.Receptor(s).recibir()
        self.assertEqual(msg["tipo"], protocolo.PREGUNTA)
        self.assertEqual(msg["valor"], "japonesa")
```

Para reglas que hoy viven dentro de métodos acoplados a sockets (p. ej.
`_process_question`), el patrón recomendado es factorizar la decisión en una
función pura, por ejemplo `evaluar(attrs: dict, atributo: str, valor: str) -> str`,
y testear esa función directamente.

**Cómo correr los tests** (desde la carpeta del proyecto):

```bash
python -m unittest discover -s tests -v      # descubre y corre todo en tests/
python -m unittest tests.test_motos -v       # un módulo concreto
python -m unittest -v                        # si los test_*.py están en la raíz
```

Las pruebas de **integración** end-to-end (levantar `server.py` y conectar
clientes por socket para jugar una partida completa) se hacen con scripts
aparte; no mezclarlas con los tests unitarios de `unittest`.
