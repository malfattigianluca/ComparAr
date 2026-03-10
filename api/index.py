from fastapi import FastAPI
from api.main import app as original_app

app = FastAPI()

# Mount the original app under /api so that Vercel's routing to /api/...
# correctly matches the endpoints defined in main.py without prefixes.
app.mount("/api", original_app)
