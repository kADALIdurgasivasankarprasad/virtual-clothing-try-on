import os, sys
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
sys.path.insert(0, ".")

import torch
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import snapshot_download

from model.cloth_masker import AutoMasker, vis_mask
from model.pipeline import CatVTONPipeline
from utils import init_weight_dtype, resize_and_crop, resize_and_padding

# Use the exact training resolution for best color accuracy
WIDTH = 768
HEIGHT = 1024
DEVICE = "cuda"

# Better quality settings (reduces blur)
NUM_INFERENCE_STEPS = 50  # More steps = sharper results (default: 30)
GUIDANCE_SCALE = 4.0      # Higher guidance = better detail preservation (default: 2.5)

repo_path = snapshot_download(repo_id="zhengchong/CatVTON")
print(f"Model downloaded to: {repo_path}")

pipeline = CatVTONPipeline(
    base_ckpt="booksforcharlie/stable-diffusion-inpainting",
    attn_ckpt=repo_path,
    attn_ckpt_version="mix",
    weight_dtype=init_weight_dtype("fp16"),
    use_tf32=True,
    device=DEVICE,
    skip_safety_check=True,
)

# CatVTON pipeline handles memory optimization internally
# No need for manual attention/VAE slicing

mask_processor = VaeImageProcessor(
    vae_scale_factor=8, do_normalize=False,
    do_binarize=True, do_convert_grayscale=True
)

automasker = AutoMasker(
    densepose_ckpt=os.path.join(repo_path, "DensePose"),
    schp_ckpt=os.path.join(repo_path, "SCHP"),
    device=DEVICE
)

def change_garment_color(image, target_color=None, mode='hue_shift', hue_shift=0):
    """
    Change garment color

    Args:
        image: PIL Image
        target_color: RGB hex string like '#FF0000' for red (optional)
        mode: 'hue_shift' or 'colorize'
        hue_shift: Hue shift in degrees (0-360) for mode='hue_shift'

    Returns:
        PIL Image with modified color
    """
    if target_color is None:
        return image

    # Convert hex to RGB if needed
    if isinstance(target_color, str) and target_color.startswith('#'):
        target_color = tuple(int(target_color[i:i+2], 16) for i in (1, 3, 5))

    # Convert PIL to OpenCV
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)

    if mode == 'colorize':
        # Calculate target hue from RGB
        target_bgr = cv2.cvtColor(np.uint8([[target_color]]), cv2.COLOR_RGB2BGR)
        target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)
        target_hue = target_hsv[0, 0, 0]

        # Replace hue while keeping saturation and value
        hsv[:, :, 0] = target_hue

        # Boost saturation slightly for vibrant colors
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.2, 0, 255).astype(np.uint8)

    elif mode == 'hue_shift':
        # Shift hue by specified amount
        hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift // 2) % 180

    # Convert back to RGB
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)

    return Image.fromarray(rgb)

def sharpen_image(image, amount=1.3):
    """Apply sharpening to reduce blur in generated images"""
    enhancer = ImageEnhance.Sharpness(image)
    return enhancer.enhance(amount)

print(f"All models loaded! Resolution: {WIDTH}x{HEIGHT}")
print(f"Better quality settings: {NUM_INFERENCE_STEPS} steps, guidance {GUIDANCE_SCALE}")
print(f"VRAM used: {torch.cuda.memory_allocated()/1024**3:.1f} GB")
