#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Monte la vidéo de démonstration de 3 minutes : vos enregistrements d'écran + sous-titres de narration (sans voix).

    python scripts/video_sous_titres.py --plan                       affiche le plan de tournage (tableau Markdown)
    python scripts/video_sous_titres.py CLIPS_DIR -o livrable/6_video/demo_salubri.mp4

CLIPS_DIR contient un enregistrement par plan, dont le nom commence par la lettre du plan : A_….mp4, B_….mp4 …
G (fin) et T (titre) sont fabriqués par le script. Chaque enregistrement est ramené à la durée prévue (accéléré s'il
est trop long, dernière image tenue s'il est trop court), mis en 1920×1080 à 30 images/s, sans son, puis sous-titré :
une étiquette d'étape en haut à gauche et la narration en bas. Outil : ffmpeg avec le filtre « ass » (libass).
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

W, H, FPS = 1920, 1080, 30
NAVY, ORANGE = "0E1A40", "F28C28"

# id, durée prévue (s), étiquette d'étape, [(début, fin, texte)] ; temps relatifs au début du plan
PLAN = [
    {
        "id": "T",
        "kind": "carte",
        "dur": 8,
        "tag": "",
        "ou": "généré (carte de titre)",
        "faire": "rien à enregistrer",
        "caps": [
            (
                0.3,
                7.7,
                "{\\fs150}Salubri{\\fs78}\\NSignaler · Vérifier · Planifier · Simuler\\N{\\fs40}L'assainissement de Ouagadougou en logiciel libre — Hackathon des universités 2026, défi 01",
            )
        ],
    },
    {
        "id": "A",
        "kind": "clip",
        "dur": 48,
        "tag": "1 · Signalement hors ligne",
        "ou": "Téléphone Android (scrcpy), mode avion",
        "faire": "Activer le mode avion. Ouvrir Salubri Go. Toucher « Français » (le bouton brille). Toucher « Photo », prendre la photo de test, attendre les cadres « Visage » / « Plaque », toucher OK. Quantité : « Une charrette ». Type : « Plastiques ». Position : toucher « Position ». Écran merci. Toucher « Voir mes signalements » (statut « En attente »).",
        "caps": [
            (0, 5, "Sans réseau : mode avion. Le signalement sera gardé sur le téléphone."),
            (5, 10, "Salubri Go parle : on choisit sa langue, français ou mooré, en touchant le bouton qui brille."),
            (10, 19, "Étape 1 : la photo. Les visages et les plaques sont floutés sur le téléphone, avant tout envoi."),
            (19, 25, "Étape 2 : la quantité. Un sac, une brouette, une charrette, un camion."),
            (25, 31, "Étape 3 : le type de déchets."),
            (31, 38, "Étape 4 : la position GPS, sans rien saisir."),
            (38, 44, "Merci. Enregistré : il partira dès que le réseau revient."),
            (44, 48, "Il attend dans « Mes envois », statut « En attente »."),
        ],
    },
    {
        "id": "B",
        "kind": "clip",
        "dur": 10,
        "tag": "2 · Retour du réseau",
        "ou": "Téléphone, même écran « Mes envois »",
        "faire": "Désactiver le mode avion (menu du téléphone) et laisser l'écran « Mes envois » ouvert jusqu'au statut « Envoyé » avec son score.",
        "caps": [
            (0, 5, "Le réseau revient : le signalement part tout seul, une seule fois."),
            (5, 10, "Statut « Envoyé », avec son score de confiance."),
        ],
    },
    {
        "id": "C",
        "kind": "clip",
        "dur": 25,
        "tag": "3 · Vérification par la mairie",
        "ou": "PC, Salubri Map (http://localhost/), connecté en demo",
        "faire": "Onglet Signalements, filtre « probable » ou « à vérifier ». Ouvrir le nouveau signalement (photo floutée visible, règles appliquées). Cliquer « Vérifier ». Passer sur la carte : le point apparaît.",
        "caps": [
            (0, 6, "Côté mairie : le signalement arrive dans Salubri Map, photo déjà floutée."),
            (6, 14, "12 règles anti-pièges calculent un score : doublons, faux GPS, photo réutilisée…"),
            (14, 20, "Un modérateur vérifie : seul un signalement vérifié entre dans le plan."),
            (20, 25, "Il apparaît sur la carte."),
        ],
    },
    {
        "id": "D",
        "kind": "clip",
        "dur": 22,
        "tag": "4 · Plan de collecte",
        "ou": "PC, Salubri Sim, scénario « Vidéo — Arrondissement 9 »",
        "faire": "Ouvrir « Plan de collecte ». Montrer le point de regroupement le plus proche du dépotoir, puis la tournée qui le dessert (camion, heure de passage).",
        "caps": [
            (0, 8, "Le plan place les points de regroupement près des dépotoirs vérifiés."),
            (8, 16, "Les tournées des camions sont optimisées, avec horaires et rotations."),
            (16, 22, "Demain matin, ce camion passe à ce point."),
        ],
    },
    {
        "id": "E",
        "kind": "clip",
        "dur": 30,
        "tag": "5 · Deux camions en panne",
        "ou": "PC, Salubri Sim, panneau Flotte",
        "faire": "Mettre en « Panne » les deux camions affichés par `python scripts/demo_video.py`. Montrer les étapes recalculées / réutilisées (~1 s) et la ligne « Cohérence avec la version précédente ».",
        "caps": [
            (0, 7, "Changement de scénario : deux camions tombent en panne."),
            (7, 17, "Recalcul en environ une seconde : aucun point de regroupement ne bouge."),
            (
                17,
                30,
                "Tournées refaites ; points non desservis et coût affichés, avec la cohérence avec le plan précédent.",
            ),
        ],
    },
    {
        "id": "F",
        "kind": "clip",
        "dur": 25,
        "tag": "6 · Saison des pluies",
        "ou": "PC, Salubri Sim, paramètres du scénario",
        "faire": "Paramètre « Saison » : pluies. Attendre le recalcul. Montrer la ligne de cohérence puis les indicateurs simulés (dépôts sauvages, coût par tonne) avec leurs intervalles ; « 30 réplications » si le temps le permet.",
        "caps": [
            (0, 7, "Saison des pluies : plus de déchets, routes plus lentes."),
            (7, 17, "Le plan est recalculé ; la simulation multi-agents donne les indicateurs."),
            (17, 25, "Dépôts sauvages, coût par tonne, avec leurs intervalles sur 30 réplications."),
        ],
    },
    {
        "id": "G",
        "kind": "carte",
        "dur": 10,
        "tag": "",
        "ou": "généré (carte de fin)",
        "faire": "rien à enregistrer",
        "caps": [
            (
                0.3,
                9.7,
                "{\\fs84}Tout est libre : code AGPL-3.0, données ouvertes\\N{\\fs52}Une commande pour l'installer : docker compose up\\NRéutilisable pour une autre commune",
            )
        ],
    },
]
TOTAL = sum(p["dur"] for p in PLAN)
assert TOTAL <= 180, TOTAL


def ts(s: float) -> str:
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def ass(p: dict) -> str:
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narration,Arial,52,&H00FFFFFF,&H00FFFFFF,&HC0{NAVY[4:]}{NAVY[2:4]}{NAVY[:2]},&HC0{NAVY[4:]}{NAVY[2:4]}{NAVY[:2]},-1,0,0,0,100,100,0,0,3,16,0,2,120,120,64,1
Style: Etape,Arial,40,&H00FFFFFF,&H00FFFFFF,&H00{ORANGE[4:]}{ORANGE[2:4]}{ORANGE[:2]},&H00{ORANGE[4:]}{ORANGE[2:4]}{ORANGE[:2]},-1,0,0,0,100,100,0,0,3,12,0,7,48,0,44,1
Style: Carte,Arial,84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,160,160,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    if p["tag"]:
        ev.append(f"Dialogue: 1,{ts(0.3)},{ts(p['dur'] - 0.2)},Etape,,0,0,0,,{p['tag']}")
    style = "Carte" if p["kind"] == "carte" else "Narration"
    for a, b, t in p["caps"]:
        ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},{style},,0,0,0,,{t}")
    return head + "\n".join(ev) + "\n"


