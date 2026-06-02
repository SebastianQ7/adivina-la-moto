# -*- coding: utf-8 -*-
"""
Base de datos de las 24 motos del tablero "Adivina Quién - Motos".

Cada moto es una entrada del diccionario `motos`, con 7 atributos basados
en datos reales del modelo:

    origen        -> japonesa / americana / italiana / inglesa / alemana / austriaca
    estilo        -> deportiva / naked / cruiser / touring / trail / enduro
    cilindrada    -> baja (<500cc) / media (500-999cc) / alta (>=1000cc)
    era           -> clasica_pre1990 / noventas / moderna_post2000
    cilindros     -> 1 / 2 / 3 / 4_o_mas
    refrigeracion -> aire / liquida
    famosa_en_cine-> si / no

La 'era' se basa en el año de debut del modelo. La 'cilindrada' usa el
cilindraje del modelo de referencia (sub-litro = media, litro o mas = alta).
"""

motos = {
    # ----------------------- JAPONESAS -----------------------
    "Honda CBR 600RR": {
        "origen": "japonesa",
        "estilo": "deportiva",
        "cilindrada": "media",          # 599 cc
        "era": "moderna_post2000",      # 2003
        "cilindros": "4_o_mas",         # inline-4
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "Kawasaki Ninja H2": {
        "origen": "japonesa",
        "estilo": "deportiva",
        "cilindrada": "media",          # 998 cc (sobrealimentada)
        "era": "moderna_post2000",      # 2015
        "cilindros": "4_o_mas",
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "Yamaha YZF-R1": {
        "origen": "japonesa",
        "estilo": "deportiva",
        "cilindrada": "media",          # 998 cc
        "era": "noventas",              # 1998
        "cilindros": "4_o_mas",
        "refrigeracion": "liquida",
        "famosa_en_cine": "si",         # Biker Boyz, Torque
    },
    "Suzuki Hayabusa": {
        "origen": "japonesa",
        "estilo": "deportiva",
        "cilindrada": "alta",           # 1340 cc
        "era": "noventas",              # 1999
        "cilindros": "4_o_mas",
        "refrigeracion": "liquida",
        "famosa_en_cine": "si",         # Dhoom, Torque
    },

    # ----------------------- AMERICANAS -----------------------
    "Harley-Davidson Fat Boy": {
        "origen": "americana",
        "estilo": "cruiser",
        "cilindrada": "alta",           # ~1745 cc
        "era": "noventas",              # 1990
        "cilindros": "2",               # V-twin
        "refrigeracion": "aire",
        "famosa_en_cine": "si",         # Terminator 2
    },
    "Harley-Davidson Sportster": {
        "origen": "americana",
        "estilo": "cruiser",
        "cilindrada": "media",          # 883 cc
        "era": "clasica_pre1990",       # 1957
        "cilindros": "2",
        "refrigeracion": "aire",
        "famosa_en_cine": "no",
    },
    "Indian Chief": {
        "origen": "americana",
        "estilo": "cruiser",
        "cilindrada": "alta",           # ~1811 cc
        "era": "clasica_pre1990",       # 1922
        "cilindros": "2",
        "refrigeracion": "aire",
        "famosa_en_cine": "no",
    },
    "Harley-Davidson Road King": {
        "origen": "americana",
        "estilo": "touring",
        "cilindrada": "alta",           # ~1745 cc
        "era": "noventas",              # 1994
        "cilindros": "2",
        "refrigeracion": "aire",
        "famosa_en_cine": "no",
    },

    # ----------------------- ITALIANAS -----------------------
    "Ducati Panigale V4": {
        "origen": "italiana",
        "estilo": "deportiva",
        "cilindrada": "alta",           # 1103 cc
        "era": "moderna_post2000",      # 2018
        "cilindros": "4_o_mas",         # V4
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "Ducati Monster": {
        "origen": "italiana",
        "estilo": "naked",
        "cilindrada": "media",          # 937 cc
        "era": "moderna_post2000",      # linaje 1993, modelo actual
        "cilindros": "2",               # L-twin
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "Aprilia RSV4": {
        "origen": "italiana",
        "estilo": "deportiva",
        "cilindrada": "alta",           # 1099 cc
        "era": "moderna_post2000",      # 2009
        "cilindros": "4_o_mas",         # V4
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "Ducati Multistrada": {
        "origen": "italiana",
        "estilo": "trail",
        "cilindrada": "alta",           # 1158 cc
        "era": "moderna_post2000",      # 2003
        "cilindros": "2",               # L-twin (modelo de referencia)
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },

    # ----------------------- INGLESAS -----------------------
    "Triumph Bonneville": {
        "origen": "inglesa",
        "estilo": "naked",
        "cilindrada": "media",          # 650 cc (clasica)
        "era": "clasica_pre1990",       # 1959
        "cilindros": "2",               # parallel-twin
        "refrigeracion": "aire",
        "famosa_en_cine": "si",         # The Great Escape (Steve McQueen)
    },
    "Triumph Speed Triple": {
        "origen": "inglesa",
        "estilo": "naked",
        "cilindrada": "alta",           # 1160 cc
        "era": "noventas",              # 1994
        "cilindros": "3",               # triple
        "refrigeracion": "liquida",
        "famosa_en_cine": "si",         # Mission: Impossible 2
    },
    "Triumph Rocket 3": {
        "origen": "inglesa",
        "estilo": "cruiser",
        "cilindrada": "alta",           # 2458 cc (la mas grande de serie)
        "era": "moderna_post2000",      # 2004
        "cilindros": "3",               # triple
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "Triumph Tiger": {
        "origen": "inglesa",
        "estilo": "trail",
        "cilindrada": "media",          # 888 cc (Tiger 900)
        "era": "moderna_post2000",      # 2010+
        "cilindros": "3",               # triple
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },

    # ----------------------- ALEMANAS -----------------------
    "BMW R 1250 GS": {
        "origen": "alemana",
        "estilo": "trail",
        "cilindrada": "alta",           # 1254 cc
        "era": "moderna_post2000",      # 2018 (linaje GS 1980)
        "cilindros": "2",               # boxer
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "BMW S1000RR": {
        "origen": "alemana",
        "estilo": "deportiva",
        "cilindrada": "media",          # 999 cc
        "era": "moderna_post2000",      # 2009
        "cilindros": "4_o_mas",         # inline-4
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "BMW R nineT": {
        "origen": "alemana",
        "estilo": "naked",
        "cilindrada": "alta",           # 1170 cc
        "era": "moderna_post2000",      # 2014
        "cilindros": "2",               # boxer
        "refrigeracion": "aire",        # boxer refrigerado por aire/aceite
        "famosa_en_cine": "no",
    },
    "BMW K 1600": {
        "origen": "alemana",
        "estilo": "touring",
        "cilindrada": "alta",           # 1649 cc
        "era": "moderna_post2000",      # 2011
        "cilindros": "4_o_mas",         # 6 cilindros en linea
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },

    # ----------------------- AUSTRIACAS -----------------------
    "KTM 1290 Super Duke": {
        "origen": "austriaca",
        "estilo": "naked",
        "cilindrada": "alta",           # 1301 cc
        "era": "moderna_post2000",      # 2014
        "cilindros": "2",               # V-twin
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "KTM 1290 Super Adventure": {
        "origen": "austriaca",
        "estilo": "trail",
        "cilindrada": "alta",           # 1301 cc
        "era": "moderna_post2000",      # 2015
        "cilindros": "2",               # V-twin
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "KTM RC 390": {
        "origen": "austriaca",
        "estilo": "deportiva",
        "cilindrada": "baja",           # 373 cc
        "era": "moderna_post2000",      # 2014
        "cilindros": "1",               # monocilindrica
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
    "KTM 690 Enduro": {
        "origen": "austriaca",
        "estilo": "enduro",
        "cilindrada": "media",          # 690 cc
        "era": "moderna_post2000",      # 2008
        "cilindros": "1",               # monocilindrica
        "refrigeracion": "liquida",
        "famosa_en_cine": "no",
    },
}


# Lista ordenada de atributos consultables en el juego.
ATRIBUTOS = [
    "origen",
    "estilo",
    "cilindrada",
    "era",
    "cilindros",
    "refrigeracion",
    "famosa_en_cine",
]


def tabla_balanceo():
    """Devuelve, por atributo, un conteo {valor: cantidad de motos}."""
    from collections import Counter
    resumen = {}
    for atributo in ATRIBUTOS:
        resumen[atributo] = Counter(m[atributo] for m in motos.values())
    return resumen


if __name__ == "__main__":
    print(f"Total de motos: {len(motos)}\n")
    print("=" * 48)
    print("  TABLA DE BALANCEO DEL TABLERO")
    print("=" * 48)
    for atributo, conteo in tabla_balanceo().items():
        print(f"\n{atributo}:")
        for valor, cantidad in sorted(conteo.items(), key=lambda x: -x[1]):
            barra = "#" * cantidad
            print(f"  {valor:<18} {cantidad:>2}  {barra}")
