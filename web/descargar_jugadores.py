# -*- coding: utf-8 -*-
"""Descarga las fotos de los 24 jugadores desde Wikipedia (licencia libre) y las
guarda en imagenes/<slug>.<ext>. Solo biblioteca estandar."""
import os
import re
import sys
import json
import time
import unicodedata
import urllib.parse
import urllib.request

# La consola de Windows (cp1252) no imprime acentos; evitamos que el script
# se caiga por un print.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(os.path.dirname(WEB_DIR), "imagenes")

UA = "AdivinaElCrack/1.0 (proyecto academico; contacto: sebasquice99@gmail.com)"

# (nombre tal cual ira en motos.py, titulo del articulo en Wikipedia EN)
JUGADORES = [
    ("Gianluigi Buffon", "Gianluigi Buffon"),
    ("Iker Casillas", "Iker Casillas"),
    ("Manuel Neuer", "Manuel Neuer"),
    ("Sergio Ramos", "Sergio Ramos"),
    ("Paolo Maldini", "Paolo Maldini"),
    ("Franz Beckenbauer", "Franz Beckenbauer"),
    ("Roberto Carlos", "Roberto Carlos (footballer)"),
    ("Fabio Cannavaro", "Fabio Cannavaro"),
    ("Zinedine Zidane", "Zinedine Zidane"),
    ("Andrés Iniesta", "Andrés Iniesta"),
    ("Xavi Hernández", "Xavi"),
    ("Luka Modrić", "Luka Modrić"),
    ("Kevin De Bruyne", "Kevin De Bruyne"),
    ("Michel Platini", "Michel Platini"),
    ("Kaká", "Kaká"),
    ("Andrea Pirlo", "Andrea Pirlo"),
    ("Lionel Messi", "Lionel Messi"),
    ("Cristiano Ronaldo", "Cristiano Ronaldo"),
    ("Pelé", "Pelé"),
    ("Diego Maradona", "Diego Maradona"),
    ("Ronaldo Nazário", "Ronaldo (Brazilian footballer)"),
    ("Ronaldinho", "Ronaldinho"),
    ("Kylian Mbappé", "Kylian Mbappé"),
    ("Robert Lewandowski", "Robert Lewandowski"),
]


def slug(nombre):
    s = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def pedir_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def url_imagen(titulo):
    """Devuelve la URL de la foto principal del articulo (thumbnail ~600px)."""
    # Via 1: API pageimages (permite pedir tamano).
    api = ("https://en.wikipedia.org/w/api.php?action=query&format=json"
           "&prop=pageimages&piprop=thumbnail&pithumbsize=600&redirects=1"
           "&titles=" + urllib.parse.quote(titulo))
    try:
        data = pedir_json(api)
        for _, pag in data.get("query", {}).get("pages", {}).items():
            thumb = pag.get("thumbnail", {}).get("source")
            if thumb:
                return thumb
    except Exception:
        pass
    # Via 2 (respaldo): REST summary.
    try:
        rest = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                + urllib.parse.quote(titulo))
        data = pedir_json(rest)
        for clave in ("thumbnail", "originalimage"):
            src = data.get(clave, {}).get("source")
            if src:
                return src
    except Exception:
        pass
    return None


def descargar(url, destino):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        datos = r.read()
    with open(destino, "wb") as f:
        f.write(datos)
    return len(datos)


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    ok, fallos = 0, []
    for nombre, titulo in JUGADORES:
        s = slug(nombre)
        try:
            url = url_imagen(titulo)
            if not url:
                fallos.append((nombre, "sin imagen"))
                print(f"  [X] {nombre}: sin imagen")
                continue
            ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                ext = ".jpg"
            destino = os.path.join(IMG_DIR, s + ext)
            n = descargar(url, destino)
            ok += 1
            print(f"  [OK] {nombre:22} -> {s}{ext}  ({n//1024} KB)")
        except Exception as e:
            fallos.append((nombre, str(e)))
            print(f"  [X] {nombre}: {e}")
        time.sleep(0.4)  # cortesia con la API
    print(f"\nDescargadas {ok}/24.")
    if fallos:
        print("Fallaron:", fallos)


if __name__ == "__main__":
    main()