def run(*cmd: str, cwd: Path | None = None) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode:
        sys.exit(f"ffmpeg a échoué :\n{r.stderr[-1500:]}")
    return r.stdout


def duree(f: Path) -> float:
    return float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)).strip())


def plan_md() -> str:
    t, rows = 0.0, []
    for p in PLAN:
        m1, m2 = f"{int(t // 60)}:{int(t % 60):02d}", f"{int((t + p['dur']) // 60)}:{int((t + p['dur']) % 60):02d}"
        rows.append(
            f"| **{p['id']}** {m1}–{m2} ({p['dur']} s) | {p['ou']} | {p['faire']} | "
            + " ".join(f"« {re.sub(r'[{][^}]*[}]', '', c[2]).replace(chr(92) + 'N', ' / ')} »" for c in p["caps"])
            + " |"
        )
        t += p["dur"]
    return (
        "| Plan | Où | Quoi faire (exactement) | Texte affiché (narration) |\n|---|---|---|---|\n"
        + "\n".join(rows)
        + f"\n\nTotal : {TOTAL} s.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clips", nargs="?", help="dossier des enregistrements A_*, B_* … G n'a pas de fichier")
    ap.add_argument("-o", "--sortie", default="demo_salubri.mp4")
    ap.add_argument("--plan", action="store_true", help="affiche le plan de tournage")
    a = ap.parse_args()
    if a.plan or not a.clips:
        print(plan_md())
        return 0
    src = Path(a.clips)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        parts = []
        for p in PLAN:
            (tmp / f"{p['id']}.ass").write_text(ass(p), encoding="utf-8")
            out = tmp / f"{p['id']}.mp4"
            enc = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS)]
            if p["kind"] == "carte":
                run(
                    "ffmpeg",
                    "-nostdin",
                    "-y",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=0x{NAVY}:s={W}x{H}:d={p['dur']}:r={FPS}",
                    "-vf",
                    f"ass={p['id']}.ass",
                    *enc,
                    str(out),
                    cwd=tmp,
                )
            else:
                found = sorted(
                    f for f in src.glob(f"{p['id']}_*") if f.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm"}
                )
                if not found:
                    sys.exit(f"enregistrement manquant : {src}/{p['id']}_….mp4 ({p['ou']})")
                d = duree(found[0])
                k = d / p["dur"]
                if k > 1.5:
                    print(
                        f"  ! {p['id']} : {d:.0f} s enregistrées pour {p['dur']} s prévues (accéléré ×{k:.1f}) — refaire plus court ?"
                    )
                filtre = (
                    (f"setpts=PTS/{k:.5f}," if k > 1 else "")
                    + f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x{NAVY},fps={FPS}"
                )
                if k < 1:
                    filtre += f",tpad=stop_mode=clone:stop_duration={p['dur'] - d:.3f}"
                run(
                    "ffmpeg",
                    "-nostdin",
                    "-y",
                    "-loglevel",
                    "error",
                    "-i",
                    str(found[0].resolve()),
                    "-vf",
                    f"{filtre},ass={p['id']}.ass",
                    "-t",
                    str(p["dur"]),
                    *enc,
                    str(out),
                    cwd=tmp,
                )
            parts.append(out)
        (tmp / "liste.txt").write_text("".join(f"file '{x.name}'\n" for x in parts), encoding="utf-8")
        dest = Path(a.sortie).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        run(
            "ffmpeg",
            "-nostdin",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "liste.txt",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(dest),
            cwd=tmp,
        )
    print(f"{dest} ({duree(dest):.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
