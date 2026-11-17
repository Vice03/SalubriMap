# Hypothèses (à confirmer avec la mairie ou le jury)

| # | Hypothèse | Valeur | Où la changer |
|---|---|---|---|
| H1 | Déchets produits par habitant | 0,6 kg/jour (ordre de grandeur cité par la mairie dans Sidwaya), +15 % en saison des pluies | `params_default.json` |
| H2 | Distance de marche acceptable vers un point ; capacité d'un point | 300 m ; 2,5 t (bac de 6 m³) | `params_default.json` |
| H3 | Flotte de démonstration | 8 camions (5 × 8 t, 3 × 12 t), dépôt unique au nord-est | `vehicles.csv`, `commune.json` |
| H4 | Position du dépôt (CTVD de Polesgo) | (−1,50 ; 12,47), approximative | `commune.json` → `depot` |
| H5 | Abonnement pré-collecte | 1 500 FCFA/mois, taux initial 35 % ; coût d'un pré-collecteur 60 000 FCFA/mois | `params_default.json` |
| H6 | Nettoyage des dépotoirs (services techniques de la mairie) | 12 t/jour | `params_default.json` |
| H6b | Brigade Laabal (police civique, ministère de la Sécurité, créée en juin 2025) : elle **ne ramasse pas**, elle contrôle, sensibilise et sanctionne | 3 opérations/semaine, 6 îlots inspectés par opération, effet dissuasif −50 % pendant 21 jours, +5 points d'abonnement sur l'îlot contrôlé, riverains contraints d'évacuer le dépôt vers leur point | `params_default.json`, `simulation/params.py` — hypothèse, aucun chiffre d'effet publié |
| H7 | Quartiers de démonstration | 24 polygones approximatifs, 35 000 à 65 000 habitants chacun | `quartiers.geojson` |
| H8 | Ville synthétique tant que les extraits réels manquent | grille de voies tous les 300 m, un marigot et trois barrages, une concession pour 25 habitants | `data/osm`, `data/open_buildings` |
| H9 | Comportement des ménages non abonnés | probabilité de dépôt sauvage σ(−1,5 + 0,004 × (distance − 300 m) + 0,5 si point plein + 0,3 en saison des pluies) | `services/simulation/params.py` |
| H10 | Réabonnement | +2 points/mois si ≥ 80 % des passages prévus ont eu lieu, −3 sinon | `services/simulation/params.py` |
| H11 | Fenêtres horaires | marchés 05 h–08 h, ailleurs 07 h–17 h ; 10 min par arrêt ; 8 h par tournée ; 2 rotations par camion | `services/plan/pipeline.py`, `planning/vrp.py` |
| H12 | Saison des pluies | vitesses × 0,7 ; pistes et voies en terre presque impraticables (OSRM) ; × 1,5 sur les distances à vol d'oiseau | `params_default.json`, `services/osrm/profiles/car_rain.lua` |
| H13 | Corroboration | 2 appareils différents, > 1 h d'écart, ≤ 30 m, même type → vérifié | `services/validation/engine.py` |
| H14 | Identifiants | UUID v4 (et non v7) | `models/__init__.py` |
| H15 | Le maximum de points (`collection_point_max`) borne un placement complet ; un nouveau quartier reçoit toujours les points dont il a besoin | | `planning/collection_points.py` |

## Référence officielle : SDGD Ouagadougou 2020

Source : *Actualisation du Schéma directeur de gestion des déchets solides de la ville de Ouagadougou*, rapport définitif phase 2 « Mise en place de la base de données » (Commune de Ouagadougou / AMGT, CID–CINTECH, financement BAD, mars 2020), enquête de terrain 2019 :

- 44 centres de collecte et de tri (CCT), 1 CTVD, 12 décharges encadrées par la DSPH, 58 décharges sauvages, 4 autres sites ;
- 13 secteurs sans aucun centre de collecte : 2, 8, 12, 13, 20, 31, 34, 35, 39, 40, 41, 45, 50 ;
- arrondissements les plus touchés par les décharges sauvages : 12, 1 et 6, puis 4 et 3.

`data/communes/ouagadougou/sdgd2020.geojson` : 115 sites numérisés depuis la carte « Répartition spatiale des décharges et CCT » (p. 29), par détection des symboles puis calage du contour de la commune sur la limite OSM (relation 5675756). Précision estimée ± 500 m ; couche de référence affichée sur la carte, non utilisée dans les calculs.

Utilisation dans les calculs (v0.2) :
- les décharges SDGD (sauvages, encadrées DSPH, autres) sont chargées comme **signalements officiels vérifiés** (`external_id = sdgd2020:…`, sans passer par les règles anti-pièges) et deviennent des dépotoirs ;
- les CCT existants qui desservent la zone active sont **gardés comme points de regroupement fixes** (paramètre « Garder les CCT existants », activé par défaut) ; l'algorithme n'ajoute des points que là où aucun CCT n'est à distance de marche.

