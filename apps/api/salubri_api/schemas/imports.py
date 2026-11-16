# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Any, Literal

from pydantic import BaseModel


class ImportRow(BaseModel):
    row: int
    status: Literal["accepted", "rejected"]
    errors: list[str] = []
    warnings: list[str] = []
    report_id: str | None = None
    external_id: str | None = None
    score: int | None = None
    report_status: str | None = None
    rule_hits: list[dict[str, Any]] = []


class ImportResult(BaseModel):
    batch_id: str | None
    dry_run: bool
    format: str
    rows_total: int
    accepted: int
    rejected: int
    report: list[ImportRow]
