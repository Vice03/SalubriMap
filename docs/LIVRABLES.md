---
title: "Salubri — où trouver chaque livrable"
---

# Salubri — bilan des livrables

**Hackathon des universités 2026 · Défi 01 « Assainissement de Ouaga »** · équipe Salubri (Salubri Go, Salubri Map, Salubri Sim)

Dépôt : <https://github.com/Vice03/SalubriMap> · Code sous AGPL-3.0-or-later, données et documents sous licences ouvertes.

> **Pour essayer tout de suite** : installer Docker Desktop, double-cliquer sur `SALUBRI.bat` à la racine du dépôt, taper **1** puis Entrée.
> Connexion mairie : identifiant `admin`, mot de passe généré au premier lancement et affiché à la fin (relisible dans `.env`). Guide pas à pas : `GUIDE_JURY.pdf`.

## Vue d'ensemble

| # | Livrable demandé | Où le trouver (dans le dépôt) | Statut |
|---|---|---|---|
| 1 | Application de signalement hors connexion, masquage automatique des visages et plaques | `livrable/1_application_signalement/` · code : `apps/go/` | Fait |
| 2 | Moteur d'optimisation et simulateur multi-agents, paramètres dans un fichier documenté | `livrable/2_moteur_et_simulateur/` · code : `apps/api/salubri_api/services/` | Fait |
| 3 | Tableau de bord des scénarios et plan de gestion d'un arrondissement | `livrable/3_tableau_de_bord/` · application : Salubri Map | Fait (arrondissement 9) |
| 4 | Jeu de signalements en GeoJSON, sous licence ouverte | `livrable/4_signalements_geojson/` | Jeu de démonstration (CC0) et décharges de référence fournis |
| 5 | Rapport : démarche, paramètres, scénarios, résultats, plan de gestion | `livrable/5_rapport/` | Fait (PDF et sources) |
| 6 | Vidéo de démonstration (3 min) | Dossier Drive ci-dessous | Hébergée sur Drive |

**Vidéo (livrable 6)** : <https://drive.google.com/drive/folders/1vDapkNbQ7dtDazXVJJZEUAqi9edlfBWA?usp=drive_link>
(dossier « Demo_Hackaton226 »). La narration est en sous-titres, sans voix.

## 1. Application de signalement hors connexion (Salubri Go)

- **Où** : `livrable/1_application_signalement/README.md` ; code dans `apps/go/` ; notice `apps/go/README.md`.
- **Ce que c'est** : une application web installable (PWA) et Android (APK). Le signalement (photo, position, type, quantité) attend dans la file « Mes envois » et part seul au retour du réseau, sans doublon.
- **Masquage** : visages et plaques floutés sur le téléphone avant tout envoi, avec une seconde passe sur le serveur (`docs/MASQUAGE.md`, `docs/MASQUAGE_EVALUATION.md`).
- **Guide vocal** pour les personnes qui ne lisent pas : voix française et voix mooré (`apps/go/public/audio/`), un grand bouton par étape. Les voix mooré restent à faire valider par un locuteur (`docs/AUDIO_GO.md`).
- **L'essayer** : `SALUBRI.bat` choix 1, puis `http://localhost/go/` (ou choix 4). APK : artefact `salubri-go-apk` du workflow GitHub « Android ».

## 2. Moteur d'optimisation et simulateur multi-agents

- **Où** : `livrable/2_moteur_et_simulateur/`.
- **Paramètres documentés** : `params_default.json` (valeurs de départ), `params_schema.json` (unité, intervalle, source, statut de chaque paramètre), `PARAMETRES.md` (table lisible).
- **Méthode** : `SIMULATION_ODD.md`, `SIMULATION_CALIBRATION.md`, `SIMULATION_SENSIBILITE.md`, `BENCHMARK_TOURNEES.md`, `HYPOTHESES.md`.
- **Code** : placement des points de regroupement et tournées (`planning/`), simulation à agents avec 30 réplications et intervalles (`simulation/abm/`).

## 3. Tableau de bord et plan de gestion

- **Où** : `livrable/3_tableau_de_bord/` (captures, figures, `PLAN_ARRONDISSEMENT_9.pdf`).
- **L'ouvrir en direct** : `SALUBRI.bat` choix 1, puis choix 3 (Salubri Map) : carte, modération, plan, comparaison de scénarios.

## 4. Jeu de signalements en GeoJSON

- **Où** : `livrable/4_signalements_geojson/`.
- **Fichiers** : `signalements_demo.geojson` (signalements simulés, CC0), `decharges_sdgd2020.geojson` (décharges et points de collecte de référence de l'étude SDGD 2020), licences et protocole de collecte (`COLLECTE_TERRAIN.md`).
- **État honnête** : le jeu de terrain de l'équipe (`signalements_equipe.geojson`, ODbL) n'est pas encore produit ; seul le jeu de démonstration est fourni.

## 5. Rapport

- **Où** : `livrable/5_rapport/`.
- **Contenu** : `RAPPORT_TECHNIQUE.pdf` (démarche, paramètres, scénarios, résultats avec intervalles, sensibilité, masquage, limites), `PLAN_ARRONDISSEMENT_9.pdf`, `MATRICE_CONTRIBUTION.md`, `CHECKLIST_FINALE.md` (chaque exigence de la fiche et où elle est satisfaite).

## 6. Vidéo de démonstration

- **Où** : dossier Drive ci-dessus.
- **Plan de tournage** : `docs/VIDEO_SCRIPT.md`. Montage avec sous-titres : `scripts/video_sous_titres.py`.

## Autres documents utiles

| Document | Emplacement |
|---|---|
| Guide d'utilisation illustré pour le jury | `GUIDE_JURY.pdf` (aussi dans `livrable/`) |
| README du dépôt | `README.md` |
| Sécurité et comptes | `docs/SECURITY.md` |
| Historique des changements | `CHANGELOG.md` |

*Le dossier `livrable/` est généré par `python scripts/livrable.py` ; les sources restent dans `apps/`, `data/` et `docs/`.*
