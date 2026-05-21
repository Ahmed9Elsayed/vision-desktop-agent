# src/actions_general.py
import time
import pyautogui
from src.logger import logger


def execute_ui_action(coords, action_type="click", payload=None):
    """
    A purely generalized OS actuator. It accepts a pixel coordinate and an 
    intent, executing the raw physical mouse/keyboard action without knowing 
    what application is receiving it.
    """
    cx, cy = coords
    logger.info(f"[*] Executing '{action_type}' at coordinates ({cx:.1f}, {cy:.1f})...")
    
    if action_type == "double_click":
        pyautogui.moveTo(cx, cy, duration=0.3)
        pyautogui.doubleClick()
        
    elif action_type == "click":
        pyautogui.moveTo(cx, cy, duration=0.3)
        pyautogui.click()
        
    elif action_type == "right_click":
        pyautogui.moveTo(cx, cy, duration=0.3)
        pyautogui.rightClick()
        
    elif action_type == "type" and payload:
        pyautogui.click(cx, cy)  # Click to ensure the element has focus
        time.sleep(0.2)
        pyautogui.write(payload, interval=0.01)
        
    elif action_type == "hotkey" and payload:
        pyautogui.hotkey(*payload)