# SPDX-License-Identifier: AGPL-3.0-or-later
"""Génère les voix françaises du guide vocal de Salubri Go (apps/go/public/audio/fr/*.mp3).

Moteur : Kokoro (kokoro-onnx, licence Apache-2.0), voix française « ff_siwis ». À lancer sur un poste avec Internet :

    pip install kokoro-onnx soundfile
    # modèle et voix : https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
    python scripts/go_audio_fr.py --model kokoro-v1.0.int8.onnx --voices voices-v1.0.bin --out apps/go/public/audio/fr

Les textes sont ceux de docs/AUDIO_GO.md. ffmpeg doit être installé (encodage MP3 mono, 24 kHz, 64 kbit/s)."""

import argparse
import subprocess
import sys
from pathlib import Path

TEXTES = {
    "lang_fr": "Si vous parlez français, appuyez ici.",
    "photo_ask": "Prenez une photo du dépotoir. Appuyez sur le bouton qui brille.",
    "photo_continue": "C'est bien. Appuyez sur le bouton pour continuer.",
    "qty_ask": "Quelle quantité de déchets estimez-vous ?",
    "qty_bag": "Un sac.",
    "qty_wheelbarrow": "Une brouette.",
    "qty_cart": "Une charrette.",
    "qty_truck": "Un camion.",
    "qty_more": "Plus qu'un camion.",
    "type_ask": "Quel type de déchets voyez-vous ?",
    "type_household": "Des ordures ménagères.",
    "type_plastic": "Des plastiques.",
    "type_organic": "Des déchets organiques : restes de nourriture, feuilles.",
    "type_rubble": "Des gravats : briques, béton, terre.",
    "type_medical": "Des déchets de soins : seringues, pansements.",
    "type_mixed": "Un mélange de tout.",
    "loc_ask": "Activez la localisation de votre téléphone, puis appuyez sur le bouton qui brille.",
    "loc_wait": "Patientez, nous cherchons votre position.",
    "loc_denied": "La localisation est coupée. Autorisez-la dans les réglages du téléphone, puis appuyez sur le bouton.",
    "thanks": "Merci pour votre signalement. Il est transmis à la mairie.",
    "thanks_offline": "Merci. Il n'y a pas de réseau : votre signalement partira dès que le réseau revient.",
    "again": "Pour faire un autre signalement, appuyez sur le bouton qui brille.",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--voices", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice", default="ff_siwis")
    ap.add_argument(
        "--speed", type=float, default=0.92, help="un peu plus lent que la normale : public qui découvre l'appli"
    )
    ap.add_argument("--only", nargs="*", help="ne générer que ces identifiants")
    a = ap.parse_args()

    import soundfile as sf
    from kokoro_onnx import Kokoro

    k = Kokoro(a.model, a.voices)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for ident, texte in TEXTES.items():
        if a.only and ident not in a.only:
            continue
        samples, rate = k.create(texte, voice=a.voice, speed=a.speed, lang="fr-fr")
        wav = out / f"{ident}.wav"
        sf.write(wav, samples, rate)
        # silences de début/fin coupés, volume normalisé, mono 64 kbit/s
        filtre = (
            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
            "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse,"
            "loudnorm=I=-16:TP=-1.5:LRA=7"
        )
        mp3 = out / f"{ident}.mp3"
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(wav),
                "-af",
                filtre,
                "-ac",
                "1",
                "-ar",
                "24000",
                "-b:a",
                "64k",
                str(mp3),
            ],
            check=False,
        )
        wav.unlink()
        if r.returncode:
            print(f"ECHEC {ident}", file=sys.stderr)
            return 1
        print(f"{ident}.mp3  {mp3.stat().st_size // 1024} ko")
    return 0


if __name__ == "__main__":
    sys.exit(main())
