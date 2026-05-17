import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[3]
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME") or os.getenv("GCS_BUCKET_NAME")
APP_VERTEX_PROJECT = os.getenv("APP_VERTEX_PROJECT")
APP_VERTEX_LOCATION = os.getenv("APP_VERTEX_LOCATION", "us-central1")
SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", 45))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 1))
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-3.0-generate-002")
GENAI_MODEL = os.getenv("GENAI_MODEL", "gemini-2.5-flash")
LOCAL_OUTPUT_DIR = Path(os.getenv("LOCAL_OUTPUT_DIR", REPO_ROOT / "generated_images"))
