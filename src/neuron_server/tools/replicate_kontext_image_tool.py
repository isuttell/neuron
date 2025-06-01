import asyncio
import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime
from io import BufferedReader, BytesIO
from typing import Any, Literal
from uuid import uuid4

import aiofiles
import aiohttp
import replicate
import replicate.helpers
from langchain.schema import HumanMessage
from langchain.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from PIL import Image, PngImagePlugin
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.image_utilities import create_image_url, create_thumbnails
from neuron_server.util.slug import safe_filename

logger = logging.getLogger(__name__)


@dataclass
class ImageEditingParams:
    model: str
    name: str
    prompt: str
    input_args: dict[str, Any]
    describe: bool
    config: RunnableConfig


class ImageDescription(BaseModel):
    description: str = Field(description="The description of the edited image")
    caption: str = Field(description="A short caption for the edited image")
    edit_comparison: str = Field(
        description=(
            "A description of the changes made during editing, highlighting what "
            "was modified, added, or removed from the original image"
        )
    )


# Initialize the model for image description
model = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.2)

chain = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """\
You are an intelligent assistant that inspects AI-edited images and returns
descriptions of them to understand what changes were made. Be detailed and
descriptive about the current state of the image after editing. Make sure to
include the style, composition, lighting, mood, subject, and any other relevant
details. Use the editing prompt for context but focus on describing what you
actually see in the final image. Explain the changes that were made.

The editing prompt was: <prompt>{prompt}</prompt>
""".strip(),
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
) | model.with_structured_output(ImageDescription)


