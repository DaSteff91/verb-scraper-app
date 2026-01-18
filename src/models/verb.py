"""
Database models for Verb and its related conjugations.
"""

from __future__ import annotations
from datetime import datetime
from typing import List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.extensions import db


class Verb(db.Model):  # type: ignore
    """Represents a verb in its infinitive form."""

    __tablename__ = "verbs"

    id: Mapped[int] = mapped_column(primary_key=True)
    infinitive: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(datetime.UTC)
    )

    conjugations: Mapped[List["Conjugation"]] = relationship(
        back_populates="verb", cascade="all, delete-orphan"
    )


class Mode(db.Model):  # type: ignore
    """Represents a grammatical mode (e.g., Indicativo)."""

    __tablename__ = "modes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tenses: Mapped[List["Tense"]] = relationship(back_populates="mode")


class Tense(db.Model):  # type: ignore
    """Represents a grammatical tense (e.g., Presente)."""

    __tablename__ = "tenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    mode_id: Mapped[int] = mapped_column(ForeignKey("modes.id"), nullable=False)
    mode: Mapped["Mode"] = relationship(back_populates="tenses")


class Person(db.Model):  # type: ignore
    """Represents a grammatical person (e.g., eu, tu)."""

    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0)


class Conjugation(db.Model):  # type: ignore
    """Represents a specific conjugated form of a verb."""

    __tablename__ = "conjugations"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    verb_id: Mapped[int] = mapped_column(ForeignKey("verbs.id"), nullable=False)
    tense_id: Mapped[int] = mapped_column(ForeignKey("tenses.id"), nullable=False)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), nullable=False)

    verb: Mapped["Verb"] = relationship(back_populates="conjugations")
    tense: Mapped["Tense"] = relationship()
    person: Mapped["Person"] = relationship()