## Comptes et rôles (0.3, lot A1)

Choix faits là où la consigne laissait le choix (option la plus simple et sûre) :

- **Rôles** : `moderateur` (modération des signalements, actions sur les dépotoirs) et `admin` (en plus : imports et annulation, scénarios, flotte, quartiers, recalculs, réplications de simulation). L'admin a tous les droits du modérateur. Les lectures restent publiques ; `POST /api/reports` reste ouvert aux citoyens.
- **Réplications** (`POST /api/plans/{id}/simulate`) classées *admin* : elles lancent un calcul lourd, comme un recalcul de scénario.
- **Sessions** : jeton signé HMAC-SHA256 (bibliothèque standard), valable 8 h (`SALUBRI_SESSION_HOURS`), envoyé en `Authorization: Bearer …`. Révocation par un compteur `session_version` sur le compte : déconnexion, changement de mot de passe et désactivation ferment toutes les sessions du compte (pas de table de sessions).
- **Clé de signature** : `SALUBRI_SECRET_KEY`. Vide → clé aléatoire tirée au démarrage de l'API : les sessions ne survivent pas à un redémarrage (on se reconnecte). Le lot A2 rendra la clé obligatoire hors mode démonstration.
- **Mots de passe** : argon2id (`argon2-cffi`), 8 caractères minimum ; login enregistré en minuscules.
- **Identifiant de service** : `X-Salubri-Token` (= `SALUBRI_ADMIN_TOKEN`) garde les droits admin pour les scripts (`rehearse.py`, `bench_pipeline.py`) et pour l'interface web tant que l'écran de connexion (lot A7) n'existe pas ; le journal le signe « service (admin) ».
- **Journal** : chaque action d'un humain est signée « login (rôle) » ; « system » est réservé aux tâches de fond et au chargement des données, « console » à l'outil `python -m salubri_api.users`. Le champ `actor` envoyé par l'interface lors d'une modération est ignoré : l'auteur est le compte connecté.

## Mode démonstration et secrets (0.3, lot A2)

