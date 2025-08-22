#!/usr/bin/env python

"""
AWS Nova Canvas MCP Server
==========================

The AWS Nova Canvas Model Context Protocol (MCP) Server is a MCP server for generating images using Amazon Nova Canvas

Features
- Text-based image generation
- Create images from text prompts with generate_image
- Customizable dimensions (320-4096px), quality options, and negative prompting
- Supports multiple image generation (1-5) in single request
- Adjustable parameters like cfg_scale (1.1-10.0) and seeded generation

Color-guided image generation
- Generate images with specific color palettes using generate_image_with_colors
- Define up to 10 hex color values to influence the image style and mood
- Same customization options as text-based generation

Workspace integration
- Images saved to user-specified workspace directories with automatic folder creation

AWS authentication
- Uses AWS profiles for secure access to Amazon Nova Canvas services

Prerequisites
1. Install uv from Astral or the GitHub README
2. Install Python using uv python install 3.10+
3. Set up AWS credentials with access to Amazon Bedrock and Nova Canvas
   - You need an AWS account with Amazon Bedrock and Amazon Nova Canvas enabled
   - Configure AWS credentials with aws configure or environment variables
   - Ensure your IAM role/user has permissions to use Amazon Bedrock and Nova Canvas
4. Output directory must be created (default is ./output)
5. The files `amazon_image_gen.py` and `file_utils.py` should placed be in the same
   folder as this file. The download locations for these files are:
   - file_utils.py: https://github.com/aws-samples/amazon-nova-samples/blob/main/multimodal-generation/image-generation/notebook/file_utils.py
   - amazon_image_gen.py: https://github.com/aws-samples/amazon-nova-samples/blob/main/multimodal-generation/image-generation/notebook/amazon_image_gen.py

Common errors
- Running in a region where Nova Canvas is not available
- Not creating an output directory, or not having write permissions to the directory

Tools
- mcp_generate_image
- mcp_generate_image_with_colors
(Most up to date list of tools here: https://github.com/awslabs/mcp/blob/main/src/nova-canvas-mcp-server/awslabs/nova_canvas_mcp_server/server.py)

References
- Github: https://github.com/awslabs/mcp/tree/main/src/nova-canvas-mcp-server
- Home Page: https://awslabs.github.io/mcp/servers/nova-canvas-mcp-server/

"""

import base64
import file_utils
import logging
import os
import sys

from amazon_image_gen import BedrockImageGenerator
from botocore.config import Config
from datetime import datetime
from mcp import stdio_client, StdioServerParameters
from PIL import Image
from random import randint
from shutil import which
from typing import List

from strands import Agent, tool
from strands.handlers.callback_handler import PrintingCallbackHandler
from strands.models.bedrock import BedrockModel
from strands_tools import file_read, file_write
from strands.tools.mcp.mcp_client import MCPClient


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logging.getLogger("strands").setLevel(logging.INFO)
logging.getLogger("strands.agent").setLevel(logging.INFO)
logging.getLogger("strands.event_loop").setLevel(logging.INFO)
logging.getLogger("strands.handlers").setLevel(logging.INFO)
logging.getLogger("strands.models").setLevel(logging.INFO)
logging.getLogger("strands.tools").setLevel(logging.INFO)
logging.getLogger("strands.types").setLevel(logging.INFO)

# Configuration with environment variable fallbacks
HOME = os.getenv('HOME')
PWD = os.getenv('PWD', os.getcwd())
BEDROCK_REGION = os.getenv("BEDROCK_REGION", 'us-east-1')
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")
BEDROCK_CANVAS_MODEL_ID = os.getenv("BEDROCK_CANVAS_MODEL_ID", "us.amazon.bedrock-nova-canvas-v1:0")
AWS_API_MCP_WORKING_DIR = os.getenv('AWS_API_MCP_WORKING_DIR', os.path.join(PWD, "output"))

# Ensure working directory exists
os.makedirs(AWS_API_MCP_WORKING_DIR, exist_ok=True)



@tool
def resize_image(image_path: str, width: int, height: int) -> str:
    """
    Resize an image to specified dimensions using Pillow.

    Args:
        image_path (str): Path to input image file to resize
        width (int): Target width in pixels
        height (int): Target height in pixels

    Returns:
        str: Path to resized image if successful, error message if failed

    Example:
        >>> resize_image("input.jpg", 800, 600)
        'output/2024-01-20_12-34-56/resized_image.jpg'
    """

    try:
        # Open the image
        img = Image.open(image_path)

        # Resize image
        resized_img = img.resize((width, height))

        # Create output directory
        generation_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_directory = f"output/{generation_id}"
        os.makedirs(output_directory, exist_ok=True)

        # Generate output path
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(output_directory, f"{name}_resized{ext}")

        # Save resized image
        resized_img.save(output_path)
        return output_path

    except Exception as e:
        return f"Error resizing image: {str(e)}"



