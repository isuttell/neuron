from langchain.tools import BaseTool
import requests
from PIL import Image
from io import BytesIO
import base64
import time
from datetime import datetime
from neuron_server.config import config
from neuron_server.logger import logger


class HuggingFaceImageGenerationTool(BaseTool):
    name: str = "HuggingFaceImageGenerationTool"
    description: str = (
        "A tool that generates images based on a given prompt using diffusion models from HuggingFace. Always use the default values for guidance_scale and num_inference_steps. Use this when the user asks for an image. Returns the url to the generated image which should be displayed using markdown."
    )
    api_url: str

    def generate_image(
        self,
        prompt: str,
        guidance_scale: float = 3.5,
        num_inference_steps: int = 20,
    ) -> Image.Image:
        """
        Generate an image based on the given prompt using diffusion models from HuggingFace.

        Args:
            prompt (str): The prompt to generate the image from.
            guidance_scale (float, optional): The guidance scale for the image generation. Defaults to 3.5.
            num_inference_steps (int, optional): The number of inference steps for the image generation. Defaults to 10.

        Returns:
            Image.ImageFile: The generated image.
        """
        start_time = time.perf_counter()
        try:
            logger.debug(
                f'Generating image of "{prompt}" using {self.api_url} with guidance_scale={guidance_scale} and num_inference_steps={num_inference_steps}'
            )
            headers = {
                "Authorization": f"Bearer {config.hf_token}",
                "Accept": "image/png",
            }
            response = requests.post(
                self.api_url,
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
            logger.debug(f"GET {self.api_url} - {round(response_time, 2)}s")

    def _run(
        self, prompt: str, guidance_scale: float = 3.5, num_inference_steps: int = 20
    ) -> str:
        """
        Run the tool to generate an image based on the given prompt.
        Args:
            prompt (str): The prompt to generate the image from.
            guidance_scale (float, optional): The guidance scale for the image generation. Defaults to 3.5.
            num_inference_steps (int, optional): The number of inference steps for the image generation. Defaults to 10.

        Returns:
            str: The URL or path to the generated image.
        """
        image = self.generate_image(
            prompt, guidance_scale, num_inference_steps=num_inference_steps
        )
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"generated_image_{timestamp}.png"
        file_path = f"{config.static_folder}/images/{filename}"
        image.save(file_path, format="png")
        logger.debug(f"Saved image to {file_path}")
        return f"http://localhost:5000/static/images/{filename}"
        # buffered = BytesIO()
        # image.save(buffered, format="png")
        # img_str = base64.b64encode(buffered.getvalue()).decode()
        # return f"data:image/png;base64,{img_str}"


flux_tool = HuggingFaceImageGenerationTool(
    api_url="https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev",
    description="A tool that generates images based on a given prompt using FLUX.1-dev. Always use the default values for guidance_scale and num_inference_steps. Use this when the user asks for an image. Returns the url to the generated image which should be displayed using markdown.",
)

stable_diffusion_tool = HuggingFaceImageGenerationTool(
    api_url="https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3.5-large",
    description="A tool that generates images based on a given prompt using Stable Diffussion 3.5 Large. Always use the default values for guidance_scale and num_inference_steps. Use this when the user asks for an image. Returns the url to the generated image which should be displayed using markdown.",
)


stable_diffusion_tool = HuggingFaceImageGenerationTool(
    api_url="https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3.5-large",
    description="A tool that generates images based on a given prompt using Stable Diffussion 3.5 Large. Always use the default values for guidance_scale and num_inference_steps. Use this when the user asks for an image. Returns the url to the generated image which should be displayed using markdown.",
)


if __name__ == "__main__":
    import argparse

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

    tool = HuggingFaceImageGenerationTool(
        api_url="https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3.5-large"
    )
    tool._run(args.prompt, args.guidance_scale, args.num_inference_steps)
    print("Done")
