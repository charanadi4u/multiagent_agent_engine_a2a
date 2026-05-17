import logging
import asyncio
import os
from pathlib import Path

import vertexai
from dotenv import load_dotenv
from google.oauth2 import service_account
from vertexai import agent_engines

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_ENV_PATH = (
    REPO_ROOT
    / "image_scoring_adk_a2a_server"
    / "remote_a2a"
    / "image_scoring"
    / ".env"
)

# Load environment variables from the local agent .env, if present.
load_dotenv(AGENT_ENV_PATH)

AUTH_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def get_credentials():
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        return None

    key_file = Path(credentials_path)
    if not key_file.exists():
        raise FileNotFoundError(
            f"GOOGLE_APPLICATION_CREDENTIALS points to a missing file: {key_file}"
        )

    return service_account.Credentials.from_service_account_file(
        key_file,
        scopes=AUTH_SCOPES,
    )


async def call_agent_engine(
    prompt: str,
    project_id: str,
    location: str,
    staging_bucket: str,
    reasoning_engine_id: str,
    user_id: str = "user_123",
) -> None:
    """Initializes Vertex AI, gets a remote agent, creates a session, and streams a query.

    Args:
        prompt: The query to send to the agent.
        project_id: The Google Cloud project ID.
        location: The Google Cloud location for Vertex AI.
        staging_bucket: The GCS bucket for staging.
        reasoning_engine_id: The ID of the deployed agent engine.
        user_id: The ID for the user session.

    Yields:
        Events from the agent's streamed response.
    """
    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=staging_bucket,
        credentials=get_credentials(),
    )

    # Create a session service client
    remote_agent = agent_engines.get(reasoning_engine_id)
    print(remote_agent)
    remote_session=await remote_agent.async_create_session(user_id="u_456")

    async for event in remote_agent.async_stream_query(
        user_id="u_456",
        session_id=remote_session["id"],
        message=prompt,
    ):
        print(event)

def get_agent_engine_list(project_id,location,staging_bucket):
    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=staging_bucket,
    )
    engines=agent_engines.AgentEngine.list()
    logging.info(engines)
    return engines




PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or "charan-245405"
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = f"gs://{os.getenv('GOOGLE_CLOUD_STORAGE_BUCKET')}"

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    REASONING_ENGINE_ID = os.getenv(
        "REASONING_ENGINE_ID",
        "projects/xxx/locations/us-central1/reasoningEngines/xxx",
    )
    #REASONING_ENGINE_ID="projects/85469421903/locations/us-central1/reasoningEngines/428031080600174592"

    prompt = os.getenv("AGENT_TEST_PROMPT", "Create image of a cat")

    #engines=get_agent_engine_list(PROJECT_ID,LOCATION,STAGING_BUCKET)
    #REASONING_ENGINE_ID=engines[0].resource_name
    try:
        response_stream = asyncio.run(call_agent_engine(
            prompt=prompt,
            project_id=PROJECT_ID,
            location=LOCATION,
            staging_bucket=STAGING_BUCKET,
            reasoning_engine_id=REASONING_ENGINE_ID,
        ))
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
