import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.models.models import Claim, ClaimDocument, AdjudicationResult, AuditLog
from typing import List, Optional, Dict, Any

def create_claim(db: Session, member_id: str, patient_name: str, claim_amount: float, treatment_date: datetime.date, hospital_name: Optional[str] = None, cashless_request: bool = False, claim_id: Optional[str] = None) -> Claim:
    # If claim_id is not provided, generate a unique one
    if not claim_id:
        import uuid
        claim_id = f"CLM_{uuid.uuid4().hex[:8].upper()}"
        
    db_claim = Claim(
        id=claim_id,
        member_id=member_id,
        patient_name=patient_name,
        claim_amount=claim_amount,
        status="PENDING",
        hospital_name=hospital_name,
        cashless_request=cashless_request,
        treatment_date=treatment_date
    )
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    
    # Create initial audit log
    create_audit_log(db, claim_id, "CLAIM_SUBMITTED", f"Claim of ₹{claim_amount} submitted for patient {patient_name}.")
    
    return db_claim

def get_claim(db: Session, claim_id: str) -> Optional[Claim]:
    return db.query(Claim).filter(Claim.id == claim_id).first()

def get_claims(db: Session, status: Optional[str] = None, search: Optional[str] = None) -> List[Claim]:
    query = db.query(Claim)
    if status:
        query = query.filter(Claim.status == status)
    if search:
        query = query.filter(
            (Claim.patient_name.ilike(f"%{search}%")) | 
            (Claim.id.ilike(f"%{search}%")) |
            (Claim.member_id.ilike(f"%{search}%"))
        )
    return query.order_by(desc(Claim.submitted_at)).all()

def update_claim_status(db: Session, claim_id: str, status: str) -> Optional[Claim]:
    db_claim = get_claim(db, claim_id)
    if db_claim:
        old_status = db_claim.status
        db_claim.status = status
        db.commit()
        db.refresh(db_claim)
        create_audit_log(db, claim_id, "STATUS_UPDATED", f"Claim status transitioned from {old_status} to {status}.")
    return db_claim

def create_document(db: Session, claim_id: str, document_type: str, file_path: str, file_name: str, file_size: int) -> ClaimDocument:
    db_doc = ClaimDocument(
        claim_id=claim_id,
        document_type=document_type,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    create_audit_log(db, claim_id, "DOCUMENT_ADDED", f"Document of type {document_type} uploaded: {file_name}")
    return db_doc

def update_document_extracted_data(db: Session, document_id: int, extracted_data: Dict[str, Any], raw_llm_response: str) -> Optional[ClaimDocument]:
    db_doc = db.query(ClaimDocument).filter(ClaimDocument.id == document_id).first()
    if db_doc:
        db_doc.extracted_data = extracted_data
        db_doc.raw_llm_response = raw_llm_response
        db.commit()
        db.refresh(db_doc)
        create_audit_log(db, db_doc.claim_id, "OCR_EXTRACTED", f"Metadata extracted from {db_doc.document_type} document.")
    return db_doc

def create_adjudication_result(db: Session, claim_id: str, decision: str, approved_amount: float, confidence_score: float, reasons: List[str], flags: List[str], notes: Optional[str] = None, next_steps: Optional[str] = None, policy_engine_log: Optional[Dict[str, Any]] = None) -> AdjudicationResult:
    # Check if result already exists
    db_result = db.query(AdjudicationResult).filter(AdjudicationResult.claim_id == claim_id).first()
    
    if db_result:
        db_result.decision = decision
        db_result.approved_amount = approved_amount
        db_result.confidence_score = confidence_score
        db_result.reasons = reasons
        db_result.flags = flags
        db_result.notes = notes
        db_result.next_steps = next_steps
        db_result.policy_engine_log = policy_engine_log
        db_result.created_at = datetime.datetime.utcnow()
    else:
        db_result = AdjudicationResult(
            claim_id=claim_id,
            decision=decision,
            approved_amount=approved_amount,
            confidence_score=confidence_score,
            reasons=reasons,
            flags=flags,
            notes=notes,
            next_steps=next_steps,
            policy_engine_log=policy_engine_log
        )
        db.add(db_result)
        
    db.commit()
    db.refresh(db_result)
    
    # Update main claim status to match decision
    update_claim_status(db, claim_id, decision)
    
    create_audit_log(db, claim_id, "ADJUDICATION_COMPLETED", f"Adjudication completed. Decision: {decision}. Approved Amount: ₹{approved_amount}.")
    return db_result

def create_audit_log(db: Session, claim_id: str, action: str, details: Optional[str] = None) -> AuditLog:
    db_log = AuditLog(
        claim_id=claim_id,
        action=action,
        details=details
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log
