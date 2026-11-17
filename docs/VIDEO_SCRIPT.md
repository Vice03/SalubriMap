<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Vidéo de 3 minutes — plan de tournage

Suit la fiche du défi : un signalement citoyen hors ligne avec masquage → vérification → sur la carte → dans le
plan → dans la tournée du lendemain ; puis un changement de paramètres (2 camions en panne, puis saison des
pluies) et le plan recalculé avec ses mesures de cohérence.

## Préparer (10 minutes avant)

1. `run/start` (mode démonstration), puis
   `python scripts/demo_video.py --api http://localhost --arrondissement 9` : crée le scénario
   « Vidéo — Arrondissement 9 », remet tous les camions en service et la saison sèche, recalcule le plan, copie la
   photo de test dans `docs/video/photo_signalement.jpg` et affiche les deux camions à mettre en panne.
2. Téléphone Android en USB : `run/telephone`, ouvrir `http://localhost/go/` une fois (mise en cache), puis
   copier la photo de test sur le téléphone (ou photographier un écran qui l'affiche).
3. PC : Salubri Map ouvert, « Se connecter » → `demo` / `ouaga2026`. Enregistreur d'écran du PC et du téléphone
   (scrcpy) prêts, 1080p.

## Plans

| Temps | Écran | Action exacte | Ce qu'on dit |
|---|---|---|---|
| 0:00–0:15 | Titre | Carte de Ouagadougou, logo Salubri | « Un dépotoir sauvage est un symptôme : Salubri le repère, le vérifie et l'intègre au plan de collecte. » |
| 0:15–0:45 | Téléphone | **Débrancher le câble USB** (hors ligne). Salubri Go → « Prendre une photo » → choisir la photo de test → l'aperçu affiche « Masquage des visages et des plaques… » puis les cadres floutés → montrer « Flouter une zone » (toucher un cadre l'annule). « Utiliser le GPS » ou « Saisir la position à la main » sur un point de l'arrondissement 9. « Quel type de déchets ? » → Plastique ; « Quelle quantité ? » → Charrette → « Envoyer le signalement ». | « Pas de réseau : le signalement attend sur le téléphone. Les visages et la plaque sont floutés avant même de partir. » |
| 0:45–1:00 | Téléphone | « Voir mes signalements » : « En attente ». **Rebrancher** le câble et relancer `run/telephone` : le statut passe à envoyé, avec son score. | « Le réseau revient, il part tout seul. » |
| 1:00–1:25 | Salubri Map | Onglet des signalements, filtre « à vérifier » ou « probable » : ouvrir le nouveau signalement (photo floutée visible, règles appliquées) → « Vérifier ». Passer sur la carte : le dépotoir apparaît. | « Un modérateur de la mairie vérifie ; seul le vérifié entre dans le plan. » |
| 1:25–1:50 | Salubri Sim | Scénario « Vidéo — Arrondissement 9 » → « Plan de collecte » : le point de regroupement le plus proche du dépotoir et la tournée qui le dessert (camion, heure de passage). | « Demain matin, le camion BF-0x passe à ce point à 7 h 40. » |
| 1:50–2:25 | Salubri Sim | Panneau Flotte : mettre en **Panne** les deux camions affichés par le script. Montrer les étapes E1–E7 (recalculées / réutilisées, ~1 s), puis la ligne « Cohérence avec la version précédente » : 100 % des points inchangés, tournées refaites, points non desservis, coût. | « Deux camions en panne : aucun bac ne bouge, les tournées sont refaites en une seconde, et l'on voit ce qui ne sera pas desservi. » |
| 2:25–2:50 | Salubri Sim | Paramètre « Saison des pluies » → recalcul → ligne de cohérence et indicateurs simulés (dépôts sauvages, coût par tonne) avec leurs intervalles ; « 30 réplications » si le temps le permet. | « En saison des pluies : plus de déchets, routes plus lentes ; la simulation à agents donne la fourchette. » |
| 2:50–3:00 | Dépôt Git | Page GitHub : licence AGPL-3.0, `docker compose up`, badge des tests. | « Tout est libre et se réinstalle pour une autre commune. » |

## Après

Remettre les camions en service (ou relancer `scripts/demo_video.py`). Le signalement de la vidéo reste dans la
base : le rejeter ou le garder, selon qu'il correspond à un vrai dépôt.

## Statut

Tournage : **à faire par l'équipe**. Le script de préparation a été lancé sur la pile locale de développement.
