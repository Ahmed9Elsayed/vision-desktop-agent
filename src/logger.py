# src/logger.py
import logging
import sys
import os
from .config import PROJECT_ROOT

def setup_logger():
    """
    Configures a dual-pipeline logging system.
    Outputs to both the live console and a persistent log file.
    """
    # 1. Ensure the logs directory exists
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "automation.log"

    # 2. Create the main logger object
    logger = logging.getLogger("TJM_Agent")
    logger.setLevel(logging.DEBUG) 

    # Prevent duplicate logs if setup_logger is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # 3. Define the formats
    # File gets exact timestamps for debugging (e.g., 2026-05-21 14:30:05 - INFO - [*] Starting...)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # Console keeps it clean for your live interview demo (e.g., [*] Starting...)
    console_formatter = logging.Formatter('%(message)s')

    # 4. Setup File Handler (writes to automation.log)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # 5. Setup Console Handler (writes to VS Code terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # 6. Attach handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Export a globally ready instance
logger = setup_logger()