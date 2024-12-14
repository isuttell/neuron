from langchain.tools import BaseTool
import requests
from PIL import Image, PngImagePlugin
from io import BytesIO
import time
from datetime import datetime, timezone
from neuron_server.config import config
from neuron_server.logger import logger
from enum import Enum
from pydantic import BaseModel, Field
from typing import Type
import aiohttp
import shutil


class HuggingFaceRepoId(Enum):
    FLUX_1_DEV = "black-forest-labs/FLUX.1-dev"
    STABLE_DIFFUSION_3_5_LARGE = "stabilityai/stable-diffusion-3.5-large"
    # STABLE_DIFFUSION_3_5_LARGE_TURBO = "stabilityai/stable-diffusion-3.5-large-turbo"


class HuggingFaceServerlessImageGenerationToolArgs(BaseModel):
    prompt: str = Field(description="The prompt to generate the image from.")
    repo_id: HuggingFaceRepoId = Field(
        description="The repository ID of the model to use for image generation."
    )
    guidance_scale: float = Field(
        description="Guidance Scale controls how closely the generated image should adhere to the prompt. A higher guidance scale makes the image more literal or faithful to the prompt, while a lower scale allows for more creativity or 'freestyle' in the output. Adjusting this can help fine-tune the balance between fidelity and variation. The default value works for most cases.",
        default=3.5,
    )
    num_inference_steps: int = Field(
        description="Minimum Inference Steps refers to the number of iterations or steps the model uses to create the image. More steps generally improve image quality and detail, but also increase computation time. Fewer steps lead to faster results with potentially less detail or accuracy. The default value works for most cases.",
        default=25,
    )
    update_tablet: bool = Field(
        description="Whether to update the smart home tablet dashboard with the generated image. Only use this if the user explicitly asks for it.",
        default=False,
    )


class HuggingFaceServerlessImageGenerationTool(BaseTool):
    name: str = "hfs_image_generation"
    description: str = (
        "A tool that generates an image based on a given prompt using diffusion models from HuggingFace and returns it in markdown format. Use this when the user asks for an image. flux.1-dev is best for storytelling or projects requiring consistent character and scene continuity across multiple images, with more stylistic flexibility and dynamic visual variety. Stable Diffusion 3.5, however, shines in creating detailed, high-quality images based closely on explicit prompts, making it ideal for realistic scenes or when precise control over each image's look is required. The prompt should be a detailed description of what to generate. Make sure to include all relevant details such as location, time of day, art style, etc. to ensure better consistency and quality. Unless you are trying to maintain a specific style or look add random modern styles to ensure variety. Image generation times make take up to a minute. Returns a markdown image tag to be shown to the user."
    )
    args_schema: Type[HuggingFaceServerlessImageGenerationToolArgs] = (
        HuggingFaceServerlessImageGenerationToolArgs
    )
    base_api_url: str = "https://api-inference.huggingface.co/models"

    async def generate_image(
        self,
        prompt: str,
        repo_id: str,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 25,
    ) -> Image.Image:
        """
        Generate an image based on the given prompt using diffusion models from HuggingFace.

        Args:
            prompt (str): The prompt to generate the image from.
            repo_id (HuggingFaceRepoId): The repository ID of the model to use for image generation.
            guidance_scale (float, optional): The guidance scale for the image generation. Defaults to 3.5.
            num_inference_steps (int, optional): The number of inference steps for the image generation. Defaults to 25.

        Returns:
            Image.ImageFile: The generated image.
        """
        logger.debug(f"Generating hugging face image for prompt: {prompt}")
        start_time = time.perf_counter()
        url = f"{self.base_api_url}/{repo_id}"
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {config.hf_token}",
                    "Accept": "image/png",
                }
                async with session.post(
                    url,
                    headers=headers,
                    json={
                        "inputs": prompt,
                        "parameters": {
                            "guidance_scale": guidance_scale,
                            "num_inference_steps": num_inference_steps,
                        },
                    },
                ) as response:
                    response.raise_for_status()
                    image_data = await response.read()
                    return Image.open(BytesIO(image_data))
        finally:
            response_time = time.perf_counter() - start_time
            logger.debug(f"POST {url} - {round(response_time, 2)}s")

    def _run(
        self,
        prompt: str,
        repo_id: HuggingFaceRepoId = HuggingFaceRepoId.FLUX_1_DEV,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 25,
    ) -> str:
        return asyncio.run(
            self._arun(prompt, repo_id, guidance_scale, num_inference_steps)
        )

    async def _arun(
        self,
        prompt: str,
        repo_id: HuggingFaceRepoId = HuggingFaceRepoId.FLUX_1_DEV,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 25,
        update_tablet: bool = False,
    ) -> str:
        """
        Run the tool to generate an image based on the given prompt.
        Args:
            prompt (str): The prompt to generate the image from.
            repo_id (HuggingFaceRepoId, optional): The repository ID of the model to use for image generation. Defaults to FLUX_1_DEV.
            guidance_scale (float, optional): The guidance scale for the image generation. Defaults to 3.5.
            num_inference_steps (int, optional): The number of inference steps for the image generation. Defaults to 25.

        Returns:
            str: The URL or path to the generated image.
        """
        repo_id: str = repo_id if isinstance(repo_id, str) else repo_id.value
        try:
            image = await self.generate_image(
                prompt=prompt,
                repo_id=repo_id,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
            )
            now = datetime.now(timezone.utc).astimezone()
            timestamp = now.strftime("%Y%m%d%H%M%S")
            filename = f"generated_image_{timestamp}.png"
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("Description", prompt)
            pnginfo.add_text("Software", f"Repo: {repo_id}")
            pnginfo.add_text(
                "Parameters",
                f"guidance_scale={guidance_scale}, num_inference_steps={num_inference_steps}",
            )
            pnginfo.add_text(
                "DateTimeOriginal",
                now.isoformat(timespec="seconds"),
            )
            file_path = f"{config.static_folder}/images/{filename}"
            image.save(file_path, format="png", pnginfo=pnginfo)
            url = f"{config.static_content_url}/images/{filename}"
            logger.debug(f"Saved generated image to {file_path} <{url}>")
            if update_tablet:
                shutil.copy(file_path, config.tablet_image_filename)
                logger.debug(
                    f"Copied generated image to {config.tablet_image_filename}"
                )
            return f"![{prompt}]({url})"
        except Exception as e:
            logger.exception(e)
            return f"Error generating image: {str(e)}"


async def main(args):
    tool = HuggingFaceServerlessImageGenerationTool()
    return tool._run(
        prompt=args.prompt,
        guidance_scale=args.guidance_scale,
        num_inference_steps=args.num_inference_steps,
    )


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Generate an image using a prompt.")
    parser.add_argument(
        "prompt", type=str, help="The prompt to generate the image from."
    )
    parser.add_argument(
        "--guidance_scale",
        type=float,
        default=3.5,
        help="The guidance scale for the image generation.",
    )
    parser.add_argument(
        "--num_inference_steps",
        type=int,
        default=20,
        help="The number of inference steps for the image generation.",
    )
    args = parser.parse_args()

    print(asyncio.run(main(args)))