def load_and_resize_if_needed(image_path: str, max_pixels: int = 4194304) -> str:

    """
    Load an image and resize it if the total pixel count exceeds max_pixels.
    Maintains aspect ratio while resizing. Returns base64 encoded image data.

    Args:
        image_path (str): Path to input image file
        max_pixels (int): Maximum number of pixels allowed (width * height)
                         Defaults to 4194304 (2048 x 2048)

    Returns:
        str: Base64 encoded image data if successful, error message if failed.
             If image is under max_pixels, returns original image path.

    Example:
        >>> load_and_resize_if_needed("large_image.jpg")
        'data:image/jpeg;base64,/9j/4AAQSkZJRg...'
    """

    try:
        # Open and get image dimensions
        img = Image.open(image_path)
        width, height = img.size
        current_pixels = width * height

        # Return original if under max pixels
        if current_pixels <= max_pixels:
            return image_path

        # Calculate new dimensions maintaining aspect ratio
        ratio = width / height
        new_height = int((max_pixels / ratio) ** 0.5)
        new_width = int(new_height * ratio)

        # Use resize_image function to resize and save
        resized_image_path = resize_image(image_path, new_width, new_height)
        with open(resized_image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf8")

    except Exception as e:
        return f"Error processing image: {str(e)}"



@tool
def remove_background(image_path: str) -> str:
    """
    Remove the background from an input image using AWS Bedrock Nova Canvas.

    Args:
        image_path (str): Path to input image file to remove background from.
                          The image should not have more than 4194304 pixels

    Returns:
        str: Success message with output directory path if successful, error message if failed

    Example:
        >>> remove_background("input.jpg")
        'Image generated and saved in the folder: output/2024-01-20_12-34-56'

    Reference:
        https://github.com/aws-samples/amazon-nova-samples/blob/main/multimodal-generation/image-generation/notebook/02_background_removal.ipynb
    """

    source_image_base64 = load_and_resize_if_needed(image_path)

    # Configure the inference parameters.
    inference_params = {
        "taskType": "BACKGROUND_REMOVAL",
        "backgroundRemovalParams": {
            "image": source_image_base64,
        },
    }

    # Define an output directory with a unique name.
    generation_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_directory = f"output/{generation_id}"

    # Create the generator.
    generator = BedrockImageGenerator(
        output_directory=output_directory
    )

    # Generate the image(s).
    response = generator.generate_images(inference_params)

    if "images" in response:
        # Save and display each image
        images = file_utils.save_base64_images(response["images"], output_directory, "image")
        if len(images):
            return f'Image generated and saved in the folder: {output_directory}'
            # return image[0]  # Return the first image
        else:
            return 'remove_background(): No images returned in response'
    else:
        return 'remove_background(): Failed to generate image'



@tool
def condition_image(image_path: str, prompt: str, control_mode: str, control_strength: float = 0.3, quality: str = "standard", width: int = 1280, height: int = 720, cfgScale: float = 8.0, seed: int = None) -> str:

    """
    Generate a new image based on a conditioning image and text prompt.

    Args:
        conditioning_image_path (str): Path to input image file that will be used as the conditioning image
        prompt (str): Text description of the desired output image
        control_mode (str): Mode for image control - either "CANNY_EDGE" or "SEGMENTATION"
        control_strength (float, optional): How closely to match the conditioning image. Defaults to 0.3.
        quality (str, optional): Image quality setting - "standard" or "premium". Defaults to "standard".
        width (int, optional): Output image width in pixels. Defaults to 1280.
        height (int, optional): Output image height in pixels (must be divisible by 16). Defaults to 720.
        cfgScale (float, optional): How closely to follow the prompt. Defaults to 8.0.
        seed (int, optional): Random seed for reproducible results. Defaults to None.

    Returns:
        str: Path to generated image if successful, error message string if failed

    Example:
        >>> condition_image("input.jpg", 
                          "3d animated film style, a woman with blond hair wearing green dress",
                          "CANNY_EDGE",
                          control_strength=0.4)
    Reference:
        https://github.com/aws-samples/amazon-nova-samples/blob/main/multimodal-generation/image-generation/notebook/03_image_guided_generation.ipynb
    """

    condition_image = load_and_resize_if_needed(image_path)

    if not seed:
        seed = randint(0, 858993459)

    # Configure the inference parameters.
    inference_params = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt,
            "conditionImage": condition_image,
            "controlMode": control_mode, # "CANNY_EDGE" or "SEGMENTATION",
            "controlStrength": control_strength  # How closely to match the condition image
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,   # Number of variations to generate. 1 to 5.
            "quality": quality,    # Allowed values are "standard" and "premium"
            "width": width,        # See README for supported output resolutions
            "height": height,      # must be divisible by 16
            "cfgScale": cfgScale,  # How closely the prompt will be followed
            "seed": seed,          # Use a random seed
        }
    }

    # Define an output directory with a unique name.
    generation_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_directory = f"output/{generation_id}"

    # Create the generator.
    generator = BedrockImageGenerator(
        output_directory=output_directory
    )

    # Generate the image(s).
    response = generator.generate_images(inference_params)

    if "images" in response:
        # Save and display each image
        images = file_utils.save_base64_images(response["images"], output_directory, "image")
        if len(images):
            return image[0]
        else:
            return 'condition_image(): No images returned in response'
    else:
        return "condition_image(): Failed to generate image"



