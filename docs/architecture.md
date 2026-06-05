# Plum OPD Claim Adjudication Tool

An intelligent, multimodal claim adjudication system for OPD (Outpatient Department) insurance claims. It combines a deterministic policy rules engine with Google Gemini 2.5 Flash to automate document extraction, eligibility checks, and final claim decisions — surfacing only genuinely ambiguous cases to human reviewers.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Database Schema (ER Diagram)](#database-schema-er-diagram)
- [Claim Decision Flow](#claim-decision-flow)
- [Tech Stack](#tech-stack)

---

## System Architecture

The system is composed of three tiers: a Streamlit web portal for claimants, a FastAPI backend hosting the adjudication logic, and two external services — the Gemini 2.5 Flash API for multimodal AI and a relational database for persistence.

```mermaid
graph TD
    User(["User / Claimant"]) <-->|"Browser / UI"| Streamlit["Streamlit Portal"]
    Streamlit <-->|"HTTP / JSON"| FastAPI["FastAPI Backend Application"]

    subgraph Backend ["FastAPI Backend"]
        Router["API Router"] <--> Repository["Repository CRUD Layer"]
        Router <--> PolicyService["Policy & Rules Engine"]
        Router <--> GeminiService["Gemini Integration Services"]

        PolicyService -->|"Check Rules"| ConfCalc["Confidence & Flags Calculator"]
    end

    GeminiService <-->|"Multimodal API / SDK"| GeminiAPI["Google Gemini 2.5 Flash API"]
    Repository <-->|"SQLAlchemy ORM"| DB[("SQLite / PostgreSQL Database")]

    classDef main fill:#1E3A8A,color:#fff,stroke:#10B981,stroke-width:2px;
    classDef external fill:#111827,color:#fff,stroke:#F59E0B,stroke-width:2px;
    classDef secondary fill:#F3F4F6,color:#1E293B,stroke:#9CA3AF,stroke-width:1px;

    class Streamlit,FastAPI,PolicyService,GeminiService main;
    class GeminiAPI,DB external;
    class Router,Repository,ConfCalc secondary;
```

### Component Summary

| Component | Role |
|---|---|
| **Streamlit Portal** | Browser-based UI for claim submission and status tracking |
| **FastAPI Backend** | REST API gateway; orchestrates all backend services |
| **API Router** | Routes incoming requests to the appropriate service layer |
| **Repository (CRUD)** | SQLAlchemy-based data access layer for all DB operations |
| **Policy & Rules Engine** | Deterministic eligibility checks (waiting period, annual limit, member status) |
| **Confidence & Flags Calculator** | Computes composite confidence score; raises fraud/ambiguity flags |
| **Gemini Integration Services** | Handles OCR extraction and AI-based adjudication via Gemini SDK |
| **Gemini 2.5 Flash API** | Google's multimodal LLM — processes bills, prescriptions, lab reports |
| **Database** | Stores members, claims, documents, results, and audit logs |

---

## Database Schema (ER Diagram)

Five entities capture the full lifecycle of a claim — from member identity through document ingestion, adjudication result, and audit trail.

```mermaid
erDiagram
    MEMBERS {
        string id PK "e.g., EMP001"
        string name
        string policy_number
        date join_date
        float annual_limit_remaining
        string status "ACTIVE / INACTIVE"
    }

    CLAIMS {
        string id PK "e.g., CLM_XXXXX"
        string member_id FK
        string patient_name
        float claim_amount
        string status "PENDING / APPROVED / REJECTED / PARTIAL / MANUAL_REVIEW"
        string hospital_name
        boolean cashless_request
        date treatment_date
        timestamp submitted_at
        timestamp updated_at
    }

    CLAIM_DOCUMENTS {
        int id PK
        string claim_id FK
        string document_type "PRESCRIPTION / BILL / LAB_REPORT / OTHER"
        string file_path
        string file_name
        int file_size
        json extracted_data
        text raw_llm_response
    }

    ADJUDICATION_RESULTS {
        int id PK
        string claim_id FK "Unique"
        string decision "APPROVED / REJECTED / PARTIAL / MANUAL_REVIEW"
        float approved_amount
        float confidence_score
        json reasons "List of strings"
        json flags "List of strings"
        text notes
        text next_steps
        json policy_engine_log
        timestamp created_at
    }

    AUDIT_LOGS {
        int id PK
        string claim_id FK
        string action "e.g., CLAIM_SUBMITTED, OCR_EXTRACTED"
        timestamp timestamp
        text details
    }

    MEMBERS ||--o{ CLAIMS : "submits"
    CLAIMS ||--o{ CLAIM_DOCUMENTS : "contains"
    CLAIMS ||--|| ADJUDICATION_RESULTS : "produces"
    CLAIMS ||--o{ AUDIT_LOGS : "records"
```

### Relationships

| Relationship | Cardinality | Description |
|---|---|---|
| `MEMBERS` → `CLAIMS` | One-to-many | A member can submit multiple claims |
| `CLAIMS` → `CLAIM_DOCUMENTS` | One-to-many | A claim can have multiple supporting documents |
| `CLAIMS` → `ADJUDICATION_RESULTS` | One-to-one | Each claim produces exactly one adjudication result |
| `CLAIMS` → `AUDIT_LOGS` | One-to-many | Every state change on a claim is logged |

---

## Claim Decision Flow

The adjudication engine processes each submitted claim through three sequential stages: deterministic eligibility checks, AI-powered medical necessity review, and a confidence threshold gate before final status assignment.

```mermaid
graph TD
    Start(["Claim Submitted"]) --> Upload["Save Documents & Metadata"]
    Upload --> OCR["Gemini Multimodal OCR & Extraction"]
    OCR --> DeterministicChecks{"Run Deterministic Checks"}

    DeterministicChecks -->|"Failed: Member Inactive / Waiting Period / Per-claim Exceeded"| Reject["Set Status: REJECTED"]
    DeterministicChecks -->|"Passed: Basic Eligibility Met"| AICheck{"Run Gemini AI Adjudication"}

    AICheck -->|"Exclusions Found / Lack of Medical Necessity"| AIReject["Set Status: REJECTED or PARTIAL"]
    AICheck -->|"Valid & Medically Necessary"| CalcLimits["Calculate Limits & Copays / Discounts"]

    CalcLimits --> ConfidenceCheck{"Evaluate Composite Confidence"}

    ConfidenceCheck -->|"Confidence < 70% or Fraud Flags"| Review["Set Status: MANUAL_REVIEW"]
    ConfidenceCheck -->|"Confidence >= 70% & No Flags"| Approve["Set Status: APPROVED or PARTIAL"]

    Approve --> UpdateLimit["Deduct Approved Amount from YTD Limit"]
    UpdateLimit --> Log["Record Adjudication & Update Status"]

    Reject --> Log
    AIReject --> Log
    Review --> Log

    Log --> End(["Processing Complete"])

    classDef process fill:#DBEAFE,color:#1E40AF,stroke:#3B82F6;
    classDef decision fill:#FEF3C7,color:#92400E,stroke:#F59E0B;
    classDef terminal fill:#FEE2E2,color:#991B1B,stroke:#EF4444;
    classDef start fill:#D1FAE5,color:#065F46,stroke:#10B981;

    class Start,End start;
    class DeterministicChecks,AICheck,ConfidenceCheck decision;
    class Upload,OCR,CalcLimits,UpdateLimit,Log process;
    class Reject,AIReject,Review,Approve terminal;
```

### Decision Stages

**Stage 1 — Deterministic Checks**
Hard policy rules evaluated before any AI call. A failure here results in an immediate rejection.

| Check | Fail Condition |
|---|---|
| Member status | Member is `INACTIVE` |
| Waiting period | Treatment date is within the policy's waiting window |
| Per-claim limit | Claimed amount exceeds the maximum allowable per single claim |

**Stage 2 — Gemini AI Adjudication**
Gemini 2.5 Flash reviews the extracted document data against policy exclusions and assesses medical necessity.

| Outcome | Description |
|---|---|
| `REJECTED` | Claim falls under a policy exclusion |
| `PARTIAL` | Partial medical necessity — only a portion of the claim is valid |
| Passes | Claim is valid and medically necessary → proceeds to limit calculation |

**Stage 3 — Confidence Gate**
A composite confidence score is computed from OCR quality, AI certainty, and policy match strength.

| Score | Fraud Flags | Final Status |
|---|---|---|
| ≥ 70% | None | `APPROVED` or `PARTIAL` |
| < 70% | Any | `MANUAL_REVIEW` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI (Python) |
| ORM | SQLAlchemy |
| Database | SQLite (dev) / PostgreSQL (prod) |
| AI / OCR | Google Gemini 2.5 Flash (multimodal) |
| Document types | Prescriptions, hospital bills, lab reports |
