from langchain.tools import BaseTool
import asyncio
import requests
import base64
from neuron_server.logger import logger
import time
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages import BaseMessage
from neuron_server.llms.clean_eos_tokens import clean_eos_tokens
from langchain_openai import ChatOpenAI


def get_message_content(message: BaseMessage):
    if not message.content:
        return None
    if isinstance(message.content, list):
        return clean_eos_tokens(
            "\n".join(
                [
                    (
                        c["text"]
                        if isinstance(c, dict) and "text" in c
                        else c if isinstance(c, str) else ""
                    )
                    for c in message.content
                ]
            )
        )
    return clean_eos_tokens(message.content)


class InspectImageTool(BaseTool):
    name: str = "inspect_image"
    description: str = (
        "This tool uses a OpenAI GPT-4o multi-modal vision capabilities to inspect an image and return a description of the image. Images are downloaded from the provided URL. The prompt should be a detailed question about what is in the image. Use this tool to when you need to answer a question about an image."
    )

    def _run(self, image_url: str, prompt: str, max_tokens: int = 300) -> str:
        """
        Inspect an image using OpenAI's GPT-4o multi-modal vision capabilities.

        Args:
            image_url (str): The URL of the image to be inspected.
            prompt (str): A question or prompt that guides the inspection of the image.
            max_tokens (int, optional): The maximum number of tokens to generate in the response. Defaults to 300.

        Returns:
            str: A description of the image based on the provided prompt.
        """
        try:
            start_time = time.perf_counter()
            logger.debug(f"Inspecting image: {image_url} with prompt: {prompt}")
            # Download the image
            response = requests.get(image_url)
            response.raise_for_status()

            # Convert the image to base64
            image_base64 = base64.b64encode(response.content).decode("utf-8")
            model = ChatOpenAI(
                model="gpt-4o",
                temperature=0.7,
                streaming=True,
                max_tokens=max_tokens,
            )
            message = model.invoke(
                [
                    SystemMessage(
                        content="You are a tool that inspects images and returns a description of the image based on a given prompt. Be descriptive and detailed. Just return the description, no other text. Do not ask for clarification."
                    ),
                    HumanMessage(
                        content=[
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    ),
                ],
                {
                    "run_name": "inspect_image",
                    "metadata": {"image_url": image_url},
                },
                max_tokens=max_tokens,
            )
            content = get_message_content(message)
            if not content:
                raise Exception("No content returned")
            logger.debug(
                f"Response: {content} - {round(time.perf_counter() - start_time, 2)}s"
            )
            return content
        except Exception as e:
            logger.exception(e)
            return f"I'm sorry, I couldn't inspect the image. {str(e)}"


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect an image and return a description."
    )

    parser.add_argument("prompt", type=str, help="The prompt to guide the inspection.")
    parser.add_argument(
        "--image_url",
        type=str,
        help="The URL of the image to inspect.",
        default="https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
    )
    parser.add_argument(
        "--max_tokens",
        type=int,
        default=300,
        help="The maximum number of tokens to generate.",
    )
    args = parser.parse_args()

    # Call the model to get the description
    tool = InspectImageTool()
    results = await tool._run(args.image_url, args.prompt, args.max_tokens)
    # Print the response
    print(results)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
