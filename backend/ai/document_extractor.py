import json
import time
import logging
from typing import Dict, Any, Tuple, Optional, Type
from pydantic import BaseModel, ValidationError
from google.genai import types
from google.genai.errors import APIError

from backend.ai.gemini_client import get_gemini_client, get_model_name
from backend.schemas.schemas import PrescriptionExtraction, BillExtraction, LabReportExtraction

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback schema for "Other" document types
class GenericExtraction(BaseModel):
    document_date: Optional[str] = None # YYYY-MM-DD
    patient_name: Optional[str] = None
    institution_name: Optional[str] = None
    summary: str
    total_amount: Optional[float] = None
    key_findings: Optional[str] = None

def get_schema_for_doc_type(doc_type: str) -> Type[BaseModel]:
    doc_type_lower = doc_type.lower()
    if "prescription" in doc_type_lower:
        return PrescriptionExtraction
    elif "bill" in doc_type_lower or "invoice" in doc_type_lower or "receipt" in doc_type_lower:
        return BillExtraction
    elif "report" in doc_type_lower or "lab" in doc_type_lower or "diagnostic" in doc_type_lower:
        return LabReportExtraction
    else:
        return GenericExtraction

def clean_json_string(text: str) -> str:
    """Repairs and extracts clean JSON from markdown code blocks if necessary."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def extract_document_data(
    file_bytes: bytes, 
    mime_type: str, 
    doc_type: str, 
    retries: int = 3, 
    backoff_factor: float = 2.0
) -> Tuple[Dict[str, Any], str, float]:
    """
    Extracts structured data from medical documents using Gemini 2.5 Flash.
    Returns: (parsed_json_dict, raw_response_text, extraction_confidence)
    """
    client = get_gemini_client()
    model = get_model_name()
    schema = get_schema_for_doc_type(doc_type)
    
    # Prompt setup
    prompt = (
        f"You are an expert insurance claims document processor. "
        f"Extract information from this medical {doc_type} according to the provided schema. "
        f"Ensure all names, dates, amounts, and medical terms are transcribed with 100% precision. "
        f"If a value is not visible or cannot be found, leave it as null/empty. "
        f"Double-check doctor registration numbers and billing items."
    )
    
    # Multimodal parts
    contents = [
        types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type
        ),
        prompt
    ]
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=0.1 # Low temperature for structured extraction
    )
    
    raw_response = ""
    attempt = 0
    delay = 1.0
    
    while attempt < retries:
        try:
            logger.info(f"Extracting {doc_type} data, attempt {attempt + 1}")
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            raw_response = response.text
            clean_json = clean_json_string(raw_response)
            
            # Validate with Pydantic
            parsed_data = schema.model_validate_json(clean_json)
            parsed_dict = parsed_data.model_dump()
            
            # Calculate extraction confidence
            # Since Gemini 2.5 Flash generated it under response_schema, structure is guaranteed.
            # We estimate extraction confidence based on completeness of required fields
            filled_fields = 0
            total_fields = 0
            
            # Simple heuristic for completeness
            for k, v in parsed_dict.items():
                total_fields += 1
                if v is not None and v != "" and v != []:
                    filled_fields += 1
            
            completeness_ratio = (filled_fields / total_fields) if total_fields > 0 else 1.0
            # Base confidence on successful API validation and completeness
            extraction_confidence = min(0.95, 0.70 + (completeness_ratio * 0.25))
            
            return parsed_dict, raw_response, extraction_confidence
            
        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning(f"JSON validation failed on attempt {attempt + 1}: {str(e)}")
            # Try to repair the JSON via prompt retry
            attempt += 1
            if attempt == retries:
                # If all retries fail, return a fallback empty/partially parsed structure
                break
            time.sleep(delay)
            delay *= backoff_factor
            
        except APIError as e:
            logger.error(f"Gemini API error on attempt {attempt + 1}: {str(e)}")
            attempt += 1
            if attempt == retries:
                raise e
            time.sleep(delay)
            delay *= backoff_factor
            
        except Exception as e:
            logger.error(f"Unexpected error during extraction: {str(e)}")
            attempt += 1
            if attempt == retries:
                raise e
            time.sleep(delay)
            delay *= backoff_factor
            
    # Fallback return in case of persistent validation failure
    logger.error("Failed to parse document extraction JSON after maximum retries. Routing to manual review.")
    
    # Return empty representation of the schema
    try:
        empty_instance = schema.model_validate({})
        return empty_instance.model_dump(), raw_response or "{}", 0.50
    except Exception:
        # If schema requires fields, return a manual fallback dict
        return {"patient_name": None, "error": "Extraction failure"}, raw_response or "{}", 0.30
