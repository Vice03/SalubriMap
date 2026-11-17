<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Masquage automatique des visages et des plaques

La fiche du défi demande que l'application de signalement **masque automatiquement les visages et les plaques
d'immatriculation**. Une photo de rue contient des données personnelles : aucune photo où l'on reconnaît une
personne ou une plaque ne doit être enregistrée ni publiée.

## Où se fait le masquage

| Étape | Où | État |
|---|---|---|
| 1. Détection + flou **sur le téléphone**, avant la file d'attente | Salubri Go (`apps/go/src/masking/`, `components/MaskEditor.tsx`) | **fait** |
| 2. Retouche par le citoyen : annuler un faux positif, « Flouter une zone » | Salubri Go | **fait** |
| 3. Seconde passe sur le serveur (filet de sécurité), imports ZIP compris, `masking: {client, server}` | API (`services/masking/`) | **fait** |
| 4. Règles anti-pièges vérifiées sur images masquées | `tests/test_masking_rules.py` | **fait** (aucun seuil changé) |
| 5. Mesure du rappel et de la précision sur des photos de terrain de Ouagadougou | `data/eval/masquage/` | à faire (étape 5 : photos de l'équipe nécessaires) |

L'image d'origine reste en mémoire le temps de l'écran ; **seule l'image masquée** est écrite dans la file
d'attente (IndexedDB) et envoyée. La position GPS et la date de prise de vue, que les règles anti-pièges
utilisent, sont lues dans l'EXIF **avant** le masquage et envoyées à part (`exif_lat`, `exif_lon`,
`exif_taken_at`) : le JPEG masqué n'a plus d'EXIF.

## Côté serveur

Chaque photo reçue (Salubri Go, autre client, import ZIP) est relue par le serveur avec **les mêmes modèles**
avant d'être enregistrée ; ce qu'il trouve encore est pixellisé de la même façon. Le signalement garde
`masking: {"client": {"faces", "plates", "manual"} | null, "server": n}` : `client` est ce que le téléphone
annonce, `server` le nombre de zones que le serveur a dû masquer lui-même (0 si le téléphone avait tout fait).

- **Sans modèles, aucune photo n'est enregistrée** : l'envoi répond 503 « Masquage des visages indisponible »
  (Salubri Go garde le signalement et réessaie), l'import refuse la ligne. `GET /api/health` affiche
  `"masking": "ok"` ou `"indisponible"`.
- Les modèles ne sont pas copiés deux fois : l'API lit `apps/go/public/models/` (monté en lecture seule dans
  le conteneur, `SALUBRI_MASKING_MODELS_DIR`).
- **Rattrapage** des photos enregistrées avant le masquage ou par une ancienne version :
  `docker compose exec api python -m salubri_api.services.masking.backfill` (`--dry-run` pour compter).
  Rejouable ; chaque photo réécrite est marquée `"rattrapage": true`.
- Règles anti-pièges : l'empreinte SHA-256 et le pHash sont calculés sur la photo **reçue**. Masquer une photo
  ne déplace son pHash que de 4/64 sur l'image de test (seuil de R2 : 8) ; la variance de luminance (R11) reste
  au-dessus du seuil ; dimensions inchangées. Aucun seuil n'a été modifié.

## Modèles choisis

