import sys
import os
import traceback
from dotenv import load_dotenv

# Load environment variables from .env before importing app
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

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