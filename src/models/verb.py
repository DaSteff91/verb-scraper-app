"""
Database models for Verb and its related conjugations.
"""

from __future__ import annotations
from datetime import UTC, datetime
import uuid
from typing import Dict, List, Any, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.extensions import db


class Verb(db.Model):  # type: ignore
    """Represents a verb in its infinitive form."""

    __tablename__ = "verbs"

    id: Mapped[int] = mapped_column(primary_key=True)
    infinitive: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

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


class BatchJob(db.Model):  # type: ignore
    """Tracks the status of background asynchronous scraping tasks."""

    __tablename__ = "batch_jobs"

    # We use a string-based UUID for the primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Status: 'pending', 'processing', 'completed', 'failed'
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # Quantitative tracking
    total_tasks: Mapped[int] = mapped_column(default=0)
    success_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the BatchJob instance into a JSON-serializable dictionary.

        Returns:
            Dict[str, Any]: A dictionary representing the job's current state,
                including progress counts and ISO-formatted timestamps.
        """
        return {
            "job_id": str(self.id),
            "status": str(self.status),
            "progress": {
                "total": int(self.total_tasks),
                "success": int(self.success_count),
                "failed": int(self.failed_count),
            },
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }
