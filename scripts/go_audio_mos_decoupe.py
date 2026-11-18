#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Découpe l'enregistrement mooré d'un seul tenant en 22 fichiers du guide vocal de Salubri Go.

    python scripts/go_audio_mos_decoupe.py scripts/audio_src/mos_enregistrement.opus apps/go/public/audio/mos

Les phrases sont repérées par leurs silences (ffmpeg silencedetect) puis rattachées aux fichiers dans l'ordre de
lecture de l'enregistrement (SEQUENCE : numéros de segments). Chaque fichier : fondu de 10/30 ms, volume normalisé,
MP3 mono 44,1 kHz 64 kbit/s. `--liste` affiche les segments et la correspondance sans rien écrire.
Outils : ffmpeg (LGPL/GPL) seulement pour fabriquer les fichiers, pas une dépendance de Salubri.
"""

import re
import subprocess
import sys
from pathlib import Path

# fichier → segments de parole (numéros dans l'ordre de l'enregistrement) ; plusieurs = une phrase en deux temps
SEQUENCE: dict[str, tuple[int, ...]] = {
    "lang_mos": (0,),
    "photo_ask": (1, 2),
    "photo_continue": (3, 4),
    "qty_ask": (5,),
    "qty_bag": (6,),
    "qty_wheelbarrow": (7,),
    "qty_cart": (8,),
    "qty_truck": (9,),
    "qty_more": (10,),
    "type_ask": (11,),
    "type_household": (12,),
    "type_rubble": (13, 14),
    "type_medical": (15,),
    "type_mixed": (16,),
    "loc_ask": (17, 18),
    "loc_wait": (19, 20),
    "loc_denied": (21,),
    "type_plastic": (22,),
    "type_organic": (23,),
    "thanks": (24, 25),
    "thanks_offline": (26, 27, 28),
    "again": (29,),
}


def segments(src: Path) -> list[tuple[float, float]]:
    err = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-i",
            str(src),
            "-af",
            "silencedetect=noise=-36dB:d=0.12",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stderr
    h, m, sec = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    dur = 3600 * int(h) + 60 * int(m) + float(sec)
    ev = [(m[1], float(m[2])) for m in re.finditer(r"silence_(start|end): ([\d.]+)", err)]
    out, cur = [], 0.0
    for k, t in ev:
        if k == "start":
            if t - cur > 0.05:
                out.append((cur, t))
        else:
            cur = t
    if dur - cur > 0.3:
        out.append((cur, dur))
    return [s for s in out if s[1] - s[0] > 0.25]  # écarte les claquements


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    seg = segments(Path(args[0]))
    inv = {i: f for f, ids in SEQUENCE.items() for i in ids}
    if "--liste" in sys.argv or len(args) < 2:
        for i, (a, b) in enumerate(seg):
            print(f"{i:2d}  {a:6.2f}–{b:6.2f}  {b - a:4.1f} s  {inv.get(i, '?')}")
        return 0
    if max(i for ids in SEQUENCE.values() for i in ids) >= len(seg):
        sys.exit(f"{len(seg)} segments trouvés, la table en attend davantage : vérifier l'enregistrement")
    out = Path(args[1])
    out.mkdir(parents=True, exist_ok=True)
    for nom, ids in SEQUENCE.items():
        a, b = seg[ids[0]][0], seg[ids[-1]][1]
        a0 = max(0.0, a - 0.12)
        b0 = b + 0.2
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-loglevel",
                "error",
                "-ss",
                f"{a0:.3f}",
                "-to",
                f"{b0:.3f}",
                "-i",
                args[0],
                "-af",
                f"afade=t=in:d=0.01,afade=t=out:st={b0 - a0 - 0.03:.3f}:d=0.03,loudnorm=I=-16:TP=-1.5:LRA=7",
                "-ac",
                "1",
                "-ar",
                "44100",
                "-b:a",
                "64k",
                str(out / f"{nom}.mp3"),
            ],
            check=True,
        )
        print(f"{nom}.mp3  {b0 - a0:4.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
