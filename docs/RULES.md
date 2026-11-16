# Règles de validation R1–R12

Chaque signalement démarre à **100 points**. Les règles retirent des points ; certaines rejettent d'office. Les seuils sont dans `data/communes/<commune>/params_default.json` (clé `validation`) et la liste est servie par `GET /api/validation/rules`.

| Règle | Piège | Condition | Pénalité |
|---|---|---|---|
| R1 | Doublon | même type à ≤ 30 m : même appareil sous 72 h, ou autre appareil sous 1 h | −40 |
| R2 | Photo réutilisée | SHA-256 identique / pHash à distance de Hamming ≤ 8 | −70 / −50 |
| R3 | Photo prise ailleurs | GPS EXIF à > 500 m du point déclaré | −30 |
| R4 | Photo ancienne | date EXIF à > 30 jours | −20 |
| R5 | Hors commune | hors des quartiers + 500 m | rejet |
| R6 | Dans un bâtiment | bâtiment Open Buildings (confiance ≥ 0,7) ≥ 40 m² / ≥ 200 m² | −35 / −50 |
| R7 | Dans l'eau | plan d'eau / à ≤ 8 m d'un cours d'eau / plan d'eau > 1 ha | −45 / −45 / rejet |
| R8 | GPS suspect | (0,0) ou hors plage / même point au mètre qu'un autre appareil / ≤ 3 décimales / précision > 150 m | rejet / −40 / −25 / −15 |
| R9 | Déplacement impossible | même appareil, > 120 km/h depuis le signalement précédent | −40 |
| R10 | Rafale | ≥ 10 envois de l'appareil dans l'heure (appareil bridé 1 h) / même commentaire 5 fois en 24 h | −30 |
| R11 | Photo inexploitable | variance de luminance < 25 ou côté < 200 px | −20 |
| R12 | Description incohérente | volume « camion » avec photo < 50 Ko / biomédical à > 300 m d'un établissement de santé | −10 |

**Statuts** : rejet d'office ou score < 40 → `rejected` ; 40–69 → `to_review` ; ≥ 70 → `probable`. Un signalement `probable` devient `verified` quand un modérateur le confirme, ou quand **deux appareils différents**, à **plus d'une heure d'écart**, signalent le même type à moins de 30 m (corroboration indépendante). Seuls les signalements vérifiés alimentent les dépotoirs et le plan.

**Ordre et stabilité** : seuls les signalements *antérieurs* comptent comme preuves (doublon, photo, coordonnées copiées), donc revalider un signalement donne le même verdict qu'à son arrivée. Un import est validé dans l'ordre chronologique des `reported_at`.

**Ce qui n'est pas détecté automatiquement** (à dire honnêtement au jury) : photo générée par IA, photo d'un autre dépotoir réel de la ville prise le même jour, faux GPS cohérent et lent. Le modérateur voit le score, la photo et l'historique de l'appareil.