def create_mcp_client() -> MCPClient:
    """Create an MCP client for the AWS Nova Canvas MCP Server.
    
    Args:
        None
        
    Returns:
        MCPClient: Configured MCP client
        
    Raises:
        RuntimeError: If required command is not found
    """
    cmd = which('uvx')
    if not cmd:
        raise RuntimeError("uvx command not found. Please install uvx.")
    return MCPClient(lambda: stdio_client(
        StdioServerParameters(
            command=cmd,
            args=['awslabs.nova-canvas-mcp-server@latest'],
            env={
                # 'AWS_PROFILE': 'default',
                'AWS_REGION': BEDROCK_REGION,
                'FASTMCP_LOG_LEVEL': 'ERROR'
            },
            disabled=False,
            autoApprove=[]
        )
    ))


def create_bedrock_model(model_id: str, region: str, temperature: float = 0.1) -> BedrockModel:
    """Create a Bedrock model with appropriate configuration.
    
    Args:
        model_id: The Bedrock model ID to use
        region: AWS region for Bedrock
        temperature: Model temperature (lower is more deterministic)
        
    Returns:
        BedrockModel: Configured Bedrock model
    """
    return BedrockModel(
        model_id=model_id,
        max_tokens=2048,
        boto_client_config=Config(
            region_name=region,
            read_timeout=120,
            connect_timeout=120,
            retries=dict(max_attempts=4, mode="adaptive"),
        ),
        temperature=temperature
    )


AWS_NOVA_CANVAS_SYSTEM_PROMPT = """
You are an AWS Nova Canvas assistant focused on image generation capabilities.

Use the available tools to:
- Generate images from text descriptions
- Create images with specific color palettes
- Configure image dimensions, quality and other parameters
- Save generated images to workspace directories
- Apply negative prompting and other advanced features
- Remove background from images
- Resize images

The output folder should be "./output", but if errors are encountered, use the current folder.

Provide accurate guidance on using AWS Nova Canvas for image generation tasks.
"""


prompts = [
    "List all my tools",
    "Generate a majestic mountain landscape at golden hour, with dramatic clouds catching the warm sunset light, snow-capped peaks, and a crystal clear alpine lake reflecting the sky",
    "Create a sprawling cyberpunk metropolis at night with towering skyscrapers, holographic billboards, flying vehicles weaving between buildings, and neon lights reflecting off rain-slicked streets",
    "Generate an ethereal abstract art piece with swirling patterns of deep sapphire blue and metallic gold, cosmic nebula-like forms, and flowing liquid textures",
    "Create a dreamy portrait in loose watercolor style with soft edges, delicate color washes, expressive brush strokes, and gentle light illuminating the subject's features",
    "Generate a pristine tropical paradise with turquoise waters, swaying palm trees, powdery white sand, dramatic cloud formations, and gentle waves lapping at the shore during magic hour",
    "Remove the background from [my_image.jpg]"
]



def run_interactive_session(agent: Agent, example_prompts: List[str]) -> None:
    """Run an interactive session with the AWS Nova Canvas Agent.
    
    Args:
        agent: The configured Strands Agent for Nova Canvas image generation
        example_prompts: List of example image generation prompts to show the user
    """
    print('------------------------')
    print('  AWS Nova Canvas Demo  ')
    print('------------------------')
    print('\nExample prompts to try:')
    print('\n'.join(['- ' + p for p in example_prompts]))
    print("\nType 'exit' to quit.\n")

    while True:
        try:
            user_input = input("Prompt: ")

            if user_input.lower() in ["exit", "quit"]:
                break

            print("\nThinking...\n")
            response = agent(user_input)
            print('\n' + '-' * 80 + '\n')
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main():
    """
    Main entry point for the AWS Nova Canvas MCP Server demo.
    """

    logging.getLogger("strands").setLevel(logging.DEBUG)
    
    try:
        # Create MCP client
        mcp_client = create_mcp_client()
        
        # Create Bedrock model
        model = create_bedrock_model(
            model_id=BEDROCK_MODEL_ID,
            region=BEDROCK_REGION
        )
        
        with mcp_client:
            # Get available tools
            tools = mcp_client.list_tools_sync() + [file_read, file_write, condition_image, remove_background]
            print(f'Tools: {tools}')

            # Create agent with callback handler for better visibility
            nova_canvas_agent = Agent(
                system_prompt = AWS_NOVA_CANVAS_SYSTEM_PROMPT,
                model = model,
                tools = tools,
                callback_handler = PrintingCallbackHandler()
            )
            
            # Run interactive session
            run_interactive_session(nova_canvas_agent, prompts)
            
    except Exception as e:
        logger.error(f"Error initializing AWS Nova Canvas Agent: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
