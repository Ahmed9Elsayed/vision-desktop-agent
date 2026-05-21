import time
import pyautogui
from src.config import TEMP_IMG
from src.scraper import fetch_posts_selenium
from src.vision2 import visual_search_cascaded 
from src.actions import run_automation_action, dismiss_blocking_window
from src.visualizer import save_annotated_screenshot
from src.logger import logger

pyautogui.FAILSAFE = False

def main():
    posts = fetch_posts_selenium(10)
    if not posts: 
        logger.info("[!] Data source unavailable. Exiting gracefully.")
        return

    # --- START PROGRAM BENCHMARK TIMER ---
    start_total_time = time.time()
    total_posts_count = len(posts)
    
    logger.info(f"\n[*] Telemetry Initialized: Processing {total_posts_count} posts...")
    
    for post in posts:
        logger.info(f"\n[>] Processing Post ID: {post['id']}")
        post_fully_processed = False
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            logger.info(f"[*] Grounding & Launch Attempt {attempt}/{max_attempts}...")
            
            # Tier 1 Clear: Reset desktop environment
            time.sleep(1)
            pyautogui.hotkey('win', 'm')
            time.sleep(2)

            # CURSOR PARKING OPTIMIZATION: Preserved at (5, 1075) per your hardware setup to prevent icon hovering pop-up
            pyautogui.moveTo(3, 3)
            time.sleep(0.2)

            # Capture and Evaluate Screen
            pyautogui.screenshot().save(TEMP_IMG)
            coords = visual_search_cascaded(TEMP_IMG)
            
            # -----------------------------------------------------------------
            # CASE A: System found an icon coordinate candidate
            # -----------------------------------------------------------------
            if coords:

                save_annotated_screenshot(TEMP_IMG, coords, post['id'])
                success = run_automation_action(coords, post)
                
                if success:
                    post_fully_processed = True
                    logger.info(f"[+] Successfully completed Post {post['id']} on attempt {attempt}.")
                    break  # Break out of retry loop immediately!
                else:
                    logger.info(f"[!] Launch verification failed on attempt {attempt} (Wrong window caught).")
                    # Clean the slate using the unified focus-and-close action function
                    dismiss_blocking_window(context_tag=f"CASE A - Att {attempt}")
                    time.sleep(1.0) # Delay to clear system buffer before retry turn
                    
            # -----------------------------------------------------------------
            # CASE B: Vision System returned None (Screen blocked or modal up)
            # -----------------------------------------------------------------
            else:
                logger.info(f"[!] Grounding model returned None on attempt {attempt}. Checking for focus locks...")
                # Clean the slate using the unified focus-and-close action function
                dismiss_blocking_window(context_tag=f"CASE B - Att {attempt}")
                time.sleep(1.0)

        # --- FINAL POST STATUS SUMMARY Evaluation ---
        if not post_fully_processed:
            logger.info(f"[!] Error: Failed to process Post {post['id']} cleanly after {max_attempts} total layout attempts. Moving to next item.")

    # --- END PROGRAM BENCHMARK TIMER ---
    end_total_time = time.time()
    
    # Metrics Calculations
    execution_duration = end_total_time - start_total_time
    average_duration_per_post = execution_duration / total_posts_count

    logger.info("\n" + "="*50)
    logger.info("                PERFORMANCE METRICS")
    logger.info("="*50)
    logger.info(f"[*] Total Posts Checked:     {total_posts_count}")
    logger.info(f"[*] Total Execution Time:    {execution_duration:.2f} seconds ({execution_duration/60:.2f} minutes)")
    logger.info(f"[*] Average Time Per Post:   {average_duration_per_post:.2f} seconds")
    logger.info("="*50)

if __name__ == "__main__":
    main()