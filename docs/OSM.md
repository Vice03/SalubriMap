# Verser la carte des dépotoirs dans OpenStreetMap

1. Présenter le projet à la communauté OSM Burkina Faso **avant** tout versement (page wiki `Import/Salubri Ouagadougou` : source, licence, étiquettes, volume, compte dédié, calendrier).
2. `GET /api/export/osm?since=<date du dernier versement>` → `salubri-depotoirs.osm` (nœuds à identifiants négatifs).
3. Ouvrir dans JOSM avec les données OSM de la zone ; vérifier qu'aucun `amenity=waste_dump_site` ou `landuse=landfill` n'existe à moins de 50 m (sinon mettre à jour l'objet existant) ; lancer le validateur.
4. Téléverser par lots de 200 objets au plus avec un compte dédié (`salubri_import`), commentaire « Salubri : dépotoirs sauvages vérifiés, Ouagadougou », `source=Salubri;survey`, `import=yes`.
5. Reporter l'identifiant OSM obtenu : `PATCH /api/dump-sites/{id}` `{"osm_id": 123456}`.
6. Un dépotoir nettoyé est **retiré** d'OSM (changeset dédié), pas laissé en place.

## Étiquettes produites

| Clé | Valeur |
|---|---|
| `amenity` | `waste_dump_site` |
| `waste` | `trash`, `plastic`, `rubble`, `organic`, `medical`, `mixed` |
| `description` | « Dépotoir sauvage signalé N fois, volume estimé X m³ » |
| `survey:date` | date du dernier signalement vérifié |
| `source` | `Salubri;survey` |
| `salubri:id` | identifiant Salubri (conflation future) |
| `salubri:confidence` | score moyen |

Jamais exporté : identifiant d'appareil, commentaire libre, photo, signalement non vérifié, point de regroupement simulé. Les signalements Salubri sont publiés sous CC0 ; les données dérivées d'OSM restent sous ODbL.
