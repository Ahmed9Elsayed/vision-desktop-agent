import base64
import json
import re
import os
import time
from PIL import Image
import google.generativeai as genai
from openai import OpenAI
from .config import GEMINI_API_KEY, QWEN_API_KEY, TARGET_LABEL

from src.logger import logger

# Setup Clients
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-3.1-flash-lite')

QWEN_CLIENT = OpenAI(
    api_key=QWEN_API_KEY,
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def get_coords_gemini(image_path, is_cropped=False):
    """Hybrid Logic: Finds the blue icon first, uses label as a tie-breaker."""
    logger.info(f"[*] Gemini 3.1 Flash Lite: Searching for blue Notepad icon (Preferring label: {TARGET_LABEL})...")
    img = Image.open(image_path)
    w, h = img.size
    
    generation_config = {
        "temperature": 0.0,  # Dropping to 0.0 for maximum strictness
        "response_mime_type": "application/json",
    }

  

    prompt = (
        f"Locate a standard blue Windows 11 notepad application shortcut icon on the screen.\n"
        f"Step 1 (Primary Target): Search for a notepad icon labeled exactly '{TARGET_LABEL}'. If found, you MUST select it.\n"
        f"Step 2 (Ambiguity Abort): If '{TARGET_LABEL}' is NOT found, and there are MULTIPLE other standard notepad icons present, you MUST NOT guess between them. The situation is ambiguous. You must abort.\n"
        f"Step 3 CRITICAL CONSTRAINT: Under all circumstances, DO NOT select any unrelated icons, folders, or unrelated text editors (such as Notepad++) even if they are named 'Notepad' or '{TARGET_LABEL}'. Your target MUST be a standard blue Windows 11 notepad application icon.\n"
        f"If the target is completely missing, or if you aborted due to Step 2 ambiguity, you MUST return exactly: {{\"x\": null, \"y\": null}}.\n"
        f"Format your response as valid JSON: {{\"x\": number or null, \"y\": number or null}} on a 1000-normalized scale."
    )

    

    
    try:
        response = gemini_model.generate_content([prompt, img], generation_config=generation_config)
        data = json.loads(response.text)
        
# ... inside the try block of get_coords_gemini ...
        x_norm = data.get("x")
        y_norm = data.get("y")

        if x_norm is not None and y_norm is not None:
            return (x_norm / 1000) * w, (y_norm / 1000) * h
        else:
            logger.info("[*] Gemini explicitly confirmed the icon is absent.")
            return "ABSENT"  # Distinct signature for a successful negative check
            
    except Exception as e:
        logger.info(f"[!] Gemini execution failed: {e}")
        return None  # Genuine system failure

def get_coords_qwen(image_path, model_name):
    logger.info(f"[*] {model_name}: Searching for icon (Target: {TARGET_LABEL})...")
    base64_str = get_base64_image(image_path)
    img = Image.open(image_path)
    w, h = img.size


    # prompt = (
    #     f"Identify all blue notepad desktop shortcut icons on the screen.\n"
    #     f"Step 1: Detect the specific notepad shortcut icon labeled exactly '{TARGET_LABEL}'.\n"
    #     f"Step 2: If multiple blue notepad icons are present, prioritize the one whose text label matches '{TARGET_LABEL}' exactly.\n"
    #     f"Step 3: If the labels are unreadable, hidden, or partially obscured, detect any available standard blue notepad icon.\n"
    #     f"Step 4: If an icon labeled exactly '{TARGET_LABEL}' does not exist on the desktop, fallback and detect any other standard blue notepad icon found.\n"
    #     f"CRITICAL CONSTRAINT: Under all circumstances, DO NOT select any unrelated icons, folders, or unrelated text editors (such as Notepad++) even if they are named 'Notepad' or '{TARGET_LABEL}'. Your target MUST be a standard blue Windows 11 notepad application icon.\n"
    #     f"If no standard blue Windows 11 notepad application shortcut icons are visible on the screen at all, you MUST return an empty JSON object {{}}.\n"
    #     f"Otherwise, provide the bounding box [xmin, ymin, xmax, ymax] on a 0-1000 scale in valid JSON format."
    # )

    prompt = (
        f"Locate a standard blue Windows 11 notepad application shortcut icon on the screen.\n"
        f"Step 1 (Primary Target): Search for a notepad icon labeled exactly '{TARGET_LABEL}'. If found, you MUST select it.\n"
        f"Step 2 (Ambiguity Abort): If '{TARGET_LABEL}' is NOT found, and there are MULTIPLE other standard notepad icons present, you MUST NOT guess between them. The situation is ambiguous. You must abort.\n"
        f"Step 3 CRITICAL CONSTRAINT: Under all circumstances, DO NOT select any unrelated icons, folders, or unrelated text editors (such as Notepad++) even if they are named 'Notepad' or '{TARGET_LABEL}'. Your target MUST be a standard blue Windows 11 notepad application icon.\n"
        f"If the target is completely missing, or if you aborted due to Step 2 ambiguity, you MUST return an empty JSON object {{}}.\n"
        f"Otherwise, provide the bounding box [xmin, ymin, xmax, ymax] on a 0-1000 scale in valid JSON format."
    )

    try:
        completion = QWEN_CLIENT.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_str}"}},
                {"type": "text", "text": prompt}
            ]}],
            stream=False,
            extra_body={"enable_thinking": True, "thinking_budget": 300}
        )
        
        raw_content = completion.choices[0].message.content
        clean_json = re.sub(r'```json|```', '', raw_content).strip()
        data = json.loads(clean_json)
        
        if not data:  # Catch empty JSON target not found scenario
            logger.info(f"[*] {model_name} explicitly reported target icon is not present.")
            return None

        if isinstance(data, list): data = data[0]
        box = data.get("bbox_2d") or data.get("box_2d") or data.get("bounding_box")
        
        if box and isinstance(box, list) and len(box) == 4:
            xmin, ymin, xmax, ymax = box
            if ymin > ymax: ymin, ymax = ymax, ymin
            if xmin > xmax: xmin, xmax = xmax, xmin

            center_x = ((xmin + xmax) / 2 / 1000) * w
            center_y = ((ymin + ymax) / 2 / 1000) * h
            return center_x, center_y
            
    except Exception as e:
        logger.info(f"[!] {model_name} processing error: {e}")
    return None


