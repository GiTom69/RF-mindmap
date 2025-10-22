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

        print("--- Finding available models for 'generateContent' ---")
        
        found_model = False
        for m in genai.list_models():
            # Check if the model supports the method our script uses
            if 'generateContent' in m.supported_generation_methods:
                print(f"Found compatible model: {m.name}")
                found_model = True
        
        if not found_model:
            print("\nCould not find any models compatible with 'generateContent'.")
            print("Please check your API key and project permissions in Google AI Studio.")

    except Exception as e:
        print(f"An error occurred while trying to connect to the API: {e}")