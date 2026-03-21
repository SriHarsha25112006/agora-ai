import os
import uvicorn
from backend.main import app

# This file serves as the entry point for deploying the backend to Render, Railway, or Heroku.
# It simply imports your FastAPI app and runs it on the correct port.

if __name__ == "__main__":
    # Render provides the PORT environment variable dynamically.
    port = int(os.environ.get("PORT", 8080))
    
    # Run the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=port)
