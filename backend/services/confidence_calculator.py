import logging
from typing import Dict, Any, List, Tuple
from fuzzywuzzy import fuzz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_completeness_score(extracted_data: List[Dict[str, Any]]) -> float:
    """Calculates completeness score (0.0 to 1.0) based on presence of essential fields."""
    if not extracted_data:
        return 0.0
        
    scores = []
    for doc in extracted_data:
        doc_type = doc.get("document_type", "").upper()
        data = doc.get("data") or {}
        if not data:
            scores.append(0.0)
            continue
            
        filled = 0
        total = 0
        
        if doc_type == "PRESCRIPTION":
            fields = ["doctor_name", "doctor_reg", "diagnosis", "treatment_date", "patient_name"]
            total = len(fields)
            filled = sum(1 for f in fields if data.get(f))
            
        elif doc_type == "BILL":
            fields = ["bill_number", "bill_date", "patient_name", "items", "total_amount"]
            total = len(fields)
            filled = sum(1 for f in fields if data.get(f))
            # Also check if items list has actual contents
            if data.get("items") and len(data["items"]) > 0:
                filled += 1
            total += 1
            
        elif doc_type == "LAB_REPORT":
            fields = ["report_id", "report_date", "patient_name", "test_results", "doctor_name"]
            total = len(fields)
            filled = sum(1 for f in fields if data.get(f))
            
        else: # Generic or other
            fields = ["patient_name", "summary"]
            total = len(fields)
            filled = sum(1 for f in fields if data.get(f))
            
        doc_score = (filled / total) if total > 0 else 1.0
        scores.append(doc_score)
        
    return sum(scores) / len(scores) if scores else 1.0

def calculate_consistency_score(
    claim_details: Dict[str, Any],
    extracted_data: List[Dict[str, Any]],
    member_name: str
) -> float:
    """Checks for consistency across patient names, dates, and billing amounts."""
    score = 1.0
    
    # 1. Check patient name consistency against database member name
    patient_name = claim_details.get("patient_name", "")
    if patient_name and member_name:
        ratio = fuzz.ratio(patient_name.lower().strip(), member_name.lower().strip())
        if ratio < 60:
            score -= 0.4  # Major penalty
        elif ratio < 85:
            score -= 0.15 # Minor penalty
            
    # Extract dates and patient names from documents
    doc_dates = []
    doc_names = []
    
    for doc in extracted_data:
        data = doc.get("data") or {}
        # Date extraction
        for date_key in ["treatment_date", "bill_date", "report_date", "document_date"]:
            if data.get(date_key):
                doc_dates.append(data[date_key])
                break
        # Patient name extraction
        if data.get("patient_name"):
            doc_names.append(data["patient_name"])
            
    # 2. Check date consistency (mismatch between treatment date, bill date, etc.)
    if doc_dates:
        unique_dates = set(doc_dates)
        # Check if they mismatch the claimed treatment date
        claim_date = claim_details.get("treatment_date")
        if isinstance(claim_date, str):
            claim_date_str = claim_date
        else:
            claim_date_str = claim_date.strftime("%Y-%m-%d") if claim_date else ""
            
        for d in unique_dates:
            if d != claim_date_str:
                score -= 0.15 # Date mismatch penalty
                break
                
    # 3. Check document name consistency (names on documents matching patient name)
    if doc_names and patient_name:
        for name in doc_names:
            ratio = fuzz.ratio(patient_name.lower().strip(), name.lower().strip())
            if ratio < 75:
                score -= 0.15 # Document name mismatch penalty
                break
                
    # 4. Check bill math (sum of items equals total)
    bill_doc = next((d for d in extracted_data if d.get("document_type") == "BILL"), None)
    if bill_doc and bill_doc.get("data"):
        data = bill_doc["data"]
        items = data.get("items", [])
        total = data.get("total_amount", 0.0)
        
        if items and total:
            items_sum = sum(item.get("amount", 0.0) for item in items)
            if abs(items_sum - total) > 10.0: # Tolerance of ₹10 for rounding/taxes
                score -= 0.15 # Arithmetic discrepancy penalty
                
    return max(0.0, score)

def evaluate_confidence(
    claim_details: Dict[str, Any],
    extracted_data: List[Dict[str, Any]],
    member_name: str,
    deterministic_checks: Dict[str, Any],
    avg_extraction_confidence: float
) -> Tuple[float, List[str]]:
    """
    Computes a composite confidence score.
    Returns: (confidence_score, List[warning_flags])
    """
    flags = []
    
    # 1. Extraction Confidence (40% weight)
    # Passed in as avg_extraction_confidence
    
    # 2. Completeness (30% weight)
    completeness = calculate_completeness_score(extracted_data)
    if completeness < 0.80:
        flags.append("Incomplete document metadata")
        
    # 3. Consistency (30% weight)
    consistency = calculate_consistency_score(claim_details, extracted_data, member_name)
    if consistency < 0.85:
        flags.append("Inconsistent claim details")
        
    # Calculate composite
    composite_score = (avg_extraction_confidence * 0.40) + (completeness * 0.30) + (consistency * 0.30)
    
    # Apply deductions/overrides based on deterministic checks
    # If policy engine failed (but we still want to evaluate confidence)
    if not deterministic_checks.get("eligible", True):
        # We can still keep confidence high if we are certain about the rejection
        # But if there are patient name mismatches, we flag it.
        if "PATIENT_MISMATCH" in deterministic_checks.get("errors", []):
            flags.append("Patient details mismatch")
            composite_score = min(composite_score, 0.60)
            
    # Check for fraud indicators (e.g. multiple claims on same day)
    previous_claims = claim_details.get("previous_claims_same_day", 0)
    if previous_claims >= 2:
        flags.append("Unusual frequency - Multiple claims same day")
        composite_score = min(composite_score, 0.65) # Force to manual review
        
    # High value claims flag (does not reduce confidence but triggers warning)
    if claim_details.get("claim_amount", 0.0) > 25000:
        flags.append("High-value claim (>₹25,000)")
        
    # Final score boundaries
    composite_score = max(0.0, min(1.0, composite_score))
    
    return composite_score, flags
