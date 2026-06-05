import os
import streamlit as st
import requests
import datetime
import pandas as pd
import json
import plotly.express as px

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Plum OPD Adjudication Portal",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper function to query the API
def api_get(endpoint: str, params: dict = None, timeout: float = 10.0):
    try:
        url_prefix = "" if endpoint == "/health" else "/api"
        # Use a smaller timeout for health check to fail fast on boot
        actual_timeout = 3.0 if endpoint == "/health" else timeout
        response = requests.get(f"{BACKEND_URL}{url_prefix}{endpoint}", params=params, timeout=actual_timeout)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Failed to connect to backend API: {str(e)}")
        return None

def api_post(endpoint: str, data: dict = None, files: dict = None, timeout: float = 90.0):
    try:
        url_prefix = "" if endpoint == "/health" else "/api"
        response = requests.post(f"{BACKEND_URL}{url_prefix}{endpoint}", data=data, files=files, timeout=timeout)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"API Error ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        st.error(f"Failed to connect to backend API: {str(e)}")
        return None

# Load test cases json if it exists
@st.cache_data
def load_test_cases():
    test_cases_path = "c:/Users/swastik/Desktop/plum/test_cases.json"
    if os.path.exists(test_cases_path):
        with open(test_cases_path, "r", encoding="utf-8") as f:
            return json.load(f).get("test_cases", [])
    return []

# App Header
st.sidebar.markdown(
    "<h2 style='text-align: center; color: #4F46E5;'>🏥 Plum OPD</h2>"
    "<p style='text-align: center; font-size: 0.85em; color: #6B7280;'>AI OPD Claims Adjudication Portal</p>"
    "<hr style='margin-top: 5px; margin-bottom: 20px;'>",
    unsafe_allow_html=True
)

# Sidebar Navigation
menu_options = [
    "📤 Submit Claim", 
    "🔍 Claim Status", 
    "📋 Claim Details", 
    "📜 Claims History", 
    "📊 Admin Dashboard"
]
choice = st.sidebar.radio("Navigation Menu", menu_options)

