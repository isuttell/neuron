import asyncio
import base64
import os
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, Literal, Optional
from uuid import uuid4

import aiohttp
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI
from PIL import Image, PngImagePlugin
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.util.image_utilities import create_thumbnails
from neuron_server.util.slug import safe_filename


class OpenAIImageArgs(BaseModel):
    name: str = Field(
        description=(
            "A unique display name for the image generation less than 256 characters"
        )
    )
    prompt: str = Field(
        description=(
            "The prompt to generate the image from.\n\n"
            "When creating prompts for images, include specific visual details, "
            "such as colors, textures, and object placements, to guide the model "
            "toward a precise result. Mention the desired style (e.g., "
            "photorealistic, cartoonish, or abstract) and add context, like "
            "background elements or lighting, for more cohesive images. Focus on "
            "clarity and conciseness in each prompt to avoid ambiguity and ensure "
            "reproducible results. Unless you are trying to maintain a specific "
            "style or look add multiple random modern art styles and artistic "
            "styles to ensure variety."
        )
    )
    size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = Field(
        description=(
            "The size of the image to generate. 'auto' lets the model "
            "choose the best size based on the prompt. 1024x1024 is square, "
            "1536x1024 is landscape, 1024x1536 is portrait."
        ),
        default="auto",
    )
    quality: Literal["low", "medium", "high", "auto"] = Field(
        description=(
            "The quality of the image to generate. 'auto' lets the model "
            "choose the best quality. Higher quality takes longer and costs "
            "more tokens."
        ),
        default="auto",
    )
    background: Literal["transparent", "opaque", "auto"] = Field(
        description=(
            "The background type. 'transparent' creates images with "
            "transparent backgrounds (useful for sprites, logos). "
            "'auto' lets the model decide."
        ),
        default="auto",
    )
    output_format: Literal["png", "jpeg", "webp"] = Field(
        description="The output format for the image. PNG supports transparency.",
        default="png",
    )
    n: int = Field(
        description="The number of images to generate. Default to 1.",
        default=1,
    )
    image_id: Optional[str] = Field(
        description=(
            "Optional: ID of an existing image generation call to edit or use "
            "as reference for multi-turn generation. When provided, the tool "
            "will edit the existing image based on the new prompt using "
            "OpenAI's Responses API multi-turn capabilities."
        ),
        default=None,
    )
    image_url: Optional[str] = Field(
        description=(
            "Optional: URL of an existing image to use as reference for "
            "image-to-image generation. When provided, the tool will "
            "download the image and use it as input along with the prompt "
            "to generate a new image based on the reference."
        ),
        default=None,
    )


