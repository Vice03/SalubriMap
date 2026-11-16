# Script de démonstration (5 minutes)

| Temps | Écran | À montrer |
|---|---|---|
| 0:00–0:30 | Une diapo | Un dépotoir sauvage est un symptôme. Salubri cartographie, vérifie, planifie et simule, en libre. |
| 0:30–1:15 | Salubri Go (téléphone projeté, mode avion) | Signaler : photo, « Plastique », « Charrette ». « Pas de réseau : c'est stocké. » Réseau → outbox verte, score 100. |
| 1:15–2:15 | Salubri Map | Le point apparaît. Même photo depuis un 2e téléphone → `R2 −70`, rejeté. Filtre « Rejetés » : trois pièges du jury et leurs règles. « Le plan ne voit que les signalements vérifiés. » |
| 2:15–3:30 | Salubri Sim | Deux camions en panne → étapes E1–E7 (3 recalculées, 4 réutilisées, ~1 s) → « 2 tournées refaites, points non desservis ». Saison des pluies. Nouveau quartier dessiné → nouveaux points, anciens figés. |
| 3:30–4:20 | Comparer | Base contre pannes + pluie : dépotoirs actifs, coût par tonne, couverture. |
| 4:20–4:50 | Export OSM | Télécharger le `.osm`, l'ouvrir dans JOSM. |
| 4:50–5:00 | Dépôt Git | AGPL-3.0, `docker compose up`, tests verts. |

## Test du mode hors ligne (Salubri Go)

Sur téléphone, le GPS et l'installation de l'appli exigent une connexion sécurisée. Deux façons de faire :

**A. Câble USB (recommandé pour la démo, Android).** `run/telephone` (adb reverse) : le téléphone ouvre `http://localhost/go/`, qui compte comme sécurisé. GPS, installation et hors ligne fonctionnent.
1. Ouvrir `http://localhost/go/` une fois avec le câble : toute l'appli est mise en cache dès cette première visite.
2. **Débrancher le câble** (le mode avion ne coupe pas l'USB), signaler un dépotoir : il apparaît « En attente » dans « Mes envois ».
3. Rebrancher et relancer `run/telephone` : l'envoi part tout seul (ou bouton « Synchroniser ») et affiche son verdict (statut + score).

**B. Wi-Fi en HTTPS (secours).** `https://<ip-du-pc>:8443/go/`, accepter l'avertissement du certificat local une fois : le GPS fonctionne. L'installation hors ligne ne marche pas avec un certificat non reconnu (limite des navigateurs) : pour la scène « hors ligne », utiliser A.

Sans l'un ou l'autre, la position se saisit à la main (champs vides par défaut) et le signalement est marqué « position saisie ».

## Code d'accès mairie et mode démonstration

Lectures publiques, envoi d'un signalement libre ; toutes les autres écritures exigent un compte de la mairie : modération et dépotoirs pour le rôle `moderateur`, imports, scénarios, flotte et quartiers pour le rôle `admin`.

`run/start` lance Salubri **en mode démonstration** (réglage par défaut, badge jaune « Mode démonstration » dans l'interface) : le compte `demo` (admin, mot de passe `ouaga2026`) est créé tout seul et le code `ouaga2026` reste accepté. L'interface le demande à la première action protégée (l'écran de connexion arrive au lot A7). Les scripts `run/rehearse` utilisent ce même code (`SALUBRI_ADMIN_TOKEN`).

**Hors démonstration** (`SALUBRI_DEMO_MODE=false` dans `.env`) : `run/start` génère un code de service et une clé de session aléatoires dans `.env` et les affiche une seule fois ; créer le premier admin avec `run/admin <login>` et désactiver `demo` s'il existe (`docker compose run --rm seed python -m salubri_api.users disable demo`). Sans cela, l'API refuse de démarrer et dit pourquoi (`docker compose logs api`).

## Avant la finale (3 fois : J-2, J-1, matin)

1. Machine de démo débranchée d'Internet : `run/reset` puis chronométrer le démarrage.
2. `run/rehearse` → rapport vert. Les pièges dépendent de la carte chargée (rues réelles ou ville synthétique) : après un changement de données, `make gen-traps` crée le jeu `data/rehearsal/traps/<carte>/`, que `rehearse` choisit tout seul.
3. Un membre joue le jury avec un autre téléphone : photo d'écran, GPS falsifié, même photo deux fois.
4. `docker compose stop osrm` pendant un recalcul → bandeau « distances approximatives », pas d'erreur ; puis `docker compose start osrm`.
