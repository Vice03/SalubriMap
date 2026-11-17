# SPDX-License-Identifier: AGPL-3.0-or-later
"""Table du module « Assistant » : passages des documents de référence (recherche BM25, sans base vectorielle)."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from salubri_api.modules.assistant.interface import Base


class AssistantPassage(Base):
    __tablename__ = "assistant_passages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc: Mapped[str] = mapped_column(String(120), index=True)  # ex. HYPOTHESES.md
    section: Mapped[str] = mapped_column(String(300))  # titre de la section (## …)
    text: Mapped[str] = mapped_column(Text)
    tokens: Mapped[str] = mapped_column(Text)  # termes normalisés séparés par des espaces