class OpenAIImageGenerationTool(BaseTool):
    name: str = "openai_image_generation"
    description: str = (
        "A tool that generates detailed, high-quality images using "
        "OpenAI's GPT-Image-1 model via the Responses API. Supports "
        "multi-turn editing by providing an image_id from a previous "
        "generation call, and image-to-image generation by providing "
        "an image_url to use as reference. Returns markdown image tags "
        "with image IDs for display and future reference."
    )
    args_schema: type[OpenAIImageArgs] = OpenAIImageArgs
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _download_and_encode_image(self, image_url: str) -> str:
        """Download and encode image as base64 for OpenAI API."""
        tmp_upload_file = None
        try:
            tmp_upload_file = os.path.join(neuron_config.temp_folder, uuid4().hex)

            # Generate proper signed session cookie for internal tool access
            cookies = None
            if neuron_config.static_require_auth:
                from neuron_server.controllers.csrf import create_session_cookie

                session_cookie, _ = create_session_cookie("system", include_csrf=False)
                cookies = {"neuron_session": session_cookie}

            async with (
                aiohttp.ClientSession(cookies=cookies) as session,
                session.get(image_url) as response,
            ):
                response.raise_for_status()
                image_data = BytesIO(await response.content.read())
                image = Image.open(image_data)

                # Convert to JPEG format for consistent base64 encoding
                image_bytes = BytesIO()
                if image.mode == "RGBA":
                    # Convert RGBA to RGB for JPEG
                    rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                    # Use alpha channel as mask if RGBA
                    rgba_channels = 4
                    mask = (
                        image.split()[-1]
                        if len(image.split()) == rgba_channels
                        else None
                    )
                    rgb_image.paste(image, mask=mask)
                    image = rgb_image

                image.save(image_bytes, format="JPEG", quality=90)
                image_bytes.seek(0)

                return base64.b64encode(image_bytes.getvalue()).decode("utf-8")
        finally:
            if tmp_upload_file and os.path.exists(tmp_upload_file):
                os.remove(tmp_upload_file)

    async def _arun(  # noqa: PLR0913, PLR0912, PLR0915
        self,
        name: str,
        prompt: str,
        config: RunnableConfig,
        size: Literal["1024x1024", "1536x1024", "1024x1536", "auto"] = "auto",
        quality: Literal["low", "medium", "high", "auto"] = "auto",
        background: Literal["transparent", "opaque", "auto"] = "auto",
        output_format: Literal["png", "jpeg", "webp"] = "png",
        image_id: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> tuple[str, dict]:
        """
        Generate an image using OpenAI's GPT-Image-1 model via Responses API.

        Args:
            name: Display name for the image.
            prompt: The prompt to generate the image from.
            size: The size of the image to generate.
            quality: The quality of the image to generate.
            background: The background type of the image.
            output_format: The output format of the image.
            image_id: Optional existing image generation call ID for multi-turn.
            image_url: Optional image URL to use as reference.

        Returns:
            tuple: (llm_content, artifact) - XML content and UI artifact
        """
        try:
            client = AsyncOpenAI(api_key=neuron_config.openai_api_key)

            # Build image generation tool parameters
            image_generation_tool = {
                "type": "image_generation",
                "size": size,
                "quality": quality,
                "background": background,
                "output_format": output_format,
            }

            # Handle different input modes
            if image_id:
                # Multi-turn editing using image generation call reference
                input_data = [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    },
                    {
                        "type": "image_generation_call",
                        "id": image_id,
                    },
                ]
                action = "Editing"
            elif image_url:
                # Image-to-image generation using provided image URL
                base64_image = await self._download_and_encode_image(image_url)
                input_data = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        ],
                    }
                ]
                action = "Generating from image"
            else:
                # New image generation
                input_data = prompt
                action = "Generating"

            logger.debug(f"{action} OpenAI image with prompt: {prompt}")

            # Use OpenAI Responses API as per official documentation
            response = await client.responses.create(
                model="gpt-4.1-mini",
                input=input_data,
                tools=[image_generation_tool],
            )

            # Extract image generation calls from response
            image_generation_calls = [
                output
                for output in response.output
                if output.type == "image_generation_call"
            ]

            if not image_generation_calls:
                return "Error: No image generation calls found in response", {}

            now = datetime.now(UTC).astimezone()
            llm_contents = []
            artifact_items = []

            for i, call in enumerate(image_generation_calls):
                if call.status != "completed":
                    logger.warning(
                        f"Image generation call {call.id} status: {call.status}"
                    )
                    continue

                # Get the base64 image data
                image_base64 = call.result
                image_bytes = base64.b64decode(image_base64)
                image = Image.open(BytesIO(image_bytes))

                # Use appropriate file extension based on output format
                file_ext = "jpg" if output_format == "jpeg" else output_format
                filename = safe_filename("openai_image", f"{name}_{i}", file_ext)

                # Add metadata to PNG images
                if output_format == "png":
                    pnginfo = PngImagePlugin.PngInfo()
                    pnginfo.add_text("Description", prompt)
                    if hasattr(call, "revised_prompt"):
                        pnginfo.add_text("RevisedPrompt", call.revised_prompt)
                    pnginfo.add_text("Model", "gpt-image-1")
                    pnginfo.add_text(
                        "DateTimeOriginal", now.isoformat(timespec="seconds")
                    )
                    pnginfo.add_text("OpenAICallId", call.id)
                    if image_id:
                        pnginfo.add_text("BaseImageCallId", image_id)
                else:
                    pnginfo = None

                file_path = os.path.abspath(
                    os.path.join(neuron_config.static_folder, filename)
                )

                # Save with appropriate format and quality
                save_kwargs = {"format": output_format.upper()}
                if pnginfo and output_format == "png":
                    save_kwargs["pnginfo"] = pnginfo
                if output_format in ["jpeg", "webp"]:
                    save_kwargs["quality"] = 95

                image.save(file_path, **save_kwargs)
                create_thumbnails(file_path)

                url = f"{neuron_config.static_content_url}/{filename}"

                logger.debug(f"Saved generated image to {file_path} <{url}>")

                # Generate a real UUID for consistent ID between artifact and media_item
                description = getattr(call, "revised_prompt", prompt)
                media_id = uuid4()

                # XML content for LLM
                llm_content = f"""<image>
    <id>{media_id}</id>
    <url>{url}</url>
    <image_id>{call.id}</image_id>
    <caption>{name}</caption>
    <prompt>{prompt}</prompt>
    <revised_prompt>{description}</revised_prompt>
</image>"""
                llm_contents.append(llm_content)

                # Artifact for UI using typed models
                from neuron_server.tools.artifact_types import (
                    ToolArtifactMetadata,
                    ToolMediaItem,
                )

                metadata = ToolArtifactMetadata(
                    model="gpt-image-1",
                    image_id=call.id,
                    aspect_ratio=size,
                    quality=quality,
                    background=background,
                    output_format=output_format,
                    revised_prompt=description,
                )

                artifact_item = ToolMediaItem(
                    id=media_id,
                    url=url,
                    caption=name,
                    description=description,
                    metadata=metadata,
                )
                artifact_items.append(artifact_item)

            if not llm_contents:
                return "Error: No images were successfully generated", {}

            # Combine XML content
            if len(llm_contents) == 1:
                full_llm_content = llm_contents[0]
            else:
                full_llm_content = (
                    "<images>\n" + "\n".join(llm_contents) + "\n</images>"
                )

            # Create typed artifact
            from neuron_server.tools.artifact_types import ToolMediaArtifact

            artifact = ToolMediaArtifact(
                media_type="image",
                items=artifact_items,  # List of ToolMediaItem instances
            )

            return full_llm_content, [artifact.model_dump()]

        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error generating image: {str(e)}", {}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate an image using OpenAI GPT-Image-1."
    )
    parser.add_argument(
        "prompt", type=str, help="The prompt to generate the image from."
    )
    parser.add_argument(
        "--name", type=str, default="test_image", help="Name for the generated image."
    )
    args = parser.parse_args()

    tool = OpenAIImageGenerationTool()
    results = tool._run(
        name=args.name,
        prompt=args.prompt,
    )
    print(results)
