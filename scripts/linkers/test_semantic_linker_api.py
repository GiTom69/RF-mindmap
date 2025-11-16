"""
Quick test to verify Gemini API works in semantic linker context
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import as the semantic linker does
try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    import os
    GEMINI_AVAILABLE = True
    # Load .env from project root
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    load_dotenv(PROJECT_ROOT / ".env")
    print(f"✓ Project root: {PROJECT_ROOT}")
    print(f"✓ .env file exists: {(PROJECT_ROOT / '.env').exists()}")
except ImportError as e:
    GEMINI_AVAILABLE = False
    print(f"✗ Import failed: {e}")
    sys.exit(1)

def test_api_key():
    """Test if API key is loaded"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("✗ GEMINI_API_KEY not found in environment")
        return False
    
    print(f"✓ GEMINI_API_KEY loaded: {api_key[:20]}...{api_key[-10:]}")
    print(f"  Key length: {len(api_key)} characters")
    return api_key

def test_api_connection(api_key):
    """Test if API connection works"""
    try:
        genai.configure(api_key=api_key)
        print("✓ Gemini API configured")
        
        # Test with gemini-2.5-flash (the model used in semantic linker)
        model = genai.GenerativeModel('gemini-2.5-flash')
        print("✓ Model 'gemini-2.5-flash' initialized")
        
        # Simple test
        response = model.generate_content("Say 'API works!'")
        print(f"✓ API Response: {response.text}")
        
        return True
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False

def test_topic_naming_simulation():
    """Simulate the topic naming function"""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Simulate a topic naming request
        prompt = """You are an expert at analyzing technical concepts and creating concise, descriptive topic names.
For each cluster of related concepts below, generate a SHORT (1-4 words) topic name that best describes the theme.
The name should be specific, technical, and capture the essence of what these concepts have in common.
Return ONLY the topic names, one per line, in the same order as provided.

Cluster 1 (5 concepts):
Amplitude Modulation, Frequency Modulation, Phase Modulation, Quadrature Amplitude Modulation, Frequency Shift Keying

Cluster 2 (4 concepts):
Low-Noise Amplifier, Power Amplifier, Variable Gain Amplifier, Operational Amplifier"""
        
        response = model.generate_content(prompt)
        print("\n" + "="*60)
        print("TOPIC NAMING SIMULATION")
        print("="*60)
        print("Generated topic names:")
        print(response.text)
        print("="*60)
        
        return True
    except Exception as e:
        print(f"✗ Topic naming simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("SEMANTIC LINKER API TEST")
    print("="*60)
    print()
    
    if not GEMINI_AVAILABLE:
        print("✗ Gemini dependencies not available")
        return
    
    # Test 1: API Key
    print("[1/3] Testing API Key Loading...")
    api_key = test_api_key()
    if not api_key:
        return
    print()
    
    # Test 2: API Connection
    print("[2/3] Testing API Connection...")
    if not test_api_connection(api_key):
        return
    print()
    
    # Test 3: Topic Naming
    print("[3/3] Testing Topic Naming (as used in semantic linker)...")
    if not test_topic_naming_simulation():
        return
    print()
    
    print("="*60)
    print("✓ ALL TESTS PASSED!")
    print("The Gemini API is ready to use in the semantic linker script.")
    print("="*60)

if __name__ == "__main__":
    main()
