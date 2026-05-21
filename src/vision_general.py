import base64
import json
import re
from PIL import Image
import google.generativeai as genai
from openai import OpenAI
from .config import GEMINI_API_KEY, QWEN_API_KEY
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

def get_coords_gemini(image_path, target_description):
    """Zero-shot visual grounding using Gemini. Agnostic to OS or application."""
    logger.info(f"[*] Gemini 3.1 Flash Lite: Attempting to ground target -> '{target_description}'")
    img = Image.open(image_path)
    
    generation_config = {
        "temperature": 0.0, # Maximum strictness for precise coordinate mapping
        "response_mime_type": "application/json",
    }

    prompt = (
        f"You are a general UI grounding agent. Look at the provided screen.\n"
        f"Find the UI element that best matches the following description: '{target_description}'.\n"
        f"Do not make assumptions based on standard OS layouts. Rely purely on visual and semantic matching.\n"
        f"If the element is present, provide its center coordinates.\n"
        f"If the element is completely absent or cannot be confidently identified, you MUST return exactly: {{\"x\": null, \"y\": null}}.\n"
        f"Format your response as valid JSON: {{\"x\": number or null, \"y\": number or null}} on a 1000-normalized scale."
    )
    
    try:
        response = gemini_model.generate_content([prompt, img], generation_config=generation_config)
        data = json.loads(response.text)
        
        x_norm = data.get("x")
        y_norm = data.get("y")
        
        if x_norm is not None and y_norm is not None:
            w, h = img.size
            return (x_norm / 1000) * w, (y_norm / 1000) * h
        else:
            logger.info("[-] Gemini confirmed target element is absent.")
            return None
            
    except Exception as e:
        logger.info(f"[!] Gemini grounding execution failed: {e}")
    return None

def get_coords_qwen(image_path, model_name, target_description):
    """Zero-shot visual grounding using Qwen. Agnostic to OS or application."""
    logger.info(f"[*] {model_name}: Attempting to ground target -> '{target_description}'")
    base64_str = get_base64_image(image_path)
    img = Image.open(image_path)
    w, h = img.size

    prompt = (
        f"You are a general UI grounding agent. Look at the provided screen.\n"
        f"Detect the UI element that best matches the following description: '{target_description}'.\n"
        f"Do not make assumptions based on standard OS layouts. Rely purely on visual and semantic matching.\n"
        f"If the element is completely absent, you MUST return an empty JSON object {{}}.\n"
        f"Otherwise, provide the bounding box [xmin, ymin, xmax, ymax] on a 0-1000 scale in valid JSON format."
    )

    try:
        completion = QWEN_CLIENT.chat.completions.create(
            model=model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_str}"}},
                    {"type": "text", "text": prompt}
                ],
            }],
            stream=False,
            extra_body={"enable_thinking": True, "thinking_budget": 300}
        )
        
        raw_content = completion.choices[0].message.content
        clean_json = re.sub(r'```json|```', '', raw_content).strip()
        data = json.loads(clean_json)
        
        if not data:
            logger.info(f"[-] {model_name} confirmed target element is absent.")
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
        else:
            logger.info(f"[!] {model_name} did not return a valid bounding box structure.")
            return None
            
    except Exception as e:
        logger.info(f"[!] {model_name} processing error: {e}")
        return None