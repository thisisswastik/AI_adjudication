from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime

# --- Structured Document Extraction Schemas ---

class MedicineExtractionItem(BaseModel):
    name: str = Field(description="Name of the medicine, e.g. Paracetamol")
    dosage: Optional[str] = Field(None, description="Dosage instructions, e.g. 650mg once daily")
    duration: Optional[str] = Field(None, description="Duration of treatment, e.g. 5 days")
    is_generic: Optional[bool] = Field(None, description="Whether this is a generic drug name (True) or branded drug name (False)")

class PrescriptionExtraction(BaseModel):
    doctor_name: str = Field(description="Name of the prescribing doctor")
    doctor_reg: str = Field(description="Registration number of the doctor. Should be in format [State Code]/[Number]/[Year], e.g. KA/45678/2015. If format differs, extract exactly what is visible.")
    hospital_clinic_name: str = Field(description="Name of the hospital or clinic")
    diagnosis: str = Field(description="Diagnosis or medical condition described by the doctor, e.g. Viral fever, Teeth decay, Gastroenteritis")
    treatment_date: str = Field(description="Date of prescription or consultation in YYYY-MM-DD format")
    patient_name: str = Field(description="Name of the patient")
    patient_age: Optional[int] = Field(None, description="Age of the patient")
    patient_gender: Optional[str] = Field(None, description="Gender of the patient")
    medicines_prescribed: List[str] = Field(description="List of names of prescribed medicines")
    medicine_details: List[MedicineExtractionItem] = Field(default=[], description="Structured list of prescribed medicines with details")
    tests_recommended: List[str] = Field(default=[], description="List of diagnostic tests recommended by doctor, e.g. CBC, Dengue test, MRI Lumbar Spine")
    procedures: List[str] = Field(default=[], description="List of procedures recommended/performed, e.g. Root canal treatment, Teeth whitening, Cleaning")

class BillExtractionItem(BaseModel):
    description: str = Field(description="Item name or description, e.g. Consultation fee, Blood test, Root canal, Paracetamol")
    category: str = Field(description="Category of service. Must be one of: 'consultation', 'diagnostic', 'pharmacy', 'dental', 'vision', 'alternative', 'other'")
    amount: float = Field(description="Total charge for this item in INR")
    unit_price: Optional[float] = Field(None, description="Price per unit in INR")
    quantity: Optional[int] = Field(None, description="Quantity purchased")

class BillExtraction(BaseModel):
    bill_number: str = Field(description="Invoice or bill reference number")
    bill_date: str = Field(description="Date of the bill in YYYY-MM-DD format")
    hospital_clinic_name: str = Field(description="Name of the hospital, clinic, pharmacy or diagnostic center")
    patient_name: str = Field(description="Name of the patient")
    items: List[BillExtractionItem] = Field(description="List of individual charges or items on the bill")
    total_amount: float = Field(description="Total billing amount in INR")
    tax_amount: Optional[float] = Field(0.0, description="Tax or GST amount in INR")

class LabReportItem(BaseModel):
    test_name: str = Field(description="Name of the test, e.g. Hemoglobin, SGPT")
    result: str = Field(description="Result value, e.g. 14.5, 35")
    normal_range: Optional[str] = Field(None, description="Reference normal range, e.g. 13-17 g/dL")
    interpretation: Optional[str] = Field(None, description="Interpretation of result, e.g. Normal, High, Low")

class LabReportExtraction(BaseModel):
    report_id: str = Field(description="Diagnostic report reference ID")
    report_date: str = Field(description="Date of the report in YYYY-MM-DD format")
    patient_name: str = Field(description="Name of the patient")
    test_results: List[LabReportItem] = Field(description="List of tests performed with their results")
    doctor_name: str = Field(description="Name of the pathologist or referring doctor")

# --- Database / API Schemas ---

class MemberBase(BaseModel):
    id: str
    name: str
    policy_number: str
    join_date: date
    annual_limit_remaining: float
    status: str

class MemberResponse(MemberBase):
    class Config:
        from_attributes = True

class ClaimDocumentResponse(BaseModel):
    id: int
    claim_id: str
    document_type: str
    file_name: str
    file_size: int
    extracted_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class AdjudicationResultResponse(BaseModel):
    decision: str
    approved_amount: float
    confidence_score: float
    reasons: List[str]
    flags: List[str]
    notes: Optional[str] = None
    next_steps: Optional[str] = None
    policy_engine_log: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    action: str
    timestamp: datetime
    details: Optional[str] = None

    class Config:
        from_attributes = True

class ClaimResponse(BaseModel):
    id: str
    member_id: str
    patient_name: str
    claim_amount: float
    status: str
    hospital_name: Optional[str] = None
    cashless_request: bool
    treatment_date: date
    submitted_at: datetime
    documents: List[ClaimDocumentResponse] = []
    adjudication_result: Optional[AdjudicationResultResponse] = None
    audit_logs: List[AuditLogResponse] = []

    class Config:
        from_attributes = True

class ClaimCreate(BaseModel):
    member_id: str
    patient_name: str
    claim_amount: float
    treatment_date: date
    hospital_name: Optional[str] = None
    cashless_request: bool = False

# --- Admin Dashboard Schemas ---

class DashboardStatsResponse(BaseModel):
    total_claims: int
    approved_claims: int
    rejected_claims: int
    manual_review_claims: int
    approval_rate: float
    average_confidence: float
    claims_by_status: Dict[str, int]
    daily_volume: List[Dict[str, Any]]
