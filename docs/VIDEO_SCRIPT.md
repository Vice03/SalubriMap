<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Vidéo de 3 minutes — plan de tournage et montage

Format : **sans voix**. La narration est affichée en sous-titres, ajoutés automatiquement par
`scripts/video_sous_titres.py` ; il suffit d'enregistrer l'écran. Durée finale : **178 s** (limite : 3 minutes).
Fil conducteur de la fiche : un signalement hors ligne avec masquage → retour du réseau → vérification → plan →
deux camions en panne → saison des pluies, plan recalculé.

## Ce qu'on enregistre : 6 enregistrements, A à F

Les cartes de titre (T) et de fin (G) sont fabriquées par le script. Chaque enregistrement est ramené à sa durée
prévue : **enregistrer au plus 1,5 fois la durée prévue**, sans se presser, en gardant 2 secondes d'arrêt sur chaque
résultat. Un enregistrement trop long est accéléré (le script le signale), un trop court voit sa dernière image tenue.

| Plan | Où | Quoi faire (exactement) | Texte affiché (narration) |
|---|---|---|---|
| **T** 0:00–0:08 (8 s) | généré (carte de titre) | rien à enregistrer | « Salubri / Signaler · Vérifier · Planifier · Simuler / L'assainissement de Ouagadougou en logiciel libre — Hackathon des universités 2026, défi 01 » |
| **A** 0:08–0:56 (48 s) | Téléphone Android (scrcpy), mode avion | Activer le mode avion. Ouvrir Salubri Go. Toucher « Français » (le bouton brille). Toucher « Photo », prendre la photo de test, attendre les cadres « Visage » / « Plaque », toucher OK. Quantité : « Une charrette ». Type : « Plastiques ». Position : toucher « Position ». Écran merci. Toucher « Voir mes signalements » (statut « En attente »). | « Sans réseau : mode avion. Le signalement sera gardé sur le téléphone. » « Salubri Go parle : on choisit sa langue, français ou mooré, en touchant le bouton qui brille. » « Étape 1 : la photo. Les visages et les plaques sont floutés sur le téléphone, avant tout envoi. » « Étape 2 : la quantité. Un sac, une brouette, une charrette, un camion. » « Étape 3 : le type de déchets. » « Étape 4 : la position GPS, sans rien saisir. » « Merci. Enregistré : il partira dès que le réseau revient. » « Il attend dans « Mes envois », statut « En attente ». » |
| **B** 0:56–1:06 (10 s) | Téléphone, même écran « Mes envois » | Désactiver le mode avion (menu du téléphone) et laisser l'écran « Mes envois » ouvert jusqu'au statut « Envoyé » avec son score. | « Le réseau revient : le signalement part tout seul, une seule fois. » « Statut « Envoyé », avec son score de confiance. » |
| **C** 1:06–1:31 (25 s) | PC, Salubri Map (http://localhost/), connecté en demo | Onglet Signalements, filtre « probable » ou « à vérifier ». Ouvrir le nouveau signalement (photo floutée visible, règles appliquées). Cliquer « Vérifier ». Passer sur la carte : le point apparaît. | « Côté mairie : le signalement arrive dans Salubri Map, photo déjà floutée. » « 12 règles anti-pièges calculent un score : doublons, faux GPS, photo réutilisée… » « Un modérateur vérifie : seul un signalement vérifié entre dans le plan. » « Il apparaît sur la carte. » |
| **D** 1:31–1:53 (22 s) | PC, Salubri Sim, scénario « Vidéo — Arrondissement 9 » | Ouvrir « Plan de collecte ». Montrer le point de regroupement le plus proche du dépotoir, puis la tournée qui le dessert (camion, heure de passage). | « Le plan place les points de regroupement près des dépotoirs vérifiés. » « Les tournées des camions sont optimisées, avec horaires et rotations. » « Demain matin, ce camion passe à ce point. » |
| **E** 1:53–2:23 (30 s) | PC, Salubri Sim, panneau Flotte | Mettre en « Panne » les deux camions affichés par `python scripts/demo_video.py`. Montrer les étapes recalculées / réutilisées (~1 s) et la ligne « Cohérence avec la version précédente ». | « Changement de scénario : deux camions tombent en panne. » « Recalcul en environ une seconde : aucun point de regroupement ne bouge. » « Tournées refaites ; points non desservis et coût affichés, avec la cohérence avec le plan précédent. » |
| **F** 2:23–2:48 (25 s) | PC, Salubri Sim, paramètres du scénario | Paramètre « Saison » : pluies. Attendre le recalcul. Montrer la ligne de cohérence puis les indicateurs simulés (dépôts sauvages, coût par tonne) avec leurs intervalles ; « 30 réplications » si le temps le permet. | « Saison des pluies : plus de déchets, routes plus lentes. » « Le plan est recalculé ; la simulation multi-agents donne les indicateurs. » « Dépôts sauvages, coût par tonne, avec leurs intervalles sur 30 réplications. » |
| **G** 2:48–2:58 (10 s) | généré (carte de fin) | rien à enregistrer | « Tout est libre : code AGPL-3.0, données ouvertes / Une commande pour l'installer : docker compose up / Réutilisable pour une autre commune » |

Total : 178 s.

Les étapes du téléphone suivent le guide vocal de Salubri Go : écran de langue → photo (cadres « Visage » et
« Plaque ») → quantité → type de déchets → position → merci → « Mes envois ». Pour le plan A, couper le son du
téléphone (les voix de l'application ne doivent pas se mêler à la lecture des sous-titres) ; montrer le bouton qui brille.

## Préparer (10 minutes avant)

1. `run/start` (version démo, choix 1 de `SALUBRI.bat`), puis
   `python scripts/demo_video.py --api http://localhost --arrondissement 9` : crée le scénario « Vidéo — Arrondissement 9 »,
   remet tous les camions en service et la saison sèche, recalcule le plan, copie la photo de test dans
   `docs/video/photo_signalement.jpg` et **affiche les deux camions à mettre en panne** (plan E).
2. Téléphone Android : installer l'APK (`apps/go/android/app/build/outputs/apk/debug/app-debug.apk`), saisir l'adresse du
   serveur affichée par `run/start` (même Wi-Fi), autoriser la localisation, **copier la photo de test sur le téléphone**
   (ou photographier un écran qui l'affiche). Ouvrir Salubri Go une fois avec réseau (mise en cache), puis fermer l'application.
3. PC : Salubri Map ouvert sur `http://localhost/`, « Se connecter » → `admin` et le mot de passe affiché au lancement (ou `demo` / `ouaga2026` si `SALUBRI_DEMO_MODE=true`). Fenêtre du navigateur en 1920×1080
   ou plein écran, zoom 100 %.
4. Fermer les notifications (mode Ne pas déranger) sur le PC et le téléphone.

## Enregistrer

- **Téléphone (A et B)** : `scrcpy --no-audio --max-size=1280 --record=video_clips/A_telephone_hors_ligne.mp4`
  (câble USB, débogage USB activé ; Ctrl+C pour finir). Pour B : `--record=video_clips/B_retour_reseau.mp4`.
  Le mode avion se bascule depuis le téléphone ; le câble reste branché (il sert à l'image, pas au réseau).
- **PC (C à F)** : barre de jeu de Windows (`Win + Alt + R` démarre et arrête) ou OBS Studio, 1080p, 30 images/s,
  sans micro. Un fichier par plan, nommé `C_verification.mp4`, `D_plan.mp4`, `E_pannes.mp4`, `F_pluies.mp4`.
- Tout dans le dossier `video_clips/` à la racine du dépôt (ignoré par git).
- Plan E : mettre en panne **les deux camions affichés** par `demo_video.py` ; plan F : bien attendre la fin du recalcul avant de couper.

## Monter

```
python scripts/video_sous_titres.py video_clips -o livrable/6_video/demo_salubri.mp4
```

Le script écrit la vidéo (1920×1080, 30 images/s, sans son), avec une étiquette d'étape en haut à gauche et la narration en bas.
Il demande `ffmpeg` (avec le filtre `ass`) et Python 3. Le tableau ci-dessus vient de `python scripts/video_sous_titres.py --plan` ;
pour changer un texte ou une durée, modifier `PLAN` dans le script (la somme doit rester ≤ 180 s).

## Contrôle avant de rendre

- La vidéo dure 3 min au plus (`ffprobe livrable/6_video/demo_salubri.mp4`).
- Chaque sous-titre reste lisible (au moins 4 s), rien ne cache l'action à l'écran.
- Aucune donnée personnelle visible : photo floutée, pas de visage ni de plaque nets, pas de numéro de téléphone ni de notifications.
- Le plan A montre bien le mode avion, les cadres de masquage et le statut « En attente » ; le plan B le statut « Envoyé ».
