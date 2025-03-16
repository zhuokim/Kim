from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sys
from pathlib import Path

# Add the parent directory to Python path
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_path)

from backend.main import app

# Update templates directory for Vercel
templates_dir = os.path.join(root_path, "backend", "templates")
static_dir = os.path.join(root_path, "backend", "static")

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Update templates configuration
app.state.templates = Jinja2Templates(directory=templates_dir)

# Export the FastAPI app for Vercel
app = app 