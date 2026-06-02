# Adivina Quién — Motos

Proyecto para la materia **Programación Distribuida y Paralela** del
**Politécnico Colombiano Jaime Isaza Cadavid**.

## Descripción

Implementación del juego de mesa *Adivina Quién* en modo cliente-servidor.
En lugar de personajes con caras, el tablero usa **24 motos icónicas reales**
como fichas.

## Stack técnico

- **Lenguaje:** Python 3 (solo biblioteca estándar)
- **Concurrencia:** módulo `threading`
- **Red:** módulo `socket` (TCP para el juego, UDP para el autodescubrimiento)
- **Interfaz:** `tkinter` (gráfica)

Uso explícito de hilos y sockets es **requisito obligatorio** de la materia.

## Arquitectura

| Rol | Descripción |
|-----|-------------|
| `server.py` | Servidor multihilo: empareja jugadores (`WaitingRoom` + `Lock`), corre cada partida en su hilo (`GameSession`) y responde al autodescubrimiento UDP |
| `gui_client.py` | Interfaz gráfica del jugador (Tkinter): lobby (nombre + avatar), tablero de cartas, preguntas, suposiciones e historial |
| `logica.py` | Reglas puras del juego (sin red ni hilos), reutilizadas por servidor y cliente |
| `protocolo.py` | Capa de comunicación compartida: tipos de mensaje, envío/recepción JSON y autodescubrimiento UDP |
| `motos.py` | Datos de las 24 motos y sus atributos (sin lógica de red) |
| `generar_avatares.py` | Utilidad que genera los avatares PNG del lobby en `imagenes/avatares/` |

## Las 24 motos del tablero

**4 motos por origen** (6 orígenes × 4 = 24). Los valores se basan en datos reales
del modelo de referencia. Atributos (los que se usan para preguntar):

- **origen** — japonesa / americana / italiana / inglesa / alemana / austriaca
- **estilo** — deportiva / naked / cruiser / touring / trail / enduro
- **cilindrada** — baja (`<500cc`) / media (`500-999cc`) / alta (`≥1000cc`)
- **era** — clasica_pre1990 / noventas / moderna_post2000
- **cilindros** — 1 / 2 / 3 / 4_o_mas
- **refrigeracion** — aire / liquida
- **famosa_en_cine** — si / no

| # | Moto | origen | estilo | cilindrada | era | cilindros | refrig. | cine |
|---|------|--------|--------|------------|-----|-----------|---------|------|
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

## Flujo del juego

1. El servidor arranca, escucha TCP en `0.0.0.0:5000` y responde al
   autodescubrimiento UDP (puerto 5001).
2. Cada jugador abre el cliente: en el **lobby** escribe su **nombre** y elige un
   **avatar**, y pulsa **JUGAR**. El cliente **busca el servidor solo** por
   broadcast UDP (no se escribe IP ni puerto).
3. Al haber dos jugadores, el servidor empareja, asigna a cada uno una moto
   secreta distinta y envía el mismo tablero (24 motos en orden aleatorio).
4. Los jugadores se turnan enviando preguntas de sí/no sobre los atributos.
5. El servidor evalúa cada pregunta contra la moto rival y responde a ambos.
6. Quien adivina la moto del rival gana (fallar al adivinar hace perder).
7. Al terminar la ronda se ofrece **revancha**; si ambos aceptan, se juega otra
   ronda y se lleva el **marcador** de partidas ganadas.

## Conexión y autodescubrimiento

- El menú de inicio **no pide host ni puerto**: solo nombre y avatar.
- El cliente encuentra el servidor en la **red local** mediante un *broadcast UDP*
  (`protocolo.descubrir_servidor`); el servidor responde con su puerto y el cliente
  deduce la IP. Funciona entre PCs distintas en la misma red y también en una sola
  máquina (se prueba localhost además del broadcast).
- El avatar es **local** (perfil personal): el rival ve tu **nombre**, no tu avatar.

## Notas de desarrollo

- Los avatares PNG viven en `imagenes/avatares/`. Se regeneran con
  `python generar_avatares.py` y se pueden reemplazar por otros PNG.
- Mensajes JSON UTF-8 delimitados por `\n` sobre TCP (ver `protocolo.py`).
