# SPDX-License-Identifier: AGPL-3.0-or-later
"""Détection des visages (YuNet 2023mar) et des plaques (YOLOv9-t 384 end2end), onnxruntime CPU.

Décodage identique à apps/go/src/masking/geometry.ts (testé des deux côtés sur la même image).
"""

import logging
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from salubri_api.config import get_settings

log = logging.getLogger("salubri.masquage")

FACE_SIZE, PLATE_SIZE = 640, 384
FACE_THRESHOLD, PLATE_THRESHOLD = 0.6, 0.25  # défauts de cv2.FaceDetectorYN et d'open-image-models
FACE_FILE, PLATE_FILE = "visages-yunet-2023mar.onnx", "plaques-yolov9t-384.onnx"
CELLS, MARGIN = 6, 0.2  # comme apps/go/src/masking/blur.ts


class MaskingUnavailable(RuntimeError):
    """Modèles absents ou illisibles : aucune photo n'est enregistrée sans masquage."""


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float
    kind: str  # « visage » | « plaque »
    score: float


_lock = threading.Lock()


@lru_cache(maxsize=1)
def _sessions(models_dir: str):  # type: ignore[no-untyped-def]
    import onnxruntime as ort

    d = Path(models_dir)
    if not (d / FACE_FILE).is_file() or not (d / PLATE_FILE).is_file():
        raise MaskingUnavailable(f"Modèles de masquage introuvables dans {d}")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    try:
        face = ort.InferenceSession(str(d / FACE_FILE), opts, providers=["CPUExecutionProvider"])
        plate = ort.InferenceSession(str(d / PLATE_FILE), opts, providers=["CPUExecutionProvider"])
    except Exception as exc:  # fichier tronqué, mauvaise version…
        raise MaskingUnavailable(f"Modèles de masquage illisibles : {exc}") from exc
    log.info("modèles de masquage chargés depuis %s", d)
    return face, plate


def available() -> bool:
    try:
        _sessions(str(get_settings().masking_models_dir))
        return True
    except MaskingUnavailable:
        return False


def _square(img: Image.Image, size: int, fill: tuple[int, int, int]) -> tuple[np.ndarray, float]:
    """Image dans un carré size×size, coin haut-gauche, reste rempli (comme le canvas du téléphone)."""
    ratio = min(size / img.width, size / img.height)
    w, h = round(img.width * ratio), round(img.height * ratio)
    canvas = Image.new("RGB", (size, size), fill)
    canvas.paste(img.resize((w, h), Image.BILINEAR), (0, 0))
    return np.asarray(canvas, dtype=np.float32), ratio


def _nms(boxes: list[Box], iou_max: float) -> list[Box]:
    keep: list[Box] = []
    for b in sorted(boxes, key=lambda b: -b.score):
        if all(_iou(k, b) <= iou_max for k in keep):
            keep.append(b)
    return keep


def _iou(a: Box, b: Box) -> float:
    x1, y1 = max(a.x, b.x), max(a.y, b.y)
    x2, y2 = min(a.x + a.w, b.x + b.w), min(a.y + a.h, b.y + b.h)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


def detect(img: Image.Image) -> list[Box]:
    """Visages et plaques d'une image RGB déjà redressée ; coordonnées dans cette image."""
    face_s, plate_s = _sessions(str(get_settings().masking_models_dir))
    rgb, r = _square(img, FACE_SIZE, (0, 0, 0))
    blob = rgb[:, :, ::-1].transpose(2, 0, 1)[None].copy()  # BGR 0–255
    with _lock:
        out = dict(zip([o.name for o in face_s.get_outputs()], face_s.run(None, {"input": blob}), strict=True))
    faces: list[Box] = []
    for s in (8, 16, 32):
        n = FACE_SIZE // s
        cls = np.clip(out[f"cls_{s}"][0, :, 0], 0, 1)
        obj = np.clip(out[f"obj_{s}"][0, :, 0], 0, 1)
        bb = out[f"bbox_{s}"][0]
        score = np.sqrt(cls * obj)
        for i in np.where(score >= FACE_THRESHOLD)[0]:
            row, col = divmod(int(i), n)
            cx, cy = (col + bb[i, 0]) * s, (row + bb[i, 1]) * s
            w, h = float(np.exp(bb[i, 2]) * s), float(np.exp(bb[i, 3]) * s)
            faces.append(Box((cx - w / 2) / r, (cy - h / 2) / r, w / r, h / r, "visage", float(score[i])))
    boxes = _nms(faces, 0.3)

    rgb, r = _square(img, PLATE_SIZE, (114, 114, 114))
    blob = (rgb / 255.0).transpose(2, 0, 1)[None].astype(np.float32)  # RGB 0–1
    with _lock:
        pred = plate_s.run(None, {"images": blob})[0]
    for p in pred:
        if p[6] >= PLATE_THRESHOLD:
            x1, y1 = p[1] / r, p[2] / r
            boxes.append(Box(float(x1), float(y1), float(p[3] / r - x1), float(p[4] / r - y1), "plaque", float(p[6])))
    return boxes


def pixelate(arr: np.ndarray, boxes: list[Box], margin: float = MARGIN) -> int:
    """En place sur un tableau H×W×3 : chaque zone (+20 %) devient au plus 6×6 aplats de sa couleur moyenne."""
    hgt, wid = arr.shape[:2]
    done = 0
    for b in boxes:
        mx, my = b.w * margin, b.h * margin
        x0, y0 = max(0, int(np.floor(b.x - mx))), max(0, int(np.floor(b.y - my)))
        x1, y1 = min(wid, int(np.ceil(b.x + b.w + mx))), min(hgt, int(np.ceil(b.y + b.h + my)))
        if x1 - x0 < 1 or y1 - y0 < 1:
            continue
        cell = max(2, int(np.ceil(max(x1 - x0, y1 - y0) / CELLS)))
        for cy in range(y0, y1, cell):
            for cx in range(x0, x1, cell):
                blk = arr[cy : min(cy + cell, y1), cx : min(cx + cell, x1)]
                blk[...] = np.round(blk.reshape(-1, blk.shape[-1]).mean(axis=0)).astype(arr.dtype)
        done += 1
    return done
