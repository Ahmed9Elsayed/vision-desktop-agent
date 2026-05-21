# src/visualizer.py
import cv2
import os
from src.config import DELIVERABLES_DIR
from src.logger import logger

def save_annotated_screenshot(screenshot_path, coords, identifier, is_general=False):
    """
    Unified annotation utility.
    - Path 2 (Default): identifier = post_id. Uses TARGET_LABEL.
    - Path 1 (is_general=True): identifier = step_num. Uses generic Task labeling.
    """
    try:
        # 1. Dynamic Routing: Decide labels and filenames based on the execution path
        if is_general:
            label_text = f"Detected: Task {identifier} Target"
            output_filename = f"path1_deliverable_step_{identifier}.png"
        else:
            # Lazy import to prevent config coupling if used strictly for general tasks
            from src.config import TARGET_LABEL 
            label_text = f"Detected: {TARGET_LABEL}"
            output_filename = f"annotated_screenshot_post_{identifier}.png"

        # 2. Raw Image Processing
        img = cv2.imread(screenshot_path)
        if img is None:
            logger.info(f"[-] Visualization Warning: Unable to read frame at {screenshot_path}")
            return
            
        height, width, _ = img.shape
        px, py = int(coords[0]), int(coords[1])
        
        # 3. Geometric Bounding Math
        box_radius = 40 
        xmin = max(0, px - box_radius)
        ymin = max(0, py - box_radius)
        xmax = min(width, px + box_radius)
        ymax = min(height, py + box_radius)
        
        # 4. Draw Overlay Assets
        cv2.rectangle(img, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
        cv2.circle(img, (px, py), 3, (0, 0, 255), -1)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)
        text_ymin = max(text_h + 10, ymin - 10)
        
        cv2.rectangle(img, (xmin, text_ymin - text_h - 6), (xmin + text_w + 6, text_ymin + 4), (0, 0, 0), -1)
        cv2.putText(img, label_text, (xmin + 3, text_ymin), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        
        # 5. Save Output
        output_path = os.path.join(DELIVERABLES_DIR, output_filename)
        cv2.imwrite(output_path, img)
        logger.info(f"[+] Deliverable Saved: {output_path}")
        
    except Exception as e:
        logger.info(f"[-] Annotation Pipeline Error: {e}")