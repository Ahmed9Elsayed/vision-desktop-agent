import os
import time
import ctypes
import pyautogui
from .config import SAVE_DIR
from src.logger import logger

# =====================================================================
# WIN32 STRUCTURES & LOW-LEVEL OS WORKSPACE HELPERS
# =====================================================================

class RECT(ctypes.Structure):
    """Win32 structure mapping for parsing hardware screen boundaries."""
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

def get_active_window_details():
    """Retrieves both the title string and physical screen boundaries of the focused window."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        
        rect = RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return title, rect
    except:
        return "", None

def get_active_window_title():
    """Helper to poll the current foreground window title text."""
    title, _ = get_active_window_details()
    return title

def is_notepad_foreground():
    """Genuinely verifies if the active window is the Notepad application, filtering out folders."""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        
        # 1. Inspect the structural Window Class Name
        class_buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, class_buf, 256)
        class_name = class_buf.value
        
        # If the class name matches File Explorer, it's a folder window, NOT the app!
        if class_name == "CabinetWClass":
            logger.info("[-] Validation Rejected: Target is a File Explorer folder window, not the Notepad application.")
            return False
            
        # 2. Check the traditional window title text
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, title_buf, length + 1)
        
        return "Notepad" in title_buf.value
    except:
        return False

# =====================================================================
# CORE REMEDIATION ACTIONS
# =====================================================================

def dismiss_blocking_window(context_tag="REMEDIATION"):
    """
    Inspects the current foreground window context. If a rogue window or blocking 
    modal is present, drives focus to its header tile and closes it via Alt+F4.
    """
    active_title, rect = get_active_window_details()
    
    if rect and active_title and active_title != "Program Manager":
        logger.info(f"[!] [{context_tag}] Targeted window barrier verified: '{active_title}'")
        
        # Calculate the exact midpoint coordinate of the window's top title bar frame
        click_x = (rect.left + rect.right) // 2
        click_y = rect.top + 15
        
        logger.info(f"[*] Driving precision focus click to header positions: ({click_x}, {click_y})")
        pyautogui.click(click_x, click_y)
        time.sleep(0.8)
        
        logger.info(f"[*] Force-closing window '{active_title}' via Alt+F4...")
        pyautogui.hotkey('alt', 'f4')
        return True
    else:
        logger.info(f"[-] [{context_tag}] Desktop wallpaper layer focused. Bypassing window closing routine safely.")
        return False

# =====================================================================
# MAIN PIPELINE AUTOMATION RUNNER
# =====================================================================

def run_automation_action(coords, post):
    """Clicks the coordinates and validates that Notepad actually launches."""
    cx, cy = coords
    logger.info(f"[*] Moving to ({cx}, {cy}) and double-clicking...")
    pyautogui.moveTo(cx, cy, duration=0.5)
    pyautogui.doubleClick()
    
    # --- LAUNCH VALIDATION WINDOW (5-Second Timeout) ---
    timeout = 5
    start_time = time.time()
    launched = False
    
    logger.info("[*] Validating Notepad launch window...")
    while time.time() - start_time < timeout:
        if is_notepad_foreground():
            launched = True
            logger.info("[+] Notepad launch verified in foreground.")
            break
        time.sleep(0.5)
        
    if not launched:
        logger.info("[!] Timeout: Notepad failed to launch (Active window misaligned).")
        return False

    # --- THE FRESH CANVAS INJECTION -> to prevent typing in an existing, previously opened note ---
    logger.info("[*] Enforcing a blank canvas: Opening a new untitled tab...")
    pyautogui.hotkey('ctrl', 'n')
    time.sleep(0.5)  # Short pause to let the new tab render cleanly

    # --- Proceed with writing if verified ---
    content = f"Title: {post['title']}\n\n{post['body']}"
    pyautogui.write(content, interval=0.01)

    # Save logic
    logger.info("[*] Saving new document...")
    pyautogui.hotkey('ctrl', 's')
    time.sleep(1)

    file_path = os.path.join(SAVE_DIR, f"post_{post['id']}.txt")
    pyautogui.write(file_path)
    pyautogui.press('enter')
    time.sleep(1)

    # --- THE OVERWRITE PROMPT DETECTION LAYER ---
    active_title = get_active_window_title()
    if "Confirm Save As" in active_title:
        logger.info(f"[!] Overwrite detected for post_{post['id']}.txt. Overriding focused default 'No'...")
        # Fire the native OS accelerator to select 'Yes' explicitly
        pyautogui.hotkey('alt', 'y')
        time.sleep(0.5)

    # Close Notepad
    pyautogui.hotkey('alt', 'f4')
    time.sleep(1)
    return True