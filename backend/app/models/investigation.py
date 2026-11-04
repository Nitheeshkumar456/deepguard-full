import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from ..database import Base

class CaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    FLAGGED = "FLAGGED"
    RESOLVED = "RESOLVED"

class CasePriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class InvestigationCase(Base):
    """Investigation case container linking multiple analyses, notes, and findings."""
    __tablename__ = "investigation_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(CaseStatus), default=CaseStatus.OPEN, nullable=False, index=True)
    priority = Column(Enum(CasePriority), default=CasePriority.MEDIUM, nullable=False)
    tags = Column(String(512), nullable=True) # Comma-separated tags or JSON

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="cases")
    case_analyses = relationship("CaseAnalysis", back_populates="case", cascade="all, delete-orphan")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan", order_by="desc(CaseNote.created_at)")

class CaseAnalysis(Base):
    """Association between an investigation case and an analysis item."""
    __tablename__ = "case_analyses"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)

    notes = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("InvestigationCase", back_populates="case_analyses")
    analysis = relationship("Analysis")

class CaseNote(Base):
    """Investigator note attached to an investigation case."""
    __tablename__ = "case_notes"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    author_name = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    case = relationship("InvestigationCase", back_populates="notes")
