<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 1 — Application de signalement hors connexion (Salubri Go)

**Code** : [`apps/go`](../../apps/go) (React + TypeScript, PWA et application Android Capacitor). Notice : [`apps/go/README.md`](../../apps/go/README.md).

- **Hors connexion** : le signalement (photo, position, type, quantité) attend dans la file « Mes envois » et part
  seul au retour du réseau ; l'envoi est idempotent (aucun doublon). Toute l'application se charge sans réseau.
- **Masquage automatique** des visages et des plaques d'immatriculation **sur le téléphone, avant tout envoi**
  (YuNet + YOLOv9-t en ONNX, WebAssembly), avec seconde passe sur le serveur. Méthode et mesures :
  [`docs/MASQUAGE.md`](../../docs/MASQUAGE.md), [`docs/MASQUAGE_EVALUATION.md`](../../docs/MASQUAGE_EVALUATION.md).
- **Guide vocal pour les personnes qui ne lisent pas** : au lancement, une voix française puis une voix mooré
  proposent la langue (le bouton de la langue qui parle brille) ; le signalement se fait ensuite pas à pas, un grand
  bouton par étape : photo → quantité → type de déchet → localisation → remerciement. Les voix françaises sont
  fournies (`apps/go/public/audio/fr/`, générées par `scripts/go_audio_fr.py`). Les voix mooré sont
  enregistrées (`apps/go/public/audio/mos/`, découpées par `scripts/go_audio_mos_decoupe.py`) et **restent à faire valider
  par un locuteur** (22 fichiers, liste et textes dans [`docs/AUDIO_GO.md`](../../docs/AUDIO_GO.md)). « Continuer sans voix » ouvre le formulaire classique.

## L'essayer

- **Navigateur / téléphone** : lancer Salubri (`SALUBRI.bat`, choix 1), puis `http://localhost/go/` ou choix 4 du menu.
- **Android (APK)** : artefact `salubri-go-apk` du workflow GitHub « Android », ou construction locale
  (`apps/go/README.md`, section Android) ; résultat `apps/go/android/app/build/outputs/apk/debug/app-debug.apk`.
  Au premier lancement, saisir l'adresse du serveur affichée par `run/start` (même Wi-Fi).
- **Tests** : `pnpm --filter ./apps/go test` (masquage, file d'attente, guide vocal) et `tests/e2e/test_go_*.py`.
