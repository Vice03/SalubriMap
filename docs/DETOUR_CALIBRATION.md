<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Calage du facteur de détour (repli sans OSRM)

Sans OSRM, les tournées utilisent « km à vol d'oiseau × facteur ». Ce facteur est maintenant un paramètre du
scénario (`fallback_detour_dry` = 1,35, `fallback_detour_rain` = 1,5 ; `docs/PARAMETRES.md`), et
`scripts/calibrer_detour.py` le cale sur la médiane du rapport km OSRM / km à vol d'oiseau sur 400 paires
(dépôt et points de regroupement du plan de base, paires de plus de 200 m), avec l'erreur moyenne par paire et le
biais total des km, avant et après calage.

## Statut : à faire par l'équipe

**Pas encore mesuré.** OSRM ne tourne pas dans l'environnement où ce lot a été développé (la construction du
graphe y a été refusée). Les valeurs 1,35 et 1,5 restent des hypothèses. Sur la machine de démonstration :

```bash
docker compose --profile osrm up -d
docker compose exec api python /app/scripts/calibrer_detour.py --osrm http://osrm:5000 --saison dry
docker compose exec api python /app/scripts/calibrer_detour.py --osrm http://osrm_rain:5000 --saison rain
docker compose exec api python /app/scripts/benchmark_tournees.py --osrm http://osrm:5000
```

Le script réécrit ce fichier avec les mesures ; recopier ensuite le facteur médian dans
`data/communes/ouagadougou/params_default.json` et relancer `python -m salubri_api.params check`.
