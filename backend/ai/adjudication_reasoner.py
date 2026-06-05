import json
import logging
import time
from typing import Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from google.genai import types
from google.genai.errors import APIError

from backend.ai.gemini_client import get_gemini_client, get_model_name

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic schema for Gemini Adjudication Output
class GeminiAdjudicationOutput(BaseModel):
    decision: str = Field(description="The adjudication decision. Must be one of: 'APPROVED', 'REJECTED', 'PARTIAL', 'MANUAL_REVIEW'.")
    confidence: float = Field(description="The confidence score of the decision between 0.0 and 1.0.")
    reasons: List[str] = Field(description="List of detailed reasons supporting the decision or explanations for rejections/deductions.")
    flags: List[str] = Field(description="List of warning flags, red flags, or fraud indicators detected.")
    covered_amount: float = Field(description="The approved/covered claim amount in INR after applying discounts, copays, exclusions, and limits.")
    notes: str = Field(description="Additional observations or notes explaining calculations (e.g., how copay or discount was applied).")
    next_steps: str = Field(description="Actionable next steps for the patient/claimant.")

def clean_json_string(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def run_ai_adjudication(
    claim_details: Dict[str, Any],
    extracted_data: List[Dict[str, Any]],
    policy_terms: Dict[str, Any],
    adjudication_rules: str,
    deterministic_checks: Dict[str, Any],
    retries: int = 3,
    backoff_factor: float = 2.0
) -> GeminiAdjudicationOutput:
    """
    Evaluates policy coverage, medical necessity, and calculates benefits using Gemini 2.5 Flash.
    """
    client = get_gemini_client()
    model = get_model_name()
    
    # Construct context for the LLM
    context = {
        "claim": claim_details,
        "extracted_documents_data": extracted_data,
        "policy_terms": policy_terms,
        "deterministic_check_results": deterministic_checks
    }
    
    prompt = (
        f"You are a Senior Insurance Claims Adjudication Specialist and Medical Officer. "
        f"Your task is to adjudicate the following OPD insurance claim. "
        f"Analyze the inputs carefully, cross-referencing the policy terms and adjudication rules.\n\n"
        f"### INPUT DATA (Claim details, Extracted Document fields, Policy Terms, and Rule Results):\n"
        f"{json.dumps(context, indent=2)}\n\n"
        f"### ADJUDICATION RULES REFERENCE:\n"
        f"{adjudication_rules}\n\n"
        f"### CRITICAL ADJUDICATION INSTRUCTIONS:\n"
        f"1. **Check Exclusions**: Verify if the diagnosis is in the policy exclusions (e.g., cosmetic whitening, weight loss).\n"
        f"2. **Check Medical Necessity**: Verify if the prescription, tests, or procedures are standard, necessary, and matching the diagnosis.\n"
        f"3. **Check Limits**: Verify that charges are within the policy category sub-limits (e.g., dental sub-limit: ₹10,000, consultation sub-limit: ₹2,000, vision: ₹5,000, alternative medicine: ₹8,000).\n"
        f"4. **Apply Discounts & Copays**:\n"
        f"   - If it's a network hospital AND cashless request is true: Apply 20% network discount to the total claim, and approve remaining as cashless. (Do not apply copay to cashless network claims).\n"
        f"   - If standard consultation reimbursement: Apply 10% copay to the entire claim if a consultation is present.\n"
        f"   - If dental/alternative medicine/diagnostic (without consultation): Apply no copay unless explicitly specified.\n"
        f"5. **Determine Decision**:\n"
        f"   - APPROVED: If all items are covered and valid.\n"
        f"   - PARTIAL: If some items are covered and some are excluded or exceed limits (calculate approved amount accordingly).\n"
        f"   - REJECTED: If the entire claim violates eligibility, waiting periods, per-claim limits (claim_amount > 5000), or is a major exclusion.\n"
        f"   - MANUAL_REVIEW: If confidence < 0.70, or fraud/unusual patterns are detected (e.g. multiple claims same day).\n"
        f"6. **Calculate Covered Amount**: Provide the exact approved amount after all calculations.\n"
        f"7. **Set Confidence**: Assess the decision's reliability. If anything is ambiguous, set confidence < 0.70 to trigger manual review.\n\n"
        f"Evaluate the data and return the structured JSON output."
    )
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GeminiAdjudicationOutput,
        temperature=0.1
    )
    
    attempt = 0
    delay = 1.0
    
    while attempt < retries:
        try:
            logger.info(f"Running AI Adjudication, attempt {attempt + 1}")
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            
            clean_json = clean_json_string(response.text)
            parsed_output = GeminiAdjudicationOutput.model_validate_json(clean_json)
            
            # If the deterministic check has already failed or flagged something, override if appropriate
            # or merge the flags/reasons.
            # Example: If a deterministic rule rejected the claim, we must respect it.
            if not deterministic_checks.get("eligible", True):
                parsed_output.decision = "REJECTED"
                parsed_output.covered_amount = 0.0
                for err in deterministic_checks.get("errors", []):
                    if err not in parsed_output.reasons:
                        parsed_output.reasons.append(err)
            
            return parsed_output
            
        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning(f"Adjudication JSON validation failed on attempt {attempt + 1}: {str(e)}")
            attempt += 1
            if attempt == retries:
                break
            time.sleep(delay)
            delay *= backoff_factor
            
        except APIError as e:
            logger.error(f"Gemini API error on adjudication: {str(e)}")
            attempt += 1
            if attempt == retries:
                raise e
            time.sleep(delay)
            delay *= backoff_factor
            
    # Fallback to MANUAL REVIEW if AI failed to return valid JSON
    logger.error("AI Adjudication failed. Routing claim to MANUAL_REVIEW.")
    reasons = ["AI Adjudication failed to generate valid results."]
    if not deterministic_checks.get("eligible", True):
        reasons.extend(deterministic_checks.get("errors", []))
        decision = "REJECTED"
        covered_amount = 0.0
    else:
        decision = "MANUAL_REVIEW"
        covered_amount = 0.0
        
    return GeminiAdjudicationOutput(
        decision=decision,
        confidence=0.50,
        reasons=reasons,
        flags=["AI_ENGINE_FAILURE"],
        covered_amount=covered_amount,
        notes="Fallback applied due to processing exception.",
        next_steps="Refer to insurance claims operations desk for manual processing."
    )
