import datetime
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from backend.database.database import Base

class Member(Base):
    __tablename__ = "members"

    id = Column(String, primary_key=True, index=True) # e.g. EMP001
    name = Column(String, nullable=False)
    policy_number = Column(String, nullable=False, default="PLUM_OPD_2024")
    join_date = Column(Date, nullable=False)
    annual_limit_remaining = Column(Float, nullable=False, default=50000.0)
    status = Column(String, nullable=False, default="ACTIVE") # ACTIVE, INACTIVE

    claims = relationship("Claim", back_populates="member")

class Claim(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True, index=True) # e.g. CLM_12345
    member_id = Column(String, ForeignKey("members.id"), nullable=False)
    patient_name = Column(String, nullable=False)
    claim_amount = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="PENDING") # PENDING, PROCESSING, APPROVED, REJECTED, PARTIAL, MANUAL_REVIEW, APPEALED
    hospital_name = Column(String, nullable=True)
    cashless_request = Column(Boolean, nullable=False, default=False)
    treatment_date = Column(Date, nullable=False)
    submitted_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    member = relationship("Member", back_populates="claims")
    documents = relationship("ClaimDocument", back_populates="claim", cascade="all, delete-orphan")
    adjudication_result = relationship("AdjudicationResult", back_populates="claim", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="claim", cascade="all, delete-orphan")

class ClaimDocument(Base):
    __tablename__ = "claim_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(String, ForeignKey("claims.id"), nullable=False)
    document_type = Column(String, nullable=False) # PRESCRIPTION, BILL, LAB_REPORT, OTHER
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    extracted_data = Column(JSON, nullable=True) # JSON of parsed fields
    raw_llm_response = Column(Text, nullable=True) # raw model output

    claim = relationship("Claim", back_populates="documents")

class AdjudicationResult(Base):
    __tablename__ = "adjudication_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(String, ForeignKey("claims.id"), unique=True, nullable=False)
    decision = Column(String, nullable=False) # APPROVED, REJECTED, PARTIAL, MANUAL_REVIEW
    approved_amount = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    reasons = Column(JSON, nullable=False, default=list) # List[str]
    flags = Column(JSON, nullable=False, default=list) # List[str]
    notes = Column(Text, nullable=True)
    next_steps = Column(Text, nullable=True)
    policy_engine_log = Column(JSON, nullable=True) # details of check results
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    claim = relationship("Claim", back_populates="adjudication_result")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(String, ForeignKey("claims.id"), nullable=False)
    action = Column(String, nullable=False) # e.g. "CLAIM_SUBMITTED", "OCR_EXTRACTED", "POLICY_VAL_SUCCESS"
    timestamp = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)

    claim = relationship("Claim", back_populates="audit_logs")
