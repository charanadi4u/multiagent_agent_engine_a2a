import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

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
    """
    Load service account credentials if GOOGLE_APPLICATION_CREDENTIALS is set.

    If GOOGLE_APPLICATION_CREDENTIALS is not set, Vertex AI will use
    Application Default Credentials created by:

        gcloud auth application-default login
    """
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not credentials_path:
        logging.info(
            "GOOGLE_APPLICATION_CREDENTIALS is not set. "
            "Using Application Default Credentials."
        )
        return None

    key_file = Path(credentials_path)

    if not key_file.exists():
        raise FileNotFoundError(
            f"GOOGLE_APPLICATION_CREDENTIALS points to a missing file: {key_file}"
        )

    logging.info("Using service account credentials from: %s", key_file)

    return service_account.Credentials.from_service_account_file(
        key_file,
        scopes=AUTH_SCOPES,
    )


def init_vertexai(
    project_id: str,
    location: str,
    staging_bucket: Optional[str] = None,
) -> None:
    """
    Initialize Vertex AI.

    staging_bucket is optional when calling an already deployed Agent Engine.
    """
    init_kwargs = {
        "project": project_id,
        "location": location,
        "credentials": get_credentials(),
    }

    if staging_bucket:
        init_kwargs["staging_bucket"] = staging_bucket
        logging.info("Using staging bucket: %s", staging_bucket)
    else:
        logging.info("No staging bucket configured. Continuing without it.")

    vertexai.init(**init_kwargs)

    logging.info(
        "Vertex AI initialized. project=%s, location=%s",
        project_id,
        location,
    )


async def call_agent_engine(
    prompt: str,
    project_id: str,
    location: str,
    staging_bucket: Optional[str],
    reasoning_engine_id: str,
    user_id: str = "u_456",
) -> None:
    """
    Initializes Vertex AI, gets the remote Agent Engine, inspects available
    operations, and calls the first supported query method.
    """
    init_vertexai(
        project_id=project_id,
        location=location,
        staging_bucket=staging_bucket,
    )

    remote_agent = agent_engines.get(reasoning_engine_id)

    logging.info("Remote agent loaded successfully.")
    logging.info("Remote agent resource name: %s", reasoning_engine_id)
    logging.info("Remote agent object: %s", remote_agent)

    available_methods = [
        method_name
        for method_name in dir(remote_agent)
        if "query" in method_name
        or "session" in method_name
        or "stream" in method_name
        or "operation" in method_name
    ]

    logging.info("Available query/session/stream/operation methods: %s", available_methods)

    try:
        operation_schemas = remote_agent.operation_schemas()
    except Exception as exc:
        operation_schemas = None
        logging.warning("Could not read operation_schemas(): %s", exc)

    logging.info("Operation schemas: %s", operation_schemas)

    if not operation_schemas:
        raise RuntimeError(
            "\n\nThe Agent Engine resource was found, but it has no registered "
            "runtime operations.\n\n"
            "This means the deployed Agent Engine does not expose query, "
            "stream_query, async_query, async_stream_query, or ADK session methods.\n\n"
            "Most likely fix:\n"
            "Redeploy the Agent Engine as an ADK app using AdkApp, or register "
            "query/stream_query operations during deployment.\n\n"
            f"Reasoning Engine ID: {reasoning_engine_id}\n"
            f"Available methods found on client object: {available_methods}\n"
        )

    logging.info("Sending prompt to remote agent.")
    logging.info("user_id=%s", user_id)
    logging.info("prompt=%s", prompt)

    if hasattr(remote_agent, "async_stream_query"):
        logging.info("Calling remote_agent.async_stream_query(...)")

        async for event in remote_agent.async_stream_query(
            user_id=user_id,
            message=prompt,
        ):
            print(event)

        return

    if hasattr(remote_agent, "stream_query"):
        logging.info("Calling remote_agent.stream_query(...)")

        for event in remote_agent.stream_query(
            user_id=user_id,
            message=prompt,
        ):
            print(event)

        return

    if hasattr(remote_agent, "async_query"):
        logging.info("Calling remote_agent.async_query(...)")

        response = await remote_agent.async_query(
            user_id=user_id,
            message=prompt,
        )

        print(response)
        return

    if hasattr(remote_agent, "query"):
        logging.info("Calling remote_agent.query(...)")

        response = remote_agent.query(
            user_id=user_id,
            message=prompt,
        )

        print(response)
        return

    raise RuntimeError(
        "\n\nOperation schemas exist, but this Python SDK client object does not "
        "expose query/stream methods directly.\n\n"
        "Please check the printed operation_schemas() output. Your deployed app "
        "may have a custom operation name that must be called differently.\n"
    )


def get_agent_engine_list(
    project_id: str,
    location: str,
    staging_bucket: Optional[str] = None,
):
    """
    Lists Agent Engines in the configured project/location.
    """
    init_vertexai(
        project_id=project_id,
        location=location,
        staging_bucket=staging_bucket,
    )

    engines = agent_engines.AgentEngine.list()

    logging.info("Agent Engines found:")

    for engine in engines:
        logging.info(engine)

    return engines


def build_staging_bucket() -> Optional[str]:
    """
    Safely builds a GCS staging bucket URI.

    If GCS_BUCKET_NAME is missing, returns None instead of gs://None.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")

    if not bucket_name:
        return None

    if bucket_name.startswith("gs://"):
        return bucket_name

    return f"gs://{bucket_name}"


# IMPORTANT:
# This project must match the project in your REASONING_ENGINE_ID.
#
# Your current REASONING_ENGINE_ID is:
# projects/787533364278/locations/us-central1/reasoningEngines/5152325231653683200
#
# So default PROJECT_ID is set to 787533364278.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or "787533364278"
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = build_staging_bucket()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    REASONING_ENGINE_ID = os.getenv(
        "REASONING_ENGINE_ID",
        "projects/787533364278/locations/us-central1/reasoningEngines/8946889392690036736",
    )

    # Alternative Agent Engine example:
    # REASONING_ENGINE_ID = (
    #     "projects/85469421903/locations/us-central1/"
    #     "reasoningEngines/428031080600174592"
    # )

    #prompt = os.getenv("AGENT_TEST_PROMPT", "Create image of a dog riding a Royal Enfield bike in a race")
    prompt = "Create image of a dog riding a Royal Enfield bike in a race"
    
    try:
        asyncio.run(
            call_agent_engine(
                prompt=prompt,
                project_id=PROJECT_ID,
                location=LOCATION,
                staging_bucket=STAGING_BUCKET,
                reasoning_engine_id=REASONING_ENGINE_ID,
                user_id=os.getenv("AGENT_TEST_USER_ID", "u_456"),
            )
        )

    except Exception as e:
        logging.error("An error occurred: %s", e, exc_info=True)