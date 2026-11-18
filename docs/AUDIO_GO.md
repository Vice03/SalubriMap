# Salubri Go — guide vocal : les fichiers audio

Le guide vocal lit chaque étape à voix haute pour les personnes qui ne lisent pas. **Le français est généré par synthèse vocale** (déjà dans `apps/go/public/audio/fr/`). **Le mooré doit être enregistré par une voix humaine** : 22 fichiers MP3, à déposer dans `apps/go/public/audio/mos/` avec **exactement** les noms ci-dessous.

Tant qu'un fichier mooré manque, l'étape s'affiche quand même (boutons qui brillent à tour de rôle), mais sans voix.

## Consignes d'enregistrement

- Une seule personne pour tous les fichiers, même micro, même distance, même volume (pièce calme, pas d'écho).
- Un fichier = une phrase. **Pas de silence au début (< 0,2 s) ni à la fin (< 0,3 s).**
- Format **MP3, mono, 44,1 ou 22,05 kHz, 64 à 96 kbit/s**. Nom en minuscules, sans accent, extension `.mp3`.
- Durée : les phrases de question ≤ 8 s ; les **choix (`qty_*`, `type_*`) ≤ 3 s** (le bouton brille pendant que le choix est dit).
- Ton clair et posé, comme on parle à quelqu'un qui découvre le téléphone. Les consignes « appuyez sur le bouton qui brille » doivent se dire de la façon la plus naturelle en mooré (la traduction mot à mot n'est pas obligatoire).

## 1. Écran de langue (au lancement)

Le français est lu d'abord (fichier français), puis le mooré (fichier mooré) ; le bouton de chaque langue brille pendant sa phrase.

| Fichier | Ce que la voix doit dire (sens) | Mooré (à compléter) |
|---|---|---|
| `lang_mos.mp3` | « Si vous parlez mooré, appuyez ici. » | |

## 2. Les 21 fichiers du parcours (même liste en mooré)

| N° | Fichier | Ce que la voix doit dire (sens) | Quand | Mooré (à compléter) |
|---|---|---|---|---|
| 1 | `photo_ask.mp3` | « Prenez une photo du dépotoir. Appuyez sur le bouton qui brille. » | Étape photo, le bouton appareil photo brille | |
| 2 | `photo_continue.mp3` | « C'est bien. Appuyez sur le bouton pour continuer. » | La photo est prise, le bouton « continuer » brille | |
| 3 | `qty_ask.mp3` | « Quelle quantité de déchets estimez-vous ? » | Début de l'étape quantité | |
| 4 | `qty_bag.mp3` | « Un sac. » | Le bouton « sac » brille | |
| 5 | `qty_wheelbarrow.mp3` | « Une brouette. » | Le bouton « brouette » brille | |
| 6 | `qty_cart.mp3` | « Une charrette. » | Le bouton « charrette » brille | |
| 7 | `qty_truck.mp3` | « Un camion. » | Le bouton « camion » brille | |
| 8 | `qty_more.mp3` | « Plus qu'un camion. » | Le bouton « plus » brille | |
| 9 | `type_ask.mp3` | « Quel type de déchets voyez-vous ? » | Début de l'étape type | |
| 10 | `type_household.mp3` | « Des ordures ménagères. » | Le bouton correspondant brille | |
| 11 | `type_plastic.mp3` | « Des plastiques. » | idem | |
| 12 | `type_organic.mp3` | « Des déchets organiques (restes de nourriture, feuilles). » | idem | |
| 13 | `type_rubble.mp3` | « Des gravats (briques, béton, terre). » | idem | |
| 14 | `type_medical.mp3` | « Des déchets de soins (seringues, pansements). » | idem | |
| 15 | `type_mixed.mp3` | « Un mélange de tout. » | idem | |
| 16 | `loc_ask.mp3` | « Activez la localisation de votre téléphone, puis appuyez sur le bouton qui brille. » | La localisation n'est pas encore active | |
| 17 | `loc_wait.mp3` | « Patientez, nous cherchons votre position. » | Recherche de la position en cours | |
| 18 | `loc_denied.mp3` | « La localisation est coupée. Autorisez-la dans les réglages du téléphone, puis appuyez sur le bouton. » | La localisation est refusée | |
| 19 | `thanks.mp3` | « Merci pour votre signalement. Il est transmis à la mairie. » | Signalement envoyé | |
| 20 | `thanks_offline.mp3` | « Merci. Il n'y a pas de réseau : votre signalement partira dès que le réseau revient. » | Envoyé sans réseau | |
| 21 | `again.mp3` | « Pour faire un autre signalement, appuyez sur le bouton qui brille. » | Après le merci | |

**Total à fournir en mooré : 22 fichiers** (`lang_mos` + les 21 ci-dessus).

## Où les mettre

```
apps/go/public/audio/mos/lang_mos.mp3
apps/go/public/audio/mos/photo_ask.mp3
… (les 22 fichiers)
```

Puis reconstruire l'application (menu `SALUBRI.bat`, ou une nouvelle version de l'APK). Rien d'autre à modifier : l'application détecte les fichiers présents.

## Français (généré)

Les 22 fichiers français portent les mêmes noms dans `apps/go/public/audio/fr/` (`lang_fr.mp3`, « Si vous parlez français, appuyez ici. », à la place de `lang_mos.mp3`). Le script `scripts/go_audio_fr.py` les régénère à partir des textes ci-dessus.