def visual_search_cascaded(image_path):
    """
    The 'ReGround' Method enhanced with an Asymmetric Fallback Chain.
    1. Global Grounding (Gemini).
    2. If verified ABSENT -> Stop immediately to save time and API costs.
    3. If system error -> Fallback to Qwen Plus -> Qwen Flash.
    4. If coordinates valid -> Crop and Re-Ground for high precision.
    """
    # 1. Global Attempt
    global_coords = get_coords_gemini(image_path)
    
    # --- SMART SKIP ACCELERATION ---
    # If Gemini successfully ran and explicitly confirmed it's not there, trust it.
    if global_coords == "ABSENT":
        logger.info("[-] Gemini confirmed absolute absence. Bypassing fallbacks to save time.")
        return None

    # --- SYSTEM ERROR FALLBACK CHAIN ---
    # If Gemini encountered a genuine execution crash/timeout (None), deploy fallbacks
    if not global_coords:
        logger.info("[*] Gemini system error. Deploying Qwen Plus fallback...")
        coords = get_coords_qwen(image_path, "qwen3-vl-plus-2025-12-19")
        
        if not coords:
            logger.info("[*] Qwen Plus failed. Deploying Qwen Flash fallback...")
            coords = get_coords_qwen(image_path, "qwen3-vl-flash")
        return coords

    # 2. Re-Grounding (Zooming in)
    try:
        img = Image.open(image_path)
        gx, gy = global_coords
        crop_size = 250 # Pixels
        left = max(0, gx - crop_size//2)
        top = max(0, gy - crop_size//2)
        right = min(img.width, gx + crop_size//2)
        bottom = min(img.height, gy + crop_size//2)
        
        crop_path = os.path.join("screenshots", "debug_crop.png")

        img.crop((left, top, right, bottom)).save(crop_path)

        logger.info("[*] Throttling API for 4 seconds to bypass free-tier rate limits...")
        time.sleep(2.5)
        
        # Ground again on the clean close-up crop
        local_coords = get_coords_gemini(crop_path, is_cropped=True)
        
        if local_coords == "ABSENT":
            return None
        elif local_coords:
            lx, ly = local_coords
            # Map coordinates back to the global screen space
            return left + lx, top + ly
            
    except Exception as e:
        logger.info(f"[!] Zoom processing framework encountered an error: {e}")

    # Return initial coords as a fallback safeguard if zooming processing fails
    return global_coords

