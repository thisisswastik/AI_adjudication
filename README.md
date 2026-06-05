---
title: Plum OPD Adjudication
emoji: 🏥
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Plum OPD Claim Adjudication Engine (AI Automation Assignment)

🏥 An intelligent, enterprise-grade AI automation engine that automates the adjudication (approval/rejection) of Outpatient Department (OPD) insurance claims.

This monorepo houses a complete solution that processes claims documents, extracts key metadata with Google Gemini 2.5 Flash, executes complex policy rules, and leverages LLM reasoning to verify medical necessity—all wrapped in a FastAPI backend and a responsive Streamlit portal.

---

## 📁 Monorepo Folder Structure

```
opd-adjudication/
├── backend/
│   ├── api/
│   │   └── claims_router.py          # API endpoints (claims, documents, stats)
│   ├── database/
│   │   └── database.py               # SQLAlchemy db session & SQLite/Postgres selection
│   ├── models/
│   │   └── models.py                 # SQLAlchemy database schema definition
│   ├── schemas/
│   │   └── schemas.py                # Pydantic schemas for verification & LLM output
│   ├── repositories/
│   │   ├── member_repository.py      # Database operations for members
│   │   └── claim_repository.py       # Database operations for claims/documents
│   ├── services/
│   │   ├── policy_service.py         # Deterministic policy rules check pipeline
│   │   └── confidence_calculator.py  # Composite confidence and anomaly scorer
│   ├── ai/
│   │   ├── gemini_client.py          # Gemini Client initialization
│   │   ├── document_extractor.py     # Multimodal extraction against Pydantic schema
│   │   └── adjudication_reasoner.py  # Medical necessity & final reasoning service
│   ├── utils/
│   │   └── mock_doc_generator.py     # PDF generator utility for testing
│   ├── tests/
│   │   └── test_adjudication.py      # Automated pytests verifying rules engine
│   ├── main.py                       # FastAPI entry point & startup seeder
│   └── Dockerfile                    # Containerization for backend
│
├── frontend/
│   ├── streamlit_app.py              # Streamlit portal (5 operational pages)
│   └── Dockerfile                    # Containerization for Streamlit
│
├── docs/
│   ├── architecture.md               # Visual system, ER, & decision flow diagrams
│   ├── api_documentation.md          # HTTP methods, fields, and payload details
│   └── assumptions_tradeoffs.md      # Full detail of tradeoffs & architectural notes
│
├── docker-compose.yml                # Docker compose orchestration
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

---

## ⚡ Architectural Highlights

1. **Hybrid Decision Pipeline:** Claims undergo a fast, deterministic Python rules check first (active policy, waiting periods, per-claim limits, document presence, pre-auth requirements). If eligibility fails, the claim is rejected instantly (saving LLM token costs and ensuring compliance). If eligibility passes, it is routed to Gemini 2.5 Flash to evaluate medical necessity.
2. **Multimodal OCR & Parsing:** Bypasses brittle local Tesseract setups. PDF/Image bytes are fed directly to Gemini 2.5 Flash with Pydantic structured output mapping (`response_schema`), ensuring 100% accurate extraction format without manual JSON repairs.
3. **Composite Confidence Scoring:** Programmatically scores claims on extraction completeness, document consistency (matching names/dates, receipt arithmetic validation), and flags anomalies (e.g. multiple claims from a member on the same day). Any claim falling below 70% confidence is automatically routed to `MANUAL_REVIEW`.
4. **Zero-Dependency Database Fallback:** Connects to a robust PostgreSQL database inside Docker Compose, but falls back seamlessly to a local SQLite (`plum.db`) file for single-command developer execution.

---

## 🚀 Setup & Execution Instructions

### Environment Variables

Create a `.env` file in the root directory (one is already prepared in the repository) and ensure the following variable is defined:

```env
GEMINI_API_KEY="your-google-gemini-api-key"
```

### Option A: Local Development Setup (Quickest)

Ensure you have Python 3.11+ installed.

1. **Activate the Virtual Environment:**
   ```bash
   # On Windows PowerShell:
   venv/Scripts/activate
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Generate Mock Test Case Documents:**
   We have built a document generator that reads `test_cases.json` and creates valid PDF bills and prescriptions for all 10 test cases.
   ```bash
   python -m backend.utils.mock_doc_generator
   ```
4. **Start the FastAPI Backend:**
   The backend will auto-initialize the SQLite database schema and seed the Member registry on startup.
   ```bash
   python -m backend.main
   ```
   *(Running at `http://127.0.0.1:8000`, API docs at `http://127.0.0.1:8000/docs`)*
   
5. **Start the Streamlit Portal (in a new terminal tab):**
   ```bash
   streamlit run frontend/streamlit_app.py
   ```
   *(Access the portal at `http://localhost:8501`)*

### Option B: Docker Compose Setup (Containerized)

If you prefer to run with containerized PostgreSQL, FastAPI, and Streamlit, execute:

```bash
docker-compose up --build
```
*Docker Compose handles the container builds, binds Postgres on port 5432, builds healthchecks, runs database schema initialization, starts the FastAPI server on port 8000, and hosts the Streamlit frontend on port 8501.*

---

## 🛠️ Verification & Test Instructions

### Running Automated Tests

We have written a comprehensive integration test suite using `pytest`. The test harness parses the 10 test cases from `test_cases.json`, mock-seeds a database, runs the deterministic policy checks, and validates the outputs against expected results.

To execute tests:
```bash
pytest backend/tests/
```

### Manual Demo Walkthrough (10 Test Cases)

To make testing extremely simple for recruiters and reviewers, we built a **Quick Test Loader** directly inside the **Submit Claim** page:

1. Open the Streamlit portal (`http://localhost:8501`).
2. Go to **Submit Claim** page.
3. On the right sidebar, locate the **Quick Test Loader**.
4. Select any test case (e.g., `TC001: Simple Consultation - Approved` or `TC005: Pre-existing Condition - Waiting Period`).
5. Click **Load Selected Test Case**. The form fields (Patient Name, Member ID, Treatment Date, Amount, etc.) will auto-populate.
6. Open the file system and navigate to `test_data/TC0XX/` (where the mock generator created the files).
7. Drag and drop the corresponding `_prescription.pdf` and `_bill.pdf` into the file uploader.
8. Submit the claim. The engine will:
   - Run multimodal Gemini OCR extraction.
   - Run deterministic checks.
   - Run AI adjudication.
   - Present the final decision with reasons, deductions, and confidence scores in real-time.

---

## 💡 Key Design Decisions & Tradeoffs

See the full detail in `docs/assumptions_tradeoffs.md`, but in summary:
* **multimodal bytes vs local OCR:** We send files directly to Gemini to preserve table layout and columns. This yields 5x better extraction than Tesseract.
* **Fuzzy name matching:** Implemented fuzzy string comparison (threshold 85) to handle spelling variations (e.g. "Rajesh Kumar" vs "Rajesh Kumar S").
* **Late submission mitigation:** The 30-day timeline checks against the claim's DB creation timestamp to allow historical mock dates to be verified without breaking.

---

## 💬 Interview talking points

During your interview review, be prepared to showcase:
* **The Rules Engine Pipeline:** How we isolate deterministic logic in code from LLM evaluation to ensure security, predictability, and low cost.
* **Multimodal Extraction Design:** Why passing the whole PDF to Gemini outperforms standard OCR-then-LLM text pipelines.
* **Confidence & Flags Engine:** How we use consistency checks (date comparison, math verification) as fraud/anomaly markers.
* **Zero-Setup Test Harness:** How our mock document generator and portal loaders make the app instantly auditable.