- `SALUBRI_DEMO_MODE` vaut **faux par défaut dans le code** (sûr) et **vrai dans `docker-compose.yml`** (la démo reste « une commande, sans compte à créer »).
- En démonstration : compte `demo` (admin, mot de passe `ouaga2026`, créé au démarrage s'il n'existe pas ; jamais recréé s'il a été désactivé), code de service `ouaga2026` si `SALUBRI_ADMIN_TOKEN` est vide, clé de session aléatoire par démarrage, badge visible (`GET /api/health` → `demo_mode`).
- Hors démonstration, l'API refuse de démarrer si : code de service vide, égal à `ouaga2026` ou de moins de 16 caractères ; clé de session de moins de 32 caractères ; aucun admin actif ; compte `demo` encore actif. Le message liste tous les problèmes à la fois.
- Génération des secrets : `run/secrets.ps1` (Windows, appelé par `run/start.bat`) et `run/secrets.sh` (appelé par `run/start.sh`), 32 octets aléatoires du système (générateur cryptographique), écrits dans `.env` (UTF-8 sans BOM), affichés une seule fois, jamais régénérés s'ils sont déjà corrects.

## Force brute et pourriel (0.3, lot A3)

- Les compteurs d'échecs de connexion sont **en mémoire du processus API** (un seul processus uvicorn) : un redémarrage les remet à zéro. Suffisant pour un poste de la mairie ; avec plusieurs processus, il faudrait les mettre en base.
- Deux clés comptées : l'identifiant (normalisé en minuscules) et l'adresse IP. Une connexion réussie efface le compteur de l'identifiant, pas celui de l'adresse.
- L'adresse vient de l'en-tête `X-Real-IP` posé par nginx. Quelqu'un qui appelle l'API directement sur le port 8000 peut l'inventer : la clé par identifiant tient toujours, et en production le port 8000 ne doit pas être exposé (voir docs/SECURITY.md, lot A6).
- Plafond par téléphone : 3 × le seuil de la règle R10 (`spam_per_hour`, 10 par défaut), soit 30 signalements reçus par heure. R10 baisse déjà le score à partir de 10 ; le refus 429 ne sert qu'à arrêter un robot. Compté sur l'heure de réception (le serveur), pas sur l'heure déclarée par le téléphone.
- L'adresse IP des échecs de connexion n'est pas écrite dans le journal (donnée personnelle, lot A4).
- En mode démonstration, un compte `demo` désactivé par un administrateur n'est pas réactivé automatiquement.

## Données personnelles (0.3, lot A4)

- « Public » = statut `verified` ou `cleaned`. Un signalement `probable` reste invisible aux visiteurs tant que la mairie ou la corroboration ne l'a pas vérifié.
- Champs retirés pour le public : appareil, identifiant client et externe, commentaire, précision GPS, heure de réception, règles déclenchées (leur texte peut citer l'appareil ou l'EXIF), nom du modérateur, EXIF. Le score et le type restent visibles.
- Les photos restent dans le même volume (aucune migration de fichiers) ; seul le chemin d'accès change. La copie publique est réencodée sans métadonnées à la volée (cache en mémoire de 256 photos) ; le lot A5 enlèvera l'EXIF dès l'enregistrement.
- Le journal contient des identifiants d'appareil, des notes et des noms de comptes : sa lecture exige un compte modérateur ou admin. Les compteurs agrégés (`/api/reports/stats`) restent publics.
- Démonstration : le navigateur qui a déjà saisi `ouaga2026` voit tout ; sur un navigateur neuf, cliquer « Se connecter » dans Signalements avant la scène « Filtre Rejetés » (ajouté à docs/DEMO.md).

## Téléversements (0.3, lot A5)

- Le plafond de 40 Mpx couvre les téléphones actuels (48 Mpx sont rares et redimensionnés par l'appareil photo par défaut). Au-delà, refus avec un message en français ; Salubri Go compresse déjà avant l'envoi.
- La copie enregistrée est un JPEG qualité 85, 2560 px au plus de côté. Les règles gardent ce qu'elles mesuraient sur l'original : empreinte SHA-256 (doublon exact), pHash, dimensions, poids, GPS et date EXIF, variance de luminance. Ces valeurs sont en base, pas dans le fichier.
- Les photos déjà enregistrées avant 0.3 gardent leur nom et leur EXIF sur le disque ; elles ne sont plus servies qu'à travers l'API, et la copie publique est sans EXIF (lot A4). Pas de migration des fichiers : plus simple et sans risque de perte.
- Le nom aléatoire empêche de deviner une photo et de savoir si deux signalements portent la même. Deux envois de la même image produisent deux fichiers : la règle de doublon s'appuie sur la base, pas sur le nom.
- Archive d'import : rien n'est extrait sur le disque ; le nom d'un fichier de l'archive ne sert que de clé pour retrouver la photo citée par la ligne.

## Connexion web (0.3, lot A7)

- Salubri Map ne se connecte plus avec le code de service : chaque personne utilise son compte (`demo` en démonstration). Le code de service reste pour les scripts (`run/rehearse`, imports automatisés).
- Une session invalide (expirée, révoquée, clé changée) est effacée à la première réponse 401, même en lecture : l'interface repasse en vue publique sans fenêtre surgissante ; seule une écriture ouvre le panneau.
- Les boutons réservés sont grisés d'après le rôle du compte ; l'API reste seule juge (un bouton forcé dans le navigateur reçoit 401/403).


## Module « Saisons » (optionnel, éteint par défaut)

Approximations volontairement simples, sans imagerie ni apprentissage ni reconstruction du graphe OSRM
(`apps/api/salubri_api/modules/seasons/service.py`) :

- **Route impraticable = couloir infranchissable** de 10 m de part et d'autre de l'axe. Marche : une paire
  (îlot, site) dont le segment à vol d'oiseau traverse le couloir est interdite ; on ne calcule pas de détour à
  pied (le ménage va à un autre point ou perd la couverture). Un site à moins de 15 m d'une route impraticable
  n'est pas utilisable.
- **Route d'accès d'un point** : la route la plus proche à moins de 30 m. Si elle est impraticable, le point va au
  site praticable le plus proche qui garde à portée de marche tous les ménages qu'il servait à portée, sans que
  leur trajet traverse le couloir ; sinon il est « inaccessible » et n'est plus desservi.
- **Tournées** : un arc dont le segment à vol d'oiseau traverse le couloir coûte 50 km et 120 min de plus
  (prohibitif face à des arcs de 1 à 5 km) ; avec OSRM, c'est la matrice OSRM qui reçoit cette pénalité. Un camion
  peut donc encore emprunter un tel arc s'il n'a aucune autre solution : le kilométrage le montre alors.
- **Facteur de vitesse** d'une route praticable mais ralentie : enregistré et affiché, pas encore appliqué aux
  temps de trajet (la matrice ne connaît pas les routes empruntées sans OSRM).
- Le placement complet tient compte des routes coupées ; un simple changement de saison garde les points (cache
  du placement) et applique seulement les déplacements ci-dessus : c'est ce qui garantit le retour exact aux
  positions de saison sèche.
