<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Simulation multi-agents de la filière déchets — protocole ODD

Description du modèle à agents de Salubri Sim selon le protocole ODD (*Overview, Design concepts, Details* ;
Grimm et al., 2006, mise à jour 2020). Code : `apps/api/salubri_api/services/simulation/abm/`. Le modèle agrégé
existant (`services/simulation/engine.py`, flux en espérance par îlot) est conservé comme **mode rapide**
(`mode: "agrege"`) ; le modèle décrit ici est le mode `agents`.

Toutes les valeurs marquées **[H]** sont des hypothèses de travail, à remplacer par des données de la mairie ou
d'une enquête ; elles sont listées au § 7 avec leur justification et font partie de l'analyse de sensibilité.

---

## 1. But

Répondre, pour un arrondissement ou toute la commune, aux questions de la fiche :

- un plan de gestion (points de regroupement + tournées) tient-il face au **comportement réel des ménages** ?
  Combien de déchets finissent en dépotoir sauvage, où, et combien de temps y restent-ils ?
- que changent les leviers de la mairie : nombre de camions, fréquence de passage, prix de l'abonnement à la
  pré-collecte, nombre de descentes de la brigade Laabal, capacité de nettoyage, budget ?
- que se passe-t-il en saison des pluies, si des camions tombent en panne, si un quartier s'ajoute ?

Le modèle agrégé répond déjà en moyenne. Le modèle à agents ajoute ce que la moyenne efface : des ménages
différents (taille, revenu, distance), des **habitudes** et l'**effet d'entraînement** des voisins, des
pré-collecteurs qui font faillite ou grandissent, et une **dispersion** des résultats (intervalles à 90 %).

Critères de réussite du modèle : bilan de masse exact, reproductible à graine égale, cohérent avec le modèle
agrégé quand l'hétérogénéité est coupée (§ 8), 90 jours d'un arrondissement en moins de 30 s.

## 2. Entités, variables d'état et échelles

### Ménages (agents actifs, un par ménage)

| Variable | Type | Initialisation |
|---|---|---|
| `ilot` | îlot de résidence | population de l'îlot ÷ taille moyenne, arrondi |
| `taille` | personnes | 1 + Poisson(taille_moy − 1) ; homogène : taille_moy |
| `revenu` | classe 0 / 1 / 2 (faible, moyen, élevé) | tirage selon parts [H] 50 / 35 / 15 % ; homogène : moyen |
| `facteur_prod` | multiplicateur de production | log-normal moyenne 1, σ = 0,3 [H] ; homogène : 1 |
| `dist_m` | marche jusqu'au point de regroupement de l'îlot | distance de l'îlot (réseau routier, plan) + U(−50, 50) m [H] ; homogène : distance de l'îlot |
| `abonne` | booléen | tirage avec probabilité `subscription_rate` |
| `collecteur` | pré-collecteur qui sert l'îlot | celui de l'îlot |
| `stock_kg` | déchets gardés à la maison | 0 |
| `habitude` | dernier choix : garder / porter / jeter | garder |
| `jete_7j` | a jeté dans les 7 derniers jours | non |
| `passages_prevus_7j`, `passages_faits_7j` | régularité vécue du service | 0 |

### Pré-collecteurs (charretiers, agents actifs)

`capacite_kg` (`precollector_capacity_t`), `jours` de tournée (`precollector_frequency_per_week` répartis dans
la semaine), `ilots` servis (15 îlots voisins au départ, comme le modèle agrégé), `cout_mois`
(`precollector_cost_fcfa_month`), `revenu_mois`, `mois_en_perte`, `actif`, `charge_moyenne` (taux de
remplissage de la charrette sur le mois).

### Brigade Laabal (un agent collectif)

`operations_semaine` (`laabal_operations_per_week`), `ilots_par_operation` (6), `duree_effet_j` (21),
`amende_fcfa` [H] 5 000 ; mémoire des îlots contrôlés (`surveille_jusqua[îlot]`).

### Mairie (un agent collectif)

