"""
app/database/models.py
───────────────────────
SQLAlchemy ORM table definitions.
Three tables: School, Proposal, ValidationResult
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean,
    DateTime, Text, ForeignKey, JSON, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class School(Base):
    """UDISE+ baseline data per school. Populated from final_dataset.csv."""
    __tablename__ = "schools"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    pseudocode      = Column(String(20), unique=True, nullable=False, index=True)
    school_level    = Column(String(20), default="primary")
    total_students  = Column(Float, default=0)
    total_boys      = Column(Float, default=0)
    total_girls     = Column(Float, default=0)
    total_tch       = Column(Float, default=0)
    regular         = Column(Float, default=0)
    contract        = Column(Float, default=0)
    classrooms_total= Column(Float, default=0)
    classrooms_pucca= Column(Float, default=0)
    classrooms_good = Column(Float, default=0)
    has_girls_toilet= Column(Integer, default=0)
    has_boys_toilet = Column(Integer, default=0)
    has_ramp        = Column(Integer, default=0)
    has_library     = Column(Integer, default=0)
    has_playground  = Column(Integer, default=0)
    has_electricity = Column(Integer, default=0)
    has_internet    = Column(Integer, default=0)
    has_handwash    = Column(Integer, default=0)
    has_boundary_wall = Column(Integer, default=0)
    has_comp_lab    = Column(Integer, default=0)
    ptr             = Column(Float, default=0)
    infrastructure_gap = Column(Float, default=0)
    risk_score      = Column(Float, default=0)
    risk_level      = Column(String(10), default="Low")

    __table_args__ = (
        Index("ix_schools_risk_level",  "risk_level"),
        Index("ix_schools_level_risk",  "school_level", "risk_score"),
    )
    created_at      = Column(DateTime, default=datetime.utcnow)

    proposals = relationship("Proposal", back_populates="school")


class Proposal(Base):
    """A school infrastructure funding proposal submitted by a principal."""
    __tablename__ = "proposals"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    school_pseudocode   = Column(String(20), ForeignKey("schools.pseudocode"), nullable=False)
    principal_name      = Column(String(200), nullable=False)
    school_name         = Column(String(300), nullable=False)
    intervention_type   = Column(String(50), nullable=False)
    classrooms_requested= Column(Integer, default=0)
    funding_requested   = Column(Float, nullable=False)
    funding_recurring   = Column(Float, default=0)
    funding_nonrecurring= Column(Float, default=0)
    project_start_date  = Column(String(20), nullable=True)
    project_end_date    = Column(String(20), nullable=True)
    udise_data_verified = Column(Boolean, default=False)
    proposal_letter     = Column(Text, nullable=True)   # free-text letter
    ai_summary          = Column(Text, nullable=True)   # Claude-generated summary
    dynamic_fields      = Column(JSON, nullable=True)   # Intervention-specific fields (sanitation, digital, etc.)
    status              = Column(String(20), default="Pending", index=True)

    __table_args__ = (
        Index("ix_proposals_school_type", "school_pseudocode", "intervention_type"),
        Index("ix_proposals_submitted",   "submitted_at"),
    )
    submitted_at        = Column(DateTime, default=datetime.utcnow)

    school  = relationship("School", back_populates="proposals")
    result  = relationship("ValidationResult", back_populates="proposal", uselist=False)


class ValidationResult(Base):
    """ML + rule engine output for a proposal."""
    __tablename__ = "validation_results"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id         = Column(Integer, ForeignKey("proposals.id"), nullable=False)
    verdict             = Column(String(20), nullable=False)   # Accept/Flag/Reject
    confidence          = Column(Float, default=0)
    risk_score          = Column(Float, default=0)
    urgency_score       = Column(Float, default=0)
    risk_level          = Column(String(10), default="Low")
    is_anomaly          = Column(Boolean, default=False)
    anomaly_score       = Column(Float, default=0)
    rule_violations     = Column(JSON, default=list)           # list of violation dicts
    ai_explanation      = Column(Text, nullable=True)          # Claude-generated reason
    feature_importances = Column(JSON, default=dict)           # top SHAP features
    score_breakdown     = Column(JSON, default=dict)           # risk score components
    validated_at        = Column(DateTime, default=datetime.utcnow)

    proposal = relationship("Proposal", back_populates="result")


class User(Base):
    """Authentication user — Admin or Principal."""
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    username        = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(20), nullable=False)   # "admin" | "principal"
    full_name       = Column(String(200), nullable=True)
    school_pseudocode = Column(String(20), nullable=True)  # only for principals
    is_active       = Column(Boolean, default=True)
    last_login      = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)