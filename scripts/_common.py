# SPDX-License-Identifier: AGPL-3.0-or-later
"""Make the API package importable from scripts/ (repository checkout or inside the api container)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "apps" / "api").exists():
    sys.path.insert(0, str(ROOT / "apps" / "api"))
DATA = Path(os.environ.get("SALUBRI_DATA_DIR", ROOT / "data"))
