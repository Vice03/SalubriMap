<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Évaluation de l'assistant

30 questions réelles d'un agent de la mairie et les faits attendus dans la réponse :
[`evaluation.json`](evaluation.json). Les faits viennent des documents du dépôt (`docs/RULES.md`,
`docs/PARAMETRES.md`, `docs/SIMULATION_*.md`, `docs/PLAN_ARRONDISSEMENT_9.md`, `docs/HYPOTHESES.md`,
`docs/RAPPORT_TECHNIQUE.md`) au 17 novembre 2026 ; ils changent si ces documents changent.

| Domaine | Questions | Exemples de faits attendus |
|---|---|---|
| Règles des signalements | 5 + 1 | 12 règles ; R2 photo réutilisée ; R5 rejet ; R9 120 km/h ; l'assistant ne valide pas |
| Paramètres | 6 | 300 m ; 2,5 t ; 0,6 kg/hab/j ; abonnement = hypothèse ; détour 1,35 non mesuré |
| Simulation | 9 | déchets par habitant en tête ; p0 non calé ; 58 décharges du SDGD ; 30 réplications ; intervalle 90 % ; logit |
| Plan de l'arrondissement 9 | 6 | 3 enlèvements ; 9 camions ; 336 483 habitants ; quartiers de démonstration ; budget −30 % sans effet |
| Masquage | 2 | cible 95 % non atteinte ; photo « à vérifier » si le serveur échoue |

## Lancer l'évaluation

Pile lancée avec le module allumé et un modèle local (voir `docs/MODULES.md`) :

```bash
SALUBRI_ADMIN_TOKEN=<code mairie> python scripts/eval_assistant.py --api http://localhost --sortie docs/assistant_eval.json
```

Le script compte « correct » (tous les faits présents), « faux » et « je ne sais pas », le taux de citation et la
durée de chaque réponse (médiane, maximum). Il attend 11 s entre deux questions (limite de 6 questions par minute).

## Résultats

**Pas encore mesuré.** Aucun modèle local ne tourne là où le module a été développé : les tests de la CI utilisent
un modèle simulé (droits, aucune écriture, injection, journal, indisponibilité, citation), pas un vrai modèle.
À faire par l'équipe, sur le PC de démonstration, avec la commande ci-dessus ; recopier ici le tableau produit.
