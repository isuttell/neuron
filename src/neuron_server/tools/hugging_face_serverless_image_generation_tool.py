from langchain.tools import BaseTool
import requests
from PIL import Image, PngImagePlugin
from io import BytesIO
import time
from datetime import datetime, timezone
from neuron_server.config import config
from neuron_server.logger import logger
from enum import Enum


class HuggingFaceRepoId(Enum):
    FLUX_1_DEV = "black-forest-labs/FLUX.1-dev"
    STABLE_DIFFUSION_3_5_LARGE = "stabilityai/stable-diffusion-3.5-large"
    # STABLE_DIFFUSION_3_5_LARGE_TURBO = "stabilityai/stable-diffusion-3.5-large-turbo"


class HuggingFaceServerlessImageGenerationTool(BaseTool):
    name: str = "hfs_image_generation"
    description: str = (
        "A tool that generates images based on a given prompt using diffusion models from HuggingFace. Always use the default values for guidance_scale and num_inference_steps unless the user specifies otherwise. Use this when the user asks for an image. flux.1-dev is best for storytelling or projects requiring consistent character and scene continuity across multiple images, with more stylistic flexibility and dynamic visual variety. Stable Diffusion 3.5, however, shines in creating detailed, high-quality images based closely on explicit prompts, making it ideal for realistic scenes or when precise control over each image's look is required. Use flux.1-dev for narrative sequences and Stable Diffusion 3.5 for fine-tuned, standalone imagery. The prompt should be a detailed description of what to generate. Make sure to include all relevant details such as location, time of day, art style, etc. Returns the url to the generated image which must be displayed using markdown."
    )
    base_api_url: str = "https://api-inference.huggingface.co/models"

    def generate_image(
        self,
        prompt: str,
        repo_id: str,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 20,
    ) -> Image.Image:
        """
        Generate an image based on the given prompt using diffusion models from HuggingFace.

        Args:
            prompt (str): The prompt to generate the image from.
            repo_id (HuggingFaceRepoId): The repository ID of the model to use for image generation.
            guidance_scale (float, optional): The guidance scale for the image generation. Defaults to 3.5.
            num_inference_steps (int, optional): The number of inference steps for the image generation. Defaults to 10.

        Returns:
            Image.ImageFile: The generated image.
        """
        start_time = time.perf_counter()
        url = f"{self.base_api_url}/{repo_id}"
        try:
            headers = {
                "Authorization": f"Bearer {config.hf_token}",
                "Accept": "image/png",
            }
            response = requests.post(
                url,
                headers=headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "guidance_scale": guidance_scale,
                        "num_inference_steps": num_inference_steps,
                    },
                },
            )
            response.raise_for_status()
            return Image.open(BytesIO(response.content))
        finally:
            response_time = time.perf_counter() - start_time
            logger.debug(f"GET {url} - {round(response_time, 2)}s")

    def _run(
        self,
        prompt: str,
        repo_id: HuggingFaceRepoId = HuggingFaceRepoId.FLUX_1_DEV,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 20,
    ) -> str:
        """
        Run the tool to generate an image based on the given prompt.
        Args:
            prompt (str): The prompt to generate the image from.
            repo_id (HuggingFaceRepoId, optional): The repository ID of the model to use for image generation. Defaults to FLUX_1_DEV.
            guidance_scale (float, optional): The guidance scale for the image generation. Defaults to 3.5.
            num_inference_steps (int, optional): The number of inference steps for the image generation. Defaults to 10.

        Returns:
            str: The URL or path to the generated image.
        """
        repo_id: str = repo_id if isinstance(repo_id, str) else repo_id.value
        try:
            image = self.generate_image(
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
