# SPDX-License-Identifier: AGPL-3.0-or-later
import os

import pytest
from playwright.sync_api import sync_playwright

BASE = os.environ.get("SALUBRI_URL", "http://localhost").rstrip("/")


@pytest.fixture(scope="session")
def browser():  # type: ignore[no-untyped-def]
    with sync_playwright() as p:
        exe = os.environ.get("SALUBRI_CHROME")
        b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe else p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def base() -> str:
    return BASE
