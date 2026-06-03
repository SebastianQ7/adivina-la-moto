# -*- coding: utf-8 -*-
"""
Quita el fondo gris de las caricaturas y lo deja BLANCO (o transparente),
normalizando el tamano. Lee de imagenes/cartoon_raw/ y guarda en imagenes/.

Uso:
  python procesar_cartoon.py            -> fondo blanco
  python procesar_cartoon.py --alpha    -> fondo transparente (PNG)

El nombre del archivo de salida es el mismo del archivo de entrada (sin ext),
asi que nombra cada caricatura con el "slug" del jugador (ver lista abajo).
"""
import os
import re
import sys
import unicodedata
from PIL import Image, ImageDraw, ImageChops


def _slug(nombre):
    """'Xavi Hernández' o 'Kaká' -> 'xavi_hernandez' / 'kaka' (igual que el servidor)."""
    s = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

WEB = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(WEB)
IN_DIR = os.path.join(ROOT, "imagenes", "cartoon_raw")
OUT_DIR = os.path.join(ROOT, "imagenes")

MAX_LADO = 512          # se reescala si es mas grande
THRESH = 55             # tolerancia del color de fondo al rellenar
BLANCO = (255, 255, 255)

# Semillas: las 4 esquinas + el centro de cada borde (el fondo es continuo).
def _semillas(w, h):
    return [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
            (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]


def procesar(path_in, path_out, alpha=False):
    im = Image.open(path_in).convert("RGB")
    w, h = im.size

    if alpha:
        # Rellena el fondo (conectado a los bordes) con un color centinela y luego
        # vuelve transparente SOLO esos pixeles. Asi las partes blancas del
        # jugador (camiseta, dientes) NO se agujerean.
        SENT = (255, 0, 255)
        flood = im.copy()
        for s in _semillas(w, h):
            ImageDraw.floodfill(flood, s, SENT, thresh=THRESH)
        diff = ImageChops.difference(flood, Image.new("RGB", im.size, SENT)).convert("L")
        mascara = diff.point(lambda v: 0 if v == 0 else 255)   # 0 = fondo -> transparente
        im = im.convert("RGBA")
        im.putalpha(mascara)
        # Normaliza el TAMANO: recorta al contenido (alpha) y lo centra en un
        # cuadrado con un margen fijo, asi todas las figuras ocupan lo mismo.
        bbox = im.split()[3].getbbox()
        if bbox:
            im = im.crop(bbox)
        lado = max(im.size)
        margen = int(lado * 0.06)
        cuadro = Image.new("RGBA", (lado + 2 * margen, lado + 2 * margen), (0, 0, 0, 0))
        off = ((cuadro.width - im.width) // 2, (cuadro.height - im.height) // 2)
        cuadro.paste(im, off, im)
        im = cuadro
    else:
        # Pinta de blanco el fondo conectado a los bordes.
        for s in _semillas(w, h):
            ImageDraw.floodfill(im, s, BLANCO, thresh=THRESH)

    if max(im.size) > MAX_LADO:
        im.thumbnail((MAX_LADO, MAX_LADO), Image.LANCZOS)
    im.save(path_out)


def main():
    alpha = "--alpha" in sys.argv
    os.makedirs(IN_DIR, exist_ok=True)
    archivos = [f for f in os.listdir(IN_DIR)
                if os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".webp")]
    if not archivos:
        print("Pon las caricaturas en:", IN_DIR)
        print("(carpeta creada; nombra cada una con el slug del jugador)")
        return
    for f in sorted(archivos):
        base = _slug(os.path.splitext(f)[0])
        out = os.path.join(OUT_DIR, base + ".png")
        try:
            procesar(os.path.join(IN_DIR, f), out, alpha=alpha)
            print(f"[OK] {f} -> {base}.png  ({'transparente' if alpha else 'blanco'})")
        except Exception as e:
            print(f"[X] {f}: {e}")


if __name__ == "__main__":
    main()
