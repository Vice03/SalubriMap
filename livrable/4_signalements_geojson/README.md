<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 4 — Jeu de signalements en GeoJSON, sous licence ouverte

| Fichier | Contenu | Licence |
|---|---|---|
| [`signalements_demo.geojson`](signalements_demo.geojson) | signalements **simulés** de la démonstration (aucun n'est un vrai citoyen) | **CC0 1.0** ([`LICENCE_signalements_demo.md`](LICENCE_signalements_demo.md)) |
| `signalements_equipe.geojson` | signalements **réels** collectés par l'équipe dans son secteur, vérifiés, photos masquées | **ODbL 1.0** ([`LICENCE_signalements_equipe.md`](LICENCE_signalements_equipe.md)) — **à ajouter après la sortie terrain** |

Champs de chaque point : `external_id`, `waste_type`, `volume_class`, `reported_at`, `accuracy`, `photo`. Jamais exporté pour les
signalements réels : identifiant d'appareil, commentaire libre, score détaillé.

**Produire le jeu de terrain** (protocole : [`COLLECTE_TERRAIN.md`](COLLECTE_TERRAIN.md)) :
`PYTHONPATH=apps/api python scripts/export_signalements_equipe.py --appareils data/communes/ouagadougou/equipe_appareils.txt`,
puis `python scripts/livrable.py` copie le fichier dans ce dossier.
**État honnête** : le jeu de terrain n'existe pas encore ; seul le jeu de démonstration est fourni.
