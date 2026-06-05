import os
from google import genai
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Get api key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # We can default to checking a local key or raising error
    raise ValueError("GEMINI_API_KEY environment variable is not set")

# Initialize client
client = genai.Client(api_key=api_key)

def get_gemini_client() -> genai.Client:
    return client

def get_model_name() -> str:
    return "gemini-2.5-flash"
