<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Contribuer à OpenStreetMap — plan

Ce qui est proposé à OSM, comment, et ce qui ne l'est **jamais**. Complète `docs/OSM.md` (procédure JOSM pas à
pas). Rien n'est versé avant l'accord de la communauté OSM du Burkina Faso.

Sources consultées (novembre 2026) : wiki OSM
[Tag:amenity=waste_dump_site](https://wiki.openstreetmap.org/wiki/Tag:amenity=waste_dump_site),
[Tag:landuse=landfill](https://wiki.openstreetmap.org/wiki/Tag:landuse=landfill) (« unofficial dumping grounds » :
`informal=yes`), [Import/Guidelines](https://wiki.openstreetmap.org/wiki/Import/Guidelines), et la discussion du
[changeset 77744814](https://www.openstreetmap.org/changeset/77744814) (usage local de `waste_dump_site` à Accra).

## 1. Ce que l'on verse

| Objet | Étiquettes | Condition |
|---|---|---|
| Dépotoir sauvage vu par l'équipe | `amenity=waste_dump_site` (« endroit où des déchets ont été jetés illégalement », statut *in use* sur le wiki OSM), `waste=*`, `survey:date`, `source=survey`, `description` | signalement de l'équipe (collecte du § 2 de `COLLECTE_TERRAIN.md`), vérifié sur place, pas déjà dans OSM |
| Point de regroupement **existant** (bac, CCT) relevé sur place | `amenity=waste_disposal` (bac) ou `amenity=waste_transfer_station` (centre de collecte et de transit) | objet réel vu sur place ; jamais un point **proposé** par le plan |

Alternative discutée sur le wiki pour les grandes décharges informelles : `landuse=landfill` + `informal=yes`.
On demandera à la communauté laquelle elle préfère pour Ouagadougou ; par défaut `amenity=waste_dump_site`,
déjà utilisé en Afrique de l'Ouest (Accra).

## 2. Ce qui n'est jamais versé

- Signalements de citoyens non vérifiés sur place par l'équipe ; signalements importés.
- Points de regroupement et tournées **calculés** par Salubri (ce sont des propositions, pas des objets réels).
- Toute donnée personnelle : identifiant de téléphone, commentaire, photo, score détaillé.
- Les étiquettes internes `salubri:id` et `salubri:confidence` sont retirées avant envoi si la communauté les juge
  inutiles (elles servent seulement à éviter les doublons lors d'un second versement).

## 3. Licence

Nos relevés sont publiés sous ODbL (`data/communes/ouagadougou/LICENCE_signalements_equipe.md`), compatible avec
OSM ; l'équipe en est l'auteur (relevé sur place), donc peut les verser sous les *Contributor Terms* d'OSM. Aucune
donnée d'une autre source (Open Buildings, mairie) n'est versée.

## 4. Démarche (lignes directrices des imports OSM)

Même pour ~50 points, on suit les lignes directrices d'import du wiki OSM : discussion avec la communauté locale
et sur le forum OSM **avant** tout envoi, page de documentation, compte dédié, sinon le compte risque d'être
bloqué par le *Data Working Group*.

1. **Contact** : message sur le forum OSM (catégorie Burkina Faso / Afrique de l'Ouest francophone) et à
   OSM Burkina Faso, avec : objectif, nombre de points, étiquettes, échantillon `.osc`, carte des points.
2. **Page wiki** `Import/Salubri Ouagadougou` : source, licence, étiquettes, volume, compte, calendrier,
   processus de contrôle.
3. **Attendre** au moins deux semaines et les retours ; adapter les étiquettes.
4. **Compte dédié** `salubri_import_ouaga`, dont la page renvoie au compte principal d'un membre et à la page wiki.
5. **Revue dans JOSM** (`docs/OSM.md`) : conflation à 50 m avec `amenity=waste_dump_site`,
   `amenity=waste_disposal` et `landuse=landfill` existants, validateur JOSM sans erreur.
6. **Envoi** en un seul changeset, commentaire « Salubri : dépotoirs sauvages relevés sur place, Ouagadougou »,
   `source=survey`, `import=yes`.
7. **Suivi** : identifiants OSM reportés (`PATCH /api/dump-sites/{id}` `{"osm_id": …}`) ; un dépotoir nettoyé
   est retiré d'OSM par un changeset dédié.

## 5. Étiquettes du changeset

`comment=Salubri : dépotoirs sauvages relevés sur place, Ouagadougou` · `source=survey` · `import=yes` ·
`created_by=JOSM` (automatique) · `url=https://wiki.openstreetmap.org/wiki/Import/Salubri_Ouagadougou` ·
`hashtags=#Salubri;#Ouagadougou`.

## 6. Brouillon de message (forum OSM Burkina Faso, puis liste/forum des imports)

> **Objet : Proposition — relevé de dépotoirs sauvages à Ouagadougou (≈ 50 points, ODbL)**
>
> Bonjour à toutes et à tous,
>
> Nous sommes une équipe d'étudiants de l'ISGE-BF (Hackathon des universités 2026, défi « Assainissement de
> Ouaga »). Nous avons relevé sur place, avec l'application libre Salubri, environ 50 dépotoirs sauvages dans
> l'arrondissement ___. Chaque point a été vu par un membre de l'équipe et vérifié par un second.
>
> Nous aimerions les ajouter à OpenStreetMap comme nœuds `amenity=waste_dump_site` avec `waste=*`,
> `survey:date=*` et `source=survey`, et les bacs ou centres de collecte existants vus sur place comme
> `amenity=waste_disposal` / `amenity=waste_transfer_station`. Aucune photo ni donnée personnelle.
>
> - Échantillon (.osc) et carte : [lien]
> - Documentation : https://wiki.openstreetmap.org/wiki/Import/Salubri_Ouagadougou
> - Compte dédié : `salubri_import_ouaga` ; revue dans JOSM, conflation à 50 m avec l'existant.
>
> Ces étiquettes vous conviennent-elles, ou préférez-vous `landuse=landfill` + `informal=yes` pour les grands
> dépôts ? Faut-il retirer les dépotoirs une fois nettoyés ? Nous attendrons vos retours (au moins deux
> semaines) avant tout envoi.
>
> Merci, l'équipe Salubri — [contact]

## 7. Export d'essai

`GET /api/export/osc` (nouveau) produit un fichier *osmChange* avec les seuls dépotoirs vérifiés **pas encore
versés** (nœuds à identifiants négatifs, dans `<create>`). Essai : `docs/osm/salubri_essai.osc`, produit le
17/11/2026 sur la base de démonstration (195 nœuds, XML valide, aucune donnée personnelle). **Ce fichier vient de
données de démonstration : il ne doit jamais être téléversé.** Le vrai fichier sera produit après la collecte
de terrain, à partir des seuls signalements de l'équipe.
