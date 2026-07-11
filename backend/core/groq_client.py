import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    groq_client = Groq(api_key=api_key)
else:
    groq_client = None
    print("Warning: GROQ_API_KEY not found. LLM features will be disabled.")
