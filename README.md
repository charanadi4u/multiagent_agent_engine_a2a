# Multi-Agent Image Scoring A2A

This project contains a Google ADK multi-agent application that generates an image from a prompt, scores the generated image against policy guidelines, and stops when the score threshold is met.

The local A2A agent lives at:

```text
image_scoring_adk_a2a_server/remote_a2a/image_scoring
```

## Prerequisites

- Python 3.10 to 3.13
- `uv`
- Docker, optional for container testing
- Google Cloud credentials with access to Vertex AI Imagen and Cloud Storage
- A GCS bucket for generated image uploads, optional for local-only testing

## Setup

From the repository root:

```powershell
cd C:\Users\mural\multiagent_agent_engine_a2a
uv sync
```

Set local environment variables:

```powershell
$env:GOOGLE_CLOUD_PROJECT="your-project-id"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
$env:GOOGLE_CLOUD_STORAGE_BUCKET="your-bucket-name"
$env:GCS_BUCKET_NAME="your-bucket-name"
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\service-account.json"
```

Do not commit service account JSON files.

## Validate

```powershell
uv run python -m compileall image_scoring_adk_a2a_server testclient deploy
```

## Run Locally

Start the local A2A server:

```powershell
uv run adk api_server --host 127.0.0.1 --port 8001 --a2a image_scoring_adk_a2a_server\remote_a2a
```

In another terminal, verify the server:

```powershell
Invoke-WebRequest http://127.0.0.1:8001/a2a/image_scoring/.well-known/agent.json
Invoke-WebRequest http://127.0.0.1:8001/list-apps
```

Both commands should return `200 OK`.

Note: `/docs` may fail in A2A mode because ADK's experimental A2A routes currently expose types that FastAPI cannot render into OpenAPI. Use the A2A agent-card endpoint above for health checks.

## Generate An Image Locally

Keep the local server running, then run:

```powershell
uv run python testclient\local_a2a_test.py "Create an image of a cat playing piano in a cozy room"
```

Generated images are saved locally under:

```text
generated_images/YYYY-MM-DD/<unique_id>/generated_image_0.png
```

Find generated images with:

```powershell
Get-ChildItem generated_images -Recurse -Filter *.png
```

If `GCS_BUCKET_NAME` or `GOOGLE_CLOUD_STORAGE_BUCKET` is set, images are also uploaded to:

```text
gs://<bucket-name>/YYYY-MM-DD/<unique_id>/generated_image_0.png
```

## Docker

Build the image:

```powershell
docker build -t image-scoring-adk-a2a:local .
```

Run the container:

```powershell
docker run --rm -p 8001:8001 `
  -e GOOGLE_CLOUD_PROJECT="your-project-id" `
  -e GOOGLE_CLOUD_LOCATION="us-central1" `
  -e GOOGLE_CLOUD_STORAGE_BUCKET="your-bucket-name" `
  -e GCS_BUCKET_NAME="your-bucket-name" `
  image-scoring-adk-a2a:local
```

Health check:

```powershell
Invoke-WebRequest http://127.0.0.1:8001/a2a/image_scoring/.well-known/agent.json
```

## Deploy To Google Agent Engine

The deployment script is:

```text
deploy/deploy.py
```

Run it locally:

```powershell
uv run python deploy/deploy.py
```

Required environment variables:

```text
GOOGLE_CLOUD_PROJECT
GOOGLE_CLOUD_LOCATION
GOOGLE_CLOUD_STORAGE_BUCKET
```

`GCS_BUCKET_NAME` can also be used by the agent runtime for generated images.

## CI

GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

The workflow validates Python source, builds the Docker image, and can deploy to Agent Engine when these GitHub secrets are configured:

```text
GCP_PROJECT_ID
GCP_WORKLOAD_IDENTITY_PROVIDER
GCP_SERVICE_ACCOUNT
GOOGLE_CLOUD_STORAGE_BUCKET
```

## References

- Google ADK docs: https://google.github.io/adk-docs/
- A2A protocol: https://a2a-protocol.org/latest/
- Codelab: https://codelabs.developers.google.com/codelabs/create-multi-agents-adk-a2a
