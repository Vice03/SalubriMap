# SPDX-License-Identifier: AGPL-3.0-or-later
"""Jeu d'import inédit (data/rehearsal/jeu_inedit) : accepté avec un rapport clair ou refusé ligne par ligne."""

import json

from salubri_api.config import REPO_ROOT

DIR = REPO_ROOT / "data" / "rehearsal" / "jeu_inedit"


def post(client, name: str, dry: bool = False):  # type: ignore[no-untyped-def]
    r = client.post(
        "/api/imports", data={"dry_run": str(dry).lower()}, files={"file": (name, (DIR / name).read_bytes())}
    )
    assert r.status_code == 200, r.text
    return r.json()


def rejected(body):  # type: ignore[no-untyped-def]
    return {row["row"]: " ".join(row["errors"]) for row in body["report"] if row["status"] == "rejected"}


def test_autres_noms_de_colonnes(client) -> None:  # type: ignore[no-untyped-def]
    body = post(client, "1_colonnes_autres.csv")
    assert body["accepted"] == 3 and body["rejected"] == 0
    col = body["colonnes"]
    assert col["Latitude_DD"] == "lat" and col["Longitude_DD"] == "lon"
    assert col["Catégorie de déchets"] == "waste_type" and col["Quantité estimée"] == "volume_class"
    assert col["Date du signalement"] == "reported_at" and col["Code"] == "external_id"
    assert col["Agent"] is None  # colonne ignorée, dite comme telle
    reports = client.get("/api/reports", params={"limit": 50}).json()
    feats = reports["features"] if isinstance(reports, dict) else reports
    assert any("Gravats" in json.dumps(f, ensure_ascii=False) or "rubble" in json.dumps(f) for f in feats)


def test_autre_systeme_de_coordonnees(client) -> None:  # type: ignore[no-untyped-def]
    body = post(client, "2_utm30n.geojson", dry=True)
    assert body["accepted"] == 3, body["report"]
    assert "EPSG:32630" in body["crs"] and "WGS 84" in body["crs"]


def test_coordonnees_en_metres_sans_crs_devinees_ou_refusees(client) -> None:  # type: ignore[no-untyped-def]
    fc = json.loads((DIR / "2_utm30n.geojson").read_text("utf-8"))
    del fc["crs"]
    r = client.post("/api/imports", data={"dry_run": "true"}, files={"file": ("m.geojson", json.dumps(fc).encode())})
    assert r.status_code == 200 and "deviné" in r.json()["crs"] and r.json()["accepted"] == 3
    for f in fc["features"]:
        f["geometry"]["coordinates"] = [5e6, 9e6]  # nulle part près de la commune
    r = client.post("/api/imports", data={"dry_run": "true"}, files={"file": ("m.geojson", json.dumps(fc).encode())})
    assert r.status_code == 422 and "convertir le fichier en WGS 84" in r.json()["detail"]
    fc["crs"] = {"type": "name", "properties": {"name": "EPSG:999999"}}
    r = client.post("/api/imports", data={"dry_run": "true"}, files={"file": ("m.geojson", json.dumps(fc).encode())})
    assert r.status_code == 422 and "inconnu" in r.json()["detail"]


def test_champs_manquants(client) -> None:  # type: ignore[no-untyped-def]
    body = post(client, "3_champs_manquants.csv", dry=True)
    rej = rejected(body)
    assert set(rej) == {2, 3}
    assert "Coordonnées manquantes" in rej[2] and "Date invalide" in rej[3]
    warn = {row["row"]: " ".join(row["warnings"]) for row in body["report"]}
    assert "inconnu" in warn[4]


def test_doublons_dans_le_fichier_et_deja_importes(client) -> None:  # type: ignore[no-untyped-def]
    body = post(client, "4_doublons.geojson")
    rej = rejected(body)
    assert body["accepted"] == 3 and set(rej) == {2, 4}
    assert "Doublon de la ligne 1" in rej[2] and "Doublon de la ligne 3" in rej[4]
    again = post(client, "4_doublons.geojson", dry=True)
    assert "Déjà importé" in rejected(again)[1] and "Déjà importé" in rejected(again)[5]


def test_points_hors_de_la_commune(client) -> None:  # type: ignore[no-untyped-def]
    """Enregistrés puis rejetés par R5 (comme un signalement de Salubri Go), avec la distance dans le rapport."""
    body = post(client, "5_hors_commune.csv", dry=True)
    rows = {row["row"]: row for row in body["report"]}
    assert rows[1]["report_status"] != "rejected" and not rows[1]["warnings"]
    for i in (2, 3, 4):
        assert rows[i]["report_status"] == "rejected"
        assert any(h["rule"] == "R5" for h in rows[i]["rule_hits"])
        assert any("Hors de la commune : à" in w and " km " in w for w in rows[i]["warnings"])


def test_photos_manquantes_ou_renommees(client) -> None:  # type: ignore[no-untyped-def]
    """Archive dont les photos ont été renommées (casse, extension, chemin Windows) ou oubliées : les lignes entrent,
    la photo retrouvée est dite sous quel nom, la photo absente est signalée, rien n'est deviné en cas de doute."""
    body = post(client, "6_photos_renommees.zip")
    assert body["accepted"] == 5 and body["rejected"] == 0, body["report"]
    warn = {row["row"]: " ".join(row["warnings"]) for row in body["report"]}
    assert warn[1] == ""  # même nom
    assert "trouvée dans l'archive sous le nom « img_0002.jpeg »" in warn[2]
    assert warn[3] == ""  # chemin Windows (C:\\Users\\…) ignoré : même nom de fichier
    assert "« IMG_0004.jpg » absente de l'archive" in warn[4]
    assert warn[5] == ""  # pas de photo déclarée : rien à dire
    reports = client.get("/api/reports", params={"limit": 100}).json()
    feats = reports["features"] if isinstance(reports, dict) else reports
    with_photo = {f["properties"].get("external_id"): bool(f["properties"].get("photo_url")) for f in feats}
    assert {k: with_photo.get(k) for k in ("PH-1", "PH-2", "PH-3", "PH-4")} == {
        "PH-1": True, "PH-2": True, "PH-3": True, "PH-4": False}  # fmt: skip


def test_photo_ambigue_non_devinee() -> None:
    from salubri_api.services.importers.common import _photo

    data, msg = _photo("IMG_9.JPG", {"img_9.jpeg": b"a", "IMG_9.png": b"b"})
    assert data is None and "ambiguë" in (msg or "")
