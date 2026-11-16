# SPDX-License-Identifier: AGPL-3.0-or-later
"""Photo analysis: hashes, EXIF and a cheap "is this informative" measure."""

import hashlib
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import imagehash
import numpy as np
from PIL import ExifTags, Image, ImageOps

GPS_TAG = 34853
EXIF_IFD = 34665
DATETIME_ORIGINAL = 36867


@dataclass(frozen=True)
class PhotoInfo:
    sha256: str
    phash: str  # 16 hex chars = 64 bits
    width: int
    height: int
    bytes: int
    exif_lat: float | None
    exif_lon: float | None
    exif_taken_at: datetime | None
    luminance_var: float

    @property
    def bands(self) -> tuple[str, str, str, str]:
        return (self.phash[0:4], self.phash[4:8], self.phash[8:12], self.phash[12:16])


def _ratio(v: object) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        num, den = v  # type: ignore[misc]
        return float(num) / float(den)


def _gps_to_deg(values: object, ref: str) -> float:
    d, m, s = (_ratio(x) for x in values)  # type: ignore[union-attr]
    deg = d + m / 60 + s / 3600
    return -deg if ref in ("S", "W") else deg


def _exif(img: Image.Image) -> tuple[float | None, float | None, datetime | None]:
    lat = lon = None
    taken: datetime | None = None
    try:
        exif = img.getexif()
    except Exception:
        return None, None, None
    try:
        gps = exif.get_ifd(GPS_TAG)
        if gps and 2 in gps and 4 in gps:
            lat = _gps_to_deg(gps[2], str(gps.get(1, "N")))
            lon = _gps_to_deg(gps[4], str(gps.get(3, "E")))
    except Exception:
        lat = lon = None
    try:
        sub = exif.get_ifd(EXIF_IFD)
        raw = sub.get(DATETIME_ORIGINAL) or exif.get(ExifTags.Base.DateTime)
        if raw:
            taken = datetime.strptime(str(raw).strip("\x00"), "%Y:%m:%d %H:%M:%S").replace(tzinfo=UTC)
    except Exception:
        taken = None
    return lat, lon, taken


def analyze(data: bytes) -> PhotoInfo:
    """Raise ValueError if the bytes are not a readable image."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise ValueError("Fichier image illisible") from exc
    lat, lon, taken = _exif(img)
    upright = ImageOps.exif_transpose(img).convert("RGB")
    grey = np.asarray(upright.convert("L").resize((64, 64)), dtype=np.float64)
    return PhotoInfo(
        sha256=hashlib.sha256(data).hexdigest(),
        phash=str(imagehash.phash(upright)),
        width=upright.width,
        height=upright.height,
        bytes=len(data),
        exif_lat=lat,
        exif_lon=lon,
        exif_taken_at=taken,
        luminance_var=float(grey.var()),
    )


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def store(data: bytes, info: PhotoInfo, photos_dir: Path) -> str:
    """Save once per content hash; return the relative path served under /photos/."""
    photos_dir.mkdir(parents=True, exist_ok=True)
    name = f"{info.sha256[:32]}.jpg"
    target = photos_dir / name
    if not target.exists():
        target.write_bytes(data)
    return name


@lru_cache(maxsize=256)
def _public_jpeg(path: str, mtime: float) -> bytes:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)  # nouvel encodage : aucune métadonnée EXIF (GPS, appareil, date)
        return buf.getvalue()


def public_jpeg(path: Path) -> bytes:
    """Copie publique d'une photo, sans EXIF (lot A4). Mise en cache par chemin et date de modification."""
    return _public_jpeg(str(path), path.stat().st_mtime)
