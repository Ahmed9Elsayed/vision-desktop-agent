import time
import pyautogui
from src.config import TEMP_IMG
from src.vision_general import get_coords_gemini, get_coords_qwen
from src.actions_general import execute_ui_action
from src.logger import logger
pyautogui.FAILSAFE = False

def main():
    logger.info("[*] Initializing Generalized Visual Grounding Agent (Path 1)...")
    
    # Tier 1 Clear: Reset desktop environment for a clean start
    logger.info("[*] Clearing desktop environment...")
    time.sleep(1)
    pyautogui.hotkey('win', 'm')
    time.sleep(2)
    
    # Cursor parking optimization to prevent hover states
    pyautogui.moveTo(5, 5) 
    time.sleep(0.5)

    # =========================================================================
    # THE GENERALIZED INSTRUCTION SET
    # The agent simply reads the screen to figure out what these natural language descriptions refer to.
    # =========================================================================
    
    # INTENT-BASED GROUNDING INSTRUCTION SET 
    # We need to use the icon's functionality to locate the icon, then do our task on it
    # the description and tasks are specific to Notepad, but we can locate and execute tasks on many icons by specifing their most used funcitonality
 
    # tasks = [
    #     {
    #         "description": "The blue Windows 11 Notepad application shortcut icon on the desktop wallpaper",
    #         "action": "double_click"
    #     },
        # {
        #     "description": "The large blank text input area in the center of the application window",
        #     "action": "type",
        #     "payload": "Hello! This text was written by a generalized visual grounding agent based on natural language task interpretation."
        # },
        # {
        #     "description": "The 'File' menu tab button at the top left of the application window frame",
        #     "action": "click"
        # },
        # {
        #     "description": "The 'Save' option text in the opened dropdown menu list",
        #     "action": "click"
        # }
    # ]

    
    # =========================================================================
    # The agent must deduce the target based purely on its functional purpose.
    # =========================================================================
    tasks = [
        # --- TEST 1: The System Trash Test ---
        {
            "description": "The system folder used to recover deleted files or empty the trash",
            "action": "double_click"
        }
        ,{
            "description": "The 'X' or cross button located (probably) at the top right corner of the active application window frame, used to close the program",
            "action": "click"
        }
        
        # --- TEST 2: The Web Browser Test (Brave/Edge/Chrome agnostic) ---
        # {
        #     "description": "The Microsoft's web browser icon used to navigate the internet",
        #     "action": "double_click"
        # }
        # ,{
        #     "description": "The 'X' or cross button located (probably) at the top right corner of the active application window frame, used to close the program",
        #     "action": "click"
        # }
        
        # --- TEST 3: The Code Editor Test (VS Code agnostic) ---
        # {
        #     "description": "The integrated development environment (IDE) or text editor used by programmers to write code",
        #     "action": "double_click"
        # }
        # ,{
        #     "description": "The 'X' or cross button located (probably) at the top right corner of the active application window frame, used to close the program",
        #     "action": "click"
        # }

        # --- TEST 4: The OS Navigation Test ---
        # {
        #     "description": "The main operating system button on the taskbar used to open the system menu or search the computer",
        #     "action": "click"
        # }
        
        # --- TEST 5: The Version Control Test ---
        # {
        #     "description": "The version control desktop client used by developers to manage and push software repositories",
        #     "action": "right_click"
        # }

        # --- TEST 6: The Media Recording Test ---
        # {
        #     "description": "The broadcasting software used to record the screen or stream video",
        #     "action": "double_click"
        # }
        # ,{
        #     "description": "The 'X' or cross button located (probably) at the top right corner of the active application window frame, used to close the program",
        #     "action": "click"
        # }


    ]

    # Execute the semantic instruction pipeline sequentially
    for step, task in enumerate(tasks, 1):
        logger.info(f"\n[>] Executing Step {step}: Grounding '{task['description']}'")
        
        # Take a fresh screenshot of the CURRENT UI state before each move
        pyautogui.screenshot().save(TEMP_IMG)
        
        # 1. Grounding Phase (Gemini Primary -> Qwen Fallbacks)
        coords = get_coords_gemini(TEMP_IMG, task['description'])
        
        if not coords:
            coords = get_coords_qwen(TEMP_IMG, "qwen3-vl-plus-2025-12-19", task['description'])
            
        if not coords:
            coords = get_coords_qwen(TEMP_IMG, "qwen3-vl-flash", task['description'])

        # 2. Actuation Phase
        if coords:
            # --- PATH 1 ANNOTATION INJECTION ---
            from src.visualizer import save_annotated_screenshot
            save_annotated_screenshot(TEMP_IMG, coords, step, is_general=True)
            # -----------------------------------
            
            execute_ui_action(coords, action_type=task['action'], payload=task.get('payload'))
            time.sleep(2) 
            pyautogui.moveTo(5, 5) # Park cursor out of the way for the next screenshot
        else:
            logger.info(f"[!] Critical Failure: Grounding engine could not locate the element.")
            logger.info("[-] Halting task sequence.")
            break

    logger.info("\n[+] Generalized Task Sequence Completed.")

if __name__ == "__main__":
    main()