# Main container styling
st.markdown(
    """
    <style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E293B; margin-bottom: 5px; }
    .sub-header { font-size: 1.1rem; color: #64748B; margin-bottom: 25px; }
    .status-badge { padding: 4px 10px; border-radius: 4px; font-weight: 600; font-size: 0.85em; display: inline-block; }
    .badge-approved { background-color: #DCFCE7; color: #15803D; }
    .badge-partial { background-color: #FEF9C3; color: #A16207; }
    .badge-rejected { background-color: #FEE2E2; color: #B91C1C; }
    .badge-review { background-color: #DBEAFE; color: #1E40AF; }
    .badge-pending { background-color: #F3F4F6; color: #4B5563; }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------- PAGE 1: SUBMIT CLAIM -----------------
if choice == "📤 Submit Claim":
    st.markdown("<div class='main-header'>Submit OPD Claim</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Upload medical bills and doctor prescriptions to process a reimbursement.</div>", unsafe_allow_html=True)
    
    # Check if backend is alive
    health = api_get("/health")
    if not health:
        st.warning("⚠️ Backend server is offline. Please make sure uvicorn is running.")
        
    test_cases = load_test_cases()
    
    col_left, col_right = st.columns([2, 1])
    
    with col_right:
        st.markdown("### ⚡ Quick Test Loader")
        st.write("Load parameters from predefined assignment test cases to quickly fill the form:")
        
        if test_cases:
            tc_names = [f"{tc['case_id']}: {tc['case_name']}" for tc in test_cases]
            selected_tc_idx = st.selectbox("Select Test Case Template", range(len(tc_names)), format_func=lambda x: tc_names[x])
            
            if st.button("Load Selected Test Case"):
                tc_data = test_cases[selected_tc_idx]
                st.session_state["member_id"] = tc_data["input_data"]["member_id"]
                st.session_state["patient_name"] = tc_data["input_data"]["member_name"]
                st.session_state["claim_amount"] = float(tc_data["input_data"]["claim_amount"])
                st.session_state["treatment_date"] = datetime.datetime.strptime(tc_data["input_data"]["treatment_date"], "%Y-%m-%d").date()
                st.session_state["hospital_name"] = tc_data["input_data"].get("hospital", "")
                st.session_state["cashless_request"] = tc_data["input_data"].get("cashless_request", False)
                st.session_state["selected_tc"] = tc_data
                st.success(f"Loaded parameters for {tc_data['case_id']}!")
        else:
            st.info("No test cases found in test_cases.json")
            
    with col_left:
        st.markdown("### 📋 Claim Fields")
        
        # Form inputs without st.form to allow interactive rerun on file upload
        member_id = st.text_input(
            "Patient Member ID (e.g. EMP001)", 
            value=st.session_state.get("member_id", "")
        )
        patient_name = st.text_input(
            "Patient Name", 
            value=st.session_state.get("patient_name", "")
        )
        claim_amount = st.number_input(
            "Total Claimed Amount (₹)", 
            min_value=0.0, 
            value=st.session_state.get("claim_amount", 0.0)
        )
        treatment_date = st.date_input(
            "Date of Treatment", 
            value=st.session_state.get("treatment_date", datetime.date.today())
        )
        hospital_name = st.text_input(
            "Hospital / Clinic Name (Optional)", 
            value=st.session_state.get("hospital_name", "")
        )
        cashless_request = st.checkbox(
            "Request Cashless Facility (Network Only)", 
            value=st.session_state.get("cashless_request", False)
        )
        
        st.markdown("### 📁 Document Attachments")
        st.write("You must upload at least a Prescription and a Bill. Supported: PDF, PNG, JPG.")
        
        uploaded_files = st.file_uploader(
            "Upload Medical Files", 
            type=["pdf", "png", "jpg", "jpeg"], 
            accept_multiple_files=True
        )
        
        # We also let the user designate types for uploaded files dynamically
        doc_type_mapping = {}
        if uploaded_files:
            st.write("Specify Document Types for each file:")
            for f in uploaded_files:
                doc_type_mapping[f.name] = st.selectbox(
                    f"Type for: {f.name}", 
                    ["Prescription", "Bill", "Lab Report", "Other"],
                    key=f"type_{f.name}"
                )
        
        submit_button = st.button("Submit Claim for Adjudication", type="primary")
            
        if submit_button:
            if not member_id or not patient_name or claim_amount <= 0:
                st.error("Please fill in Member ID, Patient Name, and a valid Claim Amount.")
            elif not uploaded_files:
                st.error("Please upload at least one document (Prescription/Bill) to proceed.")
            else:
                # 1. Create Claim Record
                with st.spinner("Creating claim record..."):
                    payload = {
                        "member_id": member_id,
                        "patient_name": patient_name,
                        "claim_amount": claim_amount,
                        "treatment_date": treatment_date.strftime("%Y-%m-%d"),
                        "hospital_name": hospital_name or "",
                        "cashless_request": str(cashless_request).lower()
                    }
                    
                    claim = api_post("/claims", data=payload)
                    
                if claim:
                    claim_id = claim["id"]
                    st.success(f"Claim record created successfully! ID: {claim_id}")
                    
                    # 2. Upload each document
                    upload_success = True
                    for f in uploaded_files:
                        with st.spinner(f"Extracting fields from {f.name} using Gemini..."):
                            doc_type = doc_type_mapping[f.name]
                            
                            files = {"file": (f.name, f.getvalue(), f.type)}
                            form_data = {"document_type": doc_type}
                            
                            doc_res = api_post(f"/claims/{claim_id}/documents", data=form_data, files=files)
                            if not doc_res:
                                upload_success = False
                                st.error(f"Failed to process document: {f.name}")
                                
                    if upload_success:
                        st.info("All documents uploaded and processed. Initializing AI Adjudication...")
                        
                        # 3. Adjudicate
                        with st.spinner("Evaluating policy terms and medical necessity..."):
                            adjudicate_res = api_post(f"/claims/{claim_id}/adjudicate")
                            
                        if adjudicate_res:
                            st.balloons()
                            st.session_state["last_claim_id"] = claim_id
                            
                            decision = adjudicate_res["decision"]
                            if decision == "APPROVED":
                                st.success(f"Claim APPROVED! Approved Amount: ₹{adjudicate_res['approved_amount']}. Confidence: {int(adjudicate_res['confidence_score']*100)}%")
                            elif decision == "PARTIAL":
                                st.warning(f"Claim PARTIALLY Approved. Approved Amount: ₹{adjudicate_res['approved_amount']}. Rejections: {', '.join(adjudicate_res['reasons'])}")
                            elif decision == "REJECTED":
                                st.error(f"Claim REJECTED. Reasons: {', '.join(adjudicate_res['reasons'])}")
                            else:
                                st.info("Claim routed to MANUAL_REVIEW. Reasons/Flags: " + ", ".join(adjudicate_res["flags"]))
                                
                            st.write(f"View full decision details in **Claim Details** page. Claim ID: `{claim_id}`")

# ----------------- PAGE 2: CLAIM STATUS -----------------
elif choice == "🔍 Claim Status":
    st.markdown("<div class='main-header'>Track Claim Status</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Check the live processing status and timeline of a submitted claim.</div>", unsafe_allow_html=True)
    
    claims = api_get("/claims")
    claim_ids = [c["id"] for c in claims] if claims else []
    
    default_id = st.session_state.get("last_claim_id", "")
    default_idx = claim_ids.index(default_id) if default_id in claim_ids else 0
    
    claim_id_input = st.selectbox("Select Claim ID to track", claim_ids) if claim_ids else st.text_input("Enter Claim ID (e.g. CLM_XXXXX)")
    
    if claim_id_input:
        claim = api_get(f"/claims/{claim_id_input}")
        if claim:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            status = claim["status"]
            badge_class = "badge-pending"
            if status == "APPROVED": badge_class = "badge-approved"
            elif status == "PARTIAL": badge_class = "badge-partial"
            elif status == "REJECTED": badge_class = "badge-rejected"
            elif status == "MANUAL_REVIEW": badge_class = "badge-review"
            
            with col1:
                st.metric("Claim ID", claim["id"])
            with col2:
                st.markdown(f"**Current Status:**<br><span class='status-badge {badge_class}'>{status}</span>", unsafe_allow_html=True)
            with col3:
                conf = claim.get("adjudication_result", {}).get("confidence_score", 0.0) if claim.get("adjudication_result") else 0.0
                st.metric("Confidence Score", f"{int(conf * 100)}%" if conf else "N/A")
                
            st.markdown("### ⏱️ Processing Timeline")
            
            # Draw a clean vertical timeline
            for log in sorted(claim.get("audit_logs", []), key=lambda x: x["timestamp"]):
                ts = datetime.datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
                action = log["action"].replace("_", " ")
                details = log["details"]
                
                with st.chat_message("system", avatar="⚙️"):
                    st.write(f"**{ts} - {action}**")
                    st.write(details)
        else:
            st.error("Claim not found.")

# ----------------- PAGE 3: CLAIM DETAILS -----------------
elif choice == "📋 Claim Details":
    st.markdown("<div class='main-header'>Claim Adjudication Details</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Detailed verification, extraction results, rule logs, and decision reasoning.</div>", unsafe_allow_html=True)
    
    claims = api_get("/claims")
    claim_ids = [c["id"] for c in claims] if claims else []
    
    default_id = st.session_state.get("last_claim_id", "")
    default_idx = claim_ids.index(default_id) if default_id in claim_ids else 0
    
    claim_id_input = st.selectbox("Select Claim ID to view details", claim_ids, index=default_idx) if claim_ids else st.text_input("Enter Claim ID")
    
    if claim_id_input:
        claim = api_get(f"/claims/{claim_id_input}")
        if claim:
            status = claim["status"]
            badge_class = "badge-pending"
            if status == "APPROVED": badge_class = "badge-approved"
            elif status == "PARTIAL": badge_class = "badge-partial"
            elif status == "REJECTED": badge_class = "badge-rejected"
            elif status == "MANUAL_REVIEW": badge_class = "badge-review"
            
            st.markdown(
                f"### Claim {claim['id']} "
                f"<span class='status-badge {badge_class}'>{status}</span>", 
                unsafe_allow_html=True
            )
            
            # Tabs for organization
            tab_decision, tab_docs, tab_rules, tab_timeline = st.tabs([
                "📊 Final Decision & Reasoning", 
                "📄 Uploaded Documents & OCR", 
                "⚙️ Policy Rules Logs", 
                "⏱️ Audit Timeline"
            ])
            
            with tab_decision:
                res = claim.get("adjudication_result")
                if res:
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"#### Decision: `{res['decision']}`")
                        st.markdown(f"**Approved Amount:** ₹{res['approved_amount']} (Claimed: ₹{claim['claim_amount']})")
                        
                        st.markdown("**Reasons:**")
                        for r in res["reasons"]:
                            st.write(f"- {r}")
                            
                        if res["flags"]:
                            st.markdown("**Flags & Alerts:**")
                            for f in res["flags"]:
                                st.warning(f"⚠️ {f}")
                                
                        if res.get("notes"):
                            st.markdown("**Explanatory Notes:**")
                            st.info(res["notes"])
                            
                        if res.get("next_steps"):
                            st.markdown("**Next Steps:**")
                            st.write(res["next_steps"])
                            
                    with col2:
                        conf = res["confidence_score"]
                        st.metric("Adjudication Confidence", f"{int(conf * 100)}%")
                        st.progress(conf)
                        if conf >= 0.85:
                            st.success("High Confidence Decision")
                        elif conf >= 0.70:
                            st.warning("Medium Confidence Decision")
                        else:
                            st.error("Low Confidence - Routed for Manual Review")
                else:
                    st.info("Claim has not been adjudicated yet.")
                    if st.button("Run Adjudication Now"):
                        with st.spinner("Processing..."):
                            api_post(f"/claims/{claim['id']}/adjudicate")
                        st.rerun()
                        
            with tab_docs:
                st.markdown("#### Extracted Fields from Gemini OCR")
                for doc in claim.get("documents", []):
                    with st.expander(f"📄 {doc['document_type']} - {doc['file_name']}"):
                        st.write(f"File Size: {round(doc['file_size']/1024, 2)} KB")
                        if doc["extracted_data"]:
                            st.json(doc["extracted_data"])
                        else:
                            st.warning("No structured data extracted yet.")
                            
            with tab_rules:
                st.markdown("#### Deterministic Policy Engine Results")
                res = claim.get("adjudication_result")
                if res and res.get("policy_engine_log"):
                    log = res["policy_engine_log"]
                    st.write(f"**Overall Eligibility:** {'✅ Passed' if log['eligible'] else '❌ Failed'}")
                    
                    if log["errors"]:
                        st.error("Violations:")
                        for err in log["errors"]:
                            st.write(f"- {err}")
                            
                    if log["warnings"]:
                        st.warning("Warnings:")
                        for w in log["warnings"]:
                            st.write(f"- {w}")
                            
                    st.markdown("**Insured Member Context:**")
                    st.json(log.get("member_info", {}))
                else:
                    st.info("No policy logs available (claim not adjudicated yet).")
                    
            with tab_timeline:
                st.markdown("#### Audit Logs")
                df = pd.DataFrame(claim.get("audit_logs", []))
                if not df.empty:
                    df = df.sort_values(by="timestamp")
                    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                    st.table(df[["timestamp", "action", "details"]])
                else:
                    st.write("No audit logs found.")
        else:
            st.error("Claim not found.")

# ----------------- PAGE 4: CLAIMS HISTORY -----------------
elif choice == "📜 Claims History":
    st.markdown("<div class='main-header'>Claims History</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>View, filter, and search all historical OPD claims.</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        status_filter = st.selectbox("Filter Status", ["All", "PENDING", "APPROVED", "REJECTED", "PARTIAL", "MANUAL_REVIEW"])
    with col2:
        search_query = st.text_input("Search (Name / Claim ID)")
        
    params = {}
    if status_filter != "All":
        params["status"] = status_filter
    if search_query:
        params["search"] = search_query
        
    claims = api_get("/claims", params=params)
    
    if claims:
        data = []
        for c in claims:
            data.append({
                "Claim ID": c["id"],
                "Patient Name": c["patient_name"],
                "Member ID": c["member_id"],
                "Amount (₹)": c["claim_amount"],
                "Treatment Date": c["treatment_date"],
                "Status": c["status"],
                "Submitted At": datetime.datetime.fromisoformat(c["submitted_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            })
            
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No claims found matching filters.")

# ----------------- PAGE 5: ADMIN DASHBOARD -----------------
elif choice == "📊 Admin Dashboard":
    st.markdown("<div class='main-header'>Admin Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Executive metrics, approval rates, and processing volumes.</div>", unsafe_allow_html=True)
    
    stats = api_get("/admin/stats")
    
    if stats:
        # Key Metrics Row
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Claims", stats["total_claims"])
        with col2:
            st.metric("Approved / Partial", stats["approved_claims"])
        with col3:
            st.metric("Rejected Claims", stats["rejected_claims"])
        with col4:
            st.metric("Manual Review", stats["manual_review_claims"])
        with col5:
            st.metric("Approval Rate", f"{stats['approval_rate']}%")
            
        st.markdown("---")
        
        col_charts_left, col_charts_right = st.columns(2)
        
        with col_charts_left:
            st.markdown("### Claims by Status")
            status_counts = stats.get("claims_by_status", {})
            if status_counts:
                df_status = pd.DataFrame([
                    {"Status": k, "Count": v} for k, v in status_counts.items()
                ])
                fig1 = px.pie(df_status, names="Status", values="Count", color="Status",
                             color_discrete_map={
                                 "APPROVED": "#10B981",
                                 "PARTIAL": "#FBBF24",
                                 "REJECTED": "#EF4444",
                                 "MANUAL_REVIEW": "#3B82F6",
                                 "PENDING": "#9CA3AF"
                             })
                fig1.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No data available.")
                
        with col_charts_right:
            st.markdown("### Daily Claim Volume")
            volume_data = stats.get("daily_volume", [])
            if volume_data:
                df_vol = pd.DataFrame(volume_data)
                fig2 = px.line(df_vol, x="date", y="count", labels={"date": "Date", "count": "Claims"},
                              markers=True, line_shape="linear")
                fig2.update_traces(line_color="#4F46E5")
                fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No data available.")
                
        st.metric("Average Decision Confidence", f"{int(stats['average_confidence'] * 100)}%")
    else:
        st.warning("Could not load dashboard statistics. Make sure claims are in the database.")
