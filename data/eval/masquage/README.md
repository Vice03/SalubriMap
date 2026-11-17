<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Jeu de terrain pour mesurer le masquage

Ce dossier reçoit les photos qui mesurent le masquage des visages et des plaques **sur nos conditions réelles**
(rues, dépotoirs et caniveaux de Ouagadougou). Il est vide tant que l'équipe n'est pas allée sur le terrain.

## Ce qu'il faut

- **Au moins 60 photos** prises avec Salubri Go ou l'appareil photo d'un téléphone, à la manière d'un signalement :
  un dépôt au premier plan, la rue autour. Varier : jour / fin de journée, passants proches et lointains, motos,
  voitures, tricycles, plaques blanches et jaunes, visages de face et de profil.
- **Au moins 40 photos avec au moins un visage** et **au moins 40 plaques**, dont des **plaques de moto** (les
  plus nombreuses à Ouagadougou ; le modèle a surtout appris des plaques de voitures européennes et américaines)
  et des plaques de voitures, sinon le rappel n'a pas de sens.
- **Consentement** : chaque personne reconnaissable a donné son accord oral (date notée dans `consentement`). Sinon,
  ne pas garder la photo. Pas d'enfants reconnaissables.

## Ce qu'on garde dans le dépôt

Les originaux contiennent des visages : ils **ne sont pas versionnés** (ils restent sur le disque de la personne
qui annote). Le dépôt ne contient que `annotations.json`, les résultats, et des copies floutées pour illustrer.

## Annotation

Préparation assistée : `PYTHONPATH=apps/api python scripts/annoter_masquage.py preparer data/eval/masquage`
pré-remplit `annotations.json` avec les zones du détecteur, marquées `"a_verifier": true` ; les annotateurs
corrigent chaque photo (déplacer, ajouter les oubliés — c'est eux qui comptent —, supprimer les faux) et retirent la
marque. `… verifier …` contrôle le format, le consentement et les minimums ; `… floutees …` écrit les copies
floutées à versionner.

`annotations.json`, coordonnées en pixels de l'image redressée (orientation EXIF appliquée) :

```json
{"images": [
  {"fichier": "rue_001.jpg", "consentement": "oral, 2026-11-20",
   "zones": [{"type": "visage", "x": 120, "y": 59, "w": 67, "h": 82},
             {"type": "plaque", "sous_type": "moto", "x": 842, "y": 197, "w": 182, "h": 69}]}
]}
```

Annoter **toutes** les têtes dont on voit le visage (même petites) et toutes les plaques, lisibles ou non : les plus
petites (visages < 20 px, plaques < 10 px de haut) sont comptées à part par le script, pas ignorées à l'annotation.
Un outil libre comme CVAT ou Label Studio convient ; convertir son export dans ce format.

## Mesurer

```bash
PYTHONPATH=apps/api python scripts/eval_masquage.py data/eval/masquage --json data/eval/masquage/resultat.json \
  --rapport docs/MASQUAGE_EVALUATION.md --nom "Jeu de terrain, Ouagadougou"
```

Le rapport donne le rappel et la précision par type, par taille (petite < 40 px, moyenne, grande ≥ 100 px), par
sous-type (moto, voiture), pour le téléphone seul et pour téléphone + seconde passe du serveur. Ne changer ni les
critères ni les cibles (rappel ≥ 0,95 visages, ≥ 0,90 plaques). **Si les plaques de moto restent sous 0,90** :
ré-entraîner le détecteur de plaques sur un jeu ouvert de plaques ouest-africaines et les plaques annotées de
l'équipe (licence notée), puis remesurer — étape prévue, pas encore faite faute de mesure.
