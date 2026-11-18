<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 2 — Moteur d'optimisation et simulateur multi-agents

**Code** : [`apps/api/salubri_api/services/`](../../apps/api/salubri_api/services) — `planning/` (îlots, demande, placement
des points de regroupement en CP-SAT, distances, tournées OR-Tools avec fenêtres horaires) et `simulation/abm/` (ménages,
pré-collecteurs, brigade Laabal, mairie ; 30 réplications avec intervalles).

**Paramètres, dans un fichier documenté** :
- [`params_default.json`](params_default.json) : les valeurs de départ ; chaque scénario en fait une copie modifiable.
- [`params_schema.json`](params_schema.json) : pour chaque paramètre, l'unité, l'intervalle plausible, la source et son
  statut (mairie, littérature, hypothèse) ; une valeur hors intervalle est refusée au chargement.
- [`PARAMETRES.md`](PARAMETRES.md) : la table lisible, générée depuis le schéma.
- Charger les valeurs de la mairie : `python -m salubri_api.params import mairie.json --simulation` (`--a-blanc` pour voir sans écrire).

**Méthode** : [`SIMULATION_ODD.md`](SIMULATION_ODD.md) (protocole ODD du modèle), [`SIMULATION_SENSIBILITE.md`](SIMULATION_SENSIBILITE.md)
(paramètres les plus influents), [`SIMULATION_CALIBRATION.md`](SIMULATION_CALIBRATION.md), [`BENCHMARK_TOURNEES.md`](BENCHMARK_TOURNEES.md)
(OR-Tools contre repli), [`HYPOTHESES.md`](HYPOTHESES.md) (ce qui est supposé et à remplacer par une donnée).

**Le lancer** : `SALUBRI.bat` → Salubri Sim, ou `run/rehearse` (rejoue l'épreuve du jury). Tests : `run/test`.
