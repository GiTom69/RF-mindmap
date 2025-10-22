import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load the API key from your .env file
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

if not gemini_key:
    print("Error: GEMINI_API_KEY not found in .env file.")
else:
    try:
        genai.configure(api_key=gemini_key)

        print("--- Finding Context Limits for Available Models ---")
        
        for m in genai.list_models():
            # We only care about models that can generate content
            if 'generateContent' in m.supported_generation_methods:
                # The property for the context window is 'input_token_limit'
                limit = m.input_token_limit
                print(f"Model: {m.name:<40} | Context Limit: {limit:,} tokens")

    except Exception as e:
        print(f"An error occurred while trying to connect to the API: {e}")