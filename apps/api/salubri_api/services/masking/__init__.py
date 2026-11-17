# SPDX-License-Identifier: AGPL-3.0-or-later
"""Masquage des visages et des plaques côté serveur (filet de sécurité, docs/MASQUAGE.md).

Mêmes modèles ONNX et même pixellisation que Salubri Go (apps/go/src/masking/) : une photo qui arrive non
masquée (ancienne version de l'application, import ZIP, outil tiers) est masquée avant d'être enregistrée.
"""

from salubri_api.services.masking.detector import Box, MaskingUnavailable, detect, pixelate

__all__ = ["Box", "MaskingUnavailable", "detect", "pixelate"]
