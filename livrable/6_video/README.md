<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 6 — Vidéo de démonstration (3 minutes)

Déposer ici la vidéo : **`demo_salubri.mp4`** (1080p, 3 min au plus). Elle suit la fiche : un signalement hors ligne avec masquage →
vérification → carte → plan → tournée du lendemain ; puis un changement de paramètres (2 camions en panne, saison des pluies) et le plan recalculé.

Format sans voix : la narration est en sous-titres. Plan de tournage (quoi faire, où, combien de temps) :
[`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md). Montage automatique des enregistrements d'écran avec les sous-titres :
`python scripts/video_sous_titres.py video_clips -o livrable/6_video/demo_salubri.mp4`. Préparation des données :
`python scripts/demo_video.py --api http://localhost --arrondissement 9`.
**État** : plan et montage prêts, vidéo à tourner.
