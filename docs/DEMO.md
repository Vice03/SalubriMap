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

1. Ouvrir `http://<ip-du-pc>/go/` sur le téléphone (même Wi-Fi).
2. **GPS et installation exigent HTTPS sur téléphone.** En HTTP sur le réseau local, Chrome Android refuse la géolocalisation : soit saisir la position à la main (le signalement passe « à revoir »), soit, sur le téléphone de démo, ouvrir `chrome://flags/#unsafely-treat-insecure-origin-as-secure`, ajouter `http://<ip-du-pc>`, relancer Chrome (GPS + installation de la PWA fonctionnent alors).
3. Page chargée, passer en mode avion, signaler un dépotoir : il apparaît « En attente » dans « Mes envois ».
4. Couper le mode avion : il part tout seul (ou bouton « Synchroniser ») et affiche son verdict (statut + score) ; il apparaît dans `GET /api/reports`.

## Code d'accès mairie

Lectures publiques, envoi d'un signalement libre ; toutes les autres écritures (modération, imports, scénarios, flotte, dépotoirs) exigent le code mairie, demandé par l'interface à la première action. Par défaut `ouaga2026` ; le changer avant la démo dans un fichier `.env` à la racine : `SALUBRI_ADMIN_TOKEN=…`. Les scripts `run/rehearse` le lisent dans la même variable.

## Avant la finale (3 fois : J-2, J-1, matin)

1. Machine de démo débranchée d'Internet : `run/reset` puis chronométrer le démarrage.
2. `run/rehearse` → rapport vert.
3. Un membre joue le jury avec un autre téléphone : photo d'écran, GPS falsifié, même photo deux fois.
4. `docker compose stop osrm` pendant un recalcul → bandeau « distances approximatives », pas d'erreur ; puis `docker compose start osrm`.
