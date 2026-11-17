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

- **Si la détection du serveur échoue** (modèles absents, erreur d'onnxruntime) : la photo est enregistrée dans
  le dossier privé `prive/` seulement, **jamais servie au public** (même si le signalement est vérifié),
  `masking.server = null` avec la cause dans `masking.erreur_serveur`, et le signalement passe « à vérifier »
  (règle M0). Le rattrapage (`python -m salubri_api.services.masking.backfill`) la masque et la sort du dossier
  privé dès que les modèles sont là. Même chose pour une photo d'import ZIP. `GET /api/health` affiche
  `"masking": "ok"` ou `"indisponible"`.
- **Mode manuel sur le téléphone** (modèles impossibles à charger) : rien ne part tant que le citoyen n'a pas
  tracé au moins une zone ou coché « Aucune personne ni plaque visible sur cette photo » ; le signalement porte
  `masking.mode = "manuel"` et passe « à vérifier » (règle M0). Le serveur masque quand même.
- **Premier chargement** : Salubri Go annonce « Préparation du détecteur… (première fois sur ce téléphone :
  ~8 Mo) » tant que les modèles n'ont jamais été chargés.
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
| Seuil | 0,5 (défaut de `cv2.FaceDetectorYN` : 0,6 ; voir « Réglage ») | 0,25 (défaut d'open-image-models) |
| Qualité publiée | WIDER Face : AP 0,834 / 0,824 / 0,708 (facile / moyen / difficile) | jeu de l'auteur : précision 0,942, rappel 0,863, mAP50 0,92 |
| Fichier dans l'app | `apps/go/public/models/visages-yunet-2023mar.onnx` | `apps/go/public/models/plaques-yolov9t-384.onnx` |

Pourquoi ceux-là :
- **même fichier ONNX** sur le téléphone (onnxruntime-web, WebAssembly) et sur le serveur (onnxruntime) : un seul
  comportement à mesurer ;
- **licences MIT**, compatibles avec l'AGPL du projet ; pas de modèle « recherche seulement » (SCRFD/insightface écartés) ;
- **petits** : YuNet tient en 230 Ko ; le détecteur de plaques est le plus léger de la famille (les variantes 256
  à 640 px pèsent toutes ~7,7 Mo ; 384 est le compromis rappel/vitesse de l'auteur) ;
- **NMS intégrée** au modèle de plaques : pas de post-traitement à réécrire.

Provenance vérifiée le 17/11/2026 (lot 2.5) :

| Modèle | Fichier officiel téléchargé | SHA-256 obtenu | Résultat |
|---|---|---|---|
| Plaques | `https://github.com/ankandrew/open-image-models/releases/download/assets/yolo-v9-t-384-license-plates-end2end.onnx` (7 771 218 octets) | `888397b9…2951a77a8` | **identique** au fichier de l'app (venu au départ du miroir Hugging Face `wide-video/open-image-models-v0.5.1`) |
| Visages | `https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx` (organisation OpenCV, 232 589 octets) | `8f2383e4…2552fa4` | **identique** |
| Visages | dépôt GitHub OpenCV Zoo (fichier stocké en Git LFS) | — | **à vérifier** : accès refusé depuis l'environnement de développement |

Commande pour la dernière ligne (sur un poste avec Internet) :

```bash
curl -sSL -o yunet.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
sha256sum yunet.onnx   # attendu : 8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4
```

Le moteur `onnxruntime-web` 1.31 (MIT, Microsoft) apporte le WebAssembly (14,8 Mo, ~3,5 Mo compressé). Modèles
et moteur sont dans la liste du service worker : téléchargés une fois à l'installation, **aucun réseau à l'usage**.
La CSP autorise `'wasm-unsafe-eval'` (compilation du WebAssembly) mais toujours pas `eval()`.

## Le flou

Chaque zone détectée est agrandie de **20 %** de chaque côté, puis réduite à une grille de **6 cases au plus**
sur son grand côté ; chaque case est peinte de sa couleur moyenne (`apps/go/src/masking/blur.ts`). Il ne reste
aucun pixel d'origine : un visage tient en quelques aplats, une plaque en 6 blocs pour 7 à 8 caractères. Ce n'est
pas un flou gaussien, qu'on peut parfois inverser.

## Réglage de la détection (lot 2.1 : petits visages et petites plaques)

**Identique sur le téléphone et le serveur** (`apps/go/src/masking/geometry.ts`, `detect.ts` ;
`apps/api/salubri_api/services/masking/detector.py` ; tests « même découpe » des deux côtés) :

1. La photo est ramenée à **1280 px** au plus (image de travail) ; les boîtes sont remises à l'échelle à la fin.
2. **Visages** : détection sur l'image entière **et** sur des tuiles carrées de **512 px** recouvrantes de 20 %
   (agrandies à l'entrée du modèle, 640 px), collées aux bords ; seuil 0,5 ; dans une tuile, seuls les visages de
   moins d'un quart de la tuile sont gardés (les grands sont vus par l'image entière) ; fusion par suppression des
   doublons (IoU > 0,3).
3. **Plaques** : image entière seulement (voir le tableau : les tuiles n'apportaient rien de mesurable).

Pourquoi : à l'entrée du modèle (640 px), un visage de 46 px sur une photo de 2400 px ne fait plus que ~12 px ;
il n'est trouvé que par les tuiles (fixture `petit_visage.jpg`, test serveur et test navigateur).

| Réglage essayé (jeu public de contrôle) | Visages rappel / précision | Plaques rappel / précision | Temps téléphone* |
|---|---|---|---|
| 2×2 tuiles fixes, image de travail entière (lot 0.4 étape 5) | 0,928 / 0,849 | 0,935 / 0,881 | — |
| tuiles visages 960 px (1,5 × l'entrée), travail 1920 px | 0,911 / 0,841 | 0,935 / 0,881 | — |
| tuiles visages 640 px, travail 1920 px, + tuiles plaques 576 px (score ≥ 0,5) | 0,931 / 0,844 | 0,952 / 0,741 | 9,7 s |
| idem, tuiles plaques à score ≥ 0,85 | 0,931 / 0,844 | 0,935 / 0,881 | — |
| tuiles visages 640 px, travail 1280 px, tuiles plaques 576 px (≥ 0,85) | 0,931 / 0,844 | 0,935 / 0,868 | 5,6 s |
| **retenu : tuiles visages 512 px, travail 1280 px, plaques sans tuiles** | **0,933 / 0,812** | **0,935 / 0,881** | **2,2 s** |

\* photo de 4000 × 2667 px, Chrome sans écran avec le processeur ralenti ×4 (profil « téléphone moyen » de
DevTools), détecteur déjà chargé ; la **première** photo, qui charge le détecteur, prend 4,9 s. Sans
ralentissement : 0,5 s (1,5 s la première). Sur un vrai téléphone : protocole dans
`docs/MASQUAGE_TELEPHONE.md` (lot 2.7), **non mesuré**.

Les tuiles de plaques à score ≥ 0,5 gagnaient 1,7 point de rappel mais faisaient perdre 14 points de précision,
rendaient la repasse instable (une photo déjà masquée redonnait une fausse plaque) et doublaient le temps : elles
sont coupées tant que le jeu de terrain (plaques de moto, § jeu de terrain) n'a pas montré qu'elles servent.
**Cible visages 0,95 : non atteinte** sur ce jeu (0,933).

## Mesures

Rapport détaillé par type, taille et chaîne (téléphone seul / téléphone + serveur) : [`MASQUAGE_EVALUATION.md`](MASQUAGE_EVALUATION.md),
généré par `scripts/eval_masquage.py`. Sur le jeu public, ce sont les **petits visages (< 40 px)** qui manquent :
rappel 0,875, contre 0,993 et 1,000 pour les moyens et les grands.

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
