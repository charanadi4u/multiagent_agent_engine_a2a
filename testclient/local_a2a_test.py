import argparse
import asyncio
import json
import uuid

import httpx
from a2a.client import A2AClient
from a2a.types import Message, MessageSendParams, Part, Role, SendMessageRequest, TextPart


async def main() -> None:
    parser = argparse.ArgumentParser(description="Send a local A2A prompt to the image scoring agent.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Create an image of a cat playing piano in a cozy room",
        help="Prompt to send to the local image scoring A2A agent.",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8001/a2a/image_scoring",
        help="Local A2A endpoint URL.",
    )
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=600) as httpx_client:
        client = A2AClient(httpx_client=httpx_client, url=args.url)
        request = SendMessageRequest(
            id=str(uuid.uuid4()),
            params=MessageSendParams(
                message=Message(
                    message_id=str(uuid.uuid4()),
                    role=Role.user,
                    parts=[Part(root=TextPart(text=args.prompt))],
                )
            ),
        )

        response = await client.send_message(request)
        print(json.dumps(response.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
