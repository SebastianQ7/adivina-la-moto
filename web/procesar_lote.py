# -*- coding: utf-8 -*-
"""
Procesa el lote de caricaturas de imagenes/cartoon_raw/:
  - Jugadores  -> imagenes/<slug>.png        (fondo transparente)
  - Entrenadores -> imagenes/avatares/<nombre>.png  (avatares del lobby)
Mapea los nombres del usuario a los slugs/nombres correctos.
"""
import os
from procesar_cartoon import procesar, _slug, IN_DIR, OUT_DIR

AVATAR_DIR = os.path.join(OUT_DIR, "avatares")

# slug del archivo del usuario -> slug correcto del jugador (motos.py)
JUGADORES = {
    "buffon": "gianluigi_buffon",
    "casillas": "iker_casillas",
    "cristiano_ronaldo": "cristiano_ronaldo",
    "debruyne": "kevin_de_bruyne",
    "fabio_canavaro": "fabio_cannavaro",
    "france_beckenbauer": "franz_beckenbauer",
    "iniesta": "andres_iniesta",
    "kaka": "kaka",
    "kylian_mbappe": "kylian_mbappe",
    "lewandoski": "robert_lewandowski",
    "luka_modric": "luka_modric",
    "manuel_neuer": "manuel_neuer",
    "maradona": "diego_maradona",
    "messi": "lionel_messi",
    "paolo_maldini": "paolo_maldini",
    "pele": "pele",
    "pirlo": "andrea_pirlo",
    "platini": "michel_platini",
    "roberto_carlos": "roberto_carlos",
    "ronaldinho": "ronaldinho",
    "ronaldo_nazario": "ronaldo_nazario",
    "sergio_ramos": "sergio_ramos",
    "xavi": "xavi_hernandez",
    "zinedin_zidane": "zinedine_zidane",
}

# slug del archivo del usuario -> nombre limpio del avatar (entrenador)
AVATARES = {
    "alex_ferguson": "alex_ferguson",
    "ancceloti": "carlo_ancelotti",
    "arsene_wenger": "arsene_wenger",
    "jose_mourinho": "jose_mourinho",
    "jurgen_klop": "jurgen_klopp",
    "luis_enrique": "luis_enrique",
    "pep_guardiola": "pep_guardiola",
    "vicente_del_boque": "vicente_del_bosque",
}


def main():
    os.makedirs(AVATAR_DIR, exist_ok=True)
    archivos = [f for f in os.listdir(IN_DIR)
                if os.path.splitext(f)[1].lower() in (".png", ".jpg", ".jpeg", ".webp")]
    jug, avs, sin = 0, 0, []
    for f in sorted(archivos):
        raw = _slug(os.path.splitext(f)[0])
        src = os.path.join(IN_DIR, f)
        if raw in JUGADORES:
            dest = os.path.join(OUT_DIR, JUGADORES[raw] + ".png")
            procesar(src, dest, alpha=True); jug += 1
            print(f"[JUGADOR] {f}  ->  {JUGADORES[raw]}.png")
        elif raw in AVATARES:
            dest = os.path.join(AVATAR_DIR, AVATARES[raw] + ".png")
            procesar(src, dest, alpha=True); avs += 1
            print(f"[AVATAR ] {f}  ->  avatares/{AVATARES[raw]}.png")
        else:
            sin.append(f)
            print(f"[? SIN MAPEAR] {f}  (slug: {raw})")
    print(f"\nJugadores: {jug}/24   Avatares: {avs}/8")
    if sin:
        print("SIN MAPEAR:", sin)


if __name__ == "__main__":
    main()
