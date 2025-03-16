from backend.main import app
from fastapi import FastAPI
import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Export the FastAPI app for Vercel
app = app 