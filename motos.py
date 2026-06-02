# -*- coding: utf-8 -*-
"""
Base de datos de los 24 jugadores del tablero "Adivina el Crack".

NOTA: por compatibilidad con el resto del proyecto (server.py, salas.py, bot.py,
logica.py, gui_client.py) este modulo se sigue llamando `motos.py` y el
diccionario se sigue llamando `motos`; solo cambio el CONTENIDO al tema futbol.
El motor del juego es generico: no sabe si son motos o jugadores.

Cada jugador tiene 7 atributos categoricos:

    posicion        -> portero / defensa / mediocampista / delantero
    confederacion   -> uefa / conmebol
    pie             -> derecho / izquierdo
    era             -> leyenda / dosmil / actual
    gano_mundial    -> si / no
    gano_balon_oro  -> si / no
    liga            -> laliga / seriea / bundesliga / premier / ligue1 / otra

La 'liga' es la mas representativa de su carrera; la 'era' es aproximada
(leyenda = carrera principalmente antes de ~1995; dosmil = pico ~1995-2010;
actual = pico 2010 en adelante).
"""

motos = {
    # ----------------------- PORTEROS -----------------------
    "Gianluigi Buffon": {
        "posicion": "portero", "confederacion": "uefa", "pie": "derecho",
        "era": "dosmil", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "seriea",
    },
    "Iker Casillas": {
        "posicion": "portero", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "laliga",
    },
    "Manuel Neuer": {
        "posicion": "portero", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "bundesliga",
    },

    # ----------------------- DEFENSAS -----------------------
    "Sergio Ramos": {
        "posicion": "defensa", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "laliga",
    },
    "Paolo Maldini": {
        "posicion": "defensa", "confederacion": "uefa", "pie": "izquierdo",
        "era": "leyenda", "gano_mundial": "no", "gano_balon_oro": "no", "liga": "seriea",
    },
    "Franz Beckenbauer": {
        "posicion": "defensa", "confederacion": "uefa", "pie": "derecho",
        "era": "leyenda", "gano_mundial": "si", "gano_balon_oro": "si", "liga": "bundesliga",
    },
    "Roberto Carlos": {
        "posicion": "defensa", "confederacion": "conmebol", "pie": "izquierdo",
        "era": "dosmil", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "laliga",
    },
    "Fabio Cannavaro": {
        "posicion": "defensa", "confederacion": "uefa", "pie": "derecho",
        "era": "dosmil", "gano_mundial": "si", "gano_balon_oro": "si", "liga": "seriea",
    },

    # ----------------------- MEDIOCAMPISTAS -----------------------
    "Zinedine Zidane": {
        "posicion": "mediocampista", "confederacion": "uefa", "pie": "derecho",
        "era": "dosmil", "gano_mundial": "si", "gano_balon_oro": "si", "liga": "laliga",
    },
    "Andrés Iniesta": {
        "posicion": "mediocampista", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "laliga",
    },
    "Xavi Hernández": {
        "posicion": "mediocampista", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "laliga",
    },
    "Luka Modrić": {
        "posicion": "mediocampista", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "no", "gano_balon_oro": "si", "liga": "laliga",
    },
    "Kevin De Bruyne": {
        "posicion": "mediocampista", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "no", "gano_balon_oro": "no", "liga": "premier",
    },
    "Michel Platini": {
        "posicion": "mediocampista", "confederacion": "uefa", "pie": "derecho",
        "era": "leyenda", "gano_mundial": "no", "gano_balon_oro": "si", "liga": "seriea",
    },
    "Kaká": {
        "posicion": "mediocampista", "confederacion": "conmebol", "pie": "derecho",
        "era": "dosmil", "gano_mundial": "si", "gano_balon_oro": "si", "liga": "seriea",
    },
    "Andrea Pirlo": {
        "posicion": "mediocampista", "confederacion": "uefa", "pie": "derecho",
        "era": "dosmil", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "seriea",
    },

    # ----------------------- DELANTEROS -----------------------
    "Lionel Messi": {
        "posicion": "delantero", "confederacion": "conmebol", "pie": "izquierdo",
        "era": "actual", "gano_mundial": "si", "gano_balon_oro": "si", "liga": "laliga",
    },
    "Cristiano Ronaldo": {
        "posicion": "delantero", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "no", "gano_balon_oro": "si", "liga": "laliga",
    },
    "Pelé": {
        "posicion": "delantero", "confederacion": "conmebol", "pie": "derecho",
        "era": "leyenda", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "otra",
    },
    "Diego Maradona": {
        "posicion": "delantero", "confederacion": "conmebol", "pie": "izquierdo",
        "era": "leyenda", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "seriea",
    },
    "Ronaldo Nazário": {
        "posicion": "delantero", "confederacion": "conmebol", "pie": "derecho",
        "era": "dosmil", "gano_mundial": "si", "gano_balon_oro": "si", "liga": "laliga",
    },
    "Ronaldinho": {
        "posicion": "delantero", "confederacion": "conmebol", "pie": "derecho",
        "era": "dosmil", "gano_mundial": "si", "gano_balon_oro": "si", "liga": "laliga",
    },
    "Kylian Mbappé": {
        "posicion": "delantero", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "si", "gano_balon_oro": "no", "liga": "ligue1",
    },
    "Robert Lewandowski": {
        "posicion": "delantero", "confederacion": "uefa", "pie": "derecho",
        "era": "actual", "gano_mundial": "no", "gano_balon_oro": "no", "liga": "bundesliga",
    },
}


# Lista ordenada de atributos consultables en el juego.
ATRIBUTOS = [
    "posicion",
    "confederacion",
    "pie",
    "era",
    "gano_mundial",
    "gano_balon_oro",
    "liga",
]


def tabla_balanceo():
    """Devuelve, por atributo, un conteo {valor: cantidad de jugadores}."""
    from collections import Counter
    resumen = {}
    for atributo in ATRIBUTOS:
        resumen[atributo] = Counter(m[atributo] for m in motos.values())
    return resumen


if __name__ == "__main__":
    print(f"Total de jugadores: {len(motos)}\n")
    print("=" * 48)
    print("  TABLA DE BALANCEO DEL TABLERO")
    print("=" * 48)
    for atributo, conteo in tabla_balanceo().items():
        print(f"\n{atributo}:")
        for valor, cantidad in sorted(conteo.items(), key=lambda x: -x[1]):
            barra = "#" * cantidad
            print(f"  {valor:<18} {cantidad:>2}  {barra}")
