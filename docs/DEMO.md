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

1. Ouvrir `http://<ip-du-pc>/go/` sur le téléphone (même Wi-Fi), installer la PWA.
2. Mode avion, signaler un dépotoir : il apparaît « En attente » dans l'outbox.
3. Couper le mode avion : il passe « Envoyé » avec son score ; il apparaît dans `GET /api/reports`.

## Avant la finale (3 fois : J-2, J-1, matin)

1. Machine de démo débranchée d'Internet : `run/reset` puis chronométrer le démarrage.
2. `run/rehearse` → rapport vert.
3. Un membre joue le jury avec un autre téléphone : photo d'écran, GPS falsifié, même photo deux fois.
4. `docker compose stop osrm` pendant un recalcul → bandeau « distances approximatives », pas d'erreur ; puis `docker compose start osrm`.
