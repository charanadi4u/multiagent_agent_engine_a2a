import os
import sys
from pathlib import Path

import vertexai
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_ROOT = REPO_ROOT / "image_scoring_adk_a2a_server" / "remote_a2a"
PACKAGE_DIR = AGENTS_ROOT / "image_scoring"
DIST_DIR = REPO_ROOT / "dist"

# Make image_scoring package importable locally
sys.path.insert(0, str(AGENTS_ROOT))

from image_scoring.agent import root_agent  # noqa: E402


# Load local environment variables when running outside CI.
load_dotenv(PACKAGE_DIR / ".env")


PROJECT_ID = (
    os.getenv("GOOGLE_CLOUD_PROJECT")
    or os.getenv("GCP_PROJECT")
    or os.getenv("CLOUDSDK_CORE_PROJECT")
)

LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"

STORAGE_BUCKET = (
    os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
    or os.getenv("GCS_BUCKET_NAME")
)

STAGING_BUCKET = f"gs://{STORAGE_BUCKET}" if STORAGE_BUCKET else None


if not PROJECT_ID:
    raise RuntimeError(
        "GOOGLE_CLOUD_PROJECT is required to deploy to Agent Engine."
    )

if not STAGING_BUCKET:
    raise RuntimeError(
        "GOOGLE_CLOUD_STORAGE_BUCKET or GCS_BUCKET_NAME is required "
        "to deploy to Agent Engine."
    )


# Find the latest built wheel.
wheel_files = sorted(DIST_DIR.glob("image_scoring-*.whl"))

if not wheel_files:
    raise RuntimeError(
        "No image_scoring wheel found. Run `uv build --wheel` before deploy."
    )

wheel_path = wheel_files[-1]

# For requirements, use a relative path from repo root.
wheel_requirement = f"./dist/{wheel_path.name}"


# Read requirements.txt safely.
requirements_path = REPO_ROOT / "requirements.txt"

if not requirements_path.exists():
    raise RuntimeError(f"requirements.txt not found at: {requirements_path}")

requirements = [
    line.strip()
    for line in requirements_path.read_text().splitlines()
    if line.strip() and not line.strip().startswith("#")
]

# Make sure Agent Engine + ADK dependencies are available in remote runtime.
required_runtime_packages = [
    "google-cloud-aiplatform[adk,agent_engines]",
    "google-adk",
    "python-dotenv",
]

for package in required_runtime_packages:
    if package not in requirements:
        requirements.append(package)

# Add your local wheel to remote runtime.
if wheel_requirement not in requirements:
    requirements.append(wheel_requirement)


print("Deploying ADK Agent Engine...")
print(f"PROJECT_ID      = {PROJECT_ID}")
print(f"LOCATION        = {LOCATION}")
print(f"STAGING_BUCKET  = {STAGING_BUCKET}")
print(f"WHEEL           = {wheel_requirement}")


client = vertexai.Client(
    project=PROJECT_ID,
    location=LOCATION,
)


# CRITICAL FIX:
# Wrap the ADK root_agent inside AdkApp.
# Do NOT deploy root_agent directly.
app = vertexai.agent_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
)


remote_app = client.agent_engines.create(
    agent=app,
    config={
        "display_name": "image-scoring",
        "staging_bucket": STAGING_BUCKET,
        "requirements": requirements,
        "extra_packages": [
            wheel_requirement,
        ],
        "env_vars": {
            "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
            "GOOGLE_CLOUD_PROJECT": PROJECT_ID,
            "GOOGLE_CLOUD_LOCATION": LOCATION,
            "APP_VERTEX_PROJECT": PROJECT_ID,
            "APP_VERTEX_LOCATION": LOCATION,
            "GCS_BUCKET_NAME": STORAGE_BUCKET,
        },
    },
)


print("\nDeployment completed successfully.")
print(f"DEBUG: AgentEngine attributes: {dir(remote_app)}")

try:
    print(f"Full resource name: {remote_app.api_resource.name}")
    print(
        "\nUse this value in remote_test.py as REASONING_ENGINE_ID:\n"
        f"{remote_app.api_resource.name}"
    )
except AttributeError:
    print("Could not find remote_app.api_resource.name.")
    print("Please check DEBUG output above.")