`budget_mois` (`budget_fcfa_month`), `budget_restant`, la flotte et les **tournées du plan** (issues du VRP,
étape E5 du pipeline : points visités, distance, capacité, coût fixe), `taux_panne` par camion et par jour,
`capacite_nettoyage_kg_j` (`cleanup_capacity_t_day`), coût du carburant par km.

### Entités passives

- **Points de regroupement** : `capacite_kg`, `niveau_kg`.
- **Dépotoirs sauvages** : un emplacement par îlot et un à côté de chaque point de regroupement (débordement) ;
  `stock_kg`, `age_j`, `pres_de_l_eau`, `recurrent` (réapparu moins de 15 jours après un nettoyage),
  `dernier_nettoyage`.

### Échelles

- **Temps** : pas d'un jour ; horizon 90 jours par défaut (7 à 365). Mois de 30 jours pour le budget, les
  abonnements et les comptes des pré-collecteurs.
- **Espace** : îlots de ~30 bâtiments (étape E1 du pipeline), regroupés autour des points du plan. Pas de
  coordonnées individuelles : un ménage hérite de l'îlot, avec une distance de marche propre.
- **Étendue** : un arrondissement (~10 à 20 000 ménages) ou la commune entière (~350 000 ménages). Mesuré :
  90 jours en 0,3 s pour 19 000 ménages et 5,2 s pour 357 000 (2 cœurs) ; le mode `agents` est donc le mode par
  défaut partout, et `agrege` reste disponible pour les très longues séries de réplications.

## 3. Vue d'ensemble des processus et ordonnancement

Chaque jour `t`, dans cet ordre (le même que le modèle agrégé, pour que les deux restent comparables) :

1. **Production** — chaque ménage ajoute `taille × kg_par_personne × facteur_prod × (1 + 15 % en saison des
   pluies)` à son stock.
2. **Pré-collecte** — chaque pré-collecteur actif dont c'est le jour passe chez ses abonnés, îlot par îlot dans
   l'ordre de sa liste, prend tout le stock du ménage tant que la charrette n'est pas pleine, et vide au point de
   regroupement de l'îlot ; ce qui ne rentre pas dans le point est déposé à côté (dépotoir de débordement). Un
   abonné non servi faute de place compte un passage manqué.
3. **Choix des ménages** — chaque ménage qui a un stock et doit décider aujourd'hui (§ 7.1) choisit entre
   *garder*, *porter au point* ou *jeter* (logit multinomial). *Porter* vide son stock dans le point (dans la
   limite de la place) ; *jeter* l'ajoute au dépotoir de son îlot.
4. **Camions de la mairie** — les jours de ramassage, chaque camion non en panne (tirage) fait sa tournée tant
   que le budget du mois n'est pas épuisé, vide les points dans l'ordre de la tournée jusqu'à sa capacité, et
   paie carburant + coût fixe.
5. **Brigade Laabal** — les descentes de la semaine sont réparties dans les jours ; chaque descente cible les
   îlots les plus sales (stock du dépotoir + bonus si récurrent), oblige les riverains à porter le dépotoir au
   point, met à l'amende les ménages qui ont jeté dans la semaine, pousse les non-abonnés à s'abonner, et
   l'îlot reste *surveillé* 21 jours.
6. **Nettoyage par la mairie** — l'équipe enlève jusqu'à `capacite_nettoyage_kg_j` dans les dépotoirs, par
   priorité (§ 7.4) ; les déchets partent en décharge.
7. **Fin de mois** (jour 29, 59, …) — comptes des pré-collecteurs (abandon ou extension, § 7.2), choix
   d'abonnement des ménages (§ 7.1), remise à zéro du budget de la mairie.
8. **Indicateurs** du jour (§ 5 du code et § 9 ici).

