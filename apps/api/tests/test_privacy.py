# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot A4 : le public ne voit que les signalements vérifiés ou nettoyés, sans donnée personnelle."""

import io

from PIL import Image
from test_accounts import bearer, make_user

from conftest import free_point, jpeg, post_report
from salubri_api.models import Report

PERSONAL = ("device_id", "comment", "external_id", "moderated_by", "received_at", "gps_accuracy_m", "rule_hits")


def _seed(db, anon, world):  # type: ignore[no-untyped-def]
    """Un signalement vérifié (forcé par un modérateur), un probable, un rejeté — tous avec photo et commentaire."""
    make_user(db, "awa", "moderateur")
    mod = bearer(anon, "awa")
    ids = {}
    for n, key in ((40, "verified"), (41, "probable")):
        ids[key] = post_report(
            anon, free_point(world, n=n), jpeg(n), device_id=f"tel-{n}", comment="appeler Awa au 70 00 00 00"
        )["id"]
    ids["rejected"] = post_report(anon, (-4.29, 11.17), jpeg(42), device_id="tel-42", comment="hors zone")["id"]
    assert anon.patch(f"/api/reports/{ids['verified']}", json={"status": "verified"}, headers=mod).status_code == 200
    db.expire_all()
    assert not {db.get(Report, ids[k]).status for k in ("probable", "rejected")} & {"verified", "cleaned"}
    return ids, mod


def test_anonymous_list_never_shows_unverified_or_personal_data(db, anon, world):  # type: ignore[no-untyped-def]
    ids, mod = _seed(db, anon, world)
    for params in ({}, {"status": "rejected"}, {"status": ["probable", "verified"]}, {"limit": 5000}):
        fc = anon.get("/api/reports", params=params).json()
        assert fc["restricted"] is True
        assert {f["properties"]["status"] for f in fc["features"]} <= {"verified", "cleaned"}
        for f in fc["features"]:
            assert not set(PERSONAL) & set(f["properties"]), f["properties"]
        assert "tel-" not in str(fc) and "70 00" not in str(fc)
    assert [f["id"] for f in anon.get("/api/reports").json()["features"]] == [ids["verified"]]
    assert anon.get("/api/reports", params={"device_id": "tel-40"}).status_code == 403
    # un modérateur voit tout, appareil et commentaire compris
    full = anon.get("/api/reports", headers=mod).json()
    assert full["restricted"] is False and full["total"] == 3
    assert {f["properties"]["device_id"] for f in full["features"]} == {"tel-40", "tel-41", "tel-42"}


def test_anonymous_detail_and_photo(db, anon, world):  # type: ignore[no-untyped-def]
    ids, mod = _seed(db, anon, world)
    assert anon.get(f"/api/reports/{ids['probable']}").status_code == 404
    assert anon.get(f"/api/reports/{ids['rejected']}/photo").status_code == 404
    pub = anon.get(f"/api/reports/{ids['verified']}").json()["properties"]
    assert "photo" not in pub and "device_id" not in pub and "comment" not in pub
    # photo publique : servie sans EXIF ; le modérateur reçoit l'original
    r = anon.get(pub["photo_url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert not Image.open(io.BytesIO(r.content)).getexif()
    staff = anon.get(f"/api/reports/{ids['probable']}/photo", headers=mod)
    assert staff.status_code == 200 and "no-store" in staff.headers["cache-control"]
    assert anon.get(f"/api/reports/{ids['probable']}", headers=mod).json()["properties"]["device_id"] == "tel-41"
    # plus de dossier /photos/ servi en direct
    assert anon.get("/photos/x.jpg").status_code == 404


def test_journal_is_staff_only(db, anon, world):  # type: ignore[no-untyped-def]
    _, mod = _seed(db, anon, world)
    assert anon.get("/api/audit").status_code == 401
    make_user(db, "kader", "admin")
    assert anon.get("/api/audit", headers=bearer(anon, "kader")).status_code == 200
    assert anon.get("/api/audit", headers=mod).status_code == 200


def test_photo_with_gps_exif_is_stripped_for_public(db, anon, world):  # type: ignore[no-untyped-def]
    make_user(db, "awa", "moderateur")
    mod = bearer(anon, "awa")
    raw = jpeg(55)
    im = Image.open(io.BytesIO(raw))
    ex = im.getexif()
    ex[0x010F] = "Fabricant-Secret"  # Make
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=ex)
    rid = post_report(anon, free_point(world, n=43), buf.getvalue(), device_id="tel-55")["id"]
    anon.patch(f"/api/reports/{rid}", json={"status": "verified"}, headers=mod)
    # depuis le lot A5, l'EXIF est retiré dès l'enregistrement : ni le public ni la mairie ne le reçoivent
    assert b"Fabricant-Secret" not in anon.get(f"/api/reports/{rid}/photo", headers=mod).content
    assert b"Fabricant-Secret" not in anon.get(f"/api/reports/{rid}/photo").content
