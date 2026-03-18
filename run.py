import sys
import os
import traceback

# Ensure the current directory is in sys.path so 'app' can be discovered as a package
# This fixes "Could not find import of app.main" errors in some environments
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load environment variables from .env before importing app
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

try:
    import uvicorn
    # Try importing the app to catch import errors early
    from app.main import app
    
    if __name__ == "__main__":
        uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)

except ImportError as e:
    error_msg = f"MISSING DEPENDENCY: {str(e)}\n\nPlease run: pip install -r requirements.txt"
    print(error_msg)
    with open("startup_error.txt", "w") as f:
        f.write(error_msg)
        
except Exception as e:
    error_msg = f"STARTUP ERROR: {str(e)}\n"
    print(error_msg)
    with open("startup_error.txt", "w") as f:
        f.write(error_msg)
        traceback.print_exc(file=f)