"""
Test script for Gemini API Key
Tests the API key with detailed debugging output
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Color codes for terminal output (Windows compatible)
try:
    import colorama
    colorama.init()
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    BLUE = colorama.Fore.BLUE
    RESET = colorama.Style.RESET_ALL
except ImportError:
    GREEN = RED = YELLOW = BLUE = RESET = ""

def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*70}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{'='*70}")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")

def print_info(text):
    """Print info message"""
    print(f"  {text}")

def test_imports():
    """Test if required libraries are installed"""
    print_header("Step 1: Testing Required Imports")
    
    results = {}
    
    # Test python-dotenv
    try:
        from dotenv import load_dotenv
        print_success("python-dotenv is installed")
        results['dotenv'] = True
    except ImportError as e:
        print_error(f"python-dotenv not installed: {e}")
        print_info("Install with: pip install python-dotenv")
        results['dotenv'] = False
    
    # Test google-generativeai
    try:
        import google.generativeai as genai
        print_success("google-generativeai is installed")
        print_info(f"Version: {genai.__version__ if hasattr(genai, '__version__') else 'Unknown'}")
        results['genai'] = True
    except ImportError as e:
        print_error(f"google-generativeai not installed: {e}")
        print_info("Install with: pip install google-generativeai")
        results['genai'] = False
    
    return results

def test_env_file():
    """Test if .env file exists and can be loaded"""
    print_header("Step 2: Testing .env File")
    
    from dotenv import load_dotenv
    
    # Find .env file
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    env_file = project_root / ".env"
    
    print_info(f"Script directory: {script_dir}")
    print_info(f"Project root: {project_root}")
    print_info(f"Looking for .env at: {env_file}")
    
    if env_file.exists():
        print_success(f".env file found at: {env_file}")
        print_info(f"File size: {env_file.stat().st_size} bytes")
        print_info(f"Last modified: {datetime.fromtimestamp(env_file.stat().st_mtime)}")
        
        # Load the .env file
        load_dotenv(env_file)
        print_success(".env file loaded successfully")
        
        # Try to read file content (sanitized)
        try:
            with open(env_file, 'r') as f:
                lines = f.readlines()
                print_info(f"Number of lines in .env: {len(lines)}")
                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key = line.split('=')[0] if '=' in line else line
                        print_info(f"  Line {i}: {key}=***")
        except Exception as e:
            print_warning(f"Could not read .env file content: {e}")
        
        return True
    else:
        print_error(f".env file NOT found at: {env_file}")
        print_info("Create a .env file in the project root with:")
        print_info("  GEMINI_API_KEY=your_api_key_here")
        return False

def test_api_key():
    """Test if API key is set in environment"""
    print_header("Step 3: Testing API Key Environment Variable")
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    if api_key:
        print_success("GEMINI_API_KEY found in environment")
        print_info(f"Key length: {len(api_key)} characters")
        print_info(f"Key prefix: {api_key[:10]}...")
        print_info(f"Key suffix: ...{api_key[-10:]}")
        
        # Basic validation
        if len(api_key) < 20:
            print_warning("API key seems unusually short")
        if ' ' in api_key:
            print_warning("API key contains spaces (might be incorrect)")
        if api_key.startswith('AIza'):
            print_success("API key format looks correct (starts with 'AIza')")
        else:
            print_warning("API key doesn't start with 'AIza' (might be incorrect)")
        
        return api_key
    else:
        print_error("GEMINI_API_KEY not found in environment variables")
        print_info("Make sure your .env file contains: GEMINI_API_KEY=your_key")
        return None

def test_api_configuration(api_key):
    """Test API configuration"""
    print_header("Step 4: Testing API Configuration")
    
    import google.generativeai as genai
    
    try:
        genai.configure(api_key=api_key)
        print_success("API configured successfully")
        return True
    except Exception as e:
        print_error(f"Failed to configure API: {e}")
        print_info(f"Error type: {type(e).__name__}")
        return False

def test_list_models(api_key):
    """Test listing available models"""
    print_header("Step 5: Testing Model Listing")
    
    import google.generativeai as genai
    
    try:
        models = genai.list_models()
        model_list = list(models)
        print_success(f"Successfully retrieved {len(model_list)} models")
        
        print_info("\nAvailable models:")
        for i, model in enumerate(model_list[:10], 1):  # Show first 10
            print_info(f"  {i}. {model.name}")
            if hasattr(model, 'display_name'):
                print_info(f"     Display: {model.display_name}")
            if hasattr(model, 'description'):
                desc = model.description[:60] + "..." if len(model.description) > 60 else model.description
                print_info(f"     Description: {desc}")
        
        if len(model_list) > 10:
            print_info(f"  ... and {len(model_list) - 10} more models")
        
        return True
    except Exception as e:
        print_error(f"Failed to list models: {e}")
        print_info(f"Error type: {type(e).__name__}")
        print_info(f"Error details: {str(e)}")
        return False

def test_simple_generation(api_key):
    """Test a simple text generation"""
    print_header("Step 6: Testing Text Generation")
    
    import google.generativeai as genai
    
    try:
        # Try the latest models that support text generation
        model_names = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.5-pro']
        
        for model_name in model_names:
            print_info(f"\nTrying model: {model_name}")
            try:
                model = genai.GenerativeModel(model_name)
                print_success(f"Model '{model_name}' initialized successfully")
                
                # Simple test prompt
                test_prompt = "Say 'Hello, the API key is working!' in exactly those words."
                print_info(f"Sending test prompt: {test_prompt}")
                
                response = model.generate_content(test_prompt)
                
                print_success("Response received successfully!")
                print_info(f"Response text: {response.text}")
                
                # Check for safety ratings
                if hasattr(response, 'prompt_feedback'):
                    print_info(f"Prompt feedback: {response.prompt_feedback}")
                
                return True
                
            except Exception as e:
                print_warning(f"Model '{model_name}' failed: {e}")
                continue
        
        print_error("All model attempts failed")
        return False
        
    except Exception as e:
        print_error(f"Failed to generate text: {e}")
        print_info(f"Error type: {type(e).__name__}")
        print_info(f"Error details: {str(e)}")
        
        # Additional debugging
        if hasattr(e, 'args'):
            print_info(f"Error args: {e.args}")
        
        return False

def test_api_limits():
    """Test API rate limits and quotas"""
    print_header("Step 7: Testing API Limits (Optional)")
    
    print_info("Making multiple rapid requests to test rate limits...")
    print_info("(This is informational only)")
    
    import google.generativeai as genai
    import time
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        for i in range(3):
            start = time.time()
            response = model.generate_content(f"Count to {i+1}")
            elapsed = time.time() - start
            print_info(f"  Request {i+1}: {elapsed:.2f}s - Response: {response.text[:50]}...")
        
        print_success("Rate limit test completed")
        return True
    except Exception as e:
        print_warning(f"Rate limit test encountered issue: {e}")
        return False

def main():
    """Main test runner"""
    print(f"\n{BLUE}{'='*70}")
    print(f"  Gemini API Key Test Suite")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}{RESET}\n")
    
    # Track results
    all_passed = True
    
    # Step 1: Test imports
    import_results = test_imports()
    if not all(import_results.values()):
        print_error("\n❌ Import test failed. Install missing packages and try again.")
        return 1
    
    # Step 2: Test .env file
    if not test_env_file():
        print_error("\n❌ .env file test failed. Create the file and try again.")
        return 1
    
    # Step 3: Test API key
    api_key = test_api_key()
    if not api_key:
        print_error("\n❌ API key test failed. Set GEMINI_API_KEY in .env file.")
        return 1
    
    # Step 4: Test API configuration
    if not test_api_configuration(api_key):
        all_passed = False
    
    # Step 5: Test listing models
    if not test_list_models(api_key):
        all_passed = False
    
    # Step 6: Test text generation
    if not test_simple_generation(api_key):
        all_passed = False
    
    # Step 7: Test API limits (optional)
    test_api_limits()
    
    # Final summary
    print_header("Test Summary")
    if all_passed:
        print_success("\n✓ All tests passed! Your Gemini API key is working correctly.")
    else:
        print_error("\n✗ Some tests failed. Check the output above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
