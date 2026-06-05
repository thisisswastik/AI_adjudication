# API Documentation

The backend service is built using FastAPI. It exposes endpoints for claim management, document upload, automated adjudication, and metrics dashboards.

The server runs locally by default at `http://127.0.0.1:8000`. Full interactive Swagger UI documentation is available at `http://127.0.0.1:8000/docs`.

---

## Endpoints Overview

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| **POST** | `/api/seed` | Seeds initial members from test cases | Public |
| **POST** | `/api/claims` | Creates a new claim | Public |
| **POST** | `/api/claims/{claim_id}/documents` | Uploads and extracts text from a file | Public |
| **POST** | `/api/claims/{claim_id}/adjudicate` | Adjudicates claim using rules & AI | Public |
| **GET** | `/api/claims/{claim_id}` | Retrieves full claim details | Public |
| **GET** | `/api/claims` | Searches/filters claims list | Public |
| **GET** | `/api/admin/stats` | Retrieves dashboard statistics | Public |
| **GET** | `/health` | API Healthcheck status | Public |

---

## 1. Seed Member Registry
* **Endpoint:** `POST /api/seed`
* **Request:** None
* **Response (200 OK):**
```json
{
  "message": "Seeding completed. Seeded 10 new members."
}
```

---

## 2. Create Claim
* **Endpoint:** `POST /api/claims`
* **Content-Type:** `application/x-www-form-urlencoded` or multipart form-data
* **Fields:**
  - `member_id` (string, required): Member ID (e.g. `EMP001`)
  - `patient_name` (string, required): Name of patient
  - `claim_amount` (float, required): Total claim amount in INR
  - `treatment_date` (string, required): Date in format `YYYY-MM-DD`
  - `hospital_name` (string, optional): Hospital/Clinic name
  - `cashless_request` (boolean, optional): Default `false`
* **Response (200 OK):**
```json
{
  "id": "CLM_A5F9B2C3",
  "member_id": "EMP001",
  "patient_name": "Rajesh Kumar",
  "claim_amount": 1500.0,
  "status": "PENDING",
  "hospital_name": "Apollo Hospitals",
  "cashless_request": true,
  "treatment_date": "2024-11-01",
  "submitted_at": "2026-06-04T18:20:00Z",
  "documents": [],
  "adjudication_result": null,
  "audit_logs": [
    {
      "id": 1,
      "action": "CLAIM_SUBMITTED",
      "timestamp": "2026-06-04T18:20:00Z",
      "details": "Claim of ₹1500.0 submitted for patient Rajesh Kumar."
    }
  ]
}
```

---

## 3. Upload Claim Document
* **Endpoint:** `POST /api/claims/{claim_id}/documents`
* **Content-Type:** `multipart/form-data`
* **Fields:**
  - `document_type` (string, required): One of: `PRESCRIPTION`, `BILL`, `LAB_REPORT`, `OTHER`
  - `file` (binary file, required): PDF, PNG, JPG, or JPEG
* **Response (200 OK):**
```json
{
  "document_id": 12,
  "document_type": "BILL",
  "file_name": "hospital_receipt.pdf",
  "extracted_data": {
    "bill_number": "INV-10293",
    "bill_date": "2024-11-01",
    "hospital_clinic_name": "Apollo Hospitals",
    "patient_name": "Rajesh Kumar",
    "items": [
      {
        "description": "Consultation fee",
        "category": "consultation",
        "amount": 1000.0
      },
      {
        "description": "CBC blood test",
        "category": "diagnostic",
        "amount": 500.0
      }
    ],
    "total_amount": 1500.0,
    "tax_amount": 0.0
  },
  "extraction_confidence": 0.94
}
```

---

## 4. Adjudicate Claim
* **Endpoint:** `POST /api/claims/{claim_id}/adjudicate`
* **Request:** None
* **Response (200 OK):**
```json
{
  "decision": "APPROVED",
  "approved_amount": 1350.0,
  "confidence_score": 0.95,
  "reasons": [
    "Medical necessity established",
    "All documents valid",
    "Amount within limits"
  ],
  "flags": [],
  "notes": "Consultation fee ₹1000 subject to 10% copay (₹100). Diagnostic test ₹500 subject to 10% copay (₹50). Total copay: ₹150.",
  "next_steps": "Your reimbursement of ₹1350 has been approved and queued for bank transfer.",
  "policy_engine_log": {
    "eligible": true,
    "errors": [],
    "warnings": [],
    "notes": "Deterministic rules check complete.",
    "member_info": {
      "id": "EMP001",
      "name": "Rajesh Kumar",
      "status": "ACTIVE",
      "annual_limit_remaining": 48650.0
    }
  }
}
```

---

## 5. Get Claim Details
* **Endpoint:** `GET /api/claims/{claim_id}`
* **Response (200 OK):** Returns the full claim schema, including documents, adjudication result, and audit log list.

---

## 6. List/Search Claims
* **Endpoint:** `GET /api/claims`
* **Query Parameters:**
  - `status` (string, optional): Filter by status (`PENDING`, `APPROVED`, etc.)
  - `search` (string, optional): Search string for names or IDs
* **Response (200 OK):** Array of claim objects.

---

## 7. Get Admin Stats
* **Endpoint:** `GET /api/admin/stats`
* **Response (200 OK):**
```json
{
  "total_claims": 24,
  "approved_claims": 18,
  "rejected_claims": 4,
  "manual_review_claims": 2,
  "approval_rate": 75.0,
  "average_confidence": 0.89,
  "claims_by_status": {
    "APPROVED": 16,
    "PARTIAL": 2,
    "REJECTED": 4,
    "MANUAL_REVIEW": 2
  },
  "daily_volume": [
    {
      "date": "2026-06-04",
      "count": 24
    }
  ]
}
```
