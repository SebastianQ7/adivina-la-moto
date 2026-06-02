# -*- coding: utf-8 -*-
"""
Generador de avatares PNG para el lobby del juego.

Crea un set de avatares circulares de colores en imagenes/avatares/ usando solo
la biblioteca estandar (Tkinter sabe escribir PNG en Tk 8.6, sin Pillow).

Se ejecuta UNA vez:  python generar_avatares.py
Luego puedes reemplazar los PNG por los tuyos propios (mismo tamano recomendado).
"""

import os
import tkinter as tk

SIZE = 96  # lado del avatar en pixeles
BG = "#1f2330"  # fondo (igual al panel del lobby) para que el circulo se integre

# Paleta de avatares: nombre de archivo -> color principal.
PALETA = [
    ("avatar_rojo", "#e10600"),
    ("avatar_azul", "#1d6fb8"),
    ("avatar_verde", "#2a9d4a"),
    ("avatar_morado", "#7b5bd6"),
    ("avatar_dorado", "#c9a227"),
    ("avatar_naranja", "#e8743b"),
    ("avatar_cyan", "#19b3c9"),
    ("avatar_rosa", "#d6457b"),
]


def _rgb(hex_color):
    """'#rrggbb' -> (r, g, b)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(r, g, b):
    """(r, g, b) -> '#rrggbb' (con recorte a 0..255)."""
    return "#%02x%02x%02x" % (max(0, min(255, int(r))),
                              max(0, min(255, int(g))),
                              max(0, min(255, int(b))))


def _mezcla(c1, c2, t):
    """Interpola dos colores: t=0 -> c1, t=1 -> c2."""
    r1, g1, b1 = _rgb(c1)
    r2, g2, b2 = _rgb(c2)
    return _hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def generar():
    """Crea la carpeta y escribe los PNG de la paleta."""
    base = os.path.dirname(os.path.abspath(__file__))
    destino = os.path.join(base, "imagenes", "avatares")
    os.makedirs(destino, exist_ok=True)

    root = tk.Tk()
    root.withdraw()  # no mostramos ventana

    cx = cy = (SIZE - 1) / 2
    radio = SIZE / 2 - 3

    for nombre, color in PALETA:
        img = tk.PhotoImage(width=SIZE, height=SIZE)
        claro = _mezcla(color, "#ffffff", 0.45)   # brillo arriba
        oscuro = _mezcla(color, "#000000", 0.35)   # borde/sombra

        filas = []
        for y in range(SIZE):
            fila = []
            for x in range(SIZE):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if d <= radio - 3:
                    # Interior con degradado vertical (brillo arriba).
                    t = y / SIZE
                    fila.append(_mezcla(claro, oscuro, t))
                elif d <= radio:
                    fila.append(oscuro)            # anillo del borde
                else:
                    fila.append(BG)                # fuera del circulo
            filas.append("{" + " ".join(fila) + "}")

        img.put(" ".join(filas))
        ruta = os.path.join(destino, nombre + ".png")
        img.write(ruta, format="png")
        print(f"Generado: {ruta}")

    root.destroy()
    print(f"\nListo: {len(PALETA)} avatares en {destino}")


if __name__ == "__main__":
    generar()