async def describe_edited_image(prompt: str, image: Image.Image) -> ImageDescription:
    image_url = create_image_url(image)

    return await chain.ainvoke(
        {
            "prompt": prompt,
            "messages": [
                HumanMessage(
                    content=[
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                ),
            ],
        },
    )


class ReplicateKontextImageToolArgs(BaseModel):
    name: str = Field(
        description=(
            "A unique display title for the edited image less than 256 characters"
        )
    )
    input_image: str = Field(
        description=(
            "URL of the image to edit. This is required and should be a valid HTTP "
            "URL pointing to an image file that can be downloaded and processed."
        )
    )
    prompt: str = Field(
        description="""\
Detailed editing instructions for transforming the input image. Be specific about
what changes you want to make. FLUX Kontext excels at:

- Style Transfer: "Convert this photo to a watercolor painting style"
- Object/Clothing Changes: "Change the person's hair to blonde", "Add sunglasses"
- Text Editing: "Replace 'old text' with 'new text'" (use quotes for exact text)
- Background Changes: "Change background to a beach while keeping the person"
- Color Modifications: "Make the sky more vibrant blue"

Prompting Best Practices:
- Be specific: Use exact colors, detailed descriptions
- Preserve intentionally: "while keeping the same facial features"
- For text edits: Use quotes around text to replace
- For backgrounds: Specify what to preserve and what to change
- Use descriptive action verbs for better control

Example prompts:
- "Change the background to a sunset beach while keeping the person"
- "Convert this to a Renaissance painting style with visible brushstrokes"
- "Replace the 'STOP' sign with 'GO' while maintaining the same design"
- "Add falling snow to this winter scene while preserving all other elements"
""".strip(),
    )
    model: Literal[
        "black-forest-labs/flux-kontext-pro",
        "black-forest-labs/flux-kontext-max",
    ] = Field(
        description=(
            "The FLUX Kontext model to use. Use 'flux-kontext-pro' for "
            "state-of-the-art performance with high quality outputs and good "
            "prompt following. Use 'flux-kontext-max' for premium model with "
            "maximum performance and improved typography generation."
        ),
        default="black-forest-labs/flux-kontext-pro",
    )
    seed: int | None = Field(
        description=(
            "Random seed for reproducible results. Set to a specific number to "
            "reproduce the same edit, or leave as -1 for random generation."
        ),
        default=-1,
    )
    describe: bool = Field(
        description=(
            "Whether to generate a detailed description of the edited image. "
            "Use this to understand what changes were made and how it looks."
        ),
        default=False,
    )


class ReplicateKontextImageTool(BaseTool):
    name: str = "replicate_kontext_image_edit"
    description: str = (
        "Use this tool to edit existing images using FLUX Kontext, a state-of-the-art "
        "text-based image editing model. Provide an image URL and detailed editing "
        "instructions to transform images. Excels at style transfer, object changes, "
        "text editing, background swapping, and maintaining character consistency. "
        "Perfect for iterating on generated images or modifying existing photos."
    )

    args_schema: type[ReplicateKontextImageToolArgs] = ReplicateKontextImageToolArgs

    async def _download_input_image(self, image_url: str) -> tuple[str, BufferedReader]:
        """Download and prepare the input image for editing."""
        tmp_upload_file = os.path.join(neuron_config.temp_folder, uuid4().hex)

        # Generate session token for auth if required
        session_token = str(uuid4())
        cookies = (
            {"neuron_session": session_token}
            if neuron_config.static_require_auth else None
        )

        async with (
            aiohttp.ClientSession(cookies=cookies) as session,
            session.get(image_url) as response,
        ):
            response.raise_for_status()
            image_data = BytesIO(await response.content.read())
            image = Image.open(image_data)
            # Save as PNG for best quality preservation
            image.save(tmp_upload_file, format="png", quality=95)

        image_file = open(tmp_upload_file, "rb")  # noqa: SIM115
        return tmp_upload_file, image_file

    def _prepare_input_args(
        self,
        prompt: str,
        input_image: BufferedReader,
        seed: int | None,
    ) -> dict[str, Any]:
        """Prepare input arguments for the FLUX Kontext model."""
        input_args = {
            "prompt": prompt,
            "input_image": input_image,
        }

        # Set seed if provided, otherwise use random
        if seed is not None and seed != -1:
            input_args["seed"] = seed
        else:
            input_args["seed"] = random.randint(0, 2147483647)

        return input_args

    async def _save_and_process_edited_image(
        self,
        result: replicate.helpers.FileOutput,
        params: ImageEditingParams,
    ) -> str:
        """Save and process the edited image."""
        filename = safe_filename(
            params.model.replace("/", "_").split(":")[0],
            params.name,
            "png",
        )
        file_path = os.path.abspath(os.path.join(neuron_config.static_folder, filename))

        # Save the edited image
        async with aiofiles.open(file_path, "wb") as file:
            async for chunk in result:
                await file.write(chunk)

        # Add metadata to the PNG
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("Description", params.name)
        pnginfo.add_text("Software", f"Model: {params.model}")
        pnginfo.add_text("EditingPrompt", params.prompt)
        pnginfo.add_text(
            "DateTimeOriginal",
            datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        pnginfo.add_text(
            "Parameters",
            "\n".join(
                f"{key}={True if key == 'input_image' and value else value}"
                for key, value in params.input_args.items()
            ),
        )

        # Load image for processing
        image = Image.open(file_path)
        described_image: ImageDescription | None = None

        if params.describe:
            logger.debug("Describing edited image")
            described_image = await describe_edited_image(params.prompt, image)
            pnginfo.add_text("Description", described_image.description)
            pnginfo.add_text("Caption", described_image.caption)
            pnginfo.add_text("EditComparison", described_image.edit_comparison)

        # Save with metadata and create thumbnails
        image.save(file_path, format="png", pnginfo=pnginfo, quality=95, optimize=True)
        create_thumbnails(file_path)

        # Create media item
        url = f"{neuron_config.static_content_url}/{filename}"
        create_params = MediaItemModel.CreateParams(
            thread_id=params.config["configurable"].get("thread_id"),
            user_id=params.config["configurable"].get("user_id"),
            url=url,
            media_type="image",
            name=described_image.caption if described_image else params.name,
            description=described_image.description if described_image else "",
        )
        media_item = await MediaItemModel.create(params=create_params)

        # Return formatted result
        if described_image:
            return f"""\
<image id="{media_item.id}">
    <display>![{described_image.caption}]({url})</display>
    <description>{described_image.description}</description>
    <edit_comparison>{described_image.edit_comparison}</edit_comparison>
</image>
"""
        return f"""\
<image id="{media_item.id}">
    <display>![{params.name}]({url})</display>
</image>
"""

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        input_image: str,
        prompt: str,
        name: str,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> str:
        # Extract kwargs with defaults
        model = kwargs.get("model", "black-forest-labs/flux-kontext-pro")
        seed = kwargs.get("seed", -1)
        describe = kwargs.get("describe", False)

        logger.debug(f"Editing image using {model}")
        tmp_upload_file = None
        input_image_file = None

        try:
            # Download and prepare input image
            tmp_upload_file, input_image_file = await self._download_input_image(
                input_image
            )

            # Prepare input arguments
            input_args = self._prepare_input_args(
                prompt=prompt,
                input_image=input_image_file,
                seed=seed,
            )

            # Call Replicate API
            output = await replicate.async_run(model, input=input_args)

            # Handle single output (FLUX Kontext returns single image)
            if not isinstance(output, replicate.helpers.FileOutput):
                raise ValueError(f"Unexpected output type: {type(output)}")

            # Save and process the edited image
            editing_params = ImageEditingParams(
                model=model,
                name=name,
                prompt=prompt,
                input_args=input_args,
                describe=describe,
                config=config,
            )
            return await self._save_and_process_edited_image(
                result=output,
                params=editing_params,
            )

        except Exception as error:
            logger.error(f"Error in FLUX Kontext image editing: {error}", exc_info=True)
            raise error
        finally:
            # Cleanup temporary files
            if input_image_file:
                input_image_file.close()
            if tmp_upload_file and os.path.exists(tmp_upload_file):
                os.remove(tmp_upload_file)
