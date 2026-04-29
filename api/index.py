import sys
sys.path.append("..")  # Ensure parent dir is in path for imports
from app import app as vercel_app

# Vercel expects a variable named 'app' or 'vercel_app'
app = vercel_app
