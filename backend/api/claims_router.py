import os
import shutil
import datetime
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from collections import defaultdict

from backend.database.database import get_db
from backend.repositories import claim_repository, member_repository
from backend.models.models import Claim
from backend.schemas import schemas
from backend.services.policy_service import PolicyService
from backend.services.confidence_calculator import evaluate_confidence
from backend.ai import document_extractor, adjudication_reasoner

router = APIRouter(prefix="/api")

# Initialize Policy Service
policy_service = PolicyService()

# Uploads directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
UPLOAD_DIR = os.path.join(WORKSPACE_ROOT, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/seed", status_code=200)
def seed_members(db: Session = Depends(get_db)):
    """Seeds the initial member registry required for the 10 test cases."""
    members_to_seed = [
        {"id": "EMP001", "name": "Rajesh Kumar", "join_date": "2024-01-01"},
        {"id": "EMP002", "name": "Priya Singh", "join_date": "2024-01-01"},
        {"id": "EMP003", "name": "Amit Verma", "join_date": "2024-01-01"},
        {"id": "EMP004", "name": "Sneha Reddy", "join_date": "2024-01-01"},
        {"id": "EMP005", "name": "Vikram Joshi", "join_date": "2024-09-01"},
        {"id": "EMP006", "name": "Kavita Nair", "join_date": "2024-01-01"},
        {"id": "EMP007", "name": "Suresh Patil", "join_date": "2024-01-01"},
        {"id": "EMP008", "name": "Ravi Menon", "join_date": "2024-01-01"},
        {"id": "EMP009", "name": "Anita Desai", "join_date": "2024-01-01"},
        {"id": "EMP010", "name": "Deepak Shah", "join_date": "2024-01-01"},
    ]
    
    seeded = 0
    for m in members_to_seed:
        existing = member_repository.get_member(db, m["id"])
        if not existing:
            member_repository.create_member(
                db, 
                member_id=m["id"], 
                name=m["name"], 
                join_date=datetime.datetime.strptime(m["join_date"], "%Y-%m-%d").date()
            )
            seeded += 1
            
    return {"message": f"Seeding completed. Seeded {seeded} new members."}

@router.post("/claims", response_model=schemas.ClaimResponse)
def create_new_claim(
    member_id: str = Form(...),
    patient_name: str = Form(...),
    claim_amount: float = Form(...),
    treatment_date: str = Form(...),
    hospital_name: Optional[str] = Form(None),
    cashless_request: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Creates a claim record in PENDING status."""
    try:
        treat_date = datetime.datetime.strptime(treatment_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid treatment_date format. Must be YYYY-MM-DD.")
        
    # Verify member exists before accepting claim
    member = member_repository.get_member(db, member_id)
    if not member:
        # Create a placeholder claim that will immediately fail deterministic checks
        # or reject it at API level. For simulation matching the assignment guidelines,
        # we can still create the claim record so the reviewer sees the failure and rejection details.
        pass

    claim = claim_repository.create_claim(
        db,
        member_id=member_id,
        patient_name=patient_name,
        claim_amount=claim_amount,
        treatment_date=treat_date,
        hospital_name=hospital_name,
        cashless_request=cashless_request
    )
    return claim

@router.post("/claims/{claim_id}/documents")
def upload_claim_document(
    claim_id: str,
    document_type: str = Form(...), # PRESCRIPTION, BILL, LAB_REPORT, OTHER
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads a file, saves it, and runs Gemini to extract structured info."""
    claim = claim_repository.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=44, detail="Claim not found")
        
    # Validate document type
    valid_types = ["PRESCRIPTION", "BILL", "LAB_REPORT", "OTHER"]
    if document_type.upper() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid document type. Must be one of: {valid_types}")
        
    # Generate local path
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{claim_id}_{document_type.upper()}_{uuid.uuid4().hex[:6]}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    file_size = os.path.getsize(file_path)
    
    # Create DB document record
    db_doc = claim_repository.create_document(
        db,
        claim_id=claim_id,
        document_type=document_type.upper(),
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size
    )
    
    # Read bytes for Gemini extraction
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
        
    # Run Gemini Multimodal Extraction
    try:
        # Determine mime type
        mime_type = file.content_type
        if not mime_type or mime_type == "application/octet-stream":
            if file_ext.lower() == ".pdf":
                mime_type = "application/pdf"
            elif file_ext.lower() in [".jpg", ".jpeg"]:
                mime_type = "image/jpeg"
            elif file_ext.lower() == ".png":
                mime_type = "image/png"
            else:
                mime_type = "image/jpeg" # Default fallback
                
        extracted_data, raw_llm, conf = document_extractor.extract_document_data(
            file_bytes=file_bytes,
            mime_type=mime_type,
            doc_type=document_type
        )
        
        # Save extraction to document record
        claim_repository.update_document_extracted_data(db, db_doc.id, extracted_data, raw_llm)
        
    except Exception as e:
        # If extraction fails, log it and set empty data, claim can be routed to manual review
        claim_repository.create_audit_log(db, claim_id, "OCR_FAILED", f"Gemini extraction failed for {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Extraction failed: {str(e)}")
        
    return {
        "document_id": db_doc.id,
        "document_type": db_doc.document_type,
        "file_name": db_doc.file_name,
        "extracted_data": extracted_data,
        "extraction_confidence": conf
    }

@router.post("/claims/{claim_id}/adjudicate", response_model=schemas.AdjudicationResultResponse)
def adjudicate_claim(claim_id: str, db: Session = Depends(get_db)):
    """Runs deterministic rules, calculates confidence, and triggers Gemini adjudication."""
    claim = claim_repository.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    # Refresh documents status
    db.refresh(claim)
    
    # 1. Run Deterministic Rules Check
    rules_result = policy_service.run_deterministic_checks(db, claim)
    
    # Pre-fetch member name (needed for consistency checks)
    member = member_repository.get_member(db, claim.member_id)
    member_name = member.name if member else ""
    
    # Prepare extracted data context
    docs_context = []
    avg_ext_conf = 0.0
    for doc in claim.documents:
        docs_context.append({
            "document_type": doc.document_type,
            "data": doc.extracted_data
        })
        # If no custom confidence was saved, we estimate a default
        avg_ext_conf += 0.90
        
    if claim.documents:
        avg_ext_conf /= len(claim.documents)
    else:
        avg_ext_conf = 0.50
        
    # 2. Calculate Composite Confidence Score
    claim_details = {
        "claim_amount": claim.claim_amount,
        "patient_name": claim.patient_name,
        "treatment_date": claim.treatment_date.strftime("%Y-%m-%d"),
        "cashless_request": claim.cashless_request,
        "hospital_name": claim.hospital_name,
        "previous_claims_same_day": len([
            c for c in member.claims 
            if c.treatment_date == claim.treatment_date and c.id != claim.id
        ]) if member else 0
    }
    
    confidence, flags = evaluate_confidence(
        claim_details=claim_details,
        extracted_data=docs_context,
        member_name=member_name,
        deterministic_checks=rules_result,
        avg_extraction_confidence=avg_ext_conf
    )
    
    # 3. Decision Pipeline
    if not rules_result["eligible"]:
        # If deterministic rules failed (e.g. WAITING_PERIOD, POLICY_INACTIVE, etc.), reject immediately
        reasons = rules_result["errors"]
        decision = "REJECTED"
        approved_amount = 0.0
        notes = "; ".join(rules_result["warnings"]) or "Deterministic eligibility rules failed."
        next_steps = "Claim has been rejected based on policy terms. Please review policy document."
        
        result = claim_repository.create_adjudication_result(
            db,
            claim_id=claim_id,
            decision=decision,
            approved_amount=approved_amount,
            confidence_score=confidence,
            reasons=reasons,
            flags=flags + reasons,
            notes=notes,
            next_steps=next_steps,
            policy_engine_log=rules_result
        )
        return result
        
    # 4. If deterministic rules passed, run Gemini AI Adjudication for Medical Necessity & Limits
    try:
        ai_result = adjudication_reasoner.run_ai_adjudication(
            claim_details=claim_details,
            extracted_data=docs_context,
            policy_terms=policy_service.policy_terms,
            adjudication_rules=policy_service.adjudication_rules,
            deterministic_checks=rules_result
        )
        
        decision = ai_result.decision
        approved_amount = ai_result.covered_amount
        reasons = ai_result.reasons
        notes = ai_result.notes
        next_steps = ai_result.next_steps
        
        # Merge flags and check confidence thresholds
        all_flags = list(set(flags + ai_result.flags))
        final_confidence = min(confidence, ai_result.confidence)
        
        # If composite confidence is low (< 0.70), route to MANUAL_REVIEW
        if final_confidence < 0.70 and decision in ["APPROVED", "PARTIAL"]:
            decision = "MANUAL_REVIEW"
            approved_amount = 0.0 # No disbursement until manual audit
            reasons.append("LOW_CONFIDENCE_THRESHOLD")
            notes += " Route to manual review due to verification details or warnings."
            next_steps = "Our claims desk will audit this claim manually. No action needed."
            
        # Deduct approved amount from member's YTD remaining limit if approved
        if decision in ["APPROVED", "PARTIAL"] and approved_amount > 0:
            new_limit = max(0.0, member.annual_limit_remaining - approved_amount)
            member_repository.update_member_limit(db, member.id, new_limit)
            
        result = claim_repository.create_adjudication_result(
            db,
            claim_id=claim_id,
            decision=decision,
            approved_amount=approved_amount,
            confidence_score=final_confidence,
            reasons=reasons,
            flags=all_flags,
            notes=notes,
            next_steps=next_steps,
            policy_engine_log=rules_result
        )
        return result
        
    except Exception as e:
        # Fallback to MANUAL_REVIEW on Exception
        claim_repository.create_audit_log(db, claim_id, "ADJUDICATION_ERROR", f"AI adjudication exception: {str(e)}")
        
        result = claim_repository.create_adjudication_result(
            db,
            claim_id=claim_id,
            decision="MANUAL_REVIEW",
            approved_amount=0.0,
            confidence_score=0.50,
            reasons=["AI_ENGINE_EXCEPTION"],
            flags=["PROCESSING_ERROR"],
            notes=f"Exception during reasoning: {str(e)}",
            next_steps="The system encountered an error. Routed for manual processing.",
            policy_engine_log=rules_result
        )
        return result

@router.get("/claims/{claim_id}", response_model=schemas.ClaimResponse)
def get_claim_details(claim_id: str, db: Session = Depends(get_db)):
    """Retrieves full claim details."""
    claim = claim_repository.get_claim(db, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@router.get("/claims", response_model=List[schemas.ClaimResponse])
def list_claims(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Search and filter claims list."""
    return claim_repository.get_claims(db, status=status, search=search)

@router.get("/admin/stats", response_model=schemas.DashboardStatsResponse)
def get_admin_dashboard_stats(db: Session = Depends(get_db)):
    """Computes stats and metrics for the Admin Dashboard."""
    claims = db.query(Claim).all()
    
    total = len(claims)
    approved = len([c for c in claims if c.status == "APPROVED"])
    rejected = len([c for c in claims if c.status == "REJECTED"])
    manual_review = len([c for c in claims if c.status == "MANUAL_REVIEW"])
    
    # Also partial approvals are counted as approved for high level stats or approved count?
    # Let's count APPROVED and PARTIAL as approved
    partial = len([c for c in claims if c.status == "PARTIAL"])
    effective_approved = approved + partial
    
    approval_rate = (effective_approved / total * 100) if total > 0 else 0.0
    
    # Calculate average confidence of adjudicated claims
    adjudicated_claims = [c for c in claims if c.adjudication_result is not None]
    avg_conf = sum(c.adjudication_result.confidence_score for c in adjudicated_claims) / len(adjudicated_claims) if adjudicated_claims else 0.0
    
    # Chart 1: Claims by status
    claims_by_status = defaultdict(int)
    for c in claims:
        claims_by_status[c.status] += 1
        
    # Chart 2: Daily claim volume
    # Group claims by submitted_at date (YYYY-MM-DD)
    daily_claims = defaultdict(int)
    for c in claims:
        date_str = c.submitted_at.strftime("%Y-%m-%d")
        daily_claims[date_str] += 1
        
    daily_volume = [
        {"date": d, "count": count} 
        for d, count in sorted(daily_claims.items())
    ]
    
    return schemas.DashboardStatsResponse(
        total_claims=total,
        approved_claims=effective_approved,
        rejected_claims=rejected,
        manual_review_claims=manual_review,
        approval_rate=round(approval_rate, 2),
        average_confidence=round(avg_conf, 2),
        claims_by_status=dict(claims_by_status),
        daily_volume=daily_volume
    )