| | Visages | Plaques |
|---|---|---|
| Modèle | **YuNet** 2023mar (`face_detection_yunet_2023mar.onnx`) | **YOLOv9-t 384 « end2end »** (`yolo-v9-t-384-license-plates-end2end.onnx`) |
| Source | OpenCV Zoo — <https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet> (copie officielle Hugging Face `opencv/face_detection_yunet`) | open-image-models d'ankandrew — <https://github.com/ankandrew/open-image-models> (release « assets ») |
| Licence | MIT | MIT |
| Taille | 232 589 octets | 7 771 218 octets |
| SHA-256 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` | `888397b96d761c89db40bc9c305838e8652660f5e282c2cadebbe8d2951a77a8` |
| Entrée | 640×640, BGR 0–255 | 384×384, RGB 0–1 (bandes grises 114) |
| Seuil | 0,6 (défaut de `cv2.FaceDetectorYN`) | 0,25 (défaut d'open-image-models) |
| Qualité publiée | WIDER Face : AP 0,834 / 0,824 / 0,708 (facile / moyen / difficile) | jeu de l'auteur : précision 0,942, rappel 0,863, mAP50 0,92 |
| Fichier dans l'app | `apps/go/public/models/visages-yunet-2023mar.onnx` | `apps/go/public/models/plaques-yolov9t-384.onnx` |

Pourquoi ceux-là :
- **même fichier ONNX** sur le téléphone (onnxruntime-web, WebAssembly) et sur le serveur (onnxruntime) : un seul
  comportement à mesurer ;
- **licences MIT**, compatibles avec l'AGPL du projet ; pas de modèle « recherche seulement » (SCRFD/insightface écartés) ;
- **petits** : YuNet tient en 230 Ko ; le détecteur de plaques est le plus léger de la famille (les variantes 256
  à 640 px pèsent toutes ~7,7 Mo ; 384 est le compromis rappel/vitesse de l'auteur) ;
- **NMS intégrée** au modèle de plaques : pas de post-traitement à réécrire.

Provenance du modèle de plaques : l'accès direct aux releases GitHub était bloqué dans l'environnement de
développement ; le fichier vient du miroir Hugging Face `wide-video/open-image-models-v0.5.1` (licence MIT,
copie de la release v0.5.1). Son empreinte SHA-256 est notée ci-dessus : **à recomparer avec le fichier de la
release officielle** avant la finale (`sha256sum`).

Le moteur `onnxruntime-web` 1.31 (MIT, Microsoft) apporte le WebAssembly (14,8 Mo, ~3,5 Mo compressé). Modèles
et moteur sont dans la liste du service worker : téléchargés une fois à l'installation, **aucun réseau à l'usage**.
La CSP autorise `'wasm-unsafe-eval'` (compilation du WebAssembly) mais toujours pas `eval()`.

## Le flou

Chaque zone détectée est agrandie de **20 %** de chaque côté, puis réduite à une grille de **6 cases au plus**
sur son grand côté ; chaque case est peinte de sa couleur moyenne (`apps/go/src/masking/blur.ts`). Il ne reste
aucun pixel d'origine : un visage tient en quelques aplats, une plaque en 6 blocs pour 7 à 8 caractères. Ce n'est
pas un flou gaussien, qu'on peut parfois inverser.

## Réglage de la détection des visages

Deux réglages, **identiques sur le téléphone et le serveur** (`apps/go/src/masking/geometry.ts`,
`apps/api/salubri_api/services/masking/detector.py`, test « même découpe que le serveur ») :

- seuil de score des visages **0,5** (défaut OpenCV : 0,6) ;
- quand la photo dépasse **1000 px** de côté, une seconde passe sur **2×2 tuiles** qui se recouvrent de 25 % ; une
  tuile ne garde que les visages de moins d'un quart de sa hauteur (elle sert aux petits visages ; au-delà, c'est
  le plus souvent une calandre ou une affiche, que la passe sur l'image entière aurait déjà vue si c'était un visage).

Pourquoi : à 640 px d'entrée, un visage de 30 px sur une photo de téléphone de 4000 px n'en fait plus que 5. Sur
le jeu public de contrôle (ci-dessous), les essais ont donné :

| Visages | Rappel | Précision | Temps serveur |
|---|---|---|---|
| seuil 0,6, image entière (réglage d'avant) | 0,822 | 0,979 | 75 ms |
| seuil 0,5, image entière | 0,871 | 0,923 | 75 ms |
| seuil 0,6, + 2×2 tuiles | 0,899 | 0,937 | ~340 ms |
| **seuil 0,5, + 2×2 tuiles, filtre de taille (retenu)** | **0,928** | **0,849** | 99 ms (médiane*) |
| seuil 0,5, + 3×3 tuiles | 0,943 | 0,814 | ~690 ms |

\* la médiane baisse parce que la moitié des photos du jeu font moins de 1000 px et n'ont pas de tuiles.
Pour la vie privée, un dépôt flouté en trop coûte moins qu'un visage oublié : on accepte la perte de précision,
et le bouton « annuler » sur chaque cadre reste là pour les faux positifs. Le 3×3 gagne peu pour deux fois le
temps : écarté.

## Mesures

### Jeu public de contrôle (pas Ouagadougou)

120 photos publiques : 60 de WIDER Face (validation, foules et scènes de rue, 829 visages annotés) et 60 du jeu
de plaques Roboflow (CC BY 4.0, 63 plaques). Réglage retenu, passe du serveur, mêmes critères que pour le jeu de
terrain (`scripts/eval_masquage.py`) :

| | Rappel | Précision | Cible de la fiche |
|---|---|---|---|
| Visages (404 zones de ≥ 20 px ; 425 plus petites ignorées) | **0,928** | 0,849 | rappel ≥ 0,95 — **non atteinte** |
| Plaques (62 zones de ≥ 10 px) | **0,935** | 0,881 | rappel ≥ 0,90 — atteinte sur ce jeu |
| Temps par photo, serveur | 99 ms (médiane, 2 cœurs) | | |

Ce jeu n'est **pas** représentatif : WIDER Face est bien plus dense en petits visages que nos photos de dépotoirs,
et les plaques Roboflow sont surtout européennes et américaines. Il sert à comparer des réglages, pas à prouver
les cibles. Les visages manqués sont surtout de 20 à 30 px, flous ou de profil.

### Jeu de terrain `data/eval/masquage/` — **non mesuré**

Protocole dans `data/eval/masquage/README.md` (au moins 60 photos de l'équipe à Ouagadougou, consentement,
annotation). Tant qu'il n'existe pas, les cibles de la fiche ne sont **pas démontrées** pour notre usage.

### Autres mesures

| Mesure | Résultat | Comment |
|---|---|---|
| Décodage identique à la référence Python | oui : boîte du visage (181, 67, 88, 107) et de la plaque (842, 197, 182, 69) égales à ±1 px | `tests/e2e/fixtures/visage_et_plaque.jpg`, référence onnxruntime Python |
| Zone masquée dans la photo en file d'attente | part de pixels texturés : visage 59 % → 13 %, plaque 56 % → 6 % | `tests/e2e/test_go_masking.py` |
| Temps sur le téléphone | non mesuré sur un vrai téléphone. Chrome sans écran, 2 cœurs, photo de 1309×512 (donc avec tuiles) : ~0,8 s par photo (1,7 s avec le chargement des modèles) ; processeur ralenti ×4 (profil « téléphone moyen » de DevTools) : ~3,3 s (4,8 s au premier) | Playwright, 5 essais |

Limites connues des modèles publiés : YuNet perd des visages de moins de ~10 px et de profil marqué ; le détecteur
de plaques est entraîné surtout sur des plaques européennes et américaines — les plaques burkinabè (fond blanc ou
jaune, format différent pour les motos) doivent être vérifiées sur le jeu de terrain.