Toutes les étapes sont vectorisées par classe d'agents (tableaux NumPy) ; seules les boucles sur les
pré-collecteurs et les camions sont explicites (quelques dizaines d'objets).

## 4. Concepts

- **Principes** : choix discret à utilité aléatoire (McFadden) pour les ménages ; règles de seuil simples pour
  les pré-collecteurs (rentabilité) et la mairie (priorités), comme les acteurs les décrivent.
- **Émergence** : la carte des dépotoirs, leur récurrence, le taux d'abonnement, le nombre de pré-collecteurs
  actifs et le coût à la tonne ne sont pas imposés ; ils naissent des choix individuels et des contraintes de
  capacité.
- **Adaptation** : les ménages adaptent leur choix au service vécu (régularité sur 7 jours), à la pression de la
  brigade et à leurs voisins ; ils s'abonnent ou se désabonnent chaque mois ; les pré-collecteurs abandonnent ou
  prennent des clients.
- **Objectifs** : implicites (utilité des ménages, rentabilité des pré-collecteurs, budget de la mairie).
- **Apprentissage** : non (pas de mémoire au-delà de l'habitude, de la régularité sur 7 jours et du mois).
- **Prédiction** : aucune ; les agents réagissent à l'état observé.
- **Perception** : un ménage connaît sa distance, si son point est plein, si son îlot est surveillé, la part de
  ménages de son îlot qui ont jeté dans la semaine, la régularité de son pré-collecteur.
- **Interactions** : indirectes par les stocks partagés (points pleins → dépôts à côté), par la norme sociale de
  l'îlot, par la brigade (ciblage des îlots sales), par les pré-collecteurs (capacité partagée entre abonnés).
- **Stochasticité** : tirages à l'initialisation (taille, revenu, facteur, distance, abonnement), choix
  quotidiens et mensuels, pannes. Un seul générateur NumPy (`default_rng(seed)`), tiré dans un ordre fixe :
  même graine → même résultat, bit pour bit.
- **Collectifs** : îlots (norme sociale), clientèles des pré-collecteurs.
- **Observation** : séries quotidiennes et résumé par scénario (§ 9), médiane et intervalle à 90 % sur
  ≥ 30 réplications.

## 5. Initialisation

À partir d'une version de plan (`PlanSnapshot`, déjà utilisée par le modèle agrégé) : populations et distances
des îlots, point de chaque îlot, capacités des points, îlots près de l'eau, tournées. Les ménages sont créés îlot
par îlot (population × `population_factor` ÷ taille moyenne). Les pré-collecteurs reçoivent 15 îlots voisins
(îlots triés par point de regroupement), comme dans le modèle agrégé. Stocks à zéro, budget plein.

## 6. Données d'entrée

Aucune donnée extérieure en cours de simulation. Les entrées sont le plan (bâtiments Open Buildings → îlots,
réseau OSM → distances, VRP → tournées) et les paramètres du scénario (`params_default.json`, éditables dans
Salubri Sim ; scénarios « 2 camions en panne », « saison des pluies », etc.).

## 7. Sous-modèles

### 7.1 Ménages

**Qui décide chaque jour.** Un ménage non abonné décide chaque jour où il a du stock. Un abonné attend son
pré-collecteur (*garder*) tant que son stock reste sous `stock_max_jours` (4 jours [H]) de production ;
au-delà — service irrégulier ou pré-collecteur disparu — il décide comme un non-abonné, avec en plus le terme de
régularité.

**Choix quotidien (logit multinomial).** Utilités, *garder* servant de référence :

```
V_garder = β_reg × régularité_7j × abonné
V_porter = α_porter si le point est à portée (dist_m ≤ walk_distance_max_m) et pas plein, sinon −∞
           − β_dist_porter × dist_m / 100
V_jeter  = p0 + slope_dist × max(dist_m − walk_distance_max_m, 0) + slope_full × point_plein + slope_rain × pluie
           + ln(1 − laabal_deterrence) × îlot_surveillé          (crainte de l'amende)
           + β_norme × (part de l'îlot qui a jeté sur 7 j − 0,2)
           + β_habitude × [dernier choix = jeter] ;  + β_habitude sur V_porter si dernier choix = porter
P(k) = exp(V_k) / Σ exp(V_j)
```

`p0`, `slope_dist`, `slope_full`, `slope_rain`, `laabal_deterrence` sont **les mêmes paramètres** que dans le
modèle agrégé, ce qui garantit la cohérence du § 8. Termes propres au modèle à agents : `α_porter` = 8 (porter
quand c'est possible est presque certain : P > 0,999 sans les autres termes), `β_dist_porter` = 0,3 par 100 m,
`β_reg` = 2, `β_norme` = 2, `β_habitude` = 0,5 — tous **[H]**, retenus parce qu'ils donnent des ordres de
grandeur raisonnables (la norme peut doubler les dépôts d'un îlot déjà sale) ; ils sont dans l'analyse de
sensibilité.

**Abonnement (fin de mois).** Pour un non-abonné dont l'îlot a un pré-collecteur actif (ou un voisin avec de la
place) :
`P(s'abonner) = sigmoïde(a_abo + β_reg_mois × (régularité_îlot − 0,8) − β_prix × prix / revenu_classe + pousse_laabal)`
et pour un abonné : `P(se désabonner) = sigmoïde(a_desabo − β_reg_mois × (régularité_vécue − 0,8) + β_prix × prix / revenu_classe)`.
Revenus de référence par classe **[H]** 40 000 / 90 000 / 250 000 FCFA par mois ; `β_prix` = 20 ;
`a_abo`, `a_desabo` calés pour reproduire en moyenne les taux `sub_up` (+2 points/mois) et `sub_down`
(−3 points/mois) du modèle agrégé à prix et régularité de référence. Après une descente Laabal, chaque
non-abonné de l'îlot s'abonne avec la probabilité `laabal_sub_boost / (1 − taux de l'îlot)` (même effet moyen
que le modèle agrégé : +5 points).

### 7.2 Pré-collecteurs

- **Tournée** : les jours prévus, sert ses abonnés îlot par îlot jusqu'à remplir la charrette.
- **Comptes** : `revenu_mois = abonnés × prix`. Deux mois de suite en perte (`revenu < cout_mois`) → abandon :
  ses abonnés n'ont plus de service (leur régularité tombe, ils se désabonnent ou décident comme non-abonnés).
- **Extension** : si `revenu ≥ 1,5 × cout_mois` et `charge_moyenne < 70 %` [H], il reprend les îlots d'un
  pré-collecteur voisin qui a abandonné (le plus proche dans l'ordre des points), au plus un par mois.
- Indicateurs : nombre actif, revenu moyen.

### 7.3 Brigade Laabal

`laabal_operations_per_week` descentes par semaine, réparties au fil des jours (accumulateur, comme le modèle
agrégé). Cible : les îlots non surveillés ayant le score `stock du dépotoir + 500 kg × récurrent` le plus haut,
6 îlots par descente. Effets : dépotoir de l'îlot porté au point dans la limite de la place, en laissant celle d'un jour normal de dépôts
(sinon le point déborde et les ménages jettent à côté ; le reste attend l'équipe de nettoyage), amende
`amende_fcfa` à chaque ménage ayant jeté dans la semaine (compteur, sans effet sur le budget de la mairie),
îlot surveillé 21 jours (terme `ln(1 − laabal_deterrence)` dans `V_jeter`), poussée à l'abonnement.

### 7.4 Mairie

- **Ramassage** : jours de ramassage = `pickup_frequency_per_week` répartis dans la semaine ; panne de chaque
  camion avec probabilité `truck_breakdown_rate_per_day` ; tournées du plan dans l'ordre, capacité du camion,
  coût = km × carburant + coût fixe de la journée ; plus de sortie quand `budget_restant ≤ 0`.
- **Nettoyage des dépotoirs** : priorité = `stock × (1,5 si près de l'eau) × (1,3 si récurrent) × (1 + âge/30)`,
  dans la limite de la capacité du jour. Le facteur « récurrent » est le seul écart avec la règle du modèle
  agrégé (qui ne l'a pas) ; il traduit la consigne de la fiche (récurrents, près de l'eau, taille).

### 7.5 Bilan de masse

Produit = camions → décharge + nettoyage → décharge + stocks des ménages + niveaux des points + stocks des
dépotoirs. Vérifié à chaque fin de simulation (erreur relative < 1e-9, testé).

## 8. Contrôle de cohérence avec le modèle agrégé

Avec `heterogeneite = False` : tous les ménages ont la taille moyenne, le revenu moyen, `facteur_prod = 1` et la
distance de leur îlot ; `β_norme = β_habitude = β_dist_porter = 0`, `V_garder = 0`, pas d'extension des
pré-collecteurs ; abonnements mensuels tirés pour reproduire exactement les
variations moyennes du modèle agrégé (+`sub_up` si régularité ≥ 0,8, sinon −`sub_down`). Le choix quotidien se
réduit alors à celui du modèle agrégé (porter si possible, sinon jeter avec la probabilité du modèle agrégé).
Le modèle agrégé a été corrigé pour suivre la même règle en espérance : chaque îlot y garde deux stocks
(abonnés, non-abonnés), le pré-collecteur ne prend que celui de ses abonnés, et un abonné qui attend plus de
`sub_wait_days` (4 jours) décide comme un non-abonné. Avant cette correction, le pré-collecteur emportait aussi une
part des déchets gardés par les non-abonnés, ce qui sous-estimait les dépôts sauvages (de 12 % sur le scénario de
test). Sur le scénario de référence, la **moyenne de 30 réplications** doit tomber à **±10 %** du modèle agrégé pour
les tonnages produit, collecté par camion, pré-collecté et jeté, et à ±0,05 sur le taux d'abonnement final
(test `test_abm_coherence`). Écarts attendus et acceptés : discrétisation (ménages entiers), effet de l'amende
en log-cote plutôt qu'en multiplicateur de probabilité.

## 9. Indicateurs

Par jour et résumés sur l'horizon : tonnes produites, pré-collectées, portées, collectées par camion, jetées,
nettoyées ; dépotoirs actifs (> 50 kg) et récurrents ; taux d'abonnement ; pré-collecteurs actifs et revenu
moyen ; descentes Laabal et amendes ; coût de la mairie à la tonne et budget restant ; **couverture** (part de la
population à moins de `walk_distance_max_m` d'un point non plein ou servie par un pré-collecteur dans les 7
derniers jours). Incertitude : ≥ 30 réplications, médiane et intervalle à 90 % (5ᵉ–95ᵉ centiles). Sensibilité
globale : criblage de Morris puis indices de Sobol sur les paramètres les plus influents
(`docs/SENSIBILITE.md`).

## 10. Limites connues

Pas de déplacement des ménages ni de nouvelles constructions pendant la simulation ; pas de tri ni de
valorisation ; norme sociale limitée à l'îlot ; un seul type de pré-collecteur ; budget de la mairie mensuel et
sans report. Les paramètres comportementaux [H] ne sont pas calés sur une enquête : les résultats sont des
**comparaisons entre scénarios**, pas des prévisions.

## 11. Comportements observés en construisant le modèle

- **Brigade Laabal** : la dissuasion réduit nettement les dépôts (sur le scénario de test, ×0,5 quand
  `laabal_deterrence` passe de 0 à 0,99 avec 14 descentes par semaine, dans les deux modèles). Mais le dépotoir que
  les riverains rapportent au point peut le faire déborder, et les ménages de ce point jettent alors à côté : avec
  une dissuasion moyenne (0,5 à 0,8) et une équipe de nettoyage réduite, l'effet net des descentes est proche de
  zéro. Les descentes doivent donc aller avec des rotations de camions sur les points concernés.
- **Pré-collecteurs** : à la capacité par défaut (1,2 t pour 15 îlots), la charrette est le goulot ; de nouveaux
  abonnés n'augmentent pas la pré-collecte tant que la capacité ne suit pas.
