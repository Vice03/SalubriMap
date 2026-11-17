<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# Briques tierces et leurs licences

Salubri est sous AGPL-3.0. Chaque dépendance ajoutée y est notée avec sa licence et la raison de son ajout.
La liste complète des paquets (fichiers de verrouillage) sera générée pour la matrice de contribution.

## Ajouts du masquage des visages et des plaques

| Brique | Version | Licence | Où | Pourquoi |
|---|---|---|---|---|
| YuNet (modèle, OpenCV Zoo) | 2023mar | MIT | `apps/go/public/models/visages-yunet-2023mar.onnx` | détection des visages, hors ligne, 232 Ko |
| open-image-models — YOLOv9-t 384 plaques (modèle, ankandrew) | release v0.5.1 | MIT | `apps/go/public/models/plaques-yolov9t-384.onnx` | détection des plaques, hors ligne, NMS intégrée |
| onnxruntime-web (Microsoft) | 1.31 | MIT | `apps/go` | exécuter les deux modèles ONNX dans le navigateur (WebAssembly) |
| onnxruntime (Microsoft) | ≥ 1.20 | MIT | `apps/api` | seconde passe du masquage sur le serveur, mêmes modèles ONNX |
| exifr (Mike Kovařík) | 7.1 | MIT | `apps/go` | lire GPS et date dans l'EXIF avant masquage (la photo masquée n'en a plus) |

Images de test (pas dans l'application) : voir `tests/e2e/fixtures/README.md` (NASA, domaine public ;
Roboflow, CC BY 4.0).

## Modules optionnels (0.5.0) — éteints par défaut

Aucune nouvelle bibliothèque dans l'application : le module « Saisons » n'utilise que shapely, numpy et
SQLAlchemy (déjà là), le module « Assistant » httpx (déjà là) et la bibliothèque standard
(`run/llm_detect.py`). Ce qui peut s'ajouter sur la machine, seulement si le module « Assistant » est allumé et
avec l'accord de l'utilisateur :

| Brique | Version | Licence | Où | Pourquoi |
|---|---|---|---|---|
| Ollama (image Docker `ollama/ollama`) | 0.12.6 | MIT | profil Docker `assistant` (absent de la pile par défaut) | servir un modèle de langue local, API compatible OpenAI |
| Qwen2.5 1,5B / 7B / 14B instruct (Alibaba, poids) | 2.5 | Apache-2.0 | volume Docker `ollama`, téléchargé par `run/llm_detect.py` après accord | modèle de l'assistant selon la machine ; le 3B (licence de recherche Qwen, usage non commercial) n'est pas proposé |

Un modèle déjà installé sur la machine (LM Studio, llama.cpp, Jan…) garde sa propre licence : `run/llm_detect.py`
l'utilise tel quel, sans le redistribuer.
