from datetime import datetime
from pathlib import Path
from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from google.cloud import storage
from .... import config
import logging
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_genai_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project=config.APP_VERTEX_PROJECT,
        location=config.APP_VERTEX_LOCATION,
    )


async def generate_images(imagen_prompt: str, tool_context: ToolContext):

    try:

        response = get_genai_client().models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=imagen_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="9:16",
                safety_filter_level="block_low_and_above",
                person_generation="allow_adult",
            ),
        )
        if response.generated_images is not None:
            for generated_image in response.generated_images:
                # Get the image bytes
                image_bytes = generated_image.image.image_bytes
                counter = str(tool_context.state.get("loop_iteration", 0))
                artifact_name = "generated_image_" + counter + ".png"
                local_path = save_to_local_file(tool_context, image_bytes, artifact_name)

                # call save to gcs function
                gcs_uri = None
                if config.GCS_BUCKET_NAME:
                    logger.info(f"DEBUG: GCS_BUCKET_NAME is set to {config.GCS_BUCKET_NAME}. Calling save_to_gcs...")
                    gcs_uri = save_to_gcs(tool_context, image_bytes, artifact_name, counter)
                else:
                    logger.info("DEBUG: GCS_BUCKET_NAME is NOT set. Skipping save_to_gcs.")

                # Save as ADK artifact (optional, if still needed by other ADK components)
                report_artifact = types.Part.from_bytes(
                    data=image_bytes, mime_type="image/png"
                )

                await tool_context.save_artifact(artifact_name, report_artifact)
                logger.info(f"Image also saved as ADK artifact: {artifact_name}")

                return {
                    "status": "success",
                    "message": f"Image generated. ADK artifact: {artifact_name}. Local file: {local_path}.",
                    "artifact_name": artifact_name,
                    "local_path": local_path,
                    "gcs_uri": gcs_uri,
                }
        else:
            # model_dump_json might not exist or be the best way to get error details
            error_details = str(response)  # Or a more specific error field if available
            logger.error(f"No images generated. Response: {error_details}")
            return {
                "status": "error",
                "message": f"No images generated. Response: {error_details}",
            }

    except Exception as e:
        logger.error(f"Error generating images: {e}")
        return {"status": "error", "message": f"No images generated.  {e}"}


def save_to_local_file(tool_context: ToolContext, image_bytes, filename: str) -> str:
    unique_id = tool_context.state.get("unique_id", "")
    current_date_str = datetime.utcnow().strftime("%Y-%m-%d")
    output_dir = Path(config.LOCAL_OUTPUT_DIR).resolve() / current_date_str / unique_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    output_path.write_bytes(image_bytes)
    logger.info(f"DEBUG: Successfully saved local image: {output_path}")
    return str(output_path)


def save_to_gcs(tool_context: ToolContext, image_bytes, filename: str, counter: str):
    # --- Save to GCS ---
    storage_client = storage.Client()  # Initialize GCS client
    bucket_name = config.GCS_BUCKET_NAME

    unique_id = tool_context.state.get("unique_id", "")
    current_date_str = datetime.utcnow().strftime("%Y-%m-%d")
    unique_filename = filename
    gcs_blob_name = f"{current_date_str}/{unique_id}/{unique_filename}"

    logger.info(f"DEBUG: Starting save_to_gcs with bucket: {bucket_name}")
    logger.info(f"DEBUG: Target blob name: {gcs_blob_name}")

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(gcs_blob_name)

    try:
        blob.upload_from_string(image_bytes, content_type="image/png")
        gcs_uri = f"gs://{bucket_name}/{gcs_blob_name}"
        logger.info(f"DEBUG: Successfully uploaded to GCS: {gcs_uri}")

        # Store GCS URI in session context
        # Store GCS URI in session context
        tool_context.state["generated_image_gcs_uri_" + counter] = gcs_uri
        return gcs_uri

    except Exception as e_gcs:
        logger.error(f"DEBUG: Error uploading to GCS: {e_gcs}")
        # Decide if this is a fatal error for the tool
        return {
            "status": "error",
            "message": f"Image generated but failed to upload to GCS: {e_gcs}",
        }
        # --- End Save to GCS ---
