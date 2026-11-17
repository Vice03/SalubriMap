<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Images de test du masquage

`visage_et_plaque.jpg` assemble deux images publiées sous licence libre, pour vérifier le flou automatique :

| Partie | Source | Licence |
|---|---|---|
| Visage (à gauche) | portrait d'astronaute, NASA, fourni par scikit-image (`skimage.data.astronaut`) | domaine public |
| Plaque (à droite) | jeu « License Plate Object Detection » de Roboflow, republié sur Hugging Face (`keremberke/license-plate-object-detection`, test, image 4) | CC BY 4.0, attribution Roboflow |

Ce ne sont pas des photos de Ouagadougou : elles valident le fonctionnement, pas le taux de détection
sur le terrain (voir `docs/MASQUAGE.md`, jeu d'évaluation `data/eval/masquage/`).
