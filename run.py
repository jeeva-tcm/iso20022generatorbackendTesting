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
        # SERVER_PORT: set explicitly in .env or Render dashboard
        # PORT: injected automatically by Render if SERVER_PORT is not set
        port = int(os.getenv("SERVER_PORT") or os.getenv("PORT") or 8001)
        host = os.getenv("SERVER_HOST", "0.0.0.0")
        reload = os.getenv("RELOAD", "false").lower() == "true"
        uvicorn.run("app.main:app", host=host, port=port, reload=reload)

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