import json
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .config import DRIVER_PATH
from .dummy_data import DUMMY_POSTS
from src.logger import logger

def fetch_posts_selenium(limit=10):
    """
    Fetches real-time blog data via Edge Headless driver. 
    Gracefully degrades to high-fidelity dummy data if driver or network faults trigger.
    """
    logger.info("[*] Contacting JSONPlaceholder API endpoint via Selenium Edge...")
    
    # Pre-flight guard check for the driver file binary path
    if not os.path.exists(DRIVER_PATH):
        logger.info(f"[!] Warning: msedgedriver.exe missing at path: {DRIVER_PATH}")
        logger.info("[➔] Activating Graceful Degradation: Deploying local dummy dataset...")
        return DUMMY_POSTS[:limit]
    
    options = Options()
    options.add_argument('--headless=new')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # 1. Initialize to None out here to safeguard the finally block
    driver = None 
    
    try:
        service = Service(executable_path=DRIVER_PATH, log_path='NUL')
        driver = webdriver.Edge(service=service, options=options)
        
        driver.get("https://jsonplaceholder.typicode.com/posts")
        wait = WebDriverWait(driver, 8)  # 8-second timeout guard line
        body = wait.until(EC.presence_of_element_located((By.TAG_NAME, "pre")))
        
        data = json.loads(body.text)
        logger.info(f"[+] Successfully pulled {len(data[:limit])} live records from endpoint.")
        return data[:limit]
        
    except Exception as e:
        logger.info(f"[!] Selenium API Runtime Exception: {e}")
        logger.info("[➔] Activating Graceful Degradation: Deploying local dummy dataset safely...")
        return DUMMY_POSTS[:limit]
        
    # 2. Add the finally block here to guarantee cleanup
    finally:
        if driver:
            logger.info("[*] Closing Edge WebDriver background processes cleanly...")
            driver.quit()