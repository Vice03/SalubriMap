<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Coût du masquage sur un téléphone d'entrée de gamme — protocole

## Ce qui est mesuré ici (17/11/2026, sans téléphone)

| Mesure | Résultat | Comment |
|---|---|---|
| Taille installée (cache de Salubri Go) | 23,9 Mo, dont moteur WebAssembly 14,8 Mo et modèles 8,0 Mo | `apps/go/dist`, 54 fichiers dans la liste du service worker |
| Téléchargé à l'installation | ~11 Mo (moteur 3,9 Mo + modèles 7,1 Mo compressés, gzip activé par nginx au lot 2.7) | `curl -H "Accept-Encoding: gzip"` sur la pile locale ; avant le lot 2.7 : 23,9 Mo |
| Détection, photo de 4000 × 2667 px, processeur ralenti ×4 (« téléphone moyen » de DevTools) | 2,2 s par photo ; 4,9 s pour la première (chargement du détecteur) | Chrome sans écran, 2 cœurs |
| Même mesure sans ralentissement | 0,5 s ; 1,5 s la première | idem |
| Message pendant le premier chargement | « Préparation du détecteur … (première fois sur ce téléphone : ~8 Mo) » | `MaskEditor.tsx` |

Le ralentissement ×4 de Chrome n'imite ni la mémoire ni le WebAssembly d'un vrai téléphone : **le temps réel sur
un téléphone d'entrée de gamme n'est pas mesuré**.

## Protocole (à faire par l'équipe, 30 minutes)

Matériel : un téléphone Android d'entrée de gamme (≤ 3 Go de mémoire, 2020 ou avant), Chrome à jour, câble USB,
le PC de démonstration lancé (`run/start`), 5 photos de rue prises avec ce téléphone (au moins une avec plusieurs
personnes au loin).

1. Effacer les données de Chrome pour `localhost` (Paramètres du site → Effacer et réinitialiser).
2. `run/telephone`, ouvrir `http://localhost/go/` ; noter l'heure. Attendre la fin de l'installation (le
   PC montre les téléchargements dans `docker compose logs web`) ; noter la durée.
3. Paramètres Android → Applications → Chrome → Stockage : noter l'espace utilisé.
4. Prendre la 1ʳᵉ photo ; quand le statut sous la photo indique le résultat, noter le temps affiché par la
   commande de la 1ʳᵉ ligne ci-dessous (ou le chronométrer à la main, du choix de la photo au message).
5. Recommencer pour les 4 autres photos. Noter les visages et plaques visibles et ceux floutés.
6. Mode avion, une 6ᵉ photo : le masquage doit marcher sans réseau.

Temps exact affiché : sur le PC, `chrome://inspect` → le téléphone → console :
`document.querySelector('.mask-status').dataset.ms` après chaque photo.

## Résultats (à remplir)

| | Valeur |
|---|---|
| Téléphone (modèle, mémoire, année) | |
| Durée de la première installation | |
| Espace occupé par Chrome après installation | |
| Photo 1 (première, chargement compris) | s |
| Photos 2 à 5 (médiane) | s |
| Photo 6 hors ligne : masquage fait ? | oui / non |
| Visages visibles / floutés sur les 6 photos | / |
| Plaques visibles / floutées sur les 6 photos | / |
| Remarques (chaleur, lenteur de l'écran, plantage) | |

Si une photo dépasse 4 s (hors la première), noter le modèle et envoyer le résultat : réglages possibles sans
toucher au rappel mesuré → image de travail 1024 px au lieu de 1280, ou moins de tuiles.
