<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Collecte de terrain — protocole de l'équipe

Objectif : **au moins 50 signalements réels**, pris par l'équipe dans un même arrondissement de Ouagadougou,
vérifiés, puis publiés en données ouvertes (ODbL) et proposés à OpenStreetMap (`docs/OSM_CONTRIBUTION.md`).
La même sortie sert à constituer le jeu de mesure du masquage (`data/eval/masquage/README.md`).

## 1. Avant de partir

- Chaque membre installe Salubri Go (lien du serveur de l'équipe) et note **l'identifiant de son téléphone**
  (écran « Mes signalements », en bas) dans `data/communes/ouagadougou/equipe_appareils.txt`, un par ligne.
- Téléphone chargé, GPS activé (« haute précision »), heure automatique.
- Binômes : un photographe, un qui note les incidents (fiche § 3). Gilet ou badge de l'école visible.
- Itinéraire : un secteur de l'arrondissement par binôme, le long des caniveaux, marchés, terrains vagues,
  abords des cours d'eau.

## 2. Pour chaque dépôt

1. Se placer **à moins de 10 m** du dépôt, attendre que la précision GPS affichée passe sous 20 m.
2. Photographier le dépôt **en entier**, de face, sans personne au premier plan si possible. Le masquage floute
   visages et plaques avant l'envoi : vérifier l'aperçu, ajouter une zone à la main si un visage est oublié.
3. Choisir le type et le volume ; pas de nom ni de numéro de téléphone dans le commentaire.
4. Envoyer (sans réseau, le signalement attend dans la file et part au retour du réseau).
5. Un même dépôt n'est signalé qu'**une fois** par l'équipe (les doublons sont fusionnés, mais faussent le
   comptage).

## 3. Consentement et sécurité

- On ne photographie pas une personne qui refuse ; on ne photographie pas l'intérieur des cours.
- Si une personne reconnaissable doit rester sur la photo (jeu de mesure du masquage) : accord oral, noté avec la
  date sur la fiche ; jamais d'enfant reconnaissable.
- On ne touche pas aux déchets médicaux ; on s'éloigne des fumées de brûlage.

## 4. Au retour

- Modération dans Salubri Map par un membre qui n'a pas pris la photo : « vérifié » si le dépôt est visible et
  bien placé, sinon « rejeté » avec le motif.
- Export : `PYTHONPATH=apps/api python scripts/export_signalements_equipe.py --appareils data/communes/ouagadougou/equipe_appareils.txt --depuis AAAA-MM-JJ`
  → `data/communes/ouagadougou/signalements_equipe.geojson`. Vérifier le nombre annoncé (≥ 50) et ouvrir le
  fichier dans geojson.io avant de le committer.

## 5. Dictionnaire des données

`signalements_equipe.geojson` — FeatureCollection, WGS 84, un point par signalement vérifié.

| Champ | Type | Contenu |
|---|---|---|
| `id` | texte (UUID) | identifiant Salubri du signalement |
| `type_dechet` | texte | `household`, `plastic`, `rubble`, `organic`, `medical`, `mixed`, `other` |
| `volume` | texte | `bag` (sac), `wheelbarrow` (brouette), `cart` (charrette), `truck` (camion) |
| `date` | date-heure ISO 8601, UTC | moment de la prise du signalement |
| `statut` | texte | `verified` (vérifié par l'équipe) ou `cleaned` (nettoyé depuis) |
| `score` | entier 0–100 | score des règles anti-pièges (`docs/RULES.md`) |
| `precision_gps_m` | entier ou null | précision annoncée par le téléphone |
| `quartier` | texte | quartier de Ouagadougou du point |
| `photo` | lien ou null | photo **masquée par le serveur** ; null si le masquage n'est pas enregistré |
| `photo_masquee` | booléen | vrai si une photo masquée est référencée |

Jamais publiés : identifiant du téléphone, commentaire libre, détail des règles, photo d'origine.

## 6. Licence

Données sous **Open Database License 1.0** (`data/communes/ouagadougou/LICENCE_signalements_equipe.md`),
attribution « © Équipe Salubri (Hackathon des universités 2026) ». L'ODbL est la licence d'OpenStreetMap : les
points vérifiés sur place par l'équipe peuvent y être versés (`docs/OSM_CONTRIBUTION.md`).

---

## Fiche de terrain (à imprimer, une page)

**Salubri — sortie du ____ / ____ / 2026 — Arrondissement : ______ — Binôme : ______________________**

1. GPS < 20 m, à moins de 10 m du dépôt. 2. Photo du dépôt en entier, personne au premier plan. 3. Vérifier
le floutage dans l'aperçu. 4. Type + volume, pas de nom dans le commentaire. 5. Envoyer. Un dépôt = un
signalement.

| N° | Heure | Lieu (repère) | Type | Volume | Personne sur la photo ? accord oral (oui/non) | Remarque |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | | | | | |
| 8 | | | | | | |
| 9 | | | | | | |
| 10 | | | | | | |

Refus de photo, déchets médicaux, brûlage : ne pas insister, noter en remarque.
