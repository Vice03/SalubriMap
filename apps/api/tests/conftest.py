# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test fixtures: a real PostGIS database (SALUBRI_TEST_DATABASE_URL), a small synthetic commune, an API client.

Run inside Docker with `make test-api`, or locally against any PostGIS:
    SALUBRI_TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/salubri_test pytest
"""

import io
import os
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

os.environ["SALUBRI_DATABASE_URL"] = os.environ.get(
    "SALUBRI_TEST_DATABASE_URL", "postgresql+psycopg://salubri:salubri@localhost:5432/salubri_test"
)
os.environ.setdefault("SALUBRI_PHOTOS_DIR", tempfile.mkdtemp(prefix="salubri-photos-"))
os.environ["SALUBRI_AUTO_RECOMPUTE"] = "false"
os.environ["SALUBRI_OSRM_URL"] = ""
os.environ["SALUBRI_OSRM_RAIN_URL"] = ""
os.environ["SALUBRI_COMMUNE"] = "testville"
os.environ["SALUBRI_ADMIN_TOKEN"] = "test-token"
os.environ["SALUBRI_DEMO_MODE"] = "true"  # comme docker-compose.yml ; le mode production est testé à part
os.environ["SALUBRI_RESUME_ON_STARTUP"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from shapely.geometry import MultiPolygon, Point, Polygon, box  # noqa: E402
from sqlalchemy import text  # noqa: E402

from salubri_api.db import get_engine, get_sessionmaker  # noqa: E402
from salubri_api.models import Base, Commune, Quartier, Scenario, Vehicle  # noqa: E402
from salubri_api.seed.load_commune import insert_world  # noqa: E402
from salubri_api.seed.synthetic import M_LAT, build_world, m_lon, synthetic_photo  # noqa: E402
from salubri_api.services.geo import to_wkb  # noqa: E402
from salubri_api.services.ilots import rebuild_ilots  # noqa: E402
from salubri_api.services.params import ScenarioParams, ValidationThresholds  # noqa: E402
from salubri_api.services.plan.pipeline import reset_cache  # noqa: E402

BBOX = (-1.56, 12.33, -1.50, 12.38)
Q1 = Polygon([(-1.555, 12.335), (-1.530, 12.335), (-1.530, 12.375), (-1.555, 12.375)])
Q2 = Polygon([(-1.530, 12.335), (-1.505, 12.335), (-1.505, 12.375), (-1.530, 12.375)])
DEPOT = (-1.52, 12.39)
NOW = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def _module_models() -> None:
    """Tables des modules optionnels (salubri_api/modules/*/models.py) dans le schéma de test, qu'on lance leurs
    tests ou non : sinon une table d'un module restée d'un passage précédent empêche de vider la base."""
    import importlib
    from pathlib import Path

    import salubri_api

    for f in sorted((Path(salubri_api.__file__).parent / "modules").glob("*/models.py")):
        importlib.import_module(f"salubri_api.modules.{f.parent.name}.models")


_module_models()


@pytest.fixture(scope="session", autouse=True)
def schema() -> Iterator[None]:
    eng = get_engine()
    with eng.begin() as c:
        c.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield


@pytest.fixture(scope="session")
def world():  # type: ignore[no-untyped-def]
    return build_world(BBOX, [("Q1", Q1, 9000), ("Q2", Q2, 9000)], seed=3)


@pytest.fixture()
def db(world) -> Iterator[object]:  # type: ignore[no-untyped-def]
    # attendre les recalculs en arrière-plan du test précédent : sinon ils bloquent le TRUNCATE (verrous)
    from salubri_api.services import background
    from salubri_api.services.plan.trigger import cancel_all
    from salubri_api.services.ratelimit import login_failures

    cancel_all()
    background.drain(60)
    login_failures.reset()  # compteurs anti-force brute : propres à chaque test
    eng = get_engine()
    with eng.begin() as c:
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        c.execute(text(f"TRUNCATE {tables} CASCADE"))
    reset_cache()
    s = get_sessionmaker()()
    params = ScenarioParams(vrp_time_limit_s=0.5).model_dump(mode="json")
    params.pop("active_quartier_ids")
    params["validation"] = ValidationThresholds().model_dump()
    c = Commune(
        slug="testville",
        name="Testville",
        bbox=to_wkb(box(*BBOX)),
        depot_geom=to_wkb(Point(*DEPOT)),
        params_default=params,
    )
    s.add(c)
    s.flush()
    for name, poly in (("Q1", Q1), ("Q2", Q2)):
        s.add(Quartier(commune_id=c.id, name=name, population=9000, geom=to_wkb(MultiPolygon([poly]))))
    s.flush()
    insert_world(s, c.id, world, True, True, True)
    for q in s.query(Quartier).all():
        rebuild_ilots(s, q)
    sc = Scenario(
        commune_id=c.id,
        name="Base",
        is_baseline=True,
        params=ScenarioParams(vrp_time_limit_s=0.5).model_dump(mode="json"),
    )
    s.add(sc)
    s.flush()
    for i, cap in enumerate([8, 8, 8, 12], start=1):
        s.add(
            Vehicle(
                scenario_id=sc.id,
                label=f"T-{i:02d}",
                kind="truck",
                capacity_t=cap,
                cost_per_km=450,
                fixed_cost_day=20000,
            )
        )
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def client(db) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    from salubri_api.main import app

    with TestClient(app, headers={"X-Salubri-Token": "test-token"}) as c:
        yield c


@pytest.fixture()
def anon(db) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    """Client sans identifiant : un citoyen ou un visiteur."""
    from salubri_api.main import app

    with TestClient(app) as c:
        yield c


def free_point(world, poly: Polygon = Q1, n: int = 0) -> tuple[float, float]:  # type: ignore[no-untyped-def]
    """A deterministic point inside `poly`, away from buildings, roads-free not required, away from water."""
    from shapely.ops import unary_union

    blds = unary_union([box(*b).buffer(5 * M_LAT) for b in world.buildings])
    wet = unary_union([w[0].buffer(30 * M_LAT) for w in world.water])
    minx, miny, maxx, maxy = poly.bounds
    k = 0
    for i in range(200):
        for j in range(200):
            p = Point(minx + (maxx - minx) * (i + 0.5) / 200, miny + (maxy - miny) * (j + 0.5) / 200)
            if poly.contains(p) and not blds.contains(p) and not wet.contains(p):
                if k == n:
                    return (round(p.x, 6) + 0.0000004, round(p.y, 6) + 0.0000003)
                k += 1
    raise RuntimeError("no free point")


def offset(lonlat: tuple[float, float], dx_m: float, dy_m: float) -> tuple[float, float]:
    lon, lat = lonlat
    return (lon + dx_m * m_lon(lat), lat + dy_m * M_LAT)


def jpeg(seed: int, **kw) -> bytes:  # type: ignore[no-untyped-def]
    return synthetic_photo(seed, **kw)


def png_small() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (120, 90), (120, 80, 40)).save(buf, "PNG")
    return buf.getvalue()


def post_report(
    client: TestClient, lonlat: tuple[float, float], photo: bytes | None = None, at: datetime | None = None, **fields
) -> dict:  # type: ignore[no-untyped-def,type-arg]
    data = {
        "lon": str(lonlat[0]),
        "lat": str(lonlat[1]),
        "waste_type": fields.pop("waste_type", "household"),
        "volume_class": fields.pop("volume_class", "cart"),
        "accuracy": str(fields.pop("accuracy", 8)),
        "reported_at": (at or NOW).isoformat(),
        "device_id": fields.pop("device_id", "dev-1"),
    }
    data.update({k: str(v) for k, v in fields.items()})
    files = {"photo": ("p.jpg", photo, "image/jpeg")} if photo is not None else None
    r = client.post("/api/reports", data=data, files=files)
    assert r.status_code in (200, 201), r.text
    return r.json()  # type: ignore[no-any-return]


@pytest.fixture()
def hours():  # type: ignore[no-untyped-def]
    return lambda h: NOW + timedelta(hours=h)
