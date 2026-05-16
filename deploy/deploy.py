import os
import sys
from pathlib import Path

import vertexai
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_ROOT = REPO_ROOT / "image_scoring_adk_a2a_server" / "remote_a2a"
PACKAGE_DIR = AGENTS_ROOT / "image_scoring"

sys.path.insert(0, str(AGENTS_ROOT))

from image_scoring.agent import root_agent

# Load local environment variables when running outside CI.
load_dotenv(PACKAGE_DIR / ".env")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
STORAGE_BUCKET = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET") or os.getenv("GCS_BUCKET_NAME")
STAGING_BUCKET = f"gs://{STORAGE_BUCKET}" if STORAGE_BUCKET else None

if not PROJECT_ID:
    raise RuntimeError("GOOGLE_CLOUD_PROJECT is required to deploy to Agent Engine.")
if not STAGING_BUCKET:
    raise RuntimeError("GOOGLE_CLOUD_STORAGE_BUCKET or GCS_BUCKET_NAME is required to deploy to Agent Engine.")

from vertexai import agent_engines

client=vertexai.Client(
    project=PROJECT_ID,
    location=LOCATION,
)


remote_app = client.agent_engines.create(
    agent=root_agent,
    config={
        "display_name": "image-scoring",
        "staging_bucket": STAGING_BUCKET,
        "requirements": (REPO_ROOT / "requirements.txt").read_text().splitlines(),
        "extra_packages": [
            str(PACKAGE_DIR),
        ],
        "env_vars":{"GCS_BUCKET_NAME": STORAGE_BUCKET}
    }
)

print(f"DEBUG: AgentEngine attributes: {dir(remote_app)}")
try:
    print(remote_app.api_resource.name)
except AttributeError:
    print("Could not find resource_name, check DEBUG output above.")